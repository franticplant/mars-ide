# Third-party notices

MARS IDE builds on and ships third-party open-source software. This file is a hand-kept
inventory, not a machine-generated notice bundle; regenerate it from the exact resolved
dependencies before a binary release (see the last section).

## MARS 4.5 (shipped: engine, all builds)

MARS — MIPS Assembler and Runtime Simulator, version 4.5.
Copyright (c) 2003-2013, Pete Sanderson and Kenneth Vollmar. MIT license.
<https://dpetersanderson.github.io/>

- `vendor/Mars4_5.jar` is the unmodified official release
  (sha256 `ac340b676ba2b62246b9df77e62f81ad4447bcfd329ab539716bcd09950b7096`); its
  license is `MARSlicense.txt` inside the jar, copied to `engine/resources/MARSlicense.txt`.
- `engine/patch_core.py` extracts the MARS sources from that jar and removes the Swing/AWT
  parts. `engine/overlay/` holds replacement classes derived from MARS sources (Settings,
  dialog syscalls, tone generator, `venus` stubs); `engine/resources/` holds MARS's own
  resource files unchanged.
- Every build contains the MARS license text: the engine jar (and so the container image)
  as `MARSlicense.txt`, the static site inside `engine/mars-engine.js`.

MARS IDE is an independent project and is not affiliated with or endorsed by the MARS
authors or Missouri State University / Otterbein University.

## Textual and its dependencies (shipped: TUI, container image)

`./build-all.sh pylib` installs `textual==8.2.8` with pip into `build/pylib`, which the
container image ships. Textual is © Textualize Inc., MIT license. Its dependencies (at the
time of writing `rich` (MIT), `markdown-it-py` (MIT), `mdurl` (MIT), `mdit-py-plugins` (MIT),
`linkify-it-py` (MIT), `platformdirs` (MIT), `typing_extensions` (PSF-2.0), `pygments`
(BSD-2-Clause)) come with
their license files in their `*.dist-info/` directories; keep those directories in anything
that ships `build/pylib`.

## TeaVM (build time; runtime library compiled into the static build)

`engine/teavm/` compiles the engine to JavaScript with TeaVM 0.16.0 (Apache-2.0,
<https://teavm.org/>). The generated `mars-engine.js` contains TeaVM's Java class library
translated to JavaScript, so the static site ships Apache-2.0 code; Apache-2.0 notice
obligations apply to it.

## Java runtime (shipped: container image)

The container image contains a jlink'd runtime (`java.base`, `jdk.httpserver`) taken from
the Eclipse Temurin 21 JDK image: OpenJDK, GPL-2.0 with the Classpath Exception.

## Base images (shipped as layers of the images)

- `docker.io/library/python:3.12-slim` (Debian; Python under PSF-2.0, Debian packages under
  their own licenses): base of `mars-ide`.
- `docker.io/nginxinc/nginx-unprivileged:alpine` (nginx: BSD-2-Clause; Alpine packages under
  their own licenses): base of `mars-ide-static`.

Build and test only, not shipped: `eclipse-temurin:21-jdk-jammy`, `maven:3.9-eclipse-temurin-21`,
`node:22-slim`, `debian:trixie` with Chromium and Playwright (Apache-2.0).

## Not yet cleared

- `web/ref/MIPS_Reference.pdf`: a one-page MIPS reference card of unknown origin and license,
  included by the maintainer's decision so the Help → Card tab can link the original. If you are
  the author and want it credited differently or removed, open an issue.
- `tools/gen_refcard.py` → `mars_tui/refcard.json`, `web/js/refcard.js`: the reference-card
  data (instruction names, operations, encodings) was transcribed from that card. Instruction
  encodings are facts of the MIPS architecture, but the selection and wording follow the card.

## Before a binary release

- regenerate the Python inventory from `build/pylib/*.dist-info` for the exact versions;
- include Apache-2.0 NOTICE material for TeaVM in the static site if it has any;
- include the base images' license material or point to it in the release notes.
