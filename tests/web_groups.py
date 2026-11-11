"""Drag/drop, touch alternatives and debugger integration across editor groups."""
import os, shutil, subprocess
from playwright.sync_api import sync_playwright

WS = "/tmp/ws-groups"
shutil.rmtree(WS, ignore_errors=True); os.makedirs(WS)
for name in ["hello.asm", "fibonacci.asm"]:
    if os.path.exists("/examples/" + name): shutil.copy("/examples/" + name, WS)
with open(WS + "/notes.md", "w") as f: f.write("# Notes\n")
srv = subprocess.Popen(["java", "-jar", "/build/mars-engine.jar", "--no-auth", "--port", "8095", "--root", WS, "--web", "/web"], stdout=subprocess.PIPE, text=True)
srv.stdout.readline(); srv.stdout.readline()
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        p = b.new_page(viewport={"width": 1400, "height": 860})
        errors = []; p.on("pageerror", lambda e: errors.append(str(e)))
        p.goto("http://127.0.0.1:8095/"); p.wait_for_selector(".ftab")
        original = p.evaluate("MarsIDE.S.current")
        p.keyboard.press("Control+Backslash")
        assert p.locator(".editor-group").count() == 2
        # Editing either source updates the same document and sibling source.
        second = p.locator(".editor-group").nth(1).locator("textarea")
        before = second.input_value()
        second.fill(before + "\n# Shared draft\n")
        assert second.input_value() == before + "\n# Shared draft\n"
        assert p.locator(".editor-group").first.locator("textarea").input_value().endswith("# Shared draft\n")
        # Shared breakpoints, assembly, stepping, and errors remain visible in both sources.
        p.locator(".editor-group").nth(1).locator('.g[data-line="12"]').click()
        assert p.locator('.editor-group .g.bp[data-line="12"]').count() == 2
        p.keyboard.press("F3"); p.wait_for_function('() => MarsIDE.R.assembled'); p.click('.tab[data-v="exec"]')
        p.click('.tab[data-v="edit"]')
        p.keyboard.press("F7"); p.wait_for_timeout(200)
        assert p.locator(".editor-group .ed-hl .l.exec").count() == 2
        second.fill(second.input_value() + "# Another unsaved edit\n")
        # Drag a second file tab into the first pane, then split it vertically by dropping at an edge.
        p.click("#btn-side")
        p.locator('.node[data-p="notes.md"]').click()
        p.locator('.group-tab.selected [title="notes.md"]').wait_for()
        # Global file tabs can open a view in a group that does not yet contain that file.
        p.locator(".editor-group").first.locator(f'[title="{original}"]').click()
        first_body = p.locator(".editor-group").first.locator(".group-body").bounding_box()
        p.locator('#filetabs .ftab[data-p="notes.md"]').hover()
        p.mouse.down(); p.mouse.move(first_body["x"] + first_body["width"] / 2, first_body["y"] + first_body["height"] / 2, steps=15); p.mouse.up()
        p.locator(".editor-group").first.locator('[title="notes.md"]').wait_for()
        assert p.locator(".editor-group").first.locator(f'[title="{original}"]').count() == 1
        p.locator(".editor-group").first.locator(".group-tab").filter(has_text="notes.md").locator("[data-close]").click()
        p.locator(".editor-group").nth(1).locator('[title="notes.md"]').click()
        tab = p.locator('.active-group .group-tab').filter(has_text="notes.md")
        target = p.locator(".editor-group").first
        box = target.locator(".group-body").bounding_box()
        tab.hover(); p.mouse.down(); p.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=15); p.mouse.up()
        p.locator('.editor-group').first.locator('[title="notes.md"]').wait_for()
        assert p.evaluate("MarsIDE.groups.groups[0].tabs.some(t => t.path === 'notes.md')")
        tab = p.locator(".editor-group").first.locator(".group-tab").filter(has_text="notes.md")
        box = p.locator(".editor-group").first.locator(".group-body").bounding_box()
        tab.hover(); p.mouse.down(); p.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] - 8, steps=15); p.mouse.up()
        assert p.locator(".editor-group").count() == 3
        assert p.locator(".group-split.split-column").count() == 1
        # Resize using keyboard and pointer handles.
        handle = p.locator(".group-divider").first
        old = handle.get_attribute("aria-valuenow")
        handle.focus(); p.keyboard.press("ArrowRight")
        assert handle.get_attribute("aria-valuenow") != old
        box = handle.bounding_box()
        p.mouse.move(box["x"] + 2, box["y"] + 2); p.mouse.down(); p.mouse.move(box["x"] + 40, box["y"] + 20); p.mouse.up()
        p.screenshot(path="/shots/groups-resize.png")
        # A Markdown pane must not be submitted to the assembler.
        p.locator('.group-tab').filter(has_text="notes.md").locator("[data-select]").click()
        assert p.evaluate("MarsIDE.S.current") == "notes.md"
        p.keyboard.press("F3")
        assert p.evaluate("MarsIDE.R.assembled")
        # Closing one duplicate source is non-destructive and does not ask to discard the shared draft.
        first = p.locator(".editor-group").first
        first.locator(".group-tab").filter(has_text=original).locator("[data-close]").click()
        assert p.locator(".modal-bg").count() == 0
        assert p.evaluate("MarsIDE.R.files.get(MarsIDE.S.open.find(p=>p.endsWith('.asm'))).text.endsWith('# Another unsaved edit\\n')")
        # The last dirty source cannot be closed without the normal discard decision.
        p.locator('.group-tab').filter(has_text=original).locator("[data-close]").click()
        p.get_by_role("button", name="Cancel", exact=True).click()
        assert p.evaluate("p => MarsIDE.R.files.has(p)", original)
        # Group menu actions provide a no-drag alternative on phone-sized screens.
        p.set_viewport_size({"width": 390, "height": 844})
        active = p.locator(".editor-group:visible")
        active.get_by_role("button", name="Editor group actions", exact=True).click()
        p.get_by_role("button", name="Next group", exact=True).click()
        assert p.locator(".editor-group:visible").count() == 1
        p.locator(".editor-group:visible").get_by_role("button", name="Editor group actions", exact=True).click()
        p.get_by_role("button", name="Join group into next", exact=True).click()
        assert p.locator(".editor-group").count() == 1
        p.set_viewport_size({"width": 1400, "height": 860})
        assert not errors, errors
        b.close()
finally:
    srv.terminate(); srv.wait(timeout=10)
print("editor groups / drag / debugger: ok")
