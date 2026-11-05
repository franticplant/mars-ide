"""Chromium resource use: static build vs server-mode page vs blank page."""
import subprocess, time, os, sys
from playwright.sync_api import sync_playwright
def chrome_procs():
    out = {}
    for pid in os.listdir("/proc"):
        if not pid.isdigit(): continue
        try:
            cmd = open(f"/proc/{pid}/cmdline").read()
            if "chromium" not in cmd: continue
            st = open(f"/proc/{pid}/stat").read().split()
            rss = int(open(f"/proc/{pid}/status").read().split("VmRSS:")[1].split()[0])
            out[pid] = (int(st[13]) + int(st[14]), rss)
        except Exception: pass
    return out
def measure(url, label, setup=None):
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        p = b.new_page(viewport={"width": 1300, "height": 820})
        sizes = []
        p.on("response", lambda r: sizes.append(int(r.headers.get("content-length") or 0)) if r.ok else None)
        p.goto(url)
        if setup: setup(p)
        p.wait_for_timeout(4000)
        a = chrome_procs(); t = time.time(); p.wait_for_timeout(10000); z = chrome_procs(); dt = time.time() - t
        hz = os.sysconf("SC_CLK_TCK")
        cpu = sum(z[k][0] - a[k][0] for k in z if k in a) / hz / dt * 100
        rss = sum(v[1] for v in z.values()) // 1024
        heap = p.evaluate("performance.memory ? Math.round(performance.memory.usedJSHeapSize/1048576) : -1")
        print(f"  {label:<26} idle CPU {cpu:5.1f}% of one core | Chromium total RSS {rss:4d} MB | page JS heap {heap} MB")
        b.close()
srv = subprocess.Popen(["java", "-jar", "/build/mars-engine.jar", "--no-auth", "--port", "8095", "--root", "/tmp", "--web", "/web"], stdout=subprocess.DEVNULL)
time.sleep(2)
ready = lambda p: p.wait_for_function("window.MarsIDE && MarsIDE.engine.connected", timeout=30000)
measure("about:blank", "blank page (baseline)")
measure("http://127.0.0.1:8095/", "server mode (:8080-style)", ready)
measure(os.environ["STATIC"], "static build (:8081)", ready)
srv.terminate()
