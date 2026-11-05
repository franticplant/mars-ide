import asyncio, os, shutil, sys
sys.path.insert(0, "/app")
from mars_tui.app import MarsApp
W, H = int(os.environ.get("W", 48)), int(os.environ.get("H", 26))
def dump(app, t):
    print(f"===== {t}")
    for s in app.screen._compositor.render_strips():
        print("".join(seg.text for seg in s).rstrip())
async def main():
    os.makedirs("/tmp/ws", exist_ok=True); shutil.copy("/app/examples/hello.asm", "/tmp/ws/hello.asm"); os.chdir("/tmp/ws")
    app = MarsApp(["hello.asm"])
    async with app.run_test(size=(W, H)) as pilot:
        for _ in range(100):
            await pilot.pause(0.1)
            if app.configs: break
        await pilot.press("f4"); await pilot.pause(0.4); dump(app, "menu")
        await pilot.press("escape"); await pilot.pause(0.2)
        await pilot.press("f10"); await pilot.pause(0.3); dump(app, "zen")
        await pilot.press("escape"); await pilot.pause(0.3)
        print("zen after esc:", app.settings["zen"])
asyncio.run(main())
