#!/usr/bin/env bash
# One-file IDE that opens from disk (double-click): build/single/mars-ide.html.
# Bundles an existing static build without the CSP meta (SKIP_SITE=1 reuses build/static).
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/container-user.sh
if [ "${SKIP_SITE:-0}" != 1 ]; then STATIC_CSP=0 bash web/static/build-static.sh; fi
podman_run -v "$PWD":/w:z -w /w "${PY_IMAGE:-docker.io/library/python:3.12-slim}" \
  python3 web/static/build-single.py build/static build/single/mars-ide.html
