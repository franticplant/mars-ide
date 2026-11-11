"""A surviving pane must fill its parent after a real UI split is closed."""
import os
import subprocess
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8096/")
server = subprocess.Popen(["python3", "-m", "http.server", "8096", "-d", "/static"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if "BASE" not in os.environ else None
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        for edge in ('right', 'bottom'):
            for side in (0, 1):
                page = browser.new_page(viewport={"width":1300, "height":800})
                page.goto(BASE)
                page.wait_for_function("window.MarsIDE && MarsIDE.engine.connected && MarsIDE.S.current", timeout=30000)
                # Use the actual group menu, not a fabricated saved layout.
                page.get_by_role('button', name='Editor group actions', exact=True).click()
                page.get_by_role('button', name='Split right' if edge == 'right' else 'Split down', exact=True).click()
                assert page.locator('.editor-group').count() == 2
                page.locator('.editor-group').nth(side).locator('.group-tab.selected [data-close]').click()
                page.wait_for_function('MarsIDE.groups.groups.length === 1')
                bounds = page.evaluate("""() => {
                  const host=document.querySelector('#editor-groups').getBoundingClientRect();
                  const pane=document.querySelector('.editor-group').getBoundingClientRect();
                  return {hostWidth:host.width, hostHeight:host.height, width:pane.width, height:pane.height};
                }""")
                assert bounds['width'] >= bounds['hostWidth'] - 2 and bounds['height'] >= bounds['hostHeight'] - 2, (edge, side, bounds)
                page.reload(); page.wait_for_function('window.MarsIDE && MarsIDE.engine.connected && MarsIDE.S.current', timeout=30000)
                assert page.locator('.editor-group').count() == 1
                page.close()
        # When the other half is itself a split, the surviving split container
        # must also lose the old parent's inline flex fraction.
        page = browser.new_page(viewport={"width":1300, "height":800})
        page.goto(BASE); page.wait_for_function('window.MarsIDE && MarsIDE.engine.connected && MarsIDE.S.current', timeout=30000)
        page.get_by_role('button', name='Editor group actions', exact=True).click()
        page.get_by_role('button', name='Split right', exact=True).click()
        page.locator('.editor-group.active-group').get_by_role('button', name='Editor group actions', exact=True).click()
        page.get_by_role('button', name='Split down', exact=True).click()
        assert page.locator('.editor-group').count() == 3
        page.locator('.editor-group').first.locator('.group-tab.selected [data-close]').click()
        page.wait_for_function('MarsIDE.groups.groups.length === 2')
        bounds = page.evaluate("""() => {
          const host=document.querySelector('#editor-groups').getBoundingClientRect();
          const root=document.querySelector('#editor-groups > .group-split').getBoundingClientRect();
          return {hostWidth:host.width,hostHeight:host.height,width:root.width,height:root.height};
        }""")
        assert bounds['width'] >= bounds['hostWidth'] - 2 and bounds['height'] >= bounds['hostHeight'] - 2, bounds
        page.close()
        browser.close()
        print('surviving split fills workspace: horizontal/vertical, both sides and reload OK')
finally:
    if server:
        server.terminate(); server.wait()
