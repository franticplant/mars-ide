"""The static (server-less) build: TeaVM engine in a Web Worker, files in IndexedDB."""
import subprocess, time
from playwright.sync_api import sync_playwright
import os
BASE = os.environ.get("BASE", "http://127.0.0.1:8096/")
srv = subprocess.Popen(["python3", "-m", "http.server", "8096", "-d", "/static"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if "8096" in BASE else None
time.sleep(1)
errs, logs = [], []
LOOP = "        .text\nmain:   li $t0, 0\n        li $t1, 2000000\nloop:   addi $t0, $t0, 1\n        bne $t0, $t1, loop\n        li $v0, 1\n        move $a0, $t0\n        syscall\n        li $v0, 10\n        syscall\n"
DLG = "        .data\nq: .asciiz \"How many? \"\n        .text\nmain:   li $v0, 51\n        la $a0, q\n        syscall\n        li $v0, 1\n        syscall\n        li $v0, 10\n        syscall\n"
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
    ctx = b.new_context(viewport={"width": 1300, "height": 820})
    p = ctx.new_page()
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.on("console", lambda m: logs.append(m.text) if m.type == "error" else None)
    t0 = time.time()
    p.goto(BASE); p.wait_for_selector(".ftab", timeout=30000)
    p.wait_for_function("window.MarsIDE && MarsIDE.engine.connected", timeout=30000)
    print(f"engine ready in {time.time() - t0:.1f}s; mnemonics: {p.evaluate('MIPS.ISA.names.length')}")
    print("files:", p.evaluate("MarsIDE.R.tree.map(n => n.path)"))
    p.keyboard.press("F3"); p.wait_for_timeout(1500)
    print("assembled:", p.evaluate("MarsIDE.R.assembled"), "| rows:", p.evaluate("MarsIDE.R.rows.length"))
    for _ in range(5): p.keyboard.press("F7"); p.wait_for_timeout(250)
    print("after 5 steps pc:", p.evaluate("MIPS.hex(MarsIDE.R.state.pc)"), "v0:", p.evaluate("MarsIDE.R.state.gpr[2]"))
    p.keyboard.press("F8"); p.wait_for_timeout(400)
    print("after back pc:", p.evaluate("MIPS.hex(MarsIDE.R.state.pc)"))
    p.keyboard.press("F5"); p.wait_for_selector("#inrow.wanted", timeout=10000)
    p.fill("#stdin", "12"); p.press("#stdin", "Enter"); p.wait_for_timeout(1500)
    print("output:", repr(p.inner_text("#out")[-60:]))
    # new file via engine fs (IndexedDB), assemble, run a 6M-instruction loop for speed
    p.evaluate(f"MarsIDE.engine.call('fs_write', {{path: 'loop.asm', text: {LOOP!r}}})")
    p.evaluate("MarsIDE.engine.call('fs_list').then(() => 0)"); p.wait_for_timeout(300)
    p.evaluate("document.querySelector('#btn-refresh').click()"); p.wait_for_timeout(300)
    p.evaluate("(async () => { const r = await MarsIDE.engine.call('fs_list'); })()")
    p.evaluate("MarsIDE.engine.call('fs_read', {path:'loop.asm'})")
    p.evaluate("window.__open = () => {}")
    p.click(".tab[data-v=edit]")
    p.evaluate("""(async () => { const e = MarsIDE; await e.engine.call('fs_list'); })()""")
    p.keyboard.press("Control+b"); p.wait_for_timeout(300)
    p.click(".node[data-p='loop.asm']"); p.wait_for_timeout(500)
    p.keyboard.press("F3"); p.wait_for_timeout(1200)
    t1 = time.time(); p.keyboard.press("F5")
    p.wait_for_function("MarsIDE.R.finished", timeout=120000)
    dt = time.time() - t1
    cnt = p.evaluate("MarsIDE.R.state.count")
    print(f"loop: {cnt} instructions in {dt:.1f}s = {cnt / dt / 1e6:.2f} M instr/s; output tail:", repr(p.inner_text('#out')[-30:]))
    # pause works mid-run
    p.keyboard.press("F12"); p.wait_for_timeout(500); p.keyboard.press("F5"); p.wait_for_timeout(300); p.keyboard.press("F9"); p.wait_for_timeout(800)
    print("paused mid-run:", p.evaluate("!MarsIDE.R.running && !MarsIDE.R.finished"), "count:", p.evaluate("MarsIDE.R.state.count"))
    # dialog syscall
    p.evaluate(f"MarsIDE.engine.call('fs_write', {{path: 'dlg.asm', text: {DLG!r}}})"); p.wait_for_timeout(200)
    p.click("#btn-refresh"); p.wait_for_timeout(300); p.click(".node[data-p='dlg.asm']"); p.wait_for_timeout(400)
    p.keyboard.press("F3"); p.wait_for_timeout(1000); p.keyboard.press("F5")
    p.wait_for_selector(".modal input.text", timeout=10000); p.fill(".modal input.text", "77"); p.keyboard.press("Enter"); p.wait_for_timeout(1200)
    print("dialog → output:", repr(p.inner_text("#out")[-20:]))
    p.screenshot(path="/shots/static-desktop.png")
    # persistence across reload (IndexedDB)
    p.reload(); p.wait_for_function("window.MarsIDE && MarsIDE.engine.connected", timeout=30000); p.wait_for_timeout(800)
    print("after reload files:", p.evaluate("MarsIDE.R.tree.map(n => n.path)"))
    b.close()
srv and srv.terminate()
print("errors:", errs or "none", "| console errors:", logs[:5] or "none")
