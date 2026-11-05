"""Import / export / drag & drop in the web UI."""
import subprocess, os, shutil, zipfile, io
from playwright.sync_api import sync_playwright
WS = "/tmp/ws"; shutil.rmtree(WS, ignore_errors=True); os.makedirs(WS); shutil.copy("/examples/hello.asm", WS)
# a deflated zip with a folder
zbuf = "/tmp/proj.zip"
with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("lab1/loop.asm", "# loop\n        .text\nmain:   li $t0, 3\nloop:   addi $t0, $t0, -1\n        bgtz $t0, loop\n        li $v0, 10\n        syscall\n")
    z.writestr("lab1/data.bin", bytes(range(256)))
open("/tmp/extra.asm", "w").write("# extra\n        .text\n        li $v0, 10\n        syscall\n")
srv = subprocess.Popen(["java", "-jar", "/build/mars-engine.jar", "--no-auth", "--port", "8097", "--root", WS, "--web", "/web"], stdout=subprocess.PIPE, text=True)
srv.stdout.readline(); srv.stdout.readline()
errs = []
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
    p = b.new_page(viewport={"width": 1300, "height": 820}, accept_downloads=True)
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.goto("http://127.0.0.1:8097/"); p.wait_for_selector(".ftab"); p.wait_for_timeout(700)
    p.keyboard.press("Control+b"); p.wait_for_timeout(200)          # show sidebar
    p.set_input_files("#file-input", [zbuf, "/tmp/extra.asm"]) if False else None
    p.evaluate("document.getElementById('btn-import').click = () => {}")  # avoid native dialog
    p.evaluate("""() => { const i = document.getElementById('file-input'); i.onchange = null; }""")
    # call the real picker path: set files then trigger the handler the button installs
    p.click("#btn-import")
    p.set_input_files("#file-input", [zbuf, "/tmp/extra.asm"])
    p.wait_for_selector(".modal footer .btn:has-text('Extract here')")   # a .zip asks where to extract
    p.click(".modal footer .btn:has-text('Extract here')"); p.wait_for_timeout(1500)
    print("disk after import:", sorted(os.path.relpath(os.path.join(d, f), WS) for d, _, fs in os.walk(WS) for f in fs))
    print("binary intact:", open(WS + "/lab1/data.bin", "rb").read() == bytes(range(256)))
    print("open tab:", p.evaluate("MarsIDE.S.current"))
    # drag & drop a file onto the lab1 folder
    p.evaluate("""() => {
      const dt = new DataTransfer();
      dt.items.add(new File(['# dropped\\n        .text\\n        nop\\n'], 'dropped.asm'));
      const tgt = document.querySelector(".node[data-p='lab1']");
      for (const t of ['dragenter', 'dragover', 'drop']) tgt.dispatchEvent(new DragEvent(t, { dataTransfer: dt, bubbles: true, cancelable: true }));
    }"""); p.wait_for_timeout(1200)
    print("dropped into folder:", os.path.exists(WS + "/lab1/dropped.asm"))
    p.screenshot(path="/shots/io-tree.png")
    # export workspace
    with p.expect_download() as dl:
        p.click("#btn-export")
    path = dl.value.path(); name = dl.value.suggested_filename
    with zipfile.ZipFile(path) as z:
        print("export:", name, sorted(z.namelist()), "| zip test:", z.testzip() is None, "| bin ok:", z.read("lab1/data.bin") == bytes(range(256)))
    # export current file
    with p.expect_download() as dl2:
        p.keyboard.press("Control+Shift+S")
    print("file download:", dl2.value.suggested_filename)
    b.close()
srv.terminate()
print("errors:", errs or "none")
