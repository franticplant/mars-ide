# Releasing

- Versions are tags `vMAJOR.MINOR.PATCH` on `main`; a suffix (`v0.2.0-rc1`) marks a release
  candidate. Every `v0.x` release is a GitHub pre-release.
- Release notes live in `docs/release-notes/<tag>.md`, written and committed **before** tagging
  (`docs: v0.1.0 release notes`). There is no CHANGELOG file; the release notes are it.
- Releases are immutable: a tag that is already released is never rebuilt or re-uploaded. Fix
  forward with a new tag.

## Steps

```sh
make test-all                                   # on the laptop, on the commit to release
$EDITOR docs/release-notes/v0.1.0.md            # see release-notes/README.md for the shape
git commit -m "docs: v0.1.0 release notes" docs/release-notes/v0.1.0.md
git tag -a v0.1.0 -m v0.1.0
git push origin main v0.1.0
```

Pushing the tag starts `.github/workflows/release.yml`: it builds everything from the tag, runs
the conformance suite, attests the files (`gh attestation verify <file> -R <owner>/<repo>`),
pushes the multi-arch images to `ghcr.io/<owner>/mars-ide` and `…/mars-ide-static` (`:latest`
too for tags without a suffix) and creates the GitHub release with the notes, the engine jar,
the static site tarball, the arm64 image archive and `SHA256SUMS`. It can also be started by
hand for an existing tag (Actions → Release → Run workflow).
