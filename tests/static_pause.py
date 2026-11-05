import os, time
from playwright.sync_api import sync_playwright
BASE = os.environ.get("BASE")
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
    p = b.new_page()
    p.goto(BASE); p.wait_for_function("window.MarsIDE && MarsIDE.engine.connected", timeout=30000)
    p.wait_for_timeout(800)
    p.evaluate("MarsIDE.engine.call('fs_write', {path:'spin.asm', text:'        .text\\nmain: addi $t0, $t0, 1\\n      j main\\n'})")
    p.keyboard.press("Control+b"); p.click("#btn-refresh"); p.wait_for_timeout(300); p.click(".node[data-p='spin.asm']"); p.wait_for_timeout(300)
    p.keyboard.press("F3"); p.wait_for_timeout(800)
    for trial in range(3):
        p.keyboard.press("F5"); p.wait_for_function("MarsIDE.R.running", timeout=5000); p.wait_for_timeout(400 + 300 * trial)
        t = time.time(); p.keyboard.press("F9")
        p.wait_for_function("!MarsIDE.R.running", timeout=10000)
        c1 = p.evaluate("MarsIDE.R.state.count"); p.wait_for_timeout(500); c2 = p.evaluate("MarsIDE.R.state.count")
        print(f"trial {trial}: paused after {(time.time() - t) * 1000:.0f} ms at {c1} instructions; still paused: {c1 == c2}; $t0 = {p.evaluate('MarsIDE.R.state.gpr[8]')}")
    b.close()
