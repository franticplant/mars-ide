"""Emacs navigation and breakpoints with line numbers hidden."""
import os
import subprocess
from playwright.sync_api import sync_playwright

BASE = os.environ.get('BASE', 'http://127.0.0.1:8096/')
server = subprocess.Popen(['python3', '-m', 'http.server', '8096', '-d', '/static'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if 'BASE' not in os.environ else None
CODE = '.data\na: .word 1\n.text\n.globl main\nmain:\n  li $t0, 1\n  li $t1, 2\n  add $t2, $t0, $t1\n  li $v0, 10\n  syscall\n'
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':1300, 'height':800})
        page.goto(BASE); page.wait_for_function('window.MarsIDE && MarsIDE.engine.connected && MarsIDE.S.current', timeout=30000)
        page.evaluate("code => MarsIDE.engine.call('fs_write',{path:'emacs.asm',text:code})", CODE)
        page.click('#btn-side'); page.click('#btn-refresh')
        page.locator('.node[data-p="emacs.asm"]').click(); page.wait_for_function("MarsIDE.S.current === 'emacs.asm'")
        page.keyboard.press('F3'); page.wait_for_function('() => MarsIDE.R.assembled')
        page.click('#btn-settings')
        page.locator('input[data-k="emacs"]').check()
        page.locator('input[data-k="lineNumbers"]').uncheck()
        page.get_by_role('button', name='Done', exact=True).click()
        assert page.evaluate("MarsIDE.S.emacs")
        assert page.locator('#app.no-lines').count() == 1
        assert page.locator('.active-group .ed-gutter').is_visible()
        assert page.evaluate("getComputedStyle(document.querySelector('.active-group .ed-gutter .g')).fontSize") == '0px'
        page.evaluate("MarsIDE.groups.active.editor.goTo(1,1)")
        def state(): return page.evaluate("(() => {const e=MarsIDE.groups.active.editor;return {line:e.cursor.line,col:e.cursor.col,start:e.ta.selectionStart,end:e.ta.selectionEnd}})()")
        assert state()['col'] == 1
        page.keyboard.press('Control+f'); assert state()['col'] == 2
        page.keyboard.press('Control+b'); assert state()['col'] == 1
        page.keyboard.press('Control+n'); assert state()['line'] == 2
        page.keyboard.press('Control+p'); assert state()['line'] == 1
        page.keyboard.press('Control+e'); assert state()['col'] == 6
        page.keyboard.press('Control+a'); assert state()['col'] == 1
        page.evaluate("MarsIDE.groups.active.editor.goTo(6,1)")
        page.keyboard.press('Alt+f'); assert state()['col'] > 1
        page.keyboard.press('Alt+b'); assert state()['col'] == 3
        page.keyboard.press('Alt+Shift+,')
        assert state()['line'] == 1 and state()['col'] == 1
        page.keyboard.press('Alt+Shift+.')
        assert page.evaluate("(() => { const e=MarsIDE.groups.active.editor; return e.ta.selectionStart === e.ta.value.length; })()")
        page.keyboard.down('Alt'); page.keyboard.press('g'); page.keyboard.up('Alt'); page.keyboard.press('g')
        page.locator('.modal input.text').fill('3'); page.locator('.modal input.text').press('Enter')
        assert state()['line'] == 3
        page.keyboard.press('Control+F8')
        assert page.evaluate("MarsIDE.S.bps['emacs.asm']").count(3) == 1
        page.locator('.active-group .g[data-line="4"]').click()
        assert 4 in page.evaluate("MarsIDE.S.bps['emacs.asm']")
        assert page.locator('.active-group .ed-hl .l').nth(3).evaluate("el => el.classList.contains('bp')")
        page.evaluate("MarsIDE.groups.active.editor.goTo(8,1)")
        page.keyboard.press('Control+F8')
        assert 8 in page.evaluate("MarsIDE.S.bps['emacs.asm']")
        page.evaluate("MarsIDE.groups.active.editor.goTo(5,1)")
        page.keyboard.press('F4')
        assert 5 in page.evaluate("MarsIDE.S.bps['emacs.asm']")
        page.keyboard.press('F4')
        assert 5 not in page.evaluate("MarsIDE.S.bps['emacs.asm']")
        # Normal save remains available (no Emacs C-x prefix is required).
        page.locator('.active-group textarea').fill(CODE + '# saved\n')
        page.keyboard.press('Control+s')
        page.wait_for_function("() => MarsIDE.R.files.get('emacs.asm').saved === MarsIDE.R.files.get('emacs.asm').text", timeout=10000)
        assert page.evaluate("MarsIDE.R.files.get('emacs.asm').saved").endswith('# saved\n')
        page.reload(); page.wait_for_function('window.MarsIDE && MarsIDE.engine.connected && MarsIDE.S.current', timeout=30000)
        assert page.evaluate("MarsIDE.S.lineNumbers === false")
        assert page.locator('.active-group .ed-gutter').is_visible()
        assert page.evaluate("MarsIDE.S.bps['emacs.asm']").count(3) == 1
        browser.close(); print('Emacs basic navigation, goto, save and breakpoints without line numbers OK')
finally:
    if server:
        server.terminate(); server.wait()
