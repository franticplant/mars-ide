#!/usr/bin/env bash
# Assemble the fully static MARS IDE (no server): web UI + TeaVM-compiled engine in a Web Worker,
# workspace in IndexedDB, offline-capable. Output: build/static/
set -euo pipefail
cd "$(dirname "$0")/../.."
source scripts/container-user.sh
bash scripts/build-web.sh
BACKEND=${STATIC_ENGINE:-js}
case "$BACKEND" in js|wasm) ;; *) echo "STATIC_ENGINE must be js or wasm" >&2; exit 1 ;; esac
if [ "${SKIP_TEAVM:-0}" != 1 ]; then
  if [ "$BACKEND" = wasm ]; then
    TARGET=WEBASSEMBLY_GC TEAVM_STAGE=build/wasm-stage TEAVM_OUT=build/wasm-trial bash engine/teavm/build-teavm.sh
  else bash engine/teavm/build-teavm.sh; fi
fi
podman_run -i -e STATIC_ENGINE="$BACKEND" -e STATIC_CSP="${STATIC_CSP:-0}" -e STATIC_OUT="${STATIC_OUT:-build/static}" -v "$PWD":/w:z -w /w "${PY_IMAGE:-docker.io/library/python:3.12-slim}" bash -se <<'SITE'
OUT=$STATIC_OUT
case "$OUT" in build/?*) ;; *) echo "STATIC_OUT must be beneath build/" >&2; exit 1 ;; esac
case "/$OUT/" in */../*|*/./*|*//*) echo "Invalid STATIC_OUT" >&2; exit 1 ;; esac
mkdir -p "$OUT"
find "$OUT" -mindepth 1 -delete
cp -r web/. "$OUT/"
rm -rf "$OUT/static"
mkdir -p "$OUT/engine"
if [ "$STATIC_ENGINE" = wasm ]; then
  cp build/wasm-trial/teavm/mars-engine.wasm build/wasm-trial/teavm/mars-engine.wasm-runtime.js "$OUT/engine/"
  cp web/static/worker-wasm.js "$OUT/engine/worker.js"
else
  cp engine/teavm/target/teavm/mars-engine.js "$OUT/engine/"
  cp web/static/worker.js "$OUT/engine/worker.js"
fi
cp web/static/idbfs.js "$OUT/js/idbfs.js"
python3 - "$OUT" <<'PY'
import json, sys, hashlib, os
from pathlib import Path
out = Path(sys.argv[1])
ex = [{"path": p.name, "text": p.read_text(encoding="utf-8")} for p in sorted(Path("examples").glob("*.asm"))]
(out / "js" / "examples.js").write_text("window.MARS_EXAMPLES = " + json.dumps(ex) + ";\n", encoding="utf-8")
# Static flags and service-worker registration live in an external bootstrap so
# the static shell needs no inline script and can use script-src 'self'.
idx = out / "index.html"
html = idx.read_text(encoding="utf-8")
html = html.replace('<script src="js/mips.js"></script>',
    '<script src="js/static-init.js"></script>\n<script src="js/idbfs.js"></script>\n<script src="js/examples.js"></script>\n<script src="js/mips.js"></script>')
html = html.replace('<script>if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});</script>\n', '')
# GitHub Pages cannot send response headers, so the Pages build carries the
# same policy in a meta CSP. Inline scripts are allowed only in this meta
# fallback because srcdoc previews inherit the parent policy and use a nonce
# renderer; the nginx deployment keeps the stricter header without unsafe-inline.
if os.environ.get("STATIC_CSP") == "1":
    csp = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
           "img-src 'self' data: blob:; connect-src 'self'; worker-src 'self'; "
           "object-src 'none'; base-uri 'none'; form-action 'none'")
    html = html.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta http-equiv="Content-Security-Policy" content="' + csp + '">', 1)
idx.write_text(html, encoding="utf-8")
boot = out / "js" / "static-init.js"
boot.write_text('window.MARS_STATIC = true; window.MARS_BACKEND = "' + os.environ["STATIC_ENGINE"] + '";\n', encoding="utf-8")
# offline cache: every file, versioned by content. static-init is excluded from
# the digest because it contains the digest itself; it changes only with the build.
# social.png is only for link previews (og:image), not needed offline.
files = sorted(f for f in (str(p.relative_to(out)).replace(os.sep, "/") for p in out.rglob("*") if p.is_file()) if f != "social.png")
ver = hashlib.sha256(b"".join((out / f).read_bytes() for f in files if f != "js/static-init.js")).hexdigest()[:12]
boot.write_text('window.MARS_STATIC = true; window.MARS_BACKEND = "' + os.environ["STATIC_ENGINE"] + '"; window.MARS_BUILD = "' + ver + '";\n'
    'if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});\n', encoding="utf-8")
sw = f"""/* offline cache for the static MARS IDE — generated */
const PREFIX = "mars-ide:" + self.registration.scope + ":";
const CACHE = PREFIX + "{ver}";
const FILES = {json.dumps(["./"] + files)};
self.addEventListener("install", e => e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES))));
self.addEventListener("activate", e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith(PREFIX) && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", e => {{
  if (e.request.method !== "GET" || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(caches.open(CACHE).then(c => c.match(e.request, {{ ignoreSearch: true }})).then(r => r || fetch(e.request)));
}});
"""
(out / "sw.js").write_text(sw, encoding="utf-8")
print(f"static: {len(files)} files, cache {ver}")
PY
du -sh "$OUT" | cut -f1 | xargs -I{} echo "static site: {} in $OUT"
SITE
