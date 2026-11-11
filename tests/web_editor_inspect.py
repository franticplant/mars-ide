"""Ctrl-click runtime inspection is compact, token-first and state-honest."""
import os
import subprocess
from playwright.sync_api import sync_playwright

BASE = os.environ.get('BASE', 'http://127.0.0.1:8096/')
server = subprocess.Popen(['python3', '-m', 'http.server', '8096', '-d', '/static'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if 'BASE' not in os.environ else None
CODE = '.data\nmsg: .asciiz "hello"\n.text\n.globl main\nmain:\n  li $t0, 7\n  la $t1, msg\n  li $v0, 10\n  syscall\n'
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':1300, 'height':800})
        page.goto(BASE); page.wait_for_function('window.MarsIDE && MarsIDE.engine.connected && MarsIDE.S.current', timeout=30000)
        page.evaluate("code => MarsIDE.engine.call('fs_write',{path:'inspect.asm',text:code})", CODE)
        page.click('#btn-side'); page.click('#btn-refresh')
        page.locator('.node[data-p="inspect.asm"]').click()
        page.wait_for_function("MarsIDE.S.current === 'inspect.asm'")
        page.keyboard.press('F3'); page.wait_for_function('() => MarsIDE.R.assembled')
        page.keyboard.press('F7'); page.wait_for_function('() => MarsIDE.R.state.gpr[8] === 7')
        for _ in range(4):
            if page.evaluate('MarsIDE.R.state.gpr[9]') != 0: break
            page.keyboard.press('F7'); page.wait_for_timeout(100)
        assert page.evaluate('MarsIDE.R.state.gpr[9]') != 0
        def point(needle, nth=0):
            return page.evaluate("""([needle,nth]) => {
              const ed=MarsIDE.groups.active.editor, text=ed.value.split('\\n');
              let seen=0;
              for (let i=0;i<text.length;i++) {
                let at=-1; while ((at=text[i].indexOf(needle, at+1)) >= 0) {
                  if (seen++ === nth) { const r=ed.ta.getBoundingClientRect();
                    return {x:r.left+ed.padLeft+(at+needle.length/2)*ed.cw-ed.ta.scrollLeft,
                            y:r.top+ed.padTop+(i+.5)*ed.lh-ed.ta.scrollTop}; }
                }
              }
              return null;
            }""", [needle,nth])
        def ctrl_click(pos):
            page.keyboard.down('Control'); page.mouse.click(pos['x'], pos['y']); page.keyboard.up('Control')
        ctrl_click(point('$t1'))
        card = page.locator('.inspector.compact'); card.wait_for()
        assert '$t1' in card.inner_text() and '0x' in card.inner_text(), card.inner_text()
        assert 'hello' in card.inner_text(), card.inner_text()
        page.keyboard.press('Escape')
        ctrl_click(point('msg'))
        card.wait_for(); txt = card.inner_text()
        assert 'label' in txt and 'hello' in txt and 'word' in txt, txt
        page.keyboard.press('Escape')
        # Paused and waiting-for-input accents are quiet, not animated/full-bright bars.
        for cls in ('st-paused', 'st-input'):
            style = page.evaluate("""cls => { const a=document.querySelector('#app'); a.classList.add(cls);
              const s=getComputedStyle(document.querySelector('.topbar'),'::after');
              const out={animation:s.animationName,bg:s.backgroundColor}; a.classList.remove(cls); return out; }""", cls)
            assert style['animation'] == 'none', (cls, style)
            assert 'rgba' in style['bg'] or '/ 0.14' in style['bg'], (cls, style)
        browser.close(); print('Ctrl-click token values, label contents and quiet state accents OK')
finally:
    if server:
        server.terminate(); server.wait()
