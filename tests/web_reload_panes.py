"""Regression: restoring mixed preview/source groups must never overwrite documents."""
import os
import subprocess
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8096/")
server = subprocess.Popen(["python3", "-m", "http.server", "8096", "-d", "/static"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if "BASE" not in os.environ else None
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        for vim in (False,):
            for active in ("preview", "source"):
                for drafts in (False, True):
                  for reversed_order in (False, True):
                    page = browser.new_page(viewport={"width": 1300, "height": 850})
                    errors = []
                    page.on("pageerror", lambda e: errors.append(str(e)))
                    page.goto(BASE)
                    page.wait_for_function("window.MarsIDE && MarsIDE.engine.connected && MarsIDE.S.current", timeout=30000)
                    page.add_init_script("""try {
                      const raw = sessionStorage.getItem('reload-test-setup');
                      if (raw) {
                        const setup = JSON.parse(raw); sessionStorage.removeItem('reload-test-setup');
                        localStorage.setItem('marside.v1', JSON.stringify(setup.state));
                        localStorage.setItem('marside.v1.drafts', JSON.stringify(setup.drafts));
                        localStorage.removeItem('marside.v1.draft-versions');
                      }
                    } catch (_) {}""")
                    page.evaluate("""async ({vim, active, drafts, reversedOrder}) => {
                      const md = '# Preview sentinel\\nMarkdown stays here.\\n';
                      const asm = '.text\\nmain: li $v0, 10\\n  syscall\\n# CODE sentinel\\n';
                      await MarsIDE.engine.call('fs_write', {path:'reload-test.md',text:md});
                      await MarsIDE.engine.call('fs_write', {path:'reload-test.asm',text:asm});
                      const s = JSON.parse(localStorage.getItem('marside.v1'));
                      s.open = ['reload-test.md', 'reload-test.asm'];
                      s.current = active === 'preview' ? 'reload-test.md' : 'reload-test.asm';
                      s.layout = {axis:'row',ratio:.5,
                        first:{tabs:[{path:'reload-test.md',mode:'preview'}],index:0,active:active==='preview'},
                        second:{tabs:[{path:'reload-test.asm',mode:'source'}],index:0,active:active==='source'}};
                      if (reversedOrder) [s.layout.first, s.layout.second] = [s.layout.second, s.layout.first];
                      sessionStorage.setItem('reload-test-setup', JSON.stringify({state:s, drafts:drafts ? {
                        'reload-test.md': md + 'MD draft\\n', 'reload-test.asm': asm + '# ASM draft\\n'
                      } : {}}));
                    }""", {"vim": vim, "active": active, "drafts": drafts, "reversedOrder": reversed_order})
                    for repeat in range(2):
                        page.reload()
                        page.wait_for_function("""() => window.MarsIDE && MarsIDE.groups.groups.length === 2 &&
                          MarsIDE.R.files.has('reload-test.md') && MarsIDE.R.files.has('reload-test.asm') &&
                          MarsIDE.groups.groups.some(g => g.preview && g.previewHost)""", timeout=30000)
                        result = page.evaluate("""async () => ({
                          md:MarsIDE.R.files.get('reload-test.md').text,
                          asm:MarsIDE.R.files.get('reload-test.asm').text,
                          storedMd:(await MarsIDE.engine.call('fs_read',{path:'reload-test.md'})).text,
                          storedAsm:(await MarsIDE.engine.call('fs_read',{path:'reload-test.asm'})).text,
                          groups:MarsIDE.groups.groups.map(g=>({tab:MarsIDE.groups.tab(g), text:g.editor.value})),
                          active:MarsIDE.S.current
                        })""")
                        want_md = '# Preview sentinel\nMarkdown stays here.\n' + ('MD draft\n' if drafts else '')
                        want_asm = '.text\nmain: li $v0, 10\n  syscall\n# CODE sentinel\n' + ('# ASM draft\n' if drafts else '')
                        label = f'active={active} drafts={drafts} reversed={reversed_order} reload={repeat}'
                        assert result['md'] == want_md, (label, result)
                        assert result['asm'] == want_asm, (label, result)
                        assert result['storedMd'] == '# Preview sentinel\nMarkdown stays here.\n', (label, result)
                        assert result['storedAsm'] == '.text\nmain: li $v0, 10\n  syscall\n# CODE sentinel\n', (label, result)
                        preview, source = (result['groups'][1], result['groups'][0]) if reversed_order else result['groups']
                        assert preview['tab']['mode'] == 'preview', (label, result)
                        assert source['tab']['path'] == 'reload-test.asm', (label, result)
                        assert source['text'] == want_asm, (label, result)
                        assert result['active'] == ('reload-test.md' if active == 'preview' else 'reload-test.asm'), (label, result)
                        assert not errors, (label, errors)
                    edited = page.evaluate("""() => {
                      const group = MarsIDE.groups.groups.find(g => MarsIDE.groups.tab(g)?.path === 'reload-test.asm');
                      MarsIDE.groups.activate(group);
                      const ed = group.editor;
                      ed.ta.setSelectionRange(ed.value.length, ed.value.length);
                      ed.insert('# isolated edit\\n');
                      return {md:MarsIDE.R.files.get('reload-test.md').text, asm:MarsIDE.R.files.get('reload-test.asm').text};
                    }""")
                    assert edited['md'] == want_md and edited['asm'] == want_asm + '# isolated edit\n', (label, edited)
                    page.close()
        browser.close()
        print('mixed preview/source restore: saved and draft data, both active panes: OK')
finally:
    if server:
        server.terminate(); server.wait()
