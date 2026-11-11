#!/usr/bin/env bash
# Browser end-to-end tests with Chromium + Playwright against the real engine:
# tests/web_*.py (web UI on the engine's own server) and tests/static_e2e.py (static build).
# Needs build/mars-engine.jar and build/static (built first if missing).
#
# Usage: scripts/test-web.sh [tests/web_e2e.py ...]
#   SHOTS=dir   where screenshots go (default: tests/shots)
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/container-user.sh
SHOTS=${SHOTS:-tests/shots}
STATIC_DIR=${STATIC_DIR:-build/static}
[ -f build/mars-engine.jar ] || ./build-all.sh engine
[ -f "$STATIC_DIR/index.html" ] || ./build-all.sh static
podman image exists mars-browser || podman build -q -t mars-browser -f tests/Containerfile.browser tests
mkdir -p "$SHOTS" build/static

if [ $# -gt 0 ]; then tests=("$@"); else tests=(tests/web_*.py tests/static_e2e.py); fi
fail=0
for t in "${tests[@]}"; do
  [ -f "$t" ] || continue
  echo "== $t"
  log="build/test-web-$(basename "$t" .py).log"
  if ! podman_run --network=none -e PYTHONDONTWRITEBYTECODE=1 \
      -v "$PWD/build":/build:ro,z -v "$(realpath "$STATIC_DIR")":/static:ro,z -v "$PWD/web":/web:ro,z \
      -v "$PWD/examples":/examples:ro,z -v "$PWD/tests":/tests:ro,z -v "$(realpath "$SHOTS")":/shots:z \
      mars-browser sh -ec 'exec /venv/bin/python "$1"' sh "/tests/$(basename "$t")" > "$log" 2>&1; then
    echo "FAIL $t (log: $log)"; tail -20 "$log"; fail=1
  else
    echo "ok   $t"
  fi
done
exit $fail
