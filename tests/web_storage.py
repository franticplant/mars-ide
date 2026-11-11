"""Detect broken browser storage without reseeding or overwriting recovery data."""
import base64, http.server, json, os, threading, zipfile
from functools import partial
from playwright.sync_api import sync_playwright, expect

revision = {"value": 0}
class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] == "/sw.js" and revision["value"]:
            data = (f"/* test revision {revision['value']} */\n".encode() + open("/static/sw.js", "rb").read())
            self.send_response(200); self.send_header("Content-Type", "text/javascript")
            self.send_header("Cache-Control", "no-cache"); self.send_header("Content-Length", str(len(data)))
            self.end_headers(); self.wfile.write(data)
        else: super().do_GET()
httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 8094), partial(Handler, directory="/static"))
threading.Thread(target=httpd.serve_forever, daemon=True).start()

def ready(browser):
    page = browser.new_context(viewport={"width": 1400, "height": 860}).new_page()
    page.goto("http://127.0.0.1:8094/")
    page.wait_for_selector(".ftab")
    return page

RAW = """async fn => {
  const db = await new Promise((resolve,reject) => { const r=indexedDB.open('mars-ide'); r.onsuccess=()=>resolve(r.result); r.onerror=()=>reject(r.error); });
  try { return await (new Function('db', 'return (' + fn + ')(db)'))(db); } finally { db.close(); }
}"""

try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        page = ready(browser)
        assert page.evaluate("""async () => {
          const good=await MarsFiles.zip([{path:'keep.md',text:'saved bytes'}]).arrayBuffer();
          if ((await MarsFiles.unzip(good))[0].path !== 'keep.md') return false;
          const bad=good.slice(0); new Uint8Array(bad)[37] ^= 1;
          try { await MarsFiles.unzip(bad); return false; } catch (e) { return /checksum/.test(e.message); }
        }""")
        page.evaluate("""async () => {
          await MarsIDBFS.write('.hidden.bin',null,'AP8S');
          await MarsIDBFS.write('bom.md',null,'77u/IyBCeXRlLXByZXNlcnZlZA==');
        }""")
        page.click('#btn-side'); page.click('#btn-refresh'); page.locator('.node[data-p="bom.md"]').click()
        with page.expect_download() as exported:
            page.click('#btn-export')
        with zipfile.ZipFile(exported.value.path()) as archive:
            assert archive.read('.hidden.bin') == bytes([0,255,18])
            assert archive.read('bom.md') == base64.b64decode('77u/IyBCeXRlLXByZXNlcnZlZA=='), "Unmodified open files must preserve their original bytes/BOM"
        page.evaluate("navigator.serviceWorker.ready.then(async r=>{window.previousWorker=r.active; await (await caches.open('other-app-owned-cache')).put('/other-app-data',new Response('keep'));})")
        revision["value"] = 1
        page.evaluate("navigator.serviceWorker.getRegistration().then(r=>r.update())")
        page.wait_for_function("async () => !!(await navigator.serviceWorker.getRegistration()).waiting")
        assert page.evaluate("navigator.serviceWorker.getRegistration().then(r=>r.active === previousWorker)"), "An update must not take over an open editing session"
        page.evaluate("MarsIDBFS.write('keep.md', '# Saved work')")
        # A stale writer is rejected atomically, and an unchanged worker mirror cannot clobber it.
        assert page.evaluate("""async () => {
          const a=await MarsIDE.engine.call('fs_write',{path:'shared.asm',text:'original'});
          await MarsIDBFS.write('shared.asm','newer external edit',null,a.version);
          await MarsIDE.engine.pullFromWorker();
          if ((await MarsIDBFS.read('shared.asm')).text !== 'newer external edit') return false;
          try { await MarsIDBFS.write('shared.asm','stale overwrite',null,a.version); return false; }
          catch (e) { return e.code === 'WORKSPACE_CONFLICT' && (await MarsIDBFS.read('shared.asm')).text === 'newer external edit'; }
        }""")
        # Typing while a save is in flight must remain dirty, not be marked as already saved.
        page.locator('.editor-group:visible textarea').fill('# First edit')
        page.evaluate("""() => {
          const call=MarsIDE.engine.call.bind(MarsIDE.engine);
          MarsIDE.engine.call=(cmd,args,...rest)=>{
            if(cmd !== 'fs_write') return call(cmd,args,...rest);
            MarsIDE.engine.call=call;
            return call(cmd,args,...rest).then(r=>{const ta=MarsIDE.groups.active.editor.ta; ta.value='# Later edit'; ta.dispatchEvent(new Event('input',{bubbles:true})); return r;});
          };
        }""")
        page.keyboard.press('Control+s')
        page.wait_for_function("() => {const f=MarsIDE.R.files.get('bom.md'); return f.text === '# Later edit' && f.saved === '# First edit';}")
        page.keyboard.press('Control+s')
        page.wait_for_function("() => MarsIDE.R.files.get('bom.md').saved === '# Later edit'")
        # A failed transaction rejects promptly, and the old committed bytes remain intact.
        result = page.evaluate("""async () => {
          const put=IDBObjectStore.prototype.put;
          IDBObjectStore.prototype.put=function(...args) { const r=put.apply(this,args); this.transaction.abort(); return r; };
          try { await MarsIDBFS.write('keep.md','bad replacement'); return false; }
          catch (_) { return (await MarsIDBFS.read('keep.md')).text === '# Saved work'; }
          finally { IDBObjectStore.prototype.put=put; }
        }""")
        assert result
        # Legacy data is readable and is not silently rewritten to add a checksum.
        page.evaluate(RAW, """db => new Promise((resolve,reject) => {
          const t=db.transaction('files','readwrite'); t.objectStore('files').put({path:'legacy.md',data:new TextEncoder().encode('legacy'),mtime:1});
          t.oncomplete=resolve; t.onabort=()=>reject(t.error);
        })""")
        page.reload(); page.wait_for_selector(".ftab")
        assert page.evaluate("MarsIDBFS.read('legacy.md').then(r=>r.text)") == "legacy"
        assert page.evaluate("MarsIDBFS.audit().then(r=>r.unchecked)") == 1
        # Deliberately change the stored bytes without changing their checksum.
        page.evaluate(RAW, """db => new Promise((resolve,reject) => {
          const t=db.transaction('files','readwrite'), st=t.objectStore('files'), r=st.get('keep.md');
          r.onsuccess=()=> { const it=r.result; it.data=new TextEncoder().encode('damaged bytes'); st.put(it); };
          t.oncomplete=resolve; t.onabort=()=>reject(t.error);
        })""")
        page.reload()
        page.get_by_text("Workspace needs attention", exact=True).wait_for()
        assert "checksum mismatch" in page.locator(".modal .body").inner_text()
        assert page.evaluate("!!MarsIDBFS.readonly")
        with page.expect_download() as download:
            page.get_by_role("button", name="Download recovery copy", exact=True).click()
        recovery = json.load(open(download.value.path()))
        record = next(it for it in recovery["records"] if it["path"] == "keep.md")
        assert base64.b64decode(record["b64"]) == b"damaged bytes"
        assert page.evaluate("MarsIDBFS.write('keep.md','overwrite').then(()=>false,()=>true)")
        assert page.evaluate("MarsIDBFS.recovery().then(r=>r.records.find(it=>it.path==='keep.md').b64)") == record["b64"]
        context = page.context
        page.close()
        probe = context.new_page(); probe.goto("http://127.0.0.1:8094/")
        probe.wait_for_function("async () => {const r=await navigator.serviceWorker.getRegistration(); return r && !r.waiting && r.active?.state === 'activated';}")
        assert probe.evaluate("caches.has('other-app-owned-cache')"), "IDE updates must not delete another app's cache"
        context.close()

        page = ready(browser)
        page.evaluate("MarsIDBFS.write('important.asm', 'saved user data')")
        page.evaluate(RAW, """db => new Promise((resolve,reject) => {
          const t=db.transaction('files','readwrite'); t.objectStore('files').clear();
          t.oncomplete=resolve; t.onabort=()=>reject(t.error);
        })""")
        page.reload()
        page.get_by_text("Workspace needs attention", exact=True).wait_for()
        assert "unexpectedly empty" in page.locator(".modal .body").inner_text()
        assert page.evaluate("MarsIDBFS.recovery().then(r=>r.records.length)") == 0, "Must not reseed examples over an unexpectedly empty workspace"
        page.context.close()

        page = ready(browser)
        page.evaluate("localStorage.setItem('marside.v1.drafts', '{broken-draft')")
        page.reload()
        page.get_by_text("Workspace needs attention", exact=True).wait_for()
        page.locator(".modal footer").get_by_role("button", name="Close", exact=True).click()
        page.locator(".editor-group:visible textarea").fill("# New unsaved text")
        page.wait_for_timeout(800)
        assert page.evaluate("localStorage.getItem('marside.v1.drafts')") == "{broken-draft"
        page.context.close()
        browser.close()
finally:
    httpd.shutdown()
print("storage: aborted transactions, legacy files, corruption, missing data and unreadable drafts preserved")
