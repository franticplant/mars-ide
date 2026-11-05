#!/usr/bin/env bash
# Compile the MARS engine to JavaScript (or WebAssembly) with TeaVM, for the static web build.
#   TARGET=JAVASCRIPT (default) | WEBASSEMBLY_GC
set -euo pipefail
cd "$(dirname "$0")/../.."
TARGET=${TARGET:-JAVASCRIPT}
FILE=mars-engine.js; [ "$TARGET" = WEBASSEMBLY_GC ] && FILE=mars-engine.wasm
[ -d build/core-src ] || python3 engine/patch_core.py vendor/Mars4_5.jar build/core-src
STAGE=build/teavm-stage
mkdir -p "$STAGE"; find "$STAGE" -mindepth 1 -delete
mkdir -p "$STAGE/src" "$STAGE/res"
cp -r build/core-src/java/. engine/src/. engine/teavm/src/. "$STAGE/src/"
cp build/core-src/resources/* "$STAGE/res/"
# Browser build only: the engine runs single-threaded (green threads), so MARS's per-instruction
# locks protect nothing but make every register access a potential thread switch. Drop them in mars/**.
python3 - "$STAGE/src/mars" <<'PY'
import re, sys
from pathlib import Path
n = 0
for f in Path(sys.argv[1]).rglob("*.java"):
    if f.name in ("SwingWorker.java",):      # keeps its join/handoff semantics
        continue
    src = f.read_text(encoding="latin-1")
    out = re.sub(r"\bsynchronized\s*\(\s*Globals\.memoryAndRegistersLock\s*\)", "if (true)", src)
    out = re.sub(r"(\b(?:public|private|protected|static|final)\s+)synchronized\s+", r"\1", out)
    if out != src:
        f.write_text(out, encoding="latin-1"); n += 1
print(f"teavm: removed locks in {n} core files")
PY
# same for the engine's own output plumbing (console streams, event sink); Mailbox keeps wait/notify
python3 - "$STAGE/src/marsx" <<'PY'
import re, sys
from pathlib import Path
for f in Path(sys.argv[1]).glob("*.java"):
    if f.name == "Mailbox.java":
        continue
    src = f.read_text(encoding="latin-1")
    out = re.sub(r"synchronized\s*\(\s*sink\s*\)\s*", "", src)
    out = re.sub(r"(@Override\s+public\s+|\bpublic\s+|\bprivate\s+|\bstatic\s+)synchronized\s+", r"\1", out)
    if out != src:
        f.write_text(out, encoding="latin-1"); print("teavm: removed locks in", f.name)
PY
mkdir -p .cache/m2      # podman refuses to mount a path that does not exist (fresh checkouts)
podman run --rm -v "$PWD":/w:z -v "$PWD/.cache/m2":/root/.m2:z -w /w/engine/teavm docker.io/library/maven:3.9-eclipse-temurin-21 \
  mvn -q -B package -Dstaged.src=/w/$STAGE/src -Dstaged.res=/w/$STAGE/res -Dteavm.target=$TARGET -Dteavm.file=$FILE -Dteavm.minify=${MINIFY:-true} \
      -DskipTests -Dmaven.test.skip=true 2>&1 | { grep -vE "^\[INFO\]|Download" || true; } | tail -60
ls -la engine/teavm/target/teavm/ 2>/dev/null || true
