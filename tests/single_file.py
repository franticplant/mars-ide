"""The single-file build (build/single/mars-ide.html) opened from disk via file://.

Checks: the engine starts from the embedded worker, a program assembles, runs and prints, files
persist across a reload, and the embedded Markdown renderer and reference PDF unpack.
BROWSER=chromium (default) | firefox | webkit; SINGLE=path to the HTML file.
"""
import os
from playwright.sync_api import sync_playwright

SINGLE = os.environ.get("SINGLE", "/single/mars-ide.html")
BROWSER = os.environ.get("BROWSER", "chromium")
PROG = ('        .data\nmsg:    .asciiz "single file ok "\n        .text\nmain:   li $v0, 4\n        la $a0, msg\n'
        '        syscall\n        li $v0, 1\n        li $a0, 42\n        syscall\n        li $v0, 10\n        syscall\n')
errs = []
with sync_playwright() as pw:
    kind = getattr(pw, BROWSER)
    b = kind.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"]) if BROWSER == "chromium" else kind.launch()
    ctx = b.new_context(viewport={"width": 1300, "height": 820})
    p = ctx.new_page()
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.goto("file://" + SINGLE)
    p.wait_for_function("window.MarsIDE && MarsIDE.engine.connected", timeout=60000)
    p.evaluate(f"MarsIDE.engine.call('fs_write', {{path: 'single.asm', text: {PROG!r}}})")
    if not p.is_visible("#btn-refresh"): p.keyboard.press("Control+b"); p.wait_for_timeout(300)
    p.click("#btn-refresh"); p.wait_for_timeout(400)
    p.click(".node[data-p='single.asm']"); p.wait_for_timeout(500)
    p.keyboard.press("F3"); p.wait_for_timeout(1500)
    assert p.evaluate("MarsIDE.R.assembled"), "did not assemble"
    p.keyboard.press("F5"); p.wait_for_function("MarsIDE.R.finished", timeout=30000)
    out = p.inner_text("#out")
    assert "single file ok 42" in out, out[-200:]
    md = p.evaluate("window.MARS_MARKDOWN().then(t => t.length)")
    assert md > 1_000_000, md
    pdf = p.evaluate("fetch(window.MARS_PDF_URL).then(r => r.arrayBuffer()).then(b => String.fromCharCode(...new Uint8Array(b, 0, 4)))")
    assert pdf == "%PDF", pdf
    assert p.evaluate("!navigator.serviceWorker || !navigator.serviceWorker.controller")
    p.reload(); p.wait_for_function("window.MarsIDE && MarsIDE.engine.connected", timeout=60000); p.wait_for_timeout(800)
    files = p.evaluate("MarsIDE.R.tree.map(n => n.path)")
    assert "single.asm" in files, f"workspace not kept across reload: {files}"
    b.close()
assert not errs, errs
print(f"ok   single file ({BROWSER}): runs, persists across reload, Markdown and PDF unpack")
