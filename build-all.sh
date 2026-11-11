#!/usr/bin/env bash
# Build everything on this machine (never on the phone):
#   ./build-all.sh engine   headless MARS core + engine + web server  -> build/mars-engine.jar
#   ./build-all.sh pylib    Textual for the TUI (pure Python)          -> build/pylib
#   ./build-all.sh image    container images (amd64 + arm64)           -> mars-ide:latest
#   ./build-all.sh static   static site: engine compiled to JS (TeaVM)  -> build/static/  (experimental)
#   ./build-all.sh test     conformance: original MARS vs desktop engine vs browser engine
#   ./build-all.sh all
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$PWD
source scripts/container-user.sh
JDK_IMAGE=${JDK_IMAGE:-docker.io/library/eclipse-temurin:21-jdk-jammy}
PY_IMAGE=${PY_IMAGE:-docker.io/library/python:3.12-slim}

engine() {
  bash scripts/build-web.sh
  podman_run -v "$ROOT":/w:z -w /w "$PY_IMAGE" sh -ec '
    python3 engine/patch_core.py vendor/Mars4_5.jar build/core-src'
  podman_run -v "$ROOT":/w:z -w /w "$JDK_IMAGE" sh -ec '
    rm -rf build/engine-classes build/desktop-classes && mkdir -p build/engine-classes build/desktop-classes
    find build/core-src/java engine/src -name "*.java" > build/engine-sources.txt
    javac -nowarn -encoding latin1 --release 11 -d build/engine-classes @build/engine-sources.txt 2>&1 | grep -v "^Note:" || true
    test -f build/engine-classes/marsx/MarsEngine.class || { echo "ENGINE BUILD FAILED"; exit 1; }
    test -f build/engine-classes/marsx/MarsEngine.class
    javac -nowarn --release 11 -cp build/engine-classes -d build/desktop-classes engine/desktop/marsx/*.java 2>&1 | grep -v "^Note:" || true
    rm -rf build/jar && mkdir -p build/jar/web
    cp -r build/engine-classes/. build/desktop-classes/. build/jar/
    cp build/core-src/resources/* build/jar/
    cp -r web/. build/jar/web/
    printf "Main-Class: marsx.WebServer\n" > build/manifest.txt
    jar --create --file build/mars-engine.jar --manifest build/manifest.txt -C build/jar .
    echo "engine: $(du -h build/mars-engine.jar | cut -f1) build/mars-engine.jar"'
}

pylib() {
  mkdir -p .cache/pip
  podman_run -v "$ROOT":/w:z -v "$ROOT/.cache/pip":/pip-cache:z -e PIP_CACHE_DIR=/pip-cache "$PY_IMAGE" sh -ec '
    rm -rf /w/build/pylib && pip install -q --root-user-action=ignore --disable-pip-version-check --target /w/build/pylib "textual==8.2.8"
    python -m compileall -q /w/build/pylib >/dev/null || true
    echo "pylib: $(du -sh /w/build/pylib | cut -f1)"'
}

case "${1:-all}" in
  engine) engine ;;
  pylib) pylib ;;
  static) bash web/static/build-static.sh ;;
  test)
    engine; bash engine/teavm/build-teavm.sh
    podman image exists mars-conformance || podman build -q -t mars-conformance -f tests/conformance/Containerfile tests/conformance
    podman_run -v "$ROOT/vendor":/v:ro,z -v "$ROOT/build":/b:z -v "$ROOT/engine/teavm/target/teavm":/e:ro,z \
      -v "$ROOT/tests/conformance":/c:z mars-conformance sh -ec 'exec python3 /c/run.py' ;;
  image) bash container/build-image.sh ;;
  all) engine; [ -d build/pylib ] || pylib; bash web/static/build-static.sh; bash container/build-image.sh ;;
  *) echo "unknown target $1"; exit 2 ;;
esac
