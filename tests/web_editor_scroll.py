"""Focused editor scrolling regressions against the static IDE."""
import os
import subprocess
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8096/")
server = subprocess.Popen(["python3", "-m", "http.server", "8096", "-d", "/static"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if "BASE" not in os.environ else None

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 390, "height": 700}, is_mobile=True, has_touch=True)
    page.goto(BASE)
    page.wait_for_function("window.MarsIDE && MarsIDE.engine.connected", timeout=30000)
    result = page.evaluate("""async () => {
      const ed = MarsIDE.groups.active.editor, ta = ed.ta;
      ed.value = Array.from({length: 100}, (_, i) => i + ' ' + 'x'.repeat(200)).join('\\n');
      ta.focus({preventScroll: true});
      ta.setSelectionRange(0, 0);
      ta.scrollTop = 1200; ta.scrollLeft = 0;
      const before = ta.scrollTop;
      window.visualViewport.dispatchEvent(new Event('scroll'));
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const after = ta.scrollTop;
      ta.dispatchEvent(new WheelEvent('wheel', {shiftKey:true, deltaY:120, bubbles:true, cancelable:true}));
      return {before, after, horizontal:ta.scrollLeft, max:ta.scrollWidth-ta.clientWidth};
    }""")
    assert result["before"] > 0 and result["after"] == result["before"], result
    assert result["max"] > 0 and result["horizontal"] > 0, result
    path = page.evaluate("MarsIDE.S.current")
    page.locator('.active-group .group-tab').first.click(button='middle')
    page.wait_for_function("p => !MarsIDE.R.files.has(p)", arg=path)
    print("editor scrolling OK:", result)
    browser.close()
if server:
    server.terminate()
    server.wait()
