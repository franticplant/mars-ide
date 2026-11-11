"""Console tails only while pinned to the bottom; scrolling up preserves position."""
import os
import subprocess
from playwright.sync_api import sync_playwright

BASE = os.environ.get('BASE', 'http://127.0.0.1:8096/')
server = subprocess.Popen(['python3', '-m', 'http.server', '8096', '-d', '/static'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if 'BASE' not in os.environ else None
CODE = ('.text\n.globl main\nmain:\n'
        '  li $t0, 0\n  li $t1, 300\n'
        'loop:\n  li $v0, 1\n  move $a0, $t0\n  syscall\n'
        '  li $v0, 11\n  li $a0, 10\n  syscall\n'
        '  addiu $t0, $t0, 1\n  bne $t0, $t1, loop\n'
        '  li $v0, 10\n  syscall\n')
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':1300, 'height':800})
        page.goto(BASE); page.wait_for_function('window.MarsIDE && MarsIDE.engine.connected && MarsIDE.S.current', timeout=30000)
        page.evaluate("code => MarsIDE.engine.call('fs_write',{path:'tail.asm',text:code})", CODE)
        page.click('#btn-side'); page.click('#btn-refresh'); page.locator('.node[data-p="tail.asm"] .nm').click()
        page.wait_for_function("MarsIDE.S.current === 'tail.asm'")
        page.keyboard.press('F3'); page.wait_for_function('() => MarsIDE.R.assembled')
        page.keyboard.press('F5'); page.wait_for_function('() => MarsIDE.R.finished', timeout=60000)
        def at_bottom():
            return page.evaluate("() => { const o=document.querySelector('#out'); return o.scrollTop + o.clientHeight >= o.scrollHeight - 4; }")
        assert at_bottom(), 'new output should leave the console pinned at the bottom'
        page.evaluate("() => { const o=document.querySelector('#out'); o.scrollTop=0; o.dispatchEvent(new Event('scroll')); }")
        page.wait_for_timeout(100)
        page.keyboard.press('Shift+F12'); page.wait_for_function('() => !MarsIDE.R.finished')
        page.keyboard.press('F5'); page.wait_for_function('() => MarsIDE.R.finished', timeout=60000)
        assert not at_bottom(), 'console should not jump down after the user scrolled up'
        page.evaluate("() => { const o=document.querySelector('#out'); o.scrollTop=o.scrollHeight; o.dispatchEvent(new Event('scroll')); }")
        page.wait_for_timeout(100)
        page.keyboard.press('Shift+F12'); page.wait_for_function('() => !MarsIDE.R.finished')
        page.keyboard.press('F5'); page.wait_for_function('() => MarsIDE.R.finished', timeout=60000)
        assert at_bottom(), 'scrolling back to the bottom should re-enable tailing'
        browser.close(); print('console tail: bottom-follow, scroll-up hold, re-engage OK')
finally:
    if server:
        server.terminate(); server.wait()
