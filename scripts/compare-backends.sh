#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/container-user.sh
[ -f engine/teavm/target/teavm/mars-engine.js ] || bash engine/teavm/build-teavm.sh
if [ ! -f build/wasm-trial/teavm/mars-engine.wasm-runtime.js ]; then
  TARGET=WEBASSEMBLY_GC TEAVM_STAGE=build/wasm-stage TEAVM_OUT=build/wasm-trial bash engine/teavm/build-teavm.sh
fi
if ! podman image exists mars-conformance; then
  echo "The cached mars-conformance test image is required. Provision it with approval before running this benchmark." >&2
  exit 1
fi
podman_run --network=none -v "$PWD":/w:z -w /w mars-conformance sh -ec 'exec python3 tests/bench/compare-backends.py "$1"' sh "${TRIALS:-3}"
