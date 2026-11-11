"""Automatic local history: migration, atomic saves, drafts and safe recovery."""
import os
import subprocess
import json
import zipfile
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8096/")
server = subprocess.Popen(["python3", "-m", "http.server", "8096", "-d", "/static"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if "BASE" not in os.environ else None
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        page = browser.new_page()
        page.goto(BASE + 'icon.svg')
        page.evaluate("""() => new Promise((resolve, reject) => {
          const r = indexedDB.open('mars-ide', 1);
          r.onupgradeneeded = () => r.result.createObjectStore('files', {keyPath:'path'});
          r.onerror = () => reject(r.error);
          r.onsuccess = () => {const db=r.result, t=db.transaction('files','readwrite');
            t.objectStore('files').put({path:'legacy.asm', data:new TextEncoder().encode('old saved'),mtime:1});
            t.oncomplete=()=>{db.close();resolve();}; t.onabort=()=>reject(t.error);};
        })""")
        page.goto(BASE)
        page.wait_for_function("window.MarsIDE && MarsIDE.engine.connected && MarsIDE.S.current", timeout=30000)
        assert page.evaluate("MarsIDBFS.read('legacy.asm').then(x=>x.text)") == 'old saved'
        page.evaluate("MarsIDBFS.write('legacy.asm','new saved')")
        records = page.evaluate("MarsIDBFS.history('legacy.asm')")
        assert [r['text'] for r in records] == ['new saved', 'old saved'], records
        page.evaluate("MarsIDBFS.write('legacy.asm','new saved')")
        assert len(page.evaluate("MarsIDBFS.history('legacy.asm')")) == 2
        result = page.evaluate("""async () => {
          const put=IDBObjectStore.prototype.put;
          IDBObjectStore.prototype.put=function(...args) { const r=put.apply(this,args); this.transaction.abort(); return r; };
          try { await MarsIDBFS.write('legacy.asm','bad'); return false; }
          catch (_) { return (await MarsIDBFS.read('legacy.asm')).text === 'new saved' && (await MarsIDBFS.history('legacy.asm')).length === 2; }
          finally { IDBObjectStore.prototype.put=put; }
        }""")
        assert result
        result = page.evaluate("""async () => {
          const add=IDBObjectStore.prototype.add;
          IDBObjectStore.prototype.add=function(...args) { if(this.name==='history') throw new DOMException('quota full','QuotaExceededError'); return add.apply(this,args); };
          try { await MarsIDBFS.write('legacy.asm','must not save'); return false; }
          catch (_) { return (await MarsIDBFS.read('legacy.asm')).text === 'new saved' && (await MarsIDBFS.history('legacy.asm')).length === 2; }
          finally { IDBObjectStore.prototype.add=add; }
        }""")
        assert result, 'A failed history write must abort the file save'
        result = page.evaluate("""async () => {
          const base = await MarsIDBFS.write('race.asm','base');
          const results = await Promise.allSettled([
            MarsIDBFS.write('race.asm','first',null,base.version),
            MarsIDBFS.write('race.asm','second',null,base.version)]);
          const stored = (await MarsIDBFS.read('race.asm')).text;
          const h = await MarsIDBFS.history('race.asm');
          return results.filter(r=>r.status==='fulfilled').length===1 &&
            results.filter(r=>r.status==='rejected' && r.reason.code==='WORKSPACE_CONFLICT').length===1 &&
            h.length===2 && h.some(v=>v.text==='base') && h.some(v=>v.text===stored);
        }""")
        assert result, 'A stale writer must not change either the saved file or its history'
        page.evaluate("""async () => {
          await MarsIDBFS.write('dedup.asm','same'); await MarsIDBFS.write('dedup.asm','other'); await MarsIDBFS.write('dedup.asm','same');
        }""")
        assert [v['text'] for v in page.evaluate("MarsIDBFS.history('dedup.asm')")] == ['same', 'other', 'same']
        assert page.evaluate("""() => new Promise((resolve, reject) => {
          const r=indexedDB.open('mars-ide'); r.onerror=()=>reject(r.error); r.onsuccess=()=>{
            const db=r.result, t=db.transaction('history'), q=t.objectStore('history').index('path').getAll('dedup.asm');
            q.onsuccess=()=>resolve(q.result.filter(v=>v.ref !== undefined).length); t.oncomplete=()=>db.close();
          };
        })""") == 1
        page.evaluate("MarsIDBFS.rename('dedup.asm','dedup-moved.asm')")
        assert [v['text'] for v in page.evaluate("MarsIDBFS.history('dedup-moved.asm')")] == ['same', 'other', 'same']
        page.click('#btn-side'); page.click('#btn-refresh'); page.locator('.node[data-p="legacy.asm"]').click()
        page.locator('.active-group textarea.ed-input').fill('unsaved draft')
        page.wait_for_timeout(3600)  # draft checkpoints intentionally wait for three quiet seconds
        current_history = page.evaluate("MarsIDBFS.history('legacy.asm')")
        assert any(v['kind'] == 'draft' and v['text'] == 'unsaved draft' for v in current_history), current_history
        with page.expect_download() as backup:
            page.click('#btn-full-backup')
        with zipfile.ZipFile(backup.value.path()) as archive:
            assert archive.read('legacy.asm') == b'new saved'
            metadata = json.loads(archive.read('.mars-backup/manifest.json'))
            assert metadata['format'] == 'mars-ide-full-backup-v1'
            assert any(d['path'] == 'legacy.asm' and d['text'] == 'unsaved draft' for d in metadata['openDrafts'])
            assert any(v['path'] == 'legacy.asm' and v['kind'] == 'draft' for v in metadata['history']), metadata['history']
        backup.value.save_as('/tmp/mars-history-test-backup.zip')
        page.click('#btn-import')
        page.locator('#file-input').set_input_files('/tmp/mars-history-test-backup.zip')
        page.get_by_role('button', name='Restore copies').click()
        page.wait_for_function("MarsIDE.S.current && MarsIDE.S.current.startsWith('Restored backup ')", timeout=10000)
        restored = page.evaluate("MarsIDBFS.files().then(fs=>fs.filter(f=>f.path.startsWith('Restored backup ')).map(f=>f.path))")
        saved_copy = next(p for p in restored if p.endswith('/legacy.asm'))
        draft_copy = next(p for p in restored if p.endswith('/legacy (draft).asm'))
        assert page.evaluate("p=>MarsIDBFS.read(p).then(x=>x.text)", saved_copy) == 'new saved'
        assert page.evaluate("p=>MarsIDBFS.read(p).then(x=>x.text)", draft_copy) == 'unsaved draft'
        assert page.evaluate("p=>MarsIDBFS.history(p).then(h=>h.some(v=>v.text==='unsaved draft'))", saved_copy)
        assert page.evaluate("MarsIDBFS.read('legacy.asm').then(x=>x.text)") == 'new saved'
        assert page.evaluate("""async () => {
          const before = await MarsIDBFS.files();
          try { await MarsIDBFS.restoreBackupCopy('Invalid restore', [{path:'../escape',data:new Uint8Array([1])}], []); return false; }
          catch (_) { return (await MarsIDBFS.files()).length === before.length; }
        }""")
        # Re-select the original; restoring a backup should not overwrite its open draft.
        page.locator('.node[data-p="legacy.asm"]').click()
        page.locator('.active-group .group-actions button').filter(has_text='History').click()
        assert 'unsaved draft' in page.locator('.history-preview').inner_text(), (page.locator('.history-preview').inner_text(), page.evaluate("MarsIDBFS.history('legacy.asm')"))
        page.get_by_role('button', name='Restore as copy').click()
        page.wait_for_function("MarsIDE.S.current.includes('(restored)')")
        assert page.evaluate("MarsIDBFS.read(MarsIDE.S.current).then(x=>x.text)") == 'unsaved draft'
        assert page.evaluate("MarsIDBFS.read('legacy.asm').then(x=>x.text)") == 'new saved'
        # Closing before the quiet-period timer still preserves the draft in history.
        page.locator('.node[data-p="legacy.asm"]').click()
        page.locator('.active-group textarea.ed-input').fill('immediate draft before close')
        page.locator('.active-group .group-tab.selected [data-close]').click()
        page.get_by_role('button', name='Discard', exact=True).click()
        page.wait_for_function("!MarsIDE.R.files.has('legacy.asm')")
        assert any(v['text'] == 'immediate draft before close' for v in page.evaluate("MarsIDBFS.history('legacy.asm')"))
        page.evaluate("MarsIDBFS.rename('legacy.asm','moved.asm')")
        assert page.evaluate("MarsIDBFS.history('moved.asm').then(h=>h.length)") >= 3
        page.evaluate("MarsIDBFS.remove('moved.asm')")
        assert page.evaluate("MarsIDBFS.history('moved.asm').then(h=>h.length)") >= 3
        page.reload(); page.wait_for_function("window.MarsIDE && MarsIDE.engine.connected")
        assert page.evaluate("MarsIDBFS.history('moved.asm').then(h=>h.length)") >= 3
        page.wait_for_selector('.ftab')
        page.evaluate("() => { MarsIDBFS.checkpoint = () => Promise.reject(new DOMException('quota full','QuotaExceededError')); }")
        page.locator('.active-group textarea.ed-input').fill('needs history warning')
        page.locator('#history-warning').wait_for(timeout=10000)
        assert 'could not be recorded' in page.locator('#history-warning').inner_text()
        browser.close()
        print('history: migration, atomic rollback, drafts, recovery copy, rename and delete OK')
finally:
    if server:
        server.terminate(); server.wait()
