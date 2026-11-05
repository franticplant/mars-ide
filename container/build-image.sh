#!/usr/bin/env bash
# Build mars-ide images for amd64 and arm64 (+ a manifest list) and an arm64 archive for the phone.
set -euo pipefail
cd "$(dirname "$0")/.."
JDK=docker.io/library/eclipse-temurin:21-jdk-jammy
ARCHES=${ARCHES:-"amd64 arm64"}
[ -f build/mars-engine.jar ] || ./build-all.sh engine
[ -d build/pylib ] || ./build-all.sh pylib
for arch in $ARCHES; do
  if [ ! -x build/jre-$arch/bin/java ]; then
    echo "== jlink runtime for $arch"
    ctr=$(podman create --platform linux/$arch $JDK true)
    mkdir -p build/jmods-$arch
    podman cp "$ctr:/opt/java/openjdk/jmods/." build/jmods-$arch/
    podman rm -f "$ctr" >/dev/null
    podman run --rm --platform linux/amd64 -v "$PWD/build":/b:z $JDK sh -ec "
      jlink --module-path /b/jmods-$arch --add-modules java.base,jdk.httpserver \
            --strip-debug --no-man-pages --no-header-files --compress=zip-6 --output /b/jre-$arch"
  fi
  echo "== image mars-ide:$arch"
  podman build -q --platform linux/$arch -f container/Containerfile -t mars-ide:$arch . >/dev/null
done
podman manifest rm mars-ide:latest >/dev/null 2>&1 || true
podman manifest create mars-ide:latest >/dev/null
for arch in $ARCHES; do podman manifest add mars-ide:latest containers-storage:localhost/mars-ide:$arch >/dev/null; done
if [[ " $ARCHES " == *" arm64 "* ]]; then
  podman save --format oci-archive -o build/mars-ide-arm64.tar localhost/mars-ide:arm64
  echo "phone image: $(du -h build/mars-ide-arm64.tar | cut -f1) build/mars-ide-arm64.tar"
fi
podman images --format '{{.Repository}}:{{.Tag}} {{.Size}}' | grep mars-ide
