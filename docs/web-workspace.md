# Browser editor groups and Markdown

Markdown (`.md`, `.markdown`) opens as editable source. The group toolbar offers **Preview**,
**Source**, and **Open preview beside**. Previews follow unsaved edits; all views of a file
share the same document, save operation and dirty state. Closing one view does not discard
another view's document. Closing the last view asks before discarding unsaved changes.

## Arrange your workspace
 
+- **Ctrl/Cmd+click** a register, label or number in the editor for a compact current-value
+  card. It shows pointer region, label and printable string where safe. While running the
+  card says *running · sampled*; memory is read only while paused, and MMIO is never read
+  automatically. The full Values button remains for deeper inspection.
 - Folder rows offer **New file here** and **New folder here**. The name field starts
  empty; the selected parent is shown separately. Typed subpaths are relative to that
  parent. Drag files/folders to move them, or use **Move to…** in the context menu;
  **Import here** remains available there too.
- Drag a group tab (or a top-level file tab) onto a pane's edge to split it; drop in the
  middle or tab bar to move it into that group. Drag along a group's tab bar to reorder.
- The group's **⋯** menu also offers split right/down, move to the next group, join groups,
  maximize/restore, and next group. These work without dragging, including on touchscreens.
- Resize splits with their handles. Focus a handle and use the arrow keys for keyboard resizing.
- Up to eight groups can be arranged in nested horizontal/vertical splits. The layout,
  active tabs and source/preview choices survive reloads in this browser.
- Narrow screens display only the active group. **Next group** switches between them; widening
  the window restores the split arrangement.
- During debugging, the editor's compact strip shows the latest values used by the next
  instruction. Tap a value for details or **Values** for the full operand view. The editor
  group's **Values** button inspects the source line containing the cursor. You can also
  double-click an assembled source line; pseudo-instructions can expand to several Basic
  instructions, so the current one is preferred when applicable. The strip is hidden for
  Markdown; instructions without explicit register operands say so.
- In Execute, tap **Basic** (or focus it and press Enter) to inspect current register
  values. The **Values** button works without double-tapping. Double-tap **Source** to open
  the corresponding editor line; use only the breakpoint gutter to toggle breakpoints.
  Values always describe the latest machine state—not a historical snapshot or a prediction.
  For a load/store, the inspector also computes its effective address and reads the current
  aligned memory word while paused. It does not automatically read MMIO or running memory.
- On phones, the bottom navigation remains at the physical bottom; the on-screen keyboard
  covers it while open instead of moving it above the keyboard or hiding it on editor focus.
- In Help → Card, tap a reference-card instruction or pseudo-instruction for a concise
  commented usage example (and its encoding, where applicable).
- **Zen (F10)** hides IDE chrome without removing any editor groups. **Maximize active pane**
  is separate and temporary. The visible **Exit Zen** button remains at the top even when the
  phone keyboard is open. Exiting restores the previous view/sidebar/panel settings; Escape
  also exits. Reloading always exits Zen, restores the prior layout, and keeps draft recovery.

Shortcuts (Command can replace Control on macOS):

| Action | Shortcut |
| --- | --- |
| Split right | Ctrl+\ |
| Toggle Markdown source/preview | Ctrl+Shift+V |
| Open Markdown preview beside | Ctrl+K, then V |
| Maximize/restore active pane | Alt+Shift+M |
| Next group | Alt+Shift+G |

## Rich content and resource policy

Previews support headings and heading anchors, emphasis, strikethrough, lists, task lists,
tables, block quotes, fenced code with syntax highlighting, links, raster images, and fenced
`mermaid` diagrams. Mermaid syntax errors are displayed in the preview without changing source.
Relative document links open workspace files; external HTTP(S) links require confirmation.
The preview uses the IDE's actual UI and syntax palettes, not a separate light/dark skin:
AMOLED stays black, all light themes use a light color scheme, diagrams follow the palette,
and fenced code follows the editor's font size and syntax colors. Changes apply live.

Local PNG/JPEG/GIF/WebP images resolve relative to the Markdown file, including `../` within
the workspace. No resource can escape the workspace. SVG images, arbitrary HTML, embedded
frames, diagram actions and document scripts are intentionally not executable features.

Remote images are blocked by default. **Images** explicitly enables HTTPS image downloads
for the current preview/file only, after confirmation. Downloads omit credentials and
referrers, reject redirects, and require the image host to permit CORS (the request origin is
opaque). Failure leaves the image's alt text; there is no server-side proxy. No chat
integration or API-token storage is included.

## Security boundary

The IDE never inserts rendered Markdown or Mermaid SVG into its own DOM. Each preview has
an opaque origin (`sandbox="allow-scripts"`, **without** `allow-same-origin`), so the trusted
renderer cannot access IDE cookies, local storage, IndexedDB, or workspace engine objects.
Only the locally bundled renderer is allowed to execute by the frame CSP. Document HTML is
disabled, generated markup/SVG is sanitized with DOMPurify, and diagram interactivity/HTML
labels are disabled. CSP denies connections, nested frames, forms, external image loads,
and other executable resources. Scripts are allowed for the trusted renderer, not documents.
The IDE fetches that fixed bundle through its own offline cache and embeds it with a script
nonce. The server generates a fresh nonce for each shell response (shared with its preview
frames); the static build generates per-frame nonces. The preview policy authorizes only
the nonce-bearing trusted renderer, not document code. Neither `unsafe-inline` scripts nor
Blob scripts are enabled by the server policy.

Messages are accepted only from the specific preview window; local paths, links and image
types are independently validated by the parent. Network-enabled image downloads happen
only through the explicit parent-side opt-in, using a separate opaque-origin downloader frame.
The server IDE keeps its `connect-src 'self'` policy; only the downloader can contact HTTPS
image hosts. Renderer/downloader code assets are public so sandboxed frames do not need the
IDE's authentication cookie; workspace data and engine APIs remain authenticated.
There is no general filesystem or engine RPC available to the preview.

GitHub Pages cannot send response headers, so the Pages build embeds a meta CSP with
`script-src 'self' 'unsafe-inline'`. Inline scripts are allowed there because `srcdoc`
previews inherit the parent policy and need their nonce renderer; the nginx deployment
keeps the stricter header without `unsafe-inline`. Meta CSP cannot enforce
`frame-ancestors`, so clickjacking protection is only present on the nginx deployment.
The sanitizer, opaque sandbox and escaping remain the primary XSS defenses in both.

Limits: 1 million source characters, 20 diagrams, 50,000 characters/500 edges per diagram,
32 images, 5 MB per image,
and approximately 20 MB of image data per preview. A rendering timeout removes a stuck frame;
source stays editable. These limits reduce accidental overload, but an iframe is not a hard
CPU/memory isolation boundary. Dependency updates and hostile-document regression tests are
still necessary; sanitization is not a claim that every future XSS is impossible.

## Building and testing

`make web-assets` uses a temporary Node/Podman container with persistent npm caches. Engine
and static-site builds do this automatically. Dependencies are pinned in
`tools/markdown/package-lock.json`; generated assets and license notices live in ignored
`web/vendor/` and ship with both web variants, including the static offline cache.
These build paths, including Python source/site generation and the browser/conformance
tests, use temporary rootless containers. Root inside the container is fine: rootless Podman
maps it to your host user on bind mounts, so artifacts stay yours. Every workload drops all
capabilities and sets `no-new-privileges`; `scripts/container-user.sh` rejects rootful Podman.
Dependency caches live in `.cache/npm`, `.cache/markdown-node`, and
`.cache/m2`; reusable artifacts remain in `build/` and `engine/teavm/target/`.

`make test-web` includes `tests/web_workspace.py`, covering authenticated server and static
UI under the GitHub Pages `/mars-ide/` subpath, rich rendering (also after an offline reload),
unsaved preview updates, layout restoration, narrow screens, origin
isolation, blocked tracking requests, and credential-free remote-image opt-in.
`tests/web_groups.py` covers real drag/drop, nested splits, resizing, shared breakpoints,
stepping, dirty-view closing, and no-drag group actions.

## Experimental browser storage and backups

Browser storage is not a backup. Export a workspace ZIP regularly, especially before updating,
switching browser profiles/origins, or clearing browser data. The IDE shows a non-blocking
experimental warning/reminder; a successful full-workspace export postpones it for a week.
Exports include hidden browser-workspace files and current unsaved editor buffers.

Newly saved files have an FNV-1a checksum to detect accidental byte changes (not malicious
tampering). Startup checks records before mirroring them into the simulator. Older files
remain readable and are not automatically rewritten just to add checksums. A separate
local-storage witness helps detect an unexpectedly emptied database. Intentionally empty
workspaces are not reseeded with examples. The database schema is unchanged.

On detected corruption/missing data, startup stops rather than repairing, reseeding, or
overwriting the stored records. **Download recovery copy** preserves available raw bytes,
draft/settings text and any open editor buffers in JSON. Invalid drafts are not overwritten
with an empty draft map. Failed transactions reject instead of hanging; failed draft saves
and simulator-file synchronization are visible. ZIP imports check entry sizes and CRCs.
Saves use a content-version check so a stale writer cannot silently replace a file changed
by another tab or the simulator. Unchanged worker copies are not written back over newer
browser files. Draft metadata checks for damage and saved-file changes across reloads;
save/reload callbacks do not mark newer typing as saved or replace a now-dirty buffer.
Recovery JSON also attempts to capture simulator-side files that could not be persisted.

Updates no longer take over an open editing session automatically. The new worker waits;
export a backup, close all IDE tabs, and reopen to update. Each worker reads only its own
versioned asset cache. Cleanup is scoped to this IDE installation, not unrelated apps.

Limits remain: clearing both IndexedDB and local storage can erase the witness too; browser
eviction, device failure and undetected corruption are still possible. Neither same-browser
metadata nor a recovery export can reconstruct bytes that are already gone. Keep exports
outside the browser; avoid editing the same unsaved draft in multiple tabs.
`tests/web_storage.py` exercises these failure paths.

## Optional WasmGC build

`make static-wasm` builds a separate experimental site in `build/static-wasm/`, without
overwriting the normal JavaScript site or its engine artifacts. It uses the same MARS Java
sources, protocol, worker isolation and browser workspace. It requires a browser supporting
WasmGC; there is no automatic JS fallback in this separate build.

`make compare-backends` records repeatable size/timing/RSS measurements and checks matching
results in `build/backend-comparison.json`. The initial three-trial Node 22 comparison found:

- Engine + loader gzip: JS 206,883 bytes; WasmGC 273,850 bytes.
- Wasm ran the sampled programs faster, but startup was slower and Node-process RSS higher.
- The Markdown renderer is much larger than either engine: 1,888,155 bytes gzip.

Node RSS includes Node/V8 and is **not** a browser-RAM measurement; results vary by workload
and device. The JavaScript backend remains the default because Wasm is not an across-the-board
size/memory win. There is no C rewrite: a hand-written rewrite would introduce a second simulator to maintain and
would need independent MARS conformance testing, not merely a new compiler switch.
