#!/usr/bin/env bash
# Bundle the isolated Markdown renderer locally, never fetch executable code at runtime.
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/container-user.sh
mkdir -p .cache/npm .cache/markdown-node web/vendor
podman_run \
  -v "$PWD":/w:z -w /w/tools/markdown --env npm_config_cache=/npm-cache \
  -v "$PWD/.cache/npm":/npm-cache:z \
  -v "$PWD/.cache/markdown-node":/w/tools/markdown/node_modules:z \
  docker.io/library/node:22-slim sh -ec '
    if ! cmp -s package-lock.json node_modules/.mars-lock; then
      npm ci --no-audit --no-fund
      cp package-lock.json node_modules/.mars-lock
    fi
    npm run build'
