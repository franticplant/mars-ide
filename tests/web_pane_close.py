"""Closing the last view in a split must collapse the empty pane."""
import os
import subprocess
from itertools import product
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8096/")
server = subprocess.Popen(["python3", "-m", "http.server", "8096", "-d", "/static"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if "BASE" not in os.environ else None
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        for closing_side, active_side, dirty, method in product(('left','right'), ('left','right'), (False,True), ('group','global')):
                    page = browser.new_page(viewport={"width": 1300, "height": 800})
                    page.goto(BASE)
                    page.wait_for_function("window.MarsIDE && MarsIDE.engine.connected && MarsIDE.S.current", timeout=30000)
                    page.evaluate("""async () => {
                      await MarsIDE.engine.call('fs_write', {path:'pane-a.asm',text:'# a\\n'});
                      await MarsIDE.engine.call('fs_write', {path:'pane-b.asm',text:'# b\\n'});
                    }""")
                    page.click('#btn-side'); page.click('#btn-refresh')
                    page.locator('.node[data-p="pane-a.asm"]').click()
                    page.wait_for_function("MarsIDE.R.files.has('pane-a.asm') && MarsIDE.S.current === 'pane-a.asm'")
                    page.locator('.node[data-p="pane-b.asm"]').click()
                    page.wait_for_function("MarsIDE.R.files.has('pane-b.asm') && MarsIDE.S.current === 'pane-b.asm'")
                    page.evaluate("""active => MarsIDE.groups.restore({axis:'row',ratio:.5,
                      first:{tabs:[{path:'pane-a.asm',mode:'source'}],index:0,active:active==='left'},
                      second:{tabs:[{path:'pane-b.asm',mode:'source'}],index:0,active:active==='right'}})""", active_side)
                    page.wait_for_function('MarsIDE.groups.groups.length === 2')
                    target = 'pane-a.asm' if closing_side == 'left' else 'pane-b.asm'
                    other = 'pane-b.asm' if closing_side == 'left' else 'pane-a.asm'
                    if dirty:
                        page.evaluate("""path => {
                          const g=MarsIDE.groups.groups.find(g=>MarsIDE.groups.tab(g)?.path===path);
                          MarsIDE.groups.activate(g); g.editor.ta.focus(); g.editor.ta.value += '# dirty\\n';
                          g.editor.ta.dispatchEvent(new Event('input',{bubbles:true}));
                        }""", target)
                    button = (page.locator('.group-tab').filter(has=page.locator(f'[title="{target}"]')).locator('[data-close]')
                              if method == 'group' else page.locator(f'#filetabs .ftab[data-p="{target}"] .x'))
                    if dirty:
                        button.click(); page.get_by_role('button', name='Cancel', exact=True).click()
                        assert page.evaluate('MarsIDE.groups.groups.length') == 2
                    button.click()
                    if dirty: page.get_by_role('button', name='Discard', exact=True).click()
                    page.wait_for_function('MarsIDE.groups.groups.length === 1', timeout=10000)
                    result = page.evaluate("""() => ({groups:MarsIDE.groups.groups.length,
                      paths:MarsIDE.groups.groups.map(g=>MarsIDE.groups.tab(g)?.path), current:MarsIDE.S.current})""")
                    assert result['groups'] == 1 and result['paths'] == [other], (closing_side, active_side, dirty, method, result)
                    page.close()
        for empty_side in ('left', 'right'):
            page = browser.new_page(viewport={"width":1300,"height":800})
            page.goto(BASE); page.wait_for_function("window.MarsIDE && MarsIDE.engine.connected && MarsIDE.S.current", timeout=30000)
            page.evaluate("""empty => {
              const p=MarsIDE.S.current, blank={tabs:[],index:0,active:true}, full={tabs:[{path:p,mode:'source'}],index:0,active:false};
              MarsIDE.groups.restore({axis:'row',ratio:.5,first:empty==='left'?blank:full,second:empty==='right'?blank:full});
            }""", empty_side)
            assert page.evaluate("MarsIDE.groups.groups.length") == 1
            page.close()
        browser.close()
        print('empty split closes: left/right, active/inactive, clean/dirty and cancel OK')
finally:
    if server:
        server.terminate(); server.wait()
