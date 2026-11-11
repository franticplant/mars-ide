"""Bundle the static site (build/static) into one HTML file that works when opened from disk.

Usage: python3 web/static/build-single.py build/static build/single/mars-ide.html

A page opened from file:// cannot load workers or fetch sibling files, so every piece is
embedded: the stylesheet inline, every script and the engine gzip+base64 encoded (base64 can
never contain "</script>"). A small loader unpacks them with DecompressionStream, starts the
engine worker from a Blob URL, and runs the app scripts in their original order. The Markdown
renderer (large) is unpacked only when a preview first opens. No service worker: the file is
already offline. The workspace lives in the browser's IndexedDB for this file.
"""
import base64, gzip, json, re, sys
from pathlib import Path

site, out = Path(sys.argv[1]), Path(sys.argv[2])
html = (site / "index.html").read_text(encoding="utf-8")

def packed(path):
    return base64.b64encode(gzip.compress((site / path).read_bytes(), 9, mtime=0)).decode("ascii")

scripts = re.findall(r'<script src="([^"]+)"></script>\n?', html)
assert scripts and scripts[0] == "js/static-init.js", scripts
html = re.sub(r'<script src="[^"]+"></script>\n?', "", html)
# no CSP meta in this build: the loader and app run as inline scripts by design
assert 'http-equiv="Content-Security-Policy"' not in html, "build the site without STATIC_CSP"
html = re.sub(r'<link rel="manifest"[^>]*>\n?', "", html)
icon = base64.b64encode((site / "icon.svg").read_bytes()).decode("ascii")
html = html.replace('href="icon.svg"', f'href="data:image/svg+xml;base64,{icon}"')
css = (site / "css/app.css").read_text(encoding="utf-8")
assert "url(" not in css.replace("url(data:", ""), "app.css references files; inline them first"
html = html.replace('<link rel="stylesheet" href="css/app.css">', "<style>\n" + css.replace("</style", "<\\/style") + "\n</style>")

build = re.search(r'MARS_BUILD = "([^"]+)"', (site / "js/static-init.js").read_text()).group(1)
worker = (site / "engine/worker.js").read_text(encoding="utf-8")
assert 'importScripts("mars-engine.js");' in worker
assets = {
    "engine": packed("engine/mars-engine.js"),
    "worker": base64.b64encode(gzip.compress(worker.replace('importScripts("mars-engine.js");', "").encode(), 9, mtime=0)).decode("ascii"),
    "markdown": packed("vendor/markdown.js"),
    "pdf": packed("ref/MIPS_Reference.pdf"),
    "scripts": [[name, packed(name)] for name in scripts[1:]],
}
loader = """<script>
window.MARS_STATIC = true; window.MARS_BACKEND = "js"; window.MARS_SINGLE = true; window.MARS_BUILD = %s;
(async () => {
  const A = %s;
  const bytes = async (b64) => {
    const raw = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
    return new Uint8Array(await new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer());
  };
  const text = async (b64) => new TextDecoder().decode(await bytes(b64));
  try {
    if (typeof DecompressionStream !== "function") throw new Error("This browser is too old for the single-file MARS IDE; use a current Chrome, Edge, Firefox or Safari, or the website.");
    const [engine, worker] = await Promise.all([text(A.engine), text(A.worker)]);
    window.MARS_WORKER_URL = URL.createObjectURL(new Blob([engine, "\\n", worker], { type: "text/javascript" }));
    window.MARS_PDF_URL = URL.createObjectURL(new Blob([await bytes(A.pdf)], { type: "application/pdf" }));
    let md = null;
    window.MARS_MARKDOWN = () => md || (md = text(A.markdown));
    for (const [name, b64] of A.scripts) {
      const s = document.createElement("script");
      s.textContent = (await text(b64)) + "\\n//# sourceURL=" + name;
      document.body.append(s);
    }
  } catch (e) {
    console.error(e);
    document.body.insertAdjacentHTML("afterbegin", '<div style="position:fixed;inset:0;z-index:99;display:grid;place-items:center;padding:24px;background:#000;color:#eee;font:16px sans-serif;text-align:center"></div>');
    document.body.firstElementChild.textContent = "MARS IDE could not start: " + (e && e.message || e);
  }
})();
</script>
""" % (json.dumps(build), json.dumps(assets, separators=(",", ":")))
assert "</script" not in loader[8:-10]
assert html.count("</body>") == 1
html = html.replace("</body>", loader + "</body>")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(html, encoding="utf-8")
print(f"single file: {out} ({out.stat().st_size / 1e6:.1f} MB, {len(scripts) - 1} scripts, build {build})")
