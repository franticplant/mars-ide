"""Run bar: a held press on Stop always works, and buttons/pill never move or resize.

Regressions: the run bar was rebuilt several times a second while running, replacing the button
under the pointer between mouse-down and mouse-up (lost clicks); labels and the status pill
changed width between states, shifting the buttons (worst on phones).
"""
import os, subprocess, time
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8096/")
srv = subprocess.Popen(["python3", "-m", "http.server", "8096", "-d", "/static"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if "BASE" not in os.environ else None
time.sleep(1)
LOOP = ".text\nmain: li $t0, 0\n li $t1, 2000000000\nloop: addi $t0, $t0, 1\n bne $t0, $t1, loop\n li $v0, 10\n syscall\n"
GEOM = ("[...document.querySelectorAll('#runbar > *, #pill')].filter(e => e.offsetParent).map(e => {"
        " const r = e.getBoundingClientRect(); return (e.dataset.slot || e.id) + ':' + Math.round(r.x) + '+' + Math.round(r.width); }).join(' ')")
errors = []
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        for name, opts in (("desktop", dict(viewport={"width": 1300, "height": 820})),
                           ("phone", dict(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True))):
            p = b.new_context(**opts).new_page()
            p.on("pageerror", lambda e: errors.append(str(e)))
            p.goto(BASE); p.wait_for_function("window.MarsIDE && MarsIDE.engine.connected && MarsIDE.S.current", timeout=60000)
            p.evaluate("t => MarsIDE.engine.call('fs_write', {path: 'runbar.asm', text: t})", LOOP)
            p.evaluate("document.querySelector('#btn-refresh').click()"); p.wait_for_timeout(300)
            p.evaluate("document.querySelector(\".node[data-p='runbar.asm']\").click()")
            p.wait_for_function("MarsIDE.S.current === 'runbar.asm'")
            geom = {}
            p.evaluate("MarsIDE.ACT.assemble()"); p.wait_for_function("MarsIDE.R.assembled"); geom["ready"] = p.evaluate(GEOM)
            p.evaluate("MarsIDE.ACT.run()"); p.wait_for_timeout(1000); geom["running"] = p.evaluate(GEOM)
            p.evaluate("MarsIDE.ACT.pause()"); p.wait_for_function("!MarsIDE.R.running"); geom["paused"] = p.evaluate(GEOM)
            assert len(set(geom.values())) == 1, f"{name}: run bar moved or resized: {geom}"
            if name == "desktop":
                for i in range(4):   # human-length presses while the step counter keeps refreshing
                    p.evaluate("MarsIDE.ACT.run()"); p.wait_for_timeout(1200)
                    box = p.locator("#runbar [data-slot=halt]").bounding_box()
                    p.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                    p.mouse.down(); p.wait_for_timeout(300); p.mouse.up(); p.wait_for_timeout(500)
                    assert not p.evaluate("MarsIDE.R.running"), f"held press {i + 1} on Stop was lost"
                    p.evaluate("MarsIDE.ACT.reset()"); p.wait_for_timeout(300)
            print(f"{name}: geometry stable across ready/running/paused")
        b.close()
finally:
    if srv: srv.terminate()
assert not errors, errors
print("ok   run bar: held presses on Stop work; buttons and pill keep their size")
