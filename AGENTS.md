# Notes for coding agents

Read [CONTRIBUTING.md](CONTRIBUTING.md) first; these are the points that matter most.

- **Build on the laptop, never on the phone.** Builds and tests run in rootless podman containers
  here. Root inside is fine (rootless podman maps it to you on bind mounts); run workloads with
  `--cap-drop=ALL --security-opt=no-new-privileges`. Don't run builds, benchmarks or long tests on
  the user's phone; keep any phone run short.
- Build and test with `make` (`make` alone lists the targets) or `./build-all.sh`. Before
  committing: `make test` for engine or execution changes, `make test-tui` for `mars_tui/`,
  `make test-web` for `web/`.
- Mount the repository into containers with `:z` (shared SELinux label), never `:Z`: other
  containers using the tree at the same time fail with "Permission denied".
- MARS 4.5 (`vendor/Mars4_5.jar`) is the oracle; results must match it. Change MARS only through
  `engine/patch_core.py` and `engine/overlay/`.
- Don't commit build outputs, keystores, tokens or the reference-card PDF; check `git status`
  before committing.
- Don't restart or rebuild containers the user runs (`mars-ide`, `mars-ide-static`) unless asked.
- Commit style: `type(scope): subject` with a body that says how it was tested, and the agent's
  `Co-Authored-By:` / `Claude-Session:` trailers. Only commit or push when the user asks.
