"""Rename only edits a basename and never silently moves a nested item."""
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
        page.evaluate("""async () => {
          await MarsIDE.engine.call('fs_write', {path:'lessons/deep/prog.asm',text:'# keep me\\n'});
          await MarsIDE.engine.call('fs_write', {path:'lessons/deep/taken.asm',text:'# other\\n'});
        }""")
        page.click('#btn-side'); page.click('#btn-refresh')
        def rename(path):
            node = page.locator(f'.node[data-p="{path}"]')
            node.hover(); node.locator('[data-a="ren"]').click()
            return page.locator('.modal input.text')
        inp = rename('lessons/deep/prog.asm')
        assert inp.input_value() == 'prog.asm'
        inp.fill('renamed.asm'); inp.press('Enter')
        page.locator('.node[data-p="lessons/deep/renamed.asm"]').wait_for()
        assert page.evaluate("MarsIDBFS.read('lessons/deep/renamed.asm').then(r=>r.text)") == '# keep me\n'
        inp = rename('lessons/deep/renamed.asm')
        inp.fill('../escape.asm'); inp.press('Enter')
        page.get_by_text('Enter a name without slashes', exact=False).wait_for()
        assert page.evaluate("MarsIDBFS.read('lessons/deep/renamed.asm').then(r=>r.text)") == '# keep me\n'
        inp = rename('lessons/deep/renamed.asm')
        inp.fill('taken.asm'); inp.press('Enter')
        page.get_by_text('already exists', exact=False).first.wait_for()
        assert page.evaluate("MarsIDBFS.read('lessons/deep/taken.asm').then(r=>r.text)") == '# other\n'
        inp = rename('lessons/deep')
        assert inp.input_value() == 'deep'
        inp.fill('renamed-folder'); inp.press('Enter')
        page.locator('.node[data-p="lessons/renamed-folder/renamed.asm"]').wait_for()
        assert page.evaluate("MarsIDBFS.read('lessons/renamed-folder/renamed.asm').then(r=>r.text)") == '# keep me\n'
        browser.close(); print('rename: basename, nested files/folders, conflicts and invalid names OK')
finally:
    if server:
        server.terminate(); server.wait()
