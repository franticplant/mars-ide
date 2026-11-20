"""Pause and Stop take effect promptly, also while a program floods the console.

Regression: output was appended to one huge text flow, so a printing loop kept the page busy
for seconds and Stop/Pause reached the engine late; the browser engine also paid two event-loop
turns per run slice. Budgets are generous for slow CI machines (typical: well under 100 ms).
"""
import os, subprocess, time
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8096/")
srv = subprocess.Popen(["python3", "-m", "http.server", "8096", "-d", "/static"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if "BASE" not in os.environ else None
time.sleep(1)
PROGS = {
    "loop": ".text\nmain: li $t0, 0\n li $t1, 2000000000\nloop: addi $t0, $t0, 1\n bne $t0, $t1, loop\n li $v0, 10\n syscall\n",
    "line": ".text\nmain: li $t0, 0\nloop: li $v0, 1\n move $a0, $t0\n syscall\n addi $t0, $t0, 1\n b loop\n",
    "lines": ".text\nmain: li $t0, 0\nloop: li $v0, 1\n move $a0, $t0\n syscall\n li $v0, 11\n li $a0, 10\n syscall\n addi $t0, $t0, 1\n b loop\n",
}
BUDGET_MS = 1000
errors, worst = [], 0
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        p = b.new_page(viewport={"width": 1300, "height": 820})
        p.on("pageerror", lambda e: errors.append(str(e)))
        p.goto(BASE); p.wait_for_function("window.MarsIDE && MarsIDE.engine.connected", timeout=60000)
        p.evaluate("""() => { window.T = {}; const w = MarsIDE.engine.worker, prev = w.onmessage;
          w.onmessage = (e) => { if (String(e.data).includes('"ev":"stopped"')) T.stopped = performance.now(); return prev(e); }; }""")
        for name, prog in PROGS.items():
            p.evaluate("([n, t]) => MarsIDE.engine.call('fs_write', {path: n + '.asm', text: t})", [name, prog])
            if not p.is_visible("#btn-refresh"): p.keyboard.press("Control+b"); p.wait_for_timeout(300)
            p.click("#btn-refresh"); p.wait_for_timeout(300); p.click(f".node[data-p='{name}.asm']"); p.wait_for_timeout(400)
            for action, key in (("pause", "F9"), ("stop", "Shift+F11")):
                p.keyboard.press("Shift+F12"); p.wait_for_timeout(300)
                p.keyboard.press("F3"); p.wait_for_timeout(1000)
                p.keyboard.press("F5"); p.wait_for_timeout(2500)
                assert p.evaluate("MarsIDE.R.running"), f"{name}: not running"
                p.evaluate("T = { t0: performance.now() }")
                p.keyboard.press(key)
                p.wait_for_function("!MarsIDE.R.running", timeout=30000, polling=5)
                ms = p.evaluate("T.stopped - T.t0")
                worst = max(worst, ms)
                print(f"{name:5} {action:5}: engine stopped {ms:5.0f} ms after the key")
                assert ms < BUDGET_MS, f"{name} {action}: {ms:.0f} ms"
                if name == "lines" and action == "stop":   # nothing lost: consecutive numbers up to $t0, then the marker
                    p.wait_for_timeout(500)
                    text, t0 = p.inner_text("#out"), p.evaluate("MarsIDE.R.state.gpr[8]")
                    assert text.rstrip().endswith("-- program stopped --"), repr(text[-80:])
                    nums = [int(l) for l in text.splitlines() if l.strip().isdigit()]
                    assert nums and all(c == a + 1 for a, c in zip(nums, nums[1:])), "gap in console output"
                    assert nums[-1] in (t0, t0 - 1), (nums[-1], t0)
                    assert p.evaluate("(o => o.scrollTop + o.clientHeight >= o.scrollHeight - 4)(document.querySelector('#out'))"), "console not at bottom"
        b.close()
finally:
    if srv: srv.terminate()
assert not errors, errors
print(f"ok   stop latency: worst {worst:.0f} ms (budget {BUDGET_MS} ms)")
