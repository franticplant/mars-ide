#!/usr/bin/env bash
# Spawn MARS IDE in a container: build the image if it is missing, then run it.
# Rootless, and published on 127.0.0.1 only unless BIND says otherwise.
#
# Usage: scripts/spawn.sh [-n] tui|web|static [args...]
#   tui      terminal IDE on the files in the workspace (default: the current directory)
#   web      web IDE server on http://127.0.0.1:8080; prints a URL with an access token
#   static   server-less static build (engine in the browser) on http://127.0.0.1:8081
#   -n       print the commands instead of running them
# Extra args go to the IDE: `spawn.sh tui hello.asm`, `spawn.sh web --no-auth`.
#
# Environment:
#   CONTAINER_ENGINE   podman or docker (default: podman if installed, else docker)
#   MARS_WORKSPACE     directory mounted as /work (default: current directory)
#   PORT               host port (default: 8080 for web, 8081 for static)
#   BIND               host address to publish on (default: 127.0.0.1); 0.0.0.0 exposes the
#                      IDE to your network, so only do that on a trusted one
#   MARS_WEB_TOKEN     fixed access token for web (default: a random one, printed)
#   MARS_IMAGE         image for tui/web (default: localhost/mars-ide:<arch>, built if missing)
#   MARS_STATIC_IMAGE  image for static (default: localhost/mars-ide-static:latest, built if missing)
#
# Building needs podman (build-all.sh and container/build-image.sh use it) and is done on
# this machine: build on the laptop, never on the phone. With docker only, point MARS_IMAGE /
# MARS_STATIC_IMAGE at published images.
set -euo pipefail
caller_pwd=$PWD
cd "$(dirname "$0")/.."

dry=0
if [[ ${1:-} == -n ]]; then dry=1; shift; fi
mode=${1:-}
[[ $# -gt 0 ]] && shift
case $mode in
  tui | web | static) ;;
  *) sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2 ;;
esac

run() {
  if [[ $dry == 1 ]]; then printf '%q ' "$@"; echo; else "$@"; fi
}

ctr=${CONTAINER_ENGINE:-}
if [[ -z $ctr ]]; then
  if command -v podman >/dev/null; then ctr=podman
  elif command -v docker >/dev/null; then ctr=docker
  else echo "spawn: neither podman nor docker found" >&2; exit 1
  fi
fi

case $(uname -m) in
  x86_64 | amd64) arch=amd64 ;;
  aarch64 | arm64) arch=arm64 ;;
  *) echo "spawn: unsupported architecture $(uname -m)" >&2; exit 1 ;;
esac

have_image() { "$ctr" image inspect "$1" >/dev/null 2>&1; }

need_podman() {
  if [[ $ctr != podman ]]; then
    echo "spawn: $1 is missing and building it needs podman; set ${2} to a published image" >&2
    exit 1
  fi
}

bind=${BIND:-127.0.0.1}
ws=${MARS_WORKSPACE:-$caller_pwd}
tty_args=(-i)
[[ -t 0 && -t 1 ]] && tty_args=(-it)
# Rootless podman maps container root to you on the bind mount, so root inside keeps the
# workspace yours. Rootful docker would leave root-owned files, so keep your UID there.
if [[ $ctr == podman ]]; then
  user_args=(--user 0:0)
else
  user_args=(--user "$(id -u):$(id -g)")
fi
hardening=(--cap-drop=ALL --security-opt=no-new-privileges)

if [[ $mode == static ]]; then
  image=${MARS_STATIC_IMAGE:-localhost/mars-ide-static:latest}
  if ! have_image "$image"; then
    need_podman "$image" MARS_STATIC_IMAGE
    [[ -f build/static/index.html ]] || run ./build-all.sh static
    run podman build -q -f container/static/Containerfile -t "$image" .
  fi
  port=${PORT:-8081}
  echo "spawn: static MARS IDE on http://$bind:$port/ (Ctrl+C stops it)" >&2
  run "$ctr" run --rm "${tty_args[@]}" "${hardening[@]}" --read-only --tmpfs /tmp \
    -p "$bind:$port:8080" "$image" "$@"
  exit
fi

image=${MARS_IMAGE:-localhost/mars-ide:$arch}
if ! have_image "$image"; then
  need_podman "$image" MARS_IMAGE
  run env ARCHES="$arch" bash container/build-image.sh
fi
mkdir -p "$ws"
ws=$(realpath "$ws")
# :z relabels the mounted tree for SELinux (shared label); never do that to your whole home or /.
if [[ $ws == "$(realpath "$HOME")" || $ws == / ]]; then
  echo "spawn: refusing to mount $ws as the workspace; cd into a project directory or set MARS_WORKSPACE" >&2
  exit 1
fi

if [[ $mode == tui ]]; then
  run "$ctr" run --rm "${tty_args[@]}" "${hardening[@]}" "${user_args[@]}" \
    -v "$ws:/work:z" "$image" "$@"
else
  port=${PORT:-8080}
  env_args=()
  [[ -n ${MARS_WEB_TOKEN:-} ]] && env_args=(-e MARS_WEB_TOKEN)
  echo "spawn: web IDE on http://$bind:$port/ — open the printed URL, replacing" \
    "localhost:8080 with $bind:$port (Ctrl+C stops it)" >&2
  run "$ctr" run --rm "${tty_args[@]}" "${hardening[@]}" "${user_args[@]}" --read-only --tmpfs /tmp \
    "${env_args[@]}" -p "$bind:$port:8080" -v "$ws:/work:z" "$image" web --port 8080 "$@"
fi
