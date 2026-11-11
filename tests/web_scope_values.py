"""Scope values: one inline label-header summary, readable/hex/off."""
import os
import subprocess
from playwright.sync_api import sync_playwright

BASE = os.environ.get('BASE', 'http://127.0.0.1:8096/')
server = subprocess.Popen(['python3', '-m', 'http.server', '8096', '-d', '/static'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if 'BASE' not in os.environ else None
CODE = '.data\nmsg: .asciiz "hello"\n.text\n.globl main\nmain:\n  li $t0, 7\n  la $t1, msg\n  li $v0, 10\n  syscall\nother:\n  li $t2, 9\n  li $v0, 10\n  syscall\n'
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':1300, 'height':800})
        page.goto(BASE); page.wait_for_function('window.MarsIDE && MarsIDE.engine.connected && MarsIDE.S.current', timeout=30000)
        page.evaluate("code => MarsIDE.engine.call('fs_write',{path:'scope.asm',text:code})", CODE)
        page.click('#btn-side'); page.click('#btn-refresh'); page.locator('.node[data-p="scope.asm"]').click()
        page.wait_for_function("MarsIDE.S.current === 'scope.asm'")
        page.keyboard.press('F3'); page.wait_for_function('() => MarsIDE.R.assembled')
        for _ in range(4):
            if page.evaluate('MarsIDE.R.state.gpr[9]') != 0: break
            page.keyboard.press('F7'); page.wait_for_timeout(80)
        assert page.evaluate('MarsIDE.R.state.gpr[9]') != 0
        assert page.locator('.active-group .scope-values').count() == 0
        page.keyboard.down('Control'); page.keyboard.down('Shift'); page.keyboard.press(';')
        page.keyboard.up('Shift'); page.keyboard.up('Control')
        assert page.evaluate('MarsIDE.S.scopeValues') == 1
        ann = page.locator('.active-group .scope-values'); ann.wait_for()
        text = ann.inner_text()
        assert '$t0=7' in text and '$t1=msg' in text, text
        assert page.locator('.active-group .ed-hl .l').nth(4).locator('.scope-values').count() == 1
        assert page.locator('.active-group .scope-values').count() == 1
        page.keyboard.down('Control'); page.keyboard.down('Shift'); page.keyboard.press(';')
        page.keyboard.up('Shift'); page.keyboard.up('Control')
        assert page.evaluate('MarsIDE.S.scopeValues') == 2
        assert '$t0=0x00000007' in page.locator('.active-group .scope-values').inner_text()
        page.keyboard.down('Control'); page.keyboard.down('Shift'); page.keyboard.press(';')
        page.keyboard.up('Shift'); page.keyboard.up('Control')
        assert page.evaluate('MarsIDE.S.scopeValues') == 0
        assert page.locator('.active-group .scope-values').count() == 0
        browser.close(); print('scope values: label-header summary, readable/hex/off, single line OK')
finally:
    if server:
        server.terminate(); server.wait()
