"""Assemble and run retain the current view; running has no animated streak."""
import os
import subprocess
from playwright.sync_api import sync_playwright

BASE = os.environ.get('BASE', 'http://127.0.0.1:8096/')
server = subprocess.Popen(['python3', '-m', 'http.server', '8096', '-d', '/static'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if 'BASE' not in os.environ else None
CODE = '.data\nmsg: .asciiz "done"\n.text\n.globl main\nmain: li $v0,4\nla $a0,msg\nsyscall\nli $v0,10\nsyscall\n'
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        for mobile in (False, True):
            context = browser.new_context(viewport={'width':390 if mobile else 1300, 'height':800}, is_mobile=mobile, has_touch=mobile)
            page = context.new_page(); page.goto(BASE)
            page.wait_for_function('window.MarsIDE && MarsIDE.engine.connected && MarsIDE.S.current', timeout=30000)
            page.evaluate("code => MarsIDE.engine.call('fs_write',{path:'stay-edit.asm',text:code})", CODE)
            page.locator('#btn-side').click(); page.locator('#btn-refresh').click()
            page.locator('.node[data-p="stay-edit.asm"]').click()
            page.wait_for_function("MarsIDE.S.current === 'stay-edit.asm'")
            page.keyboard.press('F3'); page.wait_for_function('MarsIDE.R.assembled')
            assert page.evaluate("MarsIDE.S.view === 'edit' && MarsIDE.S.m === 'edit'"), 'assemble switched views'
            page.keyboard.press('F5'); page.wait_for_function('MarsIDE.R.finished', timeout=30000)
            assert page.evaluate("MarsIDE.S.view === 'edit' && MarsIDE.S.m === 'edit'"), 'run switched views'
            if not mobile:
                assert page.locator('#console').is_visible(), 'run should still open the console'
                page.locator('.tab[data-v="labels"]').click()
                page.evaluate("MarsIDE.engine.emit({ev:'stopped',reason:'breakpoint',state:MarsIDE.R.state})")
                assert page.evaluate("MarsIDE.S.view === 'labels'"), 'breakpoint switched views'
                assert page.evaluate("""() => {
                  const app=document.querySelector('#app'); app.classList.add('st-running');
                  return getComputedStyle(document.querySelector('.topbar'),'::after').animationName === 'none';
                }""")
            context.close()
        browser.close(); print('assemble/run retain editor; breakpoint retains view; no animated running streak')
finally:
    if server:
        server.terminate(); server.wait()
