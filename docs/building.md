# Building

Build on a laptop or desktop, never on the phone: the phone only runs images or archives built
elsewhere. Every step runs in a podman container, so the host needs only `podman`, `python3`,
`make` and `git`. Outputs go to `build/` (git-ignored); container caches to `.cache/`.

| Step | `make` | `build-all.sh` | Output |
| --- | --- | --- | --- |
| Headless core, engine, web server, web UI | `make engine` | `engine` | `build/mars-engine.jar` |
| Textual for the TUI | `make pylib` | `pylib` | `build/pylib/` |
| Static site (TeaVM) | `make static-site` | `static` | `build/static/` |
| Images, amd64 + arm64, phone archive | `make image` | `image` | `mars-ide:{amd64,arm64,latest}`, `build/mars-ide-arm64.tar` |
| Static image | `make static-image` | | `mars-ide-static:latest` |
| Conformance suite | `make test` | `test` | |

`ARCHES="amd64"` limits `make image` to one architecture. `SKIP_TEAVM=1 ./build-all.sh static`
reuses an existing `engine/teavm/target/teavm/mars-engine.js`.

Container mounts of the repository use the shared SELinux label `:z`, not `:Z`: a private label
on a tree that several containers mount at once makes the others fail with "Permission denied".

## Running the IDE

`make tui|web|static` (or `scripts/spawn.sh tui|web|static` on the current directory) builds the
image if it is missing and runs it rootless, as your own uid, published on `127.0.0.1` only.
`scripts/spawn.sh -n …` prints the container command instead of running it. Variables: `PORT`,
`BIND`, `MARS_WORKSPACE`, `MARS_WEB_TOKEN`, `MARS_IMAGE`, `MARS_STATIC_IMAGE`,
`CONTAINER_ENGINE` (see the script's header). Building needs podman; with docker, point
`MARS_IMAGE` / `MARS_STATIC_IMAGE` at published images (`ghcr.io/<owner>/mars-ide:<tag>`).

Without containers (e.g. Termux on the phone, with a prebuilt `build/`): Python 3.10+ and
Java 11+:

```sh
PYTHONPATH=build/pylib:. python3 -m mars_tui            # TUI
PYTHONPATH=build/pylib:. python3 -m mars_tui web        # web server on 127.0.0.1:8080
```

On the phone (arm64) load the archive instead: `podman load -i mars-ide-arm64.tar`.

As a service: `container/mars-ide.container` is an example quadlet; replace its `User=`,
`Group=` and `PublishPort=` lines with your own before installing it.

## Reference card

The Help → Card tab is generated from `tools/gen_refcard.py` (`make refcard` writes
`mars_tui/refcard.json` and `web/js/refcard.js`). Its "Open original PDF" link points at
`web/ref/MIPS_Reference.pdf`, which is in the repository (origin and license unknown; see
THIRD_PARTY_NOTICES.md). To update the card, replace the PDF and edit `tools/gen_refcard.py`.

## Signing keys and secrets

Nothing secret is committed: `*.keystore`, `*.jks`, `signing.properties` and `.env` files are
git-ignored. Anything that needs a key or token in CI gets it from repository secrets (the
release workflow only uses the built-in `GITHUB_TOKEN`). Commits and tags are SSH-signed
(`gpg.format=ssh`, repository-local git config).
