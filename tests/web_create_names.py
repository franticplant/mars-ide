"""New file/folder dialogs use name-only inputs and preserve their chosen parent."""
import os
import subprocess
from playwright.sync_api import sync_playwright

BASE = os.environ.get('BASE', 'http://127.0.0.1:8096/')
server = subprocess.Popen(['python3', '-m', 'http.server', '8096', '-d', '/static'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if 'BASE' not in os.environ else None
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':1300, 'height':800})
        page.goto(BASE); page.wait_for_function('window.MarsIDE && MarsIDE.engine.connected && MarsIDE.S.current', timeout=30000)
        page.evaluate("MarsIDE.engine.call('fs_write',{path:'lessons/deep/existing.asm',text:'# do not overwrite'})")
        page.click('#btn-side'); page.click('#btn-refresh')
        parent = page.locator('.node[data-p="lessons/deep"]')
        parent.wait_for(); parent.hover()
        assert parent.locator('[data-a="imp"]').count() == 0
        assert parent.locator('[data-a="move"]').count() == 0
        assert parent.locator('[data-a="newdir"]').count() == 1
        parent.locator('[data-a="new"]').click()
        inp = page.locator('.modal input.text'); assert inp.input_value() == ''
        assert 'lessons/deep' in page.locator('.modal .body').inner_text()
        inp.fill('hello'); inp.press('Enter')
        page.wait_for_function("MarsIDE.S.current === 'lessons/deep/hello.asm'")
        assert page.evaluate("MarsIDBFS.read('lessons/deep/hello.asm').then(r=>r.text.includes('Hello, MIPS'))")
        parent = page.locator('.node[data-p="lessons/deep"]'); parent.hover(); parent.locator('[data-a="newdir"]').click()
        inp = page.locator('.modal input.text'); assert inp.input_value() == ''
        inp.fill('child'); inp.press('Enter')
        page.locator('.node[data-p="lessons/deep/child"]').wait_for()
        parent = page.locator('.node[data-p="lessons/deep"]'); parent.hover(); parent.locator('[data-a="newdir"]').click()
        inp = page.locator('.modal input.text'); inp.fill('existing.asm'); inp.press('Enter')
        page.get_by_text('already exists', exact=False).first.wait_for()
        assert page.evaluate("MarsIDBFS.read('lessons/deep/existing.asm').then(r=>r.text)") == '# do not overwrite'
        assert page.evaluate("""async () => {
          try { await MarsIDBFS.mkdir('lessons/deep/existing.asm'); return false; }
          catch (_) { return (await MarsIDBFS.read('lessons/deep/existing.asm')).text === '# do not overwrite'; }
        }""")
        assert page.evaluate("""async () => {
          try { await MarsIDBFS.write('lessons/deep', 'bad'); return false; }
          catch (_) { return (await MarsIDBFS.read('lessons/deep/existing.asm')).text === '# do not overwrite'; }
        }""")
        assert page.evaluate("""async () => {
          await MarsIDBFS.mkdir('empty-explicit');
          try { await MarsIDBFS.write('empty-explicit', 'bad'); return false; }
          catch (_) { return (await MarsIDBFS.list()).entries.some(e=>e.path==='empty-explicit' && e.dir); }
        }""")
        parent = page.locator('.node[data-p="lessons/deep"]'); parent.hover(); parent.locator('[data-a="new"]').click()
        inp = page.locator('.modal input.text'); inp.fill('nested/relative'); inp.press('Enter')
        page.wait_for_function("MarsIDE.S.current === 'lessons/deep/nested/relative.asm'")
        parent = page.locator('.node[data-p="lessons/deep"]'); parent.click(button='right')
        assert page.get_by_role('button', name='Move to…', exact=True).is_visible()
        assert page.get_by_role('button', name='Import here', exact=True).is_visible()
        page.locator('.modal header [data-close]').click()
        page.click('#btn-newdir'); inp = page.locator('.modal input.text'); assert inp.input_value() == ''
        inp.fill('root-folder'); inp.press('Enter'); page.locator('.node[data-p="root-folder"]').wait_for()
        page.click('#btn-newfile'); inp = page.locator('.modal input.text'); assert inp.input_value() == ''
        inp.fill('root-file'); inp.press('Enter'); page.wait_for_function("MarsIDE.S.current === 'root-file.asm'")
        page.click('#btn-newfile'); inp = page.locator('.modal input.text'); inp.fill('../escape'); inp.press('Enter')
        page.get_by_text('Enter a name or a path inside this folder', exact=False).wait_for()
        assert not page.evaluate("MarsIDBFS.files().then(fs => fs.some(f => f.path.includes('escape')))")
        browser.close(); print('create dialogs: name-only, nested paths, new-folder action and collision safety OK')
finally:
    if server:
        server.terminate(); server.wait()
