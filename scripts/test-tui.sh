#!/usr/bin/env bash
# TUI tests: drive the Textual app headless with its pilot against the real engine.
# Runs every tests/*.py that imports mars_tui, inside the conformance image (Java + Python),
# with the repository mounted read-only at /app. Needs build/mars-engine.jar and build/pylib
# (built first if missing).
#
# Usage: scripts/test-tui.sh [tests/smoke.py ...]
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f build/mars-engine.jar ] || ./build-all.sh engine
[ -d build/pylib ] || ./build-all.sh pylib
podman image exists mars-conformance ||
  podman build -q -t mars-conformance -f tests/conformance/Containerfile tests/conformance

if [ $# -gt 0 ]; then tests=("$@"); else mapfile -t tests < <(grep -l '^from mars_tui' tests/*.py); fi
fail=0
for t in "${tests[@]}"; do
  echo "== $t"
  if ! podman run --rm --network=none -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/app/build/pylib:/app \
      -v "$PWD":/app:ro,z mars-conformance python3 "/app/$t" > "build/test-tui-$(basename "$t" .py).log" 2>&1; then
    echo "FAIL $t (log: build/test-tui-$(basename "$t" .py).log)"; tail -20 "build/test-tui-$(basename "$t" .py).log"; fail=1
  else
    echo "ok   $t"
  fi
done
exit $fail
