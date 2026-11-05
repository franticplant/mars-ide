#!/usr/bin/env python3
"""Differential conformance: original MARS 4.5 (oracle) vs our desktop engine vs our browser engine.

Every program in progs/ (except inc_* helpers) is run by
  1. the unmodified Mars4_5.jar command line            (reference)
  2. marsx.StdioMain from build/mars-engine.jar          (server / TUI / desktop builds)
  3. the TeaVM-compiled engine in Node                   (static browser build)
and program output, runtime errors (line + message), instruction count and all 31 registers must be identical.
Engine-only checks (step/back-step, dialogs) compare desktop vs browser.
"""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROGS = HERE / "progs"
MARS = os.environ.get("MARS_ORACLE", "/v/Mars4_5.jar")
ENGINE_JAR = os.environ.get("ENGINE_JAR", "/b/mars-engine.jar")
ENGINE_JS = os.environ.get("ENGINE_JS", "/e/mars-engine.js")
REGS = ["$at", "$v0", "$v1", "$a0", "$a1", "$a2", "$a3", "$t0", "$t1", "$t2", "$t3", "$t4", "$t5", "$t6", "$t7",
        "$s0", "$s1", "$s2", "$s3", "$s4", "$s5", "$s6", "$s7", "$t8", "$t9", "$k0", "$k1", "$gp", "$sp", "$fp", "$ra"]
FREGS = [f"$f{i}" for i in range(32)]
DATA, HEAP = 0x10010000, 0x10040000
OPT_MAP = {"db": "delayed_branching", "smc": "self_modifying", "sm": "start_at_main", "we": "warnings_are_errors"}


def options(src: str) -> list[str]:
    m = re.search(r"^#\s*@mars:\s*(.+)$", src, re.M)
    return m.group(1).split() if m else []


def workdir(tag: str) -> Path:
    d = Path(tempfile.mkdtemp(prefix=f"conf-{tag}-"))
    for f in PROGS.iterdir():
        if f.suffix == ".asm":
            shutil.copy(f, d / f.name)
    return d


# ------------------------------------------------------------------ 1. oracle
def run_oracle(name: str, opts: list[str], inputs: list[str]) -> dict:
    d = workdir("oracle")
    cmd = ["java", "-Djava.awt.headless=true", "-jar", MARS, "nc", "ic", *opts, *REGS, *FREGS, "dump", ".data", "HexText", "data.dump", name]
    p = subprocess.run(cmd, cwd=d, input="".join(i + "\n" for i in inputs), capture_output=True, text=True, timeout=120)
    text = p.stdout.replace("This segment has not been written to, there is nothing to dump.\n", "")
    m = re.search(r"\n?(\d+)\n\n((?:\$\w+\t0x[0-9a-f]{8}(?:\t0x[0-9a-f]{16})?\n)+)\s*$", text)
    if not m:
        return {"crash": "unparsed oracle output: " + text[-300:]}
    body = text[:m.start()]
    allregs = {k: int(v, 16) for k, v in re.findall(r"(\$\w+)\t0x([0-9a-f]{8})", m.group(2))}
    regs = {k: allregs[k] for k in REGS if k in allregs}
    fregs = [allregs.get(f, 0) for f in FREGS]
    dump = [int(x, 16) for x in (d / "data.dump").read_text().split()] if (d / "data.dump").exists() else []
    err = None
    em = re.search(r"Error in \S+ line (\d+): (.*?)\n\nProcessing terminated due to errors\.\n?", body, re.S)
    if em:
        err = {"line": int(em.group(1)), "message": em.group(2).strip()}
        body = body[:em.start()]
    return {"out": body, "count": int(m.group(1)), "regs": regs, "error": err, "fpr": fregs, "data": dump}


# ------------------------------------------------------------------ 2. desktop engine (protocol over stdio)
class Desktop:
    def __init__(self, root: Path):
        self.p = subprocess.Popen(["java", "-cp", ENGINE_JAR, "marsx.StdioMain", str(root)], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, text=True, bufsize=1)
        self.seq = 0
        self.events = []
        while self.read().get("ev") != "ready":
            pass

    def read(self) -> dict:
        line = self.p.stdout.readline()
        if not line:
            raise RuntimeError("engine exited")
        return json.loads(line)

    def call(self, cmd, inputs=None, **args):
        self.seq += 1
        rid = self.seq
        self.p.stdin.write(json.dumps({"id": rid, "cmd": cmd, **args}) + "\n")
        self.p.stdin.flush()
        while True:
            m = self.read()
            if m.get("id") == rid:
                return m
            self.handle(m, inputs)

    def handle(self, m, inputs):
        ev = m.get("ev")
        if ev:
            self.events.append(m)
        if ev == "input_request":
            self.post("input", text=(inputs.pop(0) if inputs else "") + "\n")
        elif ev == "dialog":
            self.post("dialog_reply", token=m["token"], value=inputs.pop(0) if inputs else None)

    def post(self, cmd, **args):
        self.seq += 1
        self.p.stdin.write(json.dumps({"id": f"x{self.seq}", "cmd": cmd, **args}) + "\n")
        self.p.stdin.flush()

    def close(self):
        self.p.stdin.close()
        self.p.wait(5)


def run_desktop(job: dict) -> dict:
    d = workdir("desktop")
    e = Desktop(d)
    try:
        inputs = list(job.get("inputs", []))
        asm = e.call("assemble", files=[job["main"]], main=job["main"], settings=job.get("settings", {}))
        if not asm.get("success"):
            return {"assemble_error": asm.get("messages")}
        if job.get("mode") == "pausing":
            reasons = []
            for _ in range(3):
                e.call("run")
                import time; time.sleep(0.3)
                e.call("pause")
                while True:
                    m = e.read(); e.handle(m, inputs)
                    if m.get("ev") == "stopped": break
                reasons.append(m["reason"])
            st = e.call("state")["state"]
            return {"reasons": reasons, "finished": st["finished"], "running": st["running"], "t0_positive": st["gpr"][8] > 0}
        if job.get("mode") == "steps":
            st, reason, errors = asm["state"], None, None
            for _ in range(100000):
                r = e.call("step", inputs)
                if not r.get("ok", True):
                    return {"crash": "step failed: " + str(r.get("error"))}
                st = r["state"]
                if r.get("finished"):
                    reason, errors = r.get("reason"), r.get("errors")
                    break
            for _ in range(job.get("stepBack", 0)):
                st = e.call("backstep")["state"]
            res = {"reason": reason, "errors": errors, "state": st}
        else:
            e.call("run", inputs)
            while True:
                m = e.read()
                e.handle(m, inputs)
                if m.get("ev") == "stopped":
                    break
            res = {"reason": m["reason"], "errors": m.get("errors"), "state": m["state"]}
        res["out"] = "".join(x["text"] for x in e.events if x.get("ev") == "out")
        st = res.get("state") or {}
        if st.get("gpr"):
            spb = ((st["gpr"][29] & 0xffffffff) & ~3) - 512
            res["mem"] = {"data": e.call("memory", addr=DATA, words=1024)["words"],
                          "heap": e.call("memory", addr=HEAP, words=256)["words"],
                          "stack": e.call("memory", addr=spb, words=256)["words"]}
        return res
    finally:
        e.close()


# ------------------------------------------------------------------ 3. browser engine (TeaVM build in Node)
def run_browser(job: dict) -> dict:
    d = workdir("browser")
    files = [{"path": f.name, "text": f.read_text()} for f in sorted(d.iterdir()) if f.suffix == ".asm"]
    jf = d / "job.json"
    jf.write_text(json.dumps(dict(job, files=files)))
    p = subprocess.run(["node", str(HERE / "teavm-run.js"), ENGINE_JS, str(jf)], capture_output=True, text=True, timeout=300)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        return {"crash": (p.stdout + p.stderr)[-400:]}


# ------------------------------------------------------------------ comparison
def norm_engine(r: dict) -> dict:
    if "crash" in r or "assemble_error" in r:
        return r
    st = r["state"]
    err = None
    if r.get("reason") == "error" and r.get("errors"):
        e0 = r["errors"][0]
        err = {"line": e0.get("line"), "message": str(e0.get("message", "")).strip()}
    regs = {REGS[i - 1]: st["gpr"][i] & 0xffffffff for i in range(1, 32)}
    u = lambda v: (v or 0) & 0xffffffff
    mem = {k: [u(w) for w in v] for k, v in (r.get("mem") or {}).items()}
    return {"out": r.get("out", ""), "count": st.get("count"), "regs": regs, "error": err,
            "fpr": [u(v) for v in st.get("fpr", [])], "data": mem.get("data", []),
            "full": {"pc": u(st.get("pc")), "hi": u(st.get("hi")), "lo": u(st.get("lo")), "flags": st.get("flags"),
                     "cop0": {c["num"]: u(c["value"]) for c in st.get("cop0", [])}, **{"mem_" + k: v for k, v in mem.items()}}}


def diff(a: dict, b: dict, la: str, lb: str) -> list[str]:
    if "crash" in a or "crash" in b or "assemble_error" in a or "assemble_error" in b:
        return [f"{la}: {a.get('crash') or a.get('assemble_error')}" if ("crash" in a or "assemble_error" in a) else "",
                f"{lb}: {b.get('crash') or b.get('assemble_error')}" if ("crash" in b or "assemble_error" in b) else ""]
    out = []
    if a["out"].rstrip("\n") != b["out"].rstrip("\n"):
        out.append(f"output differs:\n      {la}: {a['out']!r}\n      {lb}: {b['out']!r}")
    if a["error"] != b["error"]:
        out.append(f"error differs: {la}={a['error']} {lb}={b['error']}")
    if a["count"] != b["count"]:
        out.append(f"instruction count: {la}={a['count']} {lb}={b['count']}")
    fa, fb = a.get("fpr") or [], b.get("fpr") or []
    if fa and fb and fa != fb:
        badf = [i for i in range(32) if fa[i] != fb[i]]
        out.append("FP registers: " + ", ".join(f"$f{i} {la}={fa[i]:#010x} {lb}={fb[i]:#010x}" for i in badf[:6]))
    da, db = a.get("data") or [], b.get("data") or []
    n = min(len(da), len(db))
    if n and da[:n] != db[:n]:
        i = next(i for i in range(n) if da[i] != db[i])
        out.append(f".data memory differs first at {DATA + 4 * i:#010x}: {la}={da[i]:#010x} {lb}={db[i]:#010x}")
    elif (da or db) and not n:   # MARS dumps nothing for an untouched segment: the other side must be all zero
        other = da or db
        if any(other):
            i = next(i for i, w in enumerate(other) if w)
            out.append(f".data: one side is empty but the other has {other[i]:#010x} at {DATA + 4 * i:#010x}")
    if "full" in a and "full" in b and a["full"] != b["full"]:
        for k in a["full"]:
            if a["full"][k] != b["full"].get(k):
                out.append(f"state '{k}' differs: {la}={str(a['full'][k])[:80]} {lb}={str(b['full'].get(k))[:80]}")
    bad = [k for k in REGS if a["regs"].get(k) != b["regs"].get(k)]
    if bad:
        out.append("registers: " + ", ".join(f"{k} {la}={a['regs'].get(k, 0):#010x} {lb}={b['regs'].get(k, 0):#010x}" for k in bad[:6]))
    return [x for x in out if x]


def main() -> int:
    only = set(sys.argv[1:])
    progs = sorted(p for p in PROGS.glob("*.asm") if not p.name.startswith(("inc_", "zz_")) and (not only or p.stem in only))
    failures = 0
    print(f"{'program':<12} {'oracle':>10} {'desktop':>10} {'browser':>10}   result")
    for prog in progs:
        src = prog.read_text()
        opts = options(src)
        inputs = (PROGS / (prog.stem + ".in")).read_text().splitlines() if (PROGS / (prog.stem + ".in")).exists() else []
        job = {"main": prog.name, "inputs": inputs, "settings": {OPT_MAP[o]: True for o in opts if o in OPT_MAP}}
        o = run_oracle(prog.name, opts, inputs)
        d = norm_engine(run_desktop(job))
        b = norm_engine(run_browser(job))
        problems = [f"desktop vs MARS: {x}" for x in diff(o, d, "MARS", "desktop")] + \
                   [f"browser vs MARS: {x}" for x in diff(o, b, "MARS", "browser")] + \
                   [f"desktop vs browser (full state): {x}" for x in diff(d, b, "desktop", "browser")]
        if re.search(r"^#\s*@count:\s*quirk", src, re.M):     # documented MARS counting quirk: compare everything else
            problems = [p for p in problems if "instruction count" not in p]
            problems += [f"desktop vs browser: {x}" for x in diff(d, b, "desktop", "browser")]
        cnt = lambda r: str(r.get("count", "—"))
        print(f"{prog.stem:<12} {cnt(o):>10} {cnt(d):>10} {cnt(b):>10}   {'OK' if not problems else 'MISMATCH'}"
              + (f"  (error: {o['error']['message'][:50]})" if not problems and o.get('error') else ""))
        for pr in problems:
            print("    - " + pr)
        failures += bool(problems)

    # engine-only features: stepping + back-stepping, dialogs (the MARS command line cannot do these)
    print("\nengine-only parity (desktop vs browser):")
    extra = [
        ("step+back", {"main": "calls.asm", "mode": "steps", "stepBack": 25}),
        ("step io", {"main": "io.asm", "mode": "steps", "inputs": ["21", "hello world", "Z"]}),
    ]
    dlg = PROGS / "zz_dialog.asm"
    dlg.write_text("        .data\nq: .asciiz \"n? \"\nbuf: .space 16\n        .text\nmain: li $v0, 51\n la $a0, q\n syscall\n move $s0, $a0\n move $s1, $a1\n"
                   " li $v0, 54\n la $a0, q\n la $a1, buf\n li $a2, 16\n syscall\n move $s2, $a1\n li $v0, 50\n la $a0, q\n syscall\n move $s3, $a0\n"
                   " li $v0, 4\n la $a0, buf\n syscall\n li $v0, 10\n syscall\n")
    extra.append(("dialogs", {"main": "zz_dialog.asm", "inputs": ["123", "text", "1"]}))
    (PROGS / "zz_spin.asm").write_text("        .text\nmain:   addi $t0, $t0, 1\n        j main\n")
    try:
        pj = {"main": "zz_spin.asm", "mode": "pausing"}
        d, b = run_desktop(pj), run_browser(pj)
        want = {"reasons": ["paused"] * 3, "finished": False, "running": False, "t0_positive": True}
        ok = d == want and b == want
        print(f"  {'pause x3':<10} desktop {d.get('reasons')} / browser {b.get('reasons')}   {'OK' if ok else 'MISMATCH'}")
        if not ok:
            print(f"    - desktop: {d}\n    - browser: {b}")
        failures += not ok
        for label, job in extra:
            d = norm_engine(run_desktop(job))
            b = norm_engine(run_browser(job))
            problems = diff(d, b, "desktop", "browser")
            print(f"  {label:<10} count {d.get('count')!s:>8} / {b.get('count')!s:<8} {'OK' if not problems else 'MISMATCH'}")
            for pr in problems:
                print("    - " + pr)
            failures += bool(problems)
    finally:
        dlg.unlink()
        (PROGS / "zz_spin.asm").unlink(missing_ok=True)
    print(f"\n{'ALL MATCH' if not failures else f'{failures} MISMATCH(ES)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
