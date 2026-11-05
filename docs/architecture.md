# Architecture

```
                 vendor/Mars4_5.jar  (official MARS 4.5, unmodified)
                        │ engine/patch_core.py: extract sources, drop Swing/AWT/sound,
                        │ lay engine/overlay/ on top
                        ▼
             headless MARS core  +  marsx.MarsEngine (engine/src/marsx)
             one JSON command/event protocol, java.base only
        ┌───────────────┬───────────────────────┬──────────────────────────────┐
        │ stdio         │ HTTP + SSE            │ postMessage (Web Worker)     │
   StdioMain       WebServer (engine/desktop)   TeaMain (engine/teavm), compiled
        │          /api/cmd, /api/events,       to JavaScript by TeaVM
        │          static files from web/       │
        ▼               ▼                       ▼
   TUI (mars_tui/,  web UI (web/) in        the same web UI, engine in the
   Python/Textual)  any browser             browser, files in IndexedDB
                                            (build/static/, no server)
```

## One engine

All front ends drive the same `marsx.MarsEngine` on the same patched MARS core, so assembly and
simulation are MARS's own. Only the transport differs:

- **TUI**: `mars_tui/bridge.py` starts `java -cp build/mars-engine.jar marsx.StdioMain <workspace>`
  and talks JSON lines over stdin/stdout.
- **Web UI with server**: `marsx.WebServer` (the jar's main class) serves `web/`, takes commands on
  `POST /api/cmd` and streams events on `GET /api/events` (server-sent events). It binds
  `127.0.0.1` and asks for an access token unless started with `--no-auth`.
- **Static build**: `engine/teavm/build-teavm.sh` compiles the same sources with TeaVM into
  `mars-engine.js`, which runs in a Web Worker (`web/static/worker.js`); `web/static/idbfs.js`
  keeps the workspace in IndexedDB. The browser build makes two mechanical changes (no locks, since
  it is single-threaded; shorter run slices) and nothing else.

## The headless core

`engine/patch_core.py` builds `build/core-src/` from the jar on every build: it extracts the MIT
MARS sources except the Swing IDE (`mars/venus/`) and tools (`mars/tools/`), strips every
`java.awt` / `javax.swing` / `javax.sound` use, and copies `engine/overlay/` over the result
(headless `Settings`, dialog syscalls answered by the front end, a tone generator that emits
events, `venus` stubs). `engine/resources/` holds MARS's own resource files unchanged. Nothing
under `build/` is committed; the jar is the single source.

## Front ends

- `mars_tui/`: Textual app (`app.py`, `editor.py`, `widgets.py`, `screens.py`), instruction hints
  (`mips.py`, `meaning.py`) and the reference-card data (`refcard.json`).
- `web/`: plain HTML/CSS/JS, no bundler (`js/app.js`, `js/editor.js`, `js/engine.js`,
  `js/files.js`, …). The same files are served by `WebServer`, packed into the static site and
  into the container image.

## Containers

- `container/Containerfile` → `mars-ide`: Python slim + a jlink'd JRE (`java.base`,
  `jdk.httpserver`) + `build/pylib` + the engine jar. TUI by default, `web` for the server. Runs as
  a non-root user. No `RUN` steps, so amd64 and arm64 images build on one machine without
  emulation.
- `container/static/` → `mars-ide-static`: unprivileged nginx serving `build/static/`.
- `container/mars-ide.container`: an example podman quadlet (systemd user service) for the web UI.
