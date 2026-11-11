"""Independent register and console panel controls, including persistence."""
import os
import subprocess
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8096/")
server = subprocess.Popen(["python3", "-m", "http.server", "8096", "-d", "/static"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if "BASE" not in os.environ else None
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1300, "height": 800})
        page.goto(BASE); page.wait_for_function("window.MarsIDE && MarsIDE.engine.connected && MarsIDE.S.current", timeout=30000)
        regs, console = page.locator('#regs'), page.locator('#console')
        # In initial editor focus mode, one toggle reveals just that panel.
        assert not regs.is_visible() and not console.is_visible()
        page.click('#btn-regs'); assert regs.is_visible() and not console.is_visible()
        page.click('#btn-console'); assert regs.is_visible() and console.is_visible()
        page.click('#btn-regs'); assert not regs.is_visible() and console.is_visible()
        page.reload(); page.wait_for_function("window.MarsIDE && MarsIDE.engine.connected && MarsIDE.S.current", timeout=30000)
        assert not regs.is_visible() and console.is_visible()
        page.click('#btn-console'); assert not regs.is_visible() and not console.is_visible()
        page.keyboard.press('Control+j'); assert regs.is_visible() and console.is_visible()
        page.click('#btn-console'); assert regs.is_visible() and not console.is_visible()
        # Zen preserves each independent choice.
        page.keyboard.press('F10'); page.keyboard.press('F10')
        assert regs.is_visible() and not console.is_visible()
        # The user can hide panels in the Execute view as well.
        page.click('.tab[data-v="exec"]')
        page.click('#btn-regs'); assert not regs.is_visible() and not console.is_visible()
        page.click('#btn-console'); assert not regs.is_visible() and console.is_visible()
        browser.close()
        print('independent console/register panels: toggles, combined toggle, reload and zen OK')
finally:
    if server:
        server.terminate(); server.wait()
