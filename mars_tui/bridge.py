"""Async client for the Java MARS engine process (marsx.StdioMain) (JSON lines over stdio)."""
from __future__ import annotations

import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent


class BridgeError(Exception):
    pass


def bridge_command() -> list[str]:
    jar = os.environ.get("MARS_ENGINE_JAR", str(ROOT / "build" / "mars-engine.jar"))
    java = os.environ.get("MARS_JAVA") or shutil.which("java") or "java"
    opts = os.environ.get(
        "MARS_JAVA_OPTS",
        "-XX:+UseSerialGC -Xms16m -Xmx256m -XX:TieredStopAtLevel=1 -Xshare:auto",
    ).split()
    return [java, *opts, "-Djava.awt.headless=true", "-cp", jar, "marsx.StdioMain", os.getcwd()]


class Bridge:
    def __init__(self, on_event: Callable[[dict], None]) -> None:
        self.on_event = on_event
        self.proc: asyncio.subprocess.Process | None = None
        self._pending: dict[int, asyncio.Future] = {}
        self._next = 1
        self._ready = asyncio.Event()
        self._tasks: list[asyncio.Task] = []
        self.version = "?"

    async def start(self) -> None:
        self.proc = await asyncio.create_subprocess_exec(
            *bridge_command(),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=1 << 26,
        )
        self._tasks.append(asyncio.create_task(self._read()))
        self._tasks.append(asyncio.create_task(self._drain_stderr()))
        await asyncio.wait_for(self._ready.wait(), timeout=60)

    async def _drain_stderr(self) -> None:
        assert self.proc and self.proc.stderr
        while await self.proc.stderr.readline():
            pass

    async def _read(self) -> None:
        assert self.proc and self.proc.stdout
        while True:
            line = await self.proc.stdout.readline()
            if not line:
                break
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if "ev" in msg:
                if msg["ev"] == "ready":
                    self.version = msg.get("version", "?")
                    self._ready.set()
                else:
                    try:
                        self.on_event(msg)
                    except Exception:  # never kill the reader
                        pass
                continue
            fut = self._pending.pop(msg.get("id"), None)
            if fut and not fut.done():
                fut.set_result(msg)
        err = BridgeError("MARS engine exited")
        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(err)
        self._pending.clear()
        self.on_event({"ev": "dead"})

    async def call(self, cmd: str, **args: Any) -> dict:
        if not self.proc or not self.proc.stdin or self.proc.returncode is not None:
            raise BridgeError("MARS engine is not running")
        rid = self._next
        self._next += 1
        fut = asyncio.get_running_loop().create_future()
        self._pending[rid] = fut
        self.proc.stdin.write((json.dumps({"id": rid, "cmd": cmd, **args}) + "\n").encode())
        await self.proc.stdin.drain()
        res = await fut
        if not res.get("ok", False):
            raise BridgeError(res.get("error", "unknown error"))
        return res

    async def close(self) -> None:
        if self.proc and self.proc.returncode is None:
            try:
                self.proc.stdin.close()  # type: ignore[union-attr]
                await asyncio.wait_for(self.proc.wait(), 2)
            except Exception:
                self.proc.kill()
