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
        await pilot.press("f3"); await pilot.pause(0.6)
        for _ in range(5): await pilot.press("f7"); await pilot.pause(0.15)
        t = app.query_one("#gpr"); t.focus()
        for row in (2, 4, 1, 29):
            t.move_cursor(row=row); await pilot.pause(0.5)
            print(str(app.query_one("#hint").render()))
asyncio.run(main())
