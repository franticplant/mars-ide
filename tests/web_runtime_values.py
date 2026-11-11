"""Runtime operand inspection and mobile navigation around keyboard geometry."""
import os, shutil, subprocess
from playwright.sync_api import sync_playwright

WS = "/tmp/ws-runtime-values"
shutil.rmtree(WS, ignore_errors=True); os.makedirs(WS)
with open(WS + "/inspect.asm", "w") as f:
    f.write(".data\nvalue: .word 42\n.text\n.globl main\nmain:\n  li $t0, 7\n  addiu $t1, $t0, 3\n  la $t2, value\n  lw $t3, 0($t2)\n  li $v0, 10\n  syscall\n")
srv = subprocess.Popen(["java", "-jar", "/build/mars-engine.jar", "--no-auth", "--port", "8093", "--root", WS, "--web", "/web"], stdout=subprocess.PIPE, text=True)
srv.stdout.readline(); srv.stdout.readline()
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1400, "height": 860})
        errors = []; page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto("http://127.0.0.1:8093/"); page.wait_for_selector(".ftab")
        page.keyboard.press("F3"); page.wait_for_function('() => MarsIDE.R.assembled'); page.locator('.tab[data-v="exec"]').click()
        row = page.locator('#exec-wrap tr[data-i]').filter(has_text="$t1").first
        before = page.evaluate("JSON.stringify(MarsIDE.S.bps)")
        row.locator('td.basic').dblclick()
        dialog = page.locator('.instruction-inspector')
        dialog.wait_for(); assert "$t0" in dialog.inner_text() and "$t1" in dialog.inner_text(), dialog.inner_text()
        assert "not historical" in dialog.inner_text()
        assert page.evaluate("JSON.stringify(MarsIDE.S.bps)") == before
        page.keyboard.press("Escape")
        row.locator('td.basic').focus(); page.keyboard.press('Enter')
        dialog.wait_for(); page.keyboard.press('Escape')
        page.keyboard.press('F7')
        page.locator('.tab[data-v="edit"]').click()
        page.locator('#runtime-values').wait_for()
        assert '$t0' in page.locator('#runtime-values').inner_text()
        assert '0x00000007' in page.locator('#runtime-values').inner_text()
        page.locator('#runtime-values .runtime-detail').click(); dialog.wait_for()
        page.keyboard.press('Escape')
        page.evaluate("""() => { const t=document.querySelector('#editor textarea'); const p=t.value.indexOf('addiu'); t.focus(); t.setSelectionRange(p,p); t.dispatchEvent(new MouseEvent('dblclick',{bubbles:true})); }""")
        dialog.wait_for()
        page.keyboard.press('Escape')
        # Step to the load so its base address and memory contents are real current state.
        page.locator('.tab[data-v="exec"]').click()
        for _ in range(3):
            page.keyboard.press('F7'); page.wait_for_timeout(80)
        load = page.locator('#exec-wrap tr[data-i]').filter(has_text='lw $t3').first
        load.locator('td.basic').click()
        page.locator('.instruction-memory').wait_for()
        page.wait_for_function("() => document.querySelector('.instruction-memory')?.textContent.includes('0x0000002a')")
        page.keyboard.press('Escape')
        page.locator('.tab[data-v="help"]').click()
        page.locator('#help-filter').fill('=lw')
        page.locator('#help-list tr[data-m="lw"]').click()
        assert 'lw    $t1, 0($t0)' in page.locator('tr.encrow[data-for="lw"]').inner_text()
        assert page.locator('tr.encrow[data-for="lw"] .enc').is_visible()
        page.locator('#help-filter').fill('=move')
        page.locator('#help-list tr[data-m="move"]').click()
        assert 'move  $t1, $t0' in page.locator('tr.encrow[data-for="move"]').inner_text()
        # Check every curated example against the real MARS assembler, not just HTML rendering.
        failures = page.evaluate("""async () => {
          const failures=[];
          for (const [name, snippet] of Object.entries(MIPS_EXAMPLES)) {
            const text='.text\\n.globl main\\nmain:\\n'+snippet+'\\n  nop\\n';
            await MarsIDE.engine.call('fs_write',{path:'_example_check.asm',text});
            const result=await MarsIDE.engine.call('assemble',{files:['_example_check.asm'],main:'_example_check.asm',settings:{pseudo:true}});
            if(!result.success) failures.push([name,result.messages]);
          }
          await MarsIDE.engine.call('fs_delete',{path:'_example_check.asm'});
          return failures;
        }""")
        assert not failures, failures
        assert not errors, errors
        page.close()
        context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        context.add_init_script("""window.__fakeVK=new EventTarget(); __fakeVK.boundingRect={height:0,top:844}; Object.defineProperty(navigator,'virtualKeyboard',{value:__fakeVK,configurable:true});""")
        phone = context.new_page()
        phone.goto('http://127.0.0.1:8093/'); phone.wait_for_selector('.ftab', state='attached')
        phone.tap('[data-act="assemble"]')
        phone.wait_for_function('() => MarsIDE.R.assembled'); phone.tap('#bottomnav [data-m="exec"]')
        basic = phone.locator('#exec-wrap tr[data-i] td.basic').first
        basic.tap()
        phone.locator('.instruction-inspector').wait_for()
        assert phone.evaluate("MarsIDE.S.m") == 'exec', 'tapping Basic must not navigate to source'
        phone.locator('.instruction-inspector .ins-x').tap()
        phone.tap('#bottomnav [data-m="edit"]')
        phone.locator('.active-group .group-actions').get_by_role('button', name="Inspect the current source line's runtime values").wait_for()
        phone.evaluate("""() => {const t=document.querySelector('.active-group textarea'); const p=t.value.indexOf('addiu'); t.focus(); t.setSelectionRange(p,p);} """)
        phone.locator('.active-group .group-actions').get_by_role('button', name="Inspect the current source line's runtime values").tap()
        phone.locator('.instruction-inspector').wait_for()
        phone.locator('.instruction-inspector .ins-x').tap()
        phone.locator('#editor textarea').focus()
        assert phone.locator('#bottomnav').is_visible(), 'focus alone must not hide navigation'
        phone.evaluate("__fakeVK.boundingRect={height:300,top:544}; __fakeVK.dispatchEvent(new Event('geometrychange'))")
        assert phone.evaluate("document.querySelector('#app').classList.contains('keyboard-open')")
        assert phone.evaluate("Math.abs(document.querySelector('#bottomnav').getBoundingClientRect().bottom - 844) < 3"), 'navigation stays behind the keyboard'
        assert phone.evaluate("document.querySelector('#keybar').getBoundingClientRect().bottom <= 545"), 'key row stays above the keyboard'
        phone.evaluate("__fakeVK.boundingRect={height:0,top:844}; __fakeVK.dispatchEvent(new Event('geometrychange'))")
        assert phone.evaluate("document.activeElement === document.querySelector('#editor textarea')"), 'Android can dismiss the keyboard without blurring'
        assert phone.locator('#bottomnav').is_visible()
        assert phone.evaluate("!document.querySelector('#app').classList.contains('keyboard-open')")
        assert phone.evaluate("Math.abs(document.querySelector('#bottomnav').getBoundingClientRect().bottom - innerHeight) < 3")
        phone.locator('#keybar [data-k="kbd"]').tap()
        assert phone.locator('#bottomnav').is_visible(), 'hiding keyboard must reveal navigation'
        assert phone.evaluate("Math.abs(document.querySelector('#bottomnav').getBoundingClientRect().bottom - innerHeight) < 3")
        phone.tap('#bottomnav [data-m="exec"]')
        assert phone.evaluate("MarsIDE.S.m") == 'exec'
        fallback_context = browser.new_context(viewport={"width":390,"height":844}, is_mobile=True, has_touch=True)
        fallback_context.add_init_script("""window.__fakeViewport=new EventTarget(); __fakeViewport.height=844; __fakeViewport.offsetTop=0; Object.defineProperty(window,'visualViewport',{value:__fakeViewport,configurable:true}); Object.defineProperty(navigator,'virtualKeyboard',{value:undefined,configurable:true});""")
        fallback = fallback_context.new_page(); fallback.goto('http://127.0.0.1:8093/')
        fallback.wait_for_selector('.ftab', state='attached'); fallback.locator('#editor textarea').focus()
        fallback.evaluate("__fakeViewport.height=544; __fakeViewport.dispatchEvent(new Event('resize'))")
        assert fallback.evaluate("document.querySelector('#app').classList.contains('keyboard-open')")
        fallback.evaluate("__fakeViewport.height=844; __fakeViewport.dispatchEvent(new Event('resize'))")
        assert fallback.locator('#bottomnav').is_visible()
        assert fallback.evaluate("!document.querySelector('#app').classList.contains('keyboard-open')")
        assert fallback.evaluate("Math.abs(document.querySelector('#bottomnav').getBoundingClientRect().bottom - innerHeight) < 3")
        browser.close()
finally:
    srv.terminate(); srv.wait(timeout=10)
print('runtime instruction values / mobile navigation: ok')
