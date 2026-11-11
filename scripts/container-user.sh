# Source from repository-root build/test orchestrators. Workloads stay in disposable containers.
if [ "$(id -u)" = 0 ] || [ "$(podman info --format '{{.Host.Security.Rootless}}')" != true ]; then
  echo "Builds require rootless Podman under a non-root host user." >&2
  exit 1
fi
# Root inside a rootless container is mapped to the host user on bind mounts, so files
# stay yours. Drop every capability instead of passing a host UID.
podman_run() {
  podman run --rm --cap-drop=ALL --security-opt=no-new-privileges "$@"
}
