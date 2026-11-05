#!/usr/bin/env bash
# Assemble the fully static MARS IDE (no server): web UI + TeaVM-compiled engine in a Web Worker,
# workspace in IndexedDB, offline-capable. Output: build/static/
set -euo pipefail
cd "$(dirname "$0")/../.."
[ "${SKIP_TEAVM:-0}" = 1 ] || bash engine/teavm/build-teavm.sh
OUT=build/static
mkdir -p "$OUT"
find "$OUT" -mindepth 1 -delete
cp -r web/. "$OUT/"
rm -rf "$OUT/static"
mkdir -p "$OUT/engine"
cp engine/teavm/target/teavm/mars-engine.js "$OUT/engine/"
cp web/static/worker.js "$OUT/engine/worker.js"
cp web/static/idbfs.js "$OUT/js/idbfs.js"
python3 - "$OUT" <<'PY'
import json, sys, hashlib, os
from pathlib import Path
out = Path(sys.argv[1])
ex = [{"path": p.name, "text": p.read_text(encoding="utf-8")} for p in sorted(Path("examples").glob("*.asm"))]
(out / "js" / "examples.js").write_text("window.MARS_EXAMPLES = " + json.dumps(ex) + ";\n", encoding="utf-8")
# static flag + local file system, before the app scripts
idx = out / "index.html"
html = idx.read_text(encoding="utf-8")
html = html.replace('<script src="js/mips.js"></script>',
    '<script>window.MARS_STATIC = true;</script>\n<script src="js/idbfs.js"></script>\n<script src="js/examples.js"></script>\n<script src="js/mips.js"></script>')
html = html.replace("</body>", '<script>if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});</script>\n</body>')
idx.write_text(html, encoding="utf-8")
# offline cache: every file, versioned by content
files = sorted(str(p.relative_to(out)).replace(os.sep, "/") for p in out.rglob("*") if p.is_file())
ver = hashlib.sha256(b"".join((out / f).read_bytes() for f in files)).hexdigest()[:12]
sw = f"""/* offline cache for the static MARS IDE — generated */
const CACHE = "mars-ide-{ver}";
const FILES = {json.dumps(["./"] + files)};
self.addEventListener("install", e => e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting())));
self.addEventListener("activate", e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", e => {{
  if (e.request.method !== "GET" || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(caches.match(e.request, {{ ignoreSearch: true }}).then(r => r || fetch(e.request)));
}});
"""
(out / "sw.js").write_text(sw, encoding="utf-8")
print(f"static: {len(files)} files, cache {ver}")
PY
du -sh "$OUT" | cut -f1 | xargs -I{} echo "static site: {} in $OUT"
