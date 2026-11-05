"""File tree: zip extract dialog, moving by drag & drop / Move to…, folder state.  MODE=server (default) | static.

server: java -jar /build/mars-engine.jar on /tmp/ws (files checked on disk too)
static: python -m http.server on /static (files checked in IndexedDB via fs_list)
"""
import io, os, re, shutil, subprocess, sys, time, zipfile
from playwright.sync_api import sync_playwright

MODE = os.environ.get("MODE", "server")
WS = "/tmp/ws"
PORT = 8093 if MODE == "server" else 8094
BASE = f"http://127.0.0.1:{PORT}/"
FAILS, ERRS = [], []


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAILS.append(what)


def mkzip(path, entries):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries.items():
            z.writestr(name, data)
    return path


ASM = "        .text\nmain:   li $v0, 10\n        syscall\n"
SETUP = {"hello.asm": ASM, "src/a.asm": "# a\n" + ASM, "src/sub/b.asm": "# b\n" + ASM, "docs/readme.txt": "docs readme\n",
         "readme.txt": "root readme\n", "keep/x.asm": "# x\n" + ASM, "keep/y.asm": "# y\n" + ASM}
Z1 = mkzip("/tmp/lab3.zip", {"lab3/main.asm": "# main\n" + ASM, "lab3/util/x.asm": "# util\n" + ASM})   # top folder == zip name
Z2 = mkzip("/tmp/pack.zip", {"p1.asm": ASM, "p2.asm": ASM})                                           # no top folder
Z3 = mkzip("/tmp/other.zip", {"proj/q.asm": ASM, "proj/data.bin": bytes(range(256))})                # top folder != zip name
Z4 = mkzip("/tmp/nope.zip", {"n.asm": ASM})

srv = None
if MODE == "server":
    shutil.rmtree(WS, ignore_errors=True); os.makedirs(WS)
    for k, v in SETUP.items():
        os.makedirs(os.path.dirname(os.path.join(WS, k)), exist_ok=True)
        open(os.path.join(WS, k), "w").write(v)
    os.makedirs(WS + "/empty")
    srv = subprocess.Popen(["java", "-jar", "/build/mars-engine.jar", "--no-auth", "--port", str(PORT), "--root", WS, "--web", "/web"], stdout=subprocess.PIPE, text=True)
    srv.stdout.readline(); srv.stdout.readline()
else:
    srv = subprocess.Popen(["python3", "-m", "http.server", str(PORT), "-d", "/static"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    import urllib.request
    for _ in range(50):
        try:
            urllib.request.urlopen(BASE + "index.html", timeout=1).read(); break
        except Exception:
            time.sleep(0.2)


def files(p):
    """All file paths in the workspace (engine view); in server mode also compared with the disk."""
    lst = set(p.evaluate("MarsIDE.engine.call('fs_list').then(r => r.entries.filter(e => !e.dir).map(e => e.path))"))
    if MODE == "server":
        disk = {os.path.relpath(os.path.join(d, f), WS) for d, _, fs in os.walk(WS) for f in fs if not f.startswith(".") and ".mars-tui" not in d}
        if disk != lst:
            check(False, f"disk == fs_list ({sorted(disk ^ lst)})")
    return lst


def dirs(p):
    return set(p.evaluate("MarsIDE.engine.call('fs_list').then(r => r.entries.filter(e => e.dir).map(e => e.path))"))


def visible(p):
    return p.evaluate("[...document.querySelectorAll('#tree .node')].map(n => n.dataset.p)")


def wait_tree(p, path, present=True, timeout=6000):
    try:
        p.wait_for_function("([q, on]) => MarsIDE.R.tree.some(n => n.path === q) === on", arg=[path, present], timeout=timeout)
        return True
    except Exception:
        return False


DRAG_JS = """([src, dst]) => {
  const node = q => [...document.querySelectorAll('#tree .node')].find(n => n.dataset.p === q);
  const s = node(src), d = dst.startsWith('#') || dst.startsWith('.') ? document.querySelector(dst) : node(dst);
  if (!s || !d) return { missing: true };
  const dt = new DataTransfer(), o = { dataTransfer: dt, bubbles: true, cancelable: true };
  s.dispatchEvent(new DragEvent('dragstart', o));
  d.dispatchEvent(new DragEvent('dragenter', o));
  const ov = new DragEvent('dragover', o); d.dispatchEvent(ov);
  const r = { prevented: ov.defaultPrevented, overlay: document.getElementById('dropzone').classList.contains('on'),
              target: (document.querySelector('#tree .drop-target') || {}).dataset?.p ?? null,
              root: document.getElementById('sidebar').classList.contains('drop-root'), types: [...dt.types] };
  d.dispatchEvent(new DragEvent('drop', o));
  s.dispatchEvent(new DragEvent('dragend', o));
  return r;
}"""

DROP_FILE_JS = """async ([dst, name, b64]) => {
  const node = q => [...document.querySelectorAll('#tree .node')].find(n => n.dataset.p === q);
  const d = node(dst);
  const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  const dt = new DataTransfer(); dt.items.add(new File([bytes], name));
  const o = { dataTransfer: dt, bubbles: true, cancelable: true };
  d.dispatchEvent(new DragEvent('dragenter', o)); d.dispatchEvent(new DragEvent('dragover', o));
  const r = { overlay: document.getElementById('dropzone').classList.contains('on'), target: (document.querySelector('#tree .drop-target') || {}).dataset?.p ?? null };
  d.dispatchEvent(new DragEvent('drop', o));
  return r;
}"""


def modal_btn(p, label):
    p.locator(".modal footer .btn").filter(has_text=re.compile("^" + re.escape(label) + "$")).click()


def pick(p, paths, via="#btn-import"):
    with p.expect_file_chooser() as fc:
        p.click(via) if isinstance(via, str) else via()
    fc.value.set_files(paths)


def setup_static(p):
    for k, v in SETUP.items():
        p.evaluate("([k, v]) => MarsIDE.engine.call('fs_write', { path: k, text: v })", [k, v])
    p.evaluate("MarsIDE.engine.call('fs_mkdir', { path: 'empty' })")
    p.click("#btn-refresh"); p.wait_for_timeout(300)


def shot(p, name):
    try:
        p.screenshot(path=f"/shots/tree-{MODE}-{name}.png")
    except Exception as e:
        print("note: no screenshot:", e)


def node_btn(p, path, action):
    loc = p.locator(f"#tree .node[data-p='{path}']")
    loc.hover(); loc.locator(f"[data-a='{action}']").click()


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
    # ------------------------------------------------------------------ desktop
    ctx = b.new_context(viewport={"width": 1300, "height": 860}, bypass_csp=True)
    p = ctx.new_page()
    p.on("pageerror", lambda e: ERRS.append(str(e)))
    p.on("dialog", lambda d: d.dismiss())
    p.on("console", lambda m: print("console:", m.text) if m.type == "error" else None)
    p.goto(BASE)
    p.wait_for_function("window.MarsIDE && MarsIDE.engine.connected && MarsIDE.R.fs", timeout=30000)
    p.wait_for_timeout(600)
    if not p.evaluate("!document.getElementById('app').classList.contains('no-side')"):
        p.keyboard.press("Control+b")
    if MODE == "static":
        setup_static(p)
    p.wait_for_selector("#tree .node[data-p='src/a.asm']")

    # ---- 1. zip whose single top folder equals the zip name → no double nesting
    pick(p, [Z1])
    p.wait_for_selector(".modal .zip-chips")
    check(p.input_value(".modal input.text") == "lab3", "zip dialog default = folder named after the zip")
    check("lab3/main.asm" in p.inner_text(".modal .zip-prev"), "preview shows lab3/main.asm (not lab3/lab3/…)")
    modal_btn(p, "Extract")
    check(wait_tree(p, "lab3/util/x.asm") and wait_tree(p, "lab3/main.asm"), "lab3.zip → lab3/main.asm")
    fs = files(p)
    check("lab3/util/x.asm" in fs and not any(f.startswith("lab3/lab3") for f in fs), "nested folder kept, top folder not doubled")
    p.wait_for_function("MarsIDE.S.current === 'lab3/main.asm'", timeout=4000)
    check(p.evaluate("MarsIDE.S.current") == "lab3/main.asm", "first .asm of the zip is opened")
    check("lab3/util/x.asm" in visible(p) or "lab3/util" in visible(p), "destination folder expanded in the tree")

    # ---- 2. zip without a top folder into a typed new path
    pick(p, [Z2])
    p.wait_for_selector(".modal .zip-chips")
    p.fill(".modal input.text", "imports/new")
    check("new folder" in p.inner_text(".modal .zip-prev"), "preview marks a new folder")
    p.keyboard.press("Enter")
    check(wait_tree(p, "imports/new/p2.asm") and wait_tree(p, "imports/new/p1.asm"), "pack.zip → imports/new/p1.asm (typed path, folders created)")
    check({"imports/new/p1.asm", "imports/new/p2.asm"} <= files(p), "both files extracted")
    check("imports/new/p1.asm" in visible(p), "typed destination is expanded and visible")

    # ---- 3. zip with another top folder, "Extract here"
    pick(p, [Z3])
    p.wait_for_selector(".modal .zip-chips")
    modal_btn(p, "Extract here")
    check(wait_tree(p, "proj/data.bin") and wait_tree(p, "proj/q.asm"), "Extract here: other.zip → proj/q.asm at the root")
    if MODE == "server":
        check(open(WS + "/proj/data.bin", "rb").read() == bytes(range(256)), "binary from zip intact")

    # ---- 4. cancel extracts nothing
    pick(p, [Z4])
    p.wait_for_selector(".modal .zip-chips")
    modal_btn(p, "Cancel"); p.wait_for_timeout(500)
    fs = files(p)
    check("n.asm" not in fs and not any(f.endswith("/n.asm") for f in fs), "Cancel: nothing extracted")

    # ---- 5. zip via the folder's import button → defaults to that folder
    pick(p, [Z4], via=lambda: node_btn(p, "docs", "imp"))
    p.wait_for_selector(".modal .zip-chips")
    check(p.input_value(".modal input.text") == "docs", "folder import button: default = that folder")
    modal_btn(p, "Extract")
    check(wait_tree(p, "docs/n.asm"), "nope.zip → docs/n.asm")

    # ---- 6. zip dropped (OS drop) on a folder; overlay shows for external files
    import base64
    r = p.evaluate(DROP_FILE_JS, ["keep", "drop.zip", base64.b64encode(open(Z2, "rb").read()).decode()])
    check(r["overlay"] and r["target"] == "keep", f"external drop shows overlay + highlights folder ({r})")
    p.wait_for_selector(".modal .zip-chips")
    check(p.input_value(".modal input.text") == "keep", "dropped zip: default = folder dropped on")
    p.click(".modal .zip-chips button:nth-child(2)")      # chip "New folder · keep/drop/"
    check(p.input_value(".modal input.text") == "keep/drop", "New folder chip sets keep/drop")
    modal_btn(p, "Extract")
    check(wait_tree(p, "keep/drop/p2.asm") and wait_tree(p, "keep/drop/p1.asm"), "dropped zip → keep/drop/p1.asm")
    check(not p.evaluate("document.getElementById('dropzone').classList.contains('on')"), "overlay hidden after drop")

    # ---- 7. move an open file with a breakpoint into another folder (drag & drop)
    p.click("#tree .node[data-p='src/a.asm']"); p.wait_for_function("MarsIDE.S.current === 'src/a.asm'")
    p.evaluate("MarsIDE.S.bps['src/a.asm'] = [2]")
    r = p.evaluate(DRAG_JS, ["src/a.asm", "keep"])
    check(r.get("prevented") and not r.get("overlay") and r.get("target") == "keep" and "application/x-mars-path" in r.get("types", []),
          f"internal drag: drop allowed, folder highlighted, no import overlay ({r})")
    check(wait_tree(p, "keep/a.asm") and wait_tree(p, "src/a.asm", False), "src/a.asm moved to keep/a.asm")
    st = p.evaluate("({ cur: MarsIDE.S.current, open: MarsIDE.S.open, bps: Object.keys(MarsIDE.S.bps), files: [...MarsIDE.R.files.keys()] })")
    check(st["cur"] == "keep/a.asm" and "keep/a.asm" in st["open"] and "src/a.asm" not in st["open"], f"open tab follows the move ({st['cur']})")
    check("keep/a.asm" in st["bps"] and "src/a.asm" not in st["bps"] and "keep/a.asm" in st["files"], "breakpoints + buffers follow the move")
    check(p.locator("#filetabs .ftab.active").get_attribute("data-p") == "keep/a.asm", "editor tab shows the new path")

    # ---- 8. move a folder with its contents (real HTML5 drag with the mouse)
    p.click("#tree .node[data-p='src/sub/b.asm']"); p.wait_for_function("MarsIDE.S.current === 'src/sub/b.asm'")
    p.drag_and_drop("#tree .node[data-p='src']", "#tree .node[data-p='empty']")
    ok = wait_tree(p, "empty/src/sub/b.asm")
    if not ok:      # some headless builds do not run native DnD: fall back to synthetic events
        print("note: native drag_and_drop had no effect, using DragEvents")
        p.evaluate(DRAG_JS, ["src", "empty"]); ok = wait_tree(p, "empty/src/sub/b.asm")
    check(ok and "src/sub/b.asm" not in files(p), "folder src moved into empty/ recursively")
    check(p.evaluate("MarsIDE.S.current") == "empty/src/sub/b.asm", "tab of a file inside the moved folder follows")
    check("empty/src/sub/b.asm" in visible(p), "moved-to folder is expanded")

    # ---- 9. invalid moves are refused
    before = files(p)
    r = p.evaluate(DRAG_JS, ["empty/src", "empty/src/sub"])
    check(not r.get("prevented") and r.get("target") is None, "folder into its own subfolder: not a drop target")
    p.wait_for_timeout(600)
    check(files(p) == before, "folder into own descendant: nothing moved")
    check("cannot be moved into itself" in p.inner_text("#toasts"), "…and a toast explains why")
    r = p.evaluate(DRAG_JS, ["empty/src", "empty/src"])
    p.wait_for_timeout(400)
    check(not r.get("prevented") and files(p) == before, "folder onto itself refused")
    r = p.evaluate(DRAG_JS, ["keep/a.asm", "keep/x.asm"])     # onto a sibling = same folder → no-op
    p.wait_for_timeout(400)
    check(not r.get("prevented") and files(p) == before, "no-op move (same folder) refused")

    # ---- 10. move to the workspace root (header / empty tree space)
    r = p.evaluate(DRAG_JS, ["empty/src/sub/b.asm", ".side-head"])
    check(r.get("prevented") and r.get("root"), f"Workspace header is a root drop target ({r})")
    check(wait_tree(p, "b.asm"), "file dropped on the header → b.asm at the root")
    r = p.evaluate(DRAG_JS, ["keep/x.asm", "#tree"])
    check(wait_tree(p, "x.asm"), "file dropped on empty tree space → x.asm at the root")

    # ---- 11. name clash: keep both / replace / cancel
    p.evaluate(DRAG_JS, ["docs/readme.txt", ".side-head"])
    p.wait_for_selector(".modal:has-text('Name already in use')")
    modal_btn(p, "Keep both")
    check(wait_tree(p, "readme (2).txt") and "readme.txt" in files(p), "Keep both → readme (2).txt")
    p.evaluate("MarsIDE.engine.call('fs_write', { path: 'keep/hello.asm', text: '# new hello\\n' })"); p.click("#btn-refresh"); p.wait_for_timeout(300)
    p.evaluate(DRAG_JS, ["keep/hello.asm", "#tree"])
    p.wait_for_selector(".modal:has-text('Name already in use')")
    modal_btn(p, "Cancel"); p.wait_for_timeout(400)
    check("keep/hello.asm" in files(p), "Cancel on clash: nothing moved")
    p.evaluate(DRAG_JS, ["keep/hello.asm", "#tree"])
    p.wait_for_selector(".modal:has-text('Name already in use')")
    modal_btn(p, "Replace")
    check(wait_tree(p, "keep/hello.asm", False), "Replace: source gone")
    txt = p.evaluate("MarsIDE.engine.call('fs_read', { path: 'hello.asm' }).then(r => r.text)")
    check(txt.startswith("# new hello"), "Replace: root hello.asm has the moved content")

    # ---- 12. folder state: collapse survives refresh + reload, moving into it expands it
    p.click("#tree .node[data-p='keep'] .nm")
    check("keep/a.asm" not in visible(p) and p.get_attribute("#tree .node[data-p='keep']", "aria-expanded") == "false", "click collapses a folder")
    p.click("#btn-refresh"); p.wait_for_timeout(400)
    check("keep/a.asm" not in visible(p), "collapsed state survives refresh")
    p.reload(); p.wait_for_function("window.MarsIDE && MarsIDE.engine.connected && MarsIDE.R.tree.length", timeout=30000); p.wait_for_timeout(500)
    check("keep" in visible(p) and "keep/a.asm" not in visible(p), "collapsed state survives reload")
    p.evaluate(DRAG_JS, ["b.asm", "keep"])
    check(wait_tree(p, "keep/b.asm") and "keep/b.asm" in visible(p), "moving into a collapsed folder expands it")

    # ---- 13. rename still follows open tabs (refactored renamePath)
    p.click("#tree .node[data-p='keep/a.asm']"); p.wait_for_function("MarsIDE.S.current === 'keep/a.asm'")
    node_btn(p, "keep", "ren")
    p.fill(".modal input.text", "kept"); p.keyboard.press("Enter")
    check(wait_tree(p, "kept/a.asm"), "rename folder keep → kept")
    check(p.evaluate("MarsIDE.S.current") == "kept/a.asm" and "kept/a.asm" in p.evaluate("MarsIDE.S.bps"), "rename: tab + breakpoints follow")

    # ---- 14. "Move to…" dialog (desktop button)
    node_btn(p, "x.asm", "move")
    p.wait_for_selector(".modal .dir-pick")
    p.click(".modal .dir-pick button[data-d='kept']")
    modal_btn(p, "Move")
    check(wait_tree(p, "kept/x.asm"), "Move to… dialog moves x.asm into kept/")
    shot(p, "desktop")
    ctx.close()

    # ------------------------------------------------------------------ phone (touch): long-press › Move to…
    ctx = b.new_context(viewport={"width": 400, "height": 820}, has_touch=True, is_mobile=True, device_scale_factor=2, bypass_csp=True)
    p = ctx.new_page()
    p.on("pageerror", lambda e: ERRS.append(str(e)))
    p.goto(BASE)
    p.wait_for_function("window.MarsIDE && MarsIDE.engine.connected && MarsIDE.R.fs", timeout=30000)
    p.wait_for_timeout(500)
    if MODE == "static":      # fresh context = fresh IndexedDB
        p.evaluate("MarsIDE.engine.call('fs_write', { path: 'kept/x.asm', text: '# x\\n' })")
    p.click("#bottomnav button[data-m='more']"); p.click(".sheet-grid button[data-k='files']")
    p.wait_for_selector("#tree .node[data-p='kept/x.asm']")
    check(p.evaluate("document.querySelector(\"#tree .node[data-p='kept']\").draggable") is False, "touch: rows are not HTML5-draggable")
    check(p.is_visible("#tree .node[data-p='kept/x.asm'] .more"), "touch: ⋯ actions button visible")
    box = p.locator("#tree .node[data-p='kept/x.asm']").bounding_box()
    p.evaluate("""([x, y]) => { const el = document.elementFromPoint(x, y);
        el.dispatchEvent(new PointerEvent('pointerdown', { pointerType: 'touch', clientX: x, clientY: y, bubbles: true, isPrimary: true })); }""",
               [box["x"] + 60, box["y"] + box["height"] / 2])
    p.wait_for_timeout(750)
    check(p.is_visible(".modal .node-menu"), "long-press opens the item menu")
    p.click(".modal .node-menu button[data-k='move']")
    p.wait_for_selector(".modal .dir-pick")
    p.click(".modal .dir-pick button[data-d='']")
    modal_btn(p, "Move")
    check(wait_tree(p, "x.asm"), "touch Move to… → x.asm back at the root")
    # ⋯ button → menu → Move to… typed new folder
    p.tap("#tree .node[data-p='x.asm'] .more")
    p.wait_for_selector(".modal .node-menu")
    p.tap(".modal .node-menu button[data-k='move']")
    p.wait_for_selector(".modal .dir-pick")
    p.fill(".modal input.text", "phone/new")
    modal_btn(p, "Move")
    check(wait_tree(p, "phone/new/x.asm"), "⋯ › Move to… typed folder → phone/new/x.asm")
    check("phone/new/x.asm" in visible(p), "phone: destination expanded")
    shot(p, "phone")
    ctx.close()
    b.close()

srv.terminate()
check(not ERRS, f"no page errors {ERRS if ERRS else ''}")
print(f"{MODE}: {'ALL PASSED' if not FAILS else str(len(FAILS)) + ' FAILED'}")
sys.exit(1 if FAILS else 0)
