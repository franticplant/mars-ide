# Testing

```sh
make test       # conformance suite
make test-tui   # TUI pilot tests
make test-web   # browser tests (web UI with server, static build)
make test-all   # test, test-tui and test-web
```

Run them on the laptop. Each builds what it needs first (engine jar, TeaVM engine, pylib,
static site, test images).

## Conformance suite (`tests/conformance/`)

The guarantee that the IDE behaves like MARS. `run.py` runs every program in `progs/` (except
`inc_*` helpers) on

1. the **unmodified `vendor/Mars4_5.jar`** command line: the oracle;
2. `marsx.StdioMain` from `build/mars-engine.jar`: what the TUI, the server and the image run;
3. the TeaVM engine in Node (`teavm-run.js`): what the static site runs;

and requires identical program output, runtime errors (line and message), instruction count
and all 31 registers. Engine-only features (step / back-step, stepped input, dialogs,
pause / continue) are compared between 2 and 3. It runs in the `mars-conformance` image
(`tests/conformance/Containerfile`: Temurin JDK + Node + Python).

Options for a program go in a comment, `# @mars: db smc` (delayed branching, self-modifying
code, `sm` start at main, `we` warnings are errors); input in `<name>.in`.

Adding a feature that changes execution? Add a program here first. A difference from the oracle
is a bug unless it is documented in the README ("Known, documented difference").

## TUI tests (`scripts/test-tui.sh`)

Every `tests/*.py` that starts with `from mars_tui…` (`smoke.py`, `*_tui.py`, `menu_zen.py`):
Textual's pilot drives the app headless at a fixed size against the real engine, and the
tests print screens as text. They run in the `mars-conformance` image with the repository
mounted read-only at `/app`. Logs: `build/test-tui-<name>.log`. One test: `scripts/test-tui.sh
tests/smoke.py`.

## Browser tests (`scripts/test-web.sh`)

`tests/web_*.py` start the engine's web server on the mounted `web/` and drive it in Chromium
with Playwright; `tests/static_e2e.py` serves `build/static/`. They run in the `mars-browser`
image (`tests/Containerfile.browser`: Debian, Chromium, Playwright 1.64.1, a JRE), offline.
Screenshots go to `tests/shots/` (`SHOTS=dir` to change), logs to `build/test-web-<name>.log`.
`tests/static_pause*.py` are manual checks against a running static site (`BASE=http://…`) and
are not run by the script.

## Benchmarks (`tests/bench/`)

Instruction throughput of the engines; not part of CI.

## CI

`.github/workflows/ci.yml`, on every push to `main` and every pull request: the conformance job
builds both engines and runs the suite, then the TUI, browser and image jobs reuse its engine
artifact. The image job builds the static site and the amd64 + arm64 images (no QEMU needed)
and smoke-tests them; nothing is pushed. A commit message containing `[ci skip]` skips CI.
