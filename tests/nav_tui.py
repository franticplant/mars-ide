import asyncio, os, shutil, sys
sys.path.insert(0, "/app")
from mars_tui.app import MarsApp
async def main():
    os.makedirs("/tmp/ws", exist_ok=True); shutil.copy("/app/examples/hello.asm", "/tmp/ws/hello.asm"); os.chdir("/tmp/ws")
    app = MarsApp(["hello.asm"])
    async with app.run_test(size=(120, 30)) as pilot:
        for _ in range(100):
            await pilot.pause(0.1)
            if app.configs: break
        ed = app.current_editor(); ed.focus(); ed.cursor_location = (14, 8)
        await pilot.press("f1"); await pilot.pause(0.3); print("F1        ->", app.view, repr(app.query_one('#help-filter').value))
        await pilot.press("escape"); await pilot.pause(0.3); print("Esc       ->", app.view, app.current_editor().cursor_location)
        await pilot.press("f3"); await pilot.pause(0.6); print("assemble  ->", app.view)
        await pilot.press("alt+4"); await pilot.pause(0.3); print("alt+4     ->", app.view)
        await pilot.press("alt+left"); await pilot.pause(0.3); print("alt+left  ->", app.view)
        await pilot.press("alt+left"); await pilot.pause(0.3); print("alt+left  ->", app.view, app.current_editor().cursor_location)
        await pilot.press("alt+right"); await pilot.pause(0.3); print("alt+right ->", app.view)
asyncio.run(main())
