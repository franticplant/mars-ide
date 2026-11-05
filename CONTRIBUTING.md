# Contributing

## Ground rules

- **Build on the laptop, never on the phone.** Everything builds in podman containers on a
  laptop or desktop; the phone only runs images or archives built elsewhere. Keep anything run
  on the phone short (no builds, no long benchmarks or soak tests there).
- **MARS is the oracle.** Execution must match the unmodified `vendor/Mars4_5.jar`. A change
  that affects assembly or simulation comes with a program in `tests/conformance/progs/`, and
  `make test` must pass. Don't edit `vendor/Mars4_5.jar` or `engine/resources/`; change MARS
  through `engine/patch_core.py` or `engine/overlay/`.
- **No secrets in the repository.** Keystores, tokens and `.env` files are git-ignored; CI gets
  them from repository secrets. Don't add third-party files without recording their origin and
  license in THIRD_PARTY_NOTICES.md.
- **Localhost by default.** Anything that listens binds `127.0.0.1` unless the user asks
  otherwise; containers run rootless and as a non-root user.

## Before you push

```sh
make test       # always, for engine/, web/js/engine.js, web/static/ and conformance changes
make test-tui   # mars_tui/ changes
make test-web   # web/ changes
```

CI runs all three on every push and pull request.

## Commits

History on `main` is linear: commit to `main` directly or rebase a branch onto it; no merge
commits. Pull requests come from forks, Dependabot and anyone who wants a review first; they
are rebased or squashed in.

Subject: `type(scope): what changed`, lower case, no full stop, about 72 characters at most.

- types: `feat`, `fix`, `perf`, `test`, `docs`, `ci`, `build`, `refactor`;
- scopes (optional): `engine`, `teavm`, `tui`, `web`, `static`, `container`, `conformance`;
- a commit that only touches one area can use the area as prefix instead: `scripts: …`,
  `.github: …` (Dependabot), `engine: …` (Dependabot, Maven).

Examples:

```
feat(web): import and export folders as .zip
fix(teavm): bit-exact java.util.Random in the browser engine
test(conformance): kernel exception handler and eret
docs: v0.1.0 release notes
```

Body, wrapped at about 72 columns: what was wrong or missing and what the change does, in terms
of what the user sees; then how it was tested, concretely (`Tested: make test, 20 programs
agree; stepped through handler.asm in the web UI on a phone`). Say what you could not
reproduce or did not test.

Commits made with an AI agent end with its trailers, for example:

```
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_…
```

## Releases

Tags `vX.Y.Z` on `main`, with `docs/release-notes/vX.Y.Z.md` committed before the tag. See
[docs/releasing.md](docs/releasing.md).
