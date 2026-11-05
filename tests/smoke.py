"""Headless smoke test: drives the TUI with Textual's pilot and dumps screens as text."""
import asyncio, sys, os, shutil
sys.path.insert(0, "/app")
from mars_tui.app import MarsApp

W, H = int(os.environ.get("W", 120)), int(os.environ.get("H", 36))

def dump(app, title):
    strips = app.screen._compositor.render_strips()
    print(f"===== {title} ({W}x{H}) =====")
    for s in strips:
        print("".join(seg.text for seg in s).rstrip())

async def wait_engine(app, pilot):
    for _ in range(200):
        await pilot.pause(0.1)
        if app.bridge._ready.is_set() and app.configs:
            return
    raise SystemExit("engine never ready")

async def main():
    os.makedirs("/tmp/ws", exist_ok=True)
    shutil.copy("/app/examples/hello.asm", "/tmp/ws/hello.asm")
    os.chdir("/tmp/ws")
    app = MarsApp(["hello.asm"])
    async with app.run_test(size=(W, H)) as pilot:
        await wait_engine(app, pilot)
        await pilot.pause(0.3)
        dump(app, "editor")
        await pilot.press("f3")
        await pilot.pause(0.8)
        dump(app, "after assemble")
        for _ in range(3):
            await pilot.press("f7")
            await pilot.pause(0.2)
        dump(app, "after 3 steps")
        await pilot.press("f5")
        await pilot.pause(1.0)
        dump(app, "running, waiting for input")
        app.query_one("#stdin").value = "12"
        await pilot.press("enter")
        await pilot.pause(1.0)
        dump(app, "finished")
        await pilot.press("alt+4" if W >= 100 else "alt+4")
        await pilot.pause(0.6)
        dump(app, "memory")
        await pilot.press("f1")
        await pilot.pause(0.4)
        dump(app, "help")

asyncio.run(main())
