"""Zen can always be exited on a phone and never strands a reload."""
import http.server, os, shutil, subprocess, threading
from functools import partial
from playwright.sync_api import sync_playwright

WS = "/tmp/ws-zen"
shutil.rmtree(WS, ignore_errors=True); os.makedirs(WS)
shutil.copy('/examples/hello.asm', WS)
server = subprocess.Popen(['java', '-jar', '/build/mars-engine.jar', '--no-auth', '--port', '8092', '--root', WS, '--web', '/web'], stdout=subprocess.PIPE, text=True)
server.stdout.readline(); server.stdout.readline()
httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 8091), partial(http.server.SimpleHTTPRequestHandler, directory='/static'))
threading.Thread(target=httpd.serve_forever, daemon=True).start()

def enter_from_files(page):
    page.tap('#btn-side')
    assert page.evaluate('MarsIDE.S.m') == 'files'
    page.tap('#bottomnav [data-m=more]')
    page.locator('.sheet-grid [data-k=zen]').tap()
    page.locator('#app.zen').wait_for()
    assert page.evaluate('MarsIDE.S.m') == 'edit', 'Zen must not hide navigation while leaving Files on screen'

try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        for static in [False, True]:
            ctx = browser.new_context(viewport={'width':390,'height':844}, is_mobile=True, has_touch=True)
            ctx.add_init_script("""window.__fakeVK=new EventTarget(); __fakeVK.boundingRect={height:0,top:844}; Object.defineProperty(navigator,'virtualKeyboard',{value:__fakeVK,configurable:true});""")
            page = ctx.new_page(); errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto('http://127.0.0.1:8091/' if static else 'http://127.0.0.1:8092/')
            page.wait_for_selector('.ftab', state='attached')
            page.keyboard.press('Control+Backslash')
            assert page.locator('.editor-group').count() == 2
            enter_from_files(page)
            exit_button = page.get_by_role('button', name='Exit zen mode')
            assert exit_button.is_visible()
            assert exit_button.bounding_box()['y'] < 60, 'Exit remains visible above the on-screen keyboard'
            # The escape affordance stays tappable while the editor is focused / IME open.
            page.locator('.active-group textarea').focus()
            page.evaluate("__fakeVK.boundingRect={height:300,top:544}; __fakeVK.dispatchEvent(new Event('geometrychange'))")
            exit_button.tap()
            assert not page.evaluate('MarsIDE.S.zen')
            assert page.evaluate('MarsIDE.S.m') == 'files'
            assert page.locator('#sidebar').is_visible()
            assert page.locator('.editor-group').count() == 2
            page.evaluate("__fakeVK.boundingRect={height:0,top:844}; __fakeVK.dispatchEvent(new Event('geometrychange'))")
            page.tap('#btn-side')
            # The Settings checkbox must use the same reversible Zen path.
            page.tap('#btn-settings')
            page.locator('.modal input[data-k="zen"]').check()
            page.locator('.modal header [data-close]').tap()
            assert exit_button.is_visible()
            exit_button.tap()
            assert page.locator('#bottomnav').is_visible()
            page.locator('.active-group textarea').fill('# draft survives zen reload')
            page.wait_for_timeout(700)
            enter_from_files(page)
            page.reload(); page.wait_for_selector('.ftab', state='attached')
            assert not page.evaluate('MarsIDE.S.zen'), 'Reload must escape Zen'
            assert page.locator('#bottomnav').is_visible()
            assert page.evaluate('MarsIDE.S.m') == 'files'
            assert page.locator('.editor-group').count() == 2
            page.tap('#btn-side')
            assert page.locator('.active-group textarea').input_value() == '# draft survives zen reload'
            assert not errors, errors
            ctx.close()
        browser.close()
finally:
    server.terminate(); server.wait(timeout=10); httpd.shutdown()
print('mobile Zen: visible exit, restore, keyboard and reload; server + static: ok')
