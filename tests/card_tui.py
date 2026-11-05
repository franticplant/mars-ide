import asyncio, os, shutil, sys
sys.path.insert(0, "/app")
from mars_tui.app import MarsApp
def dump(app, t, n=24):
    print(f"===== {t}")
    for s in app.screen._compositor.render_strips()[:n]:
        print("".join(seg.text for seg in s).rstrip())
async def main():
    os.makedirs("/tmp/ws", exist_ok=True); shutil.copy("/app/examples/hello.asm", "/tmp/ws/hello.asm"); os.chdir("/tmp/ws")
    app = MarsApp(["hello.asm"])
    async with app.run_test(size=(110, 24)) as pilot:
        for _ in range(100):
            await pilot.pause(0.1)
            if app.configs: break
        ed = app.current_editor(); ed.focus(); ed.cursor_location = (11, 10)   # line 12: syscall
        await pilot.pause(0.3); print("HINT:", app.query_one("#hint").render())
        await pilot.press("f1"); await pilot.pause(0.5); dump(app, "F1 on syscall", 12)
        app.query_one("#help-filter").value = ""; await pilot.pause(0.4); dump(app, "card (no filter)", 24)
asyncio.run(main())
