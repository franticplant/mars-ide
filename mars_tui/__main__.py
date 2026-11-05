"""Entry point.

  mars-tui [files…]                      terminal IDE (Textual)
  mars-tui web [--host H] [--port P]     web IDE in the browser (Java server, same engine)
               [--token T | --no-auth]
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys


def web(argv: list[str]) -> None:
    from .bridge import ROOT
    p = argparse.ArgumentParser(prog="mars-tui web", description="Serve the MARS web IDE for the current directory")
    p.add_argument("--host", default=os.environ.get("MARS_WEB_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.environ.get("MARS_WEB_PORT", "8080")))
    p.add_argument("--token", default=os.environ.get("MARS_WEB_TOKEN"), help="access token (default: random, printed)")
    p.add_argument("--no-auth", action="store_true", help="disable the access token (trusted networks only)")
    p.add_argument("--root", default=os.getcwd(), help="workspace directory (default: current directory)")
    a = p.parse_args(argv)
    jar = os.environ.get("MARS_ENGINE_JAR", str(ROOT / "build" / "mars-engine.jar"))
    java = os.environ.get("MARS_JAVA") or shutil.which("java") or "java"
    cmd = [java, "-XX:+UseSerialGC", "-Xmx256m", "-jar", jar, "--host", a.host, "--port", str(a.port), "--root", a.root]
    if a.no_auth:
        cmd.append("--no-auth")
    elif a.token:
        cmd += ["--token", a.token]
    os.execvp(cmd[0], cmd)


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "web":
        web(argv[1:])
        return
    p = argparse.ArgumentParser(prog="mars-tui", description="Terminal IDE for MIPS on the MARS engine")
    p.add_argument("files", nargs="*", help="files or directories to open")
    args = p.parse_args(argv)
    from .app import MarsApp
    MarsApp(args.files).run()


if __name__ == "__main__":
    main()
