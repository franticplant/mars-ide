import json, subprocess, time, os, sys
B = "/bench"
def oracle(prog, ic=False):
    t = time.time()
    p = subprocess.run(["java", "-Djava.awt.headless=true", "-jar", "/v/Mars4_5.jar", "nc", *(["ic"] if ic else []), prog], cwd=B, capture_output=True, text=True)
    return time.time() - t, p.stdout.split()[0] if p.stdout.split() else "?"
def desktop(prog):
    t0 = time.time()
    p = subprocess.Popen(["java", "-XX:+UseSerialGC", "-Xmx256m", "-cp", "/b/mars-engine.jar", "marsx.StdioMain", B], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    rd = lambda: json.loads(p.stdout.readline())
    while rd().get("ev") != "ready": pass
    startup = time.time() - t0
    def call(i, cmd, **a):
        p.stdin.write(json.dumps({"id": i, "cmd": cmd, **a}) + "\n"); p.stdin.flush()
        while True:
            m = rd()
            if m.get("id") == i: return m
    call(1, "assemble", files=[prog])
    runs = []
    for k in range(3):
        call(10 + k, "reset")
        t = time.time(); call(20 + k, "run")
        while True:
            m = rd()
            if m.get("ev") == "stopped": break
        runs.append((time.time() - t, m["state"]["count"]))
    rss = int(open(f"/proc/{p.pid}/status").read().split("VmHWM:")[1].split()[0]) // 1024
    p.stdin.close(); p.wait()
    return startup, runs, rss
print("== original MARS 4.5 (command line; time includes JVM start + assemble)")
for prog in ("tiny.asm", "loop.asm", "fib.asm"):
    ts = [oracle(prog)[0] for _ in range(2)]
    print(f"  {prog:<9} {min(ts):6.2f} s")
for prog in ("loop.asm", "fib.asm"):
    dt, cnt = oracle(prog, ic=True)
    print(f"  {prog:<9} with instruction count: {dt:6.2f} s")
print("== our engine on the JVM (the :8080 server / TUI path)")
for prog in ("loop.asm", "fib.asm"):
    st, runs, rss = desktop(prog)
    best = min(runs)
    print(f"  {prog:<9} startup {st:4.2f} s | run {best[0]:5.2f} s for {best[1]:>9} instr = {best[1]/best[0]/1e6:5.1f} M/s (runs: {', '.join(f'{r[0]:.2f}' for r in runs)}) | peak RSS {rss} MB")
