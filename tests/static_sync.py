"""ASSERTING test of the static build's workspace sync (IndexedDB <-> engine worker). Exit code != 0 on failure."""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright
BASE = os.environ.get("BASE", "http://127.0.0.1:8094/")
srv = subprocess.Popen(["python3", "-m", "http.server", "8094", "-d", "/static"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if "8094" in BASE else None
time.sleep(1)
fails, errs = [], []
def check(cond, what):
    print(("PASS " if cond else "FAIL ") + what)
    if not cond: fails.append(what)
MAIN = '        .include "lib.asm"\n        .text\nmain:   done\n'
LIB = '        .macro done\n        li $v0, 10\n        syscall\n        .end_macro\n'
WRITER = ('        .data\nfn: .asciiz "gen/out.txt"\nmsg: .asciiz "hello"\n        .text\nmain: li $v0, 13\n la $a0, fn\n li $a1, 1\n li $a2, 0\n syscall\n'
          ' move $s0, $v0\n li $v0, 15\n move $a0, $s0\n la $a1, msg\n li $a2, 5\n syscall\n li $v0, 16\n move $a0, $s0\n syscall\n li $v0, 10\n syscall\n')
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
    p = b.new_page()
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.goto(BASE); p.wait_for_function("window.MarsIDE && MarsIDE.engine.connected", timeout=30000)
    call = lambda cmd, **a: p.evaluate("([c, a]) => MarsIDE.engine.call(c, a).then(r => r, e => ({ok: false, error: e.message}))", [cmd, a])
    # 1. deleted include file must not assemble (worker mirror follows deletes)
    call("fs_mkdir", path="gen")
    call("fs_write", path="main.asm", text=MAIN); call("fs_write", path="lib.asm", text=LIB)
    r = call("assemble", files=["main.asm"]); check(r.get("success") is True, "assembles while lib.asm exists")
    call("fs_delete", path="lib.asm")
    r = call("assemble", files=["main.asm"]); check(r.get("success") is False, "assemble FAILS after lib.asm is deleted")
    call("fs_write", path="lib.asm", text=LIB)
    call("fs_rename", **{"from": "lib.asm", "to": "lib2.asm"})
    r = call("assemble", files=["main.asm"]); check(r.get("success") is False, "assemble FAILS after lib.asm is renamed away")
    # 2. file written by a syscall reaches the saved workspace
    call("fs_write", path="writer.asm", text=WRITER)
    call("assemble", files=["writer.asm"])
    p.evaluate("new Promise(res => { const off = MarsIDE.engine.on(ev => { if (ev.ev === 'fs_changed') { off(); res(); } }); MarsIDE.engine.call('run'); setTimeout(res, 5000); })")
    r = call("fs_read", path="gen/out.txt"); check(r.get("text") == "hello", f"syscall-written gen/out.txt is in the workspace (got {r.get('text') or r.get('error')!r})")
    p.wait_for_timeout(500)
    check(p.evaluate("MarsIDE.R.tree.some(n => n.path === 'gen/out.txt')"), "file tree shows gen/out.txt")
    # 3. survives reload (IndexedDB) and the worker sees it again
    p.reload(); p.wait_for_function("window.MarsIDE && MarsIDE.engine.connected", timeout=30000)
    r = call("fs_read", path="gen/out.txt"); check(r.get("text") == "hello", "gen/out.txt persists across reload")
    r = call("assemble", files=["main.asm"]); check(r.get("success") is False, "deleted include still absent after reload")
    # 4. float printing matches Java
    call("fs_write", path="fp.asm", text="        .text\nmain: li $t0, 1\n mtc1 $t0, $f12\n li $v0, 2\n syscall\n li $v0, 10\n syscall\n")
    call("assemble", files=["fp.asm"])
    out = p.evaluate("new Promise(res => { let o = ''; const off = MarsIDE.engine.on(ev => { if (ev.ev === 'out') o += ev.text; if (ev.ev === 'stopped') { off(); res(o); } }); MarsIDE.engine.call('run'); })")
    check(out == "1.4E-45", f"smallest float prints 1.4E-45 like MARS (got {out!r})")
    b.close()
if srv: srv.terminate()
check(not errs, f"no page errors {errs[:3]}")
print("RESULT:", "ALL PASS" if not fails else f"{len(fails)} FAILED")
sys.exit(1 if fails else 0)
