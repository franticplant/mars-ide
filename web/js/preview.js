/* Markdown is parsed and rendered only in a sandbox with no IDE origin/storage access. */
(function () {
  "use strict";
  const STYLE = `
    :root{--hair:color-mix(in srgb,var(--text) 16%,transparent);scrollbar-color:var(--muted) var(--surface)}
    body{margin:0;padding:24px;background:var(--surface);color:var(--text);font:16px/1.65 var(--sans,system-ui,sans-serif);overflow-wrap:anywhere}
    main{max-width:900px;margin:auto}h1,h2{border-bottom:1px solid var(--hair);padding-bottom:.25em}
    a{color:var(--primary)}a:focus-visible{outline:2px solid var(--primary);outline-offset:2px}
    pre{padding:14px;background:var(--panel);border:1px solid var(--hair);border-radius:7px;overflow:auto;white-space:pre;overflow-wrap:normal}
    code{font:var(--code-size,14px)/1.6 var(--mono,ui-monospace,monospace);background:var(--panel)}pre code{background:none}
    blockquote{margin-left:0;padding-left:16px;border-left:4px solid var(--hair);color:var(--muted)}
    table{border-collapse:collapse;display:block;overflow:auto}td,th{border:1px solid var(--hair);padding:6px 12px}th,tr:nth-child(even){background:var(--panel)}
    img{max-width:100%;height:auto}input{margin-right:7px;accent-color:var(--primary)}hr{border:0;border-top:1px solid var(--hair)}summary{cursor:pointer}
    ::selection{background:color-mix(in srgb,var(--primary) 28%,transparent);color:var(--text)}
    .mermaid{white-space:normal;text-align:center;background:var(--surface)}.mermaid svg{max-width:100%;height:auto}
    .hljs-keyword,.hljs-selector-tag{color:var(--s-instr)}.hljs-string{color:var(--s-string)}.hljs-title{color:var(--s-label)}
    .hljs-number,.hljs-literal{color:var(--s-number)}.hljs-comment{color:color-mix(in srgb,var(--s-comment) 70%,var(--text))}
    .hljs-built_in,.hljs-type{color:var(--s-directive)}
    @media(max-width:500px){body{padding:16px}}
  `;
  const COLOR_KEYS = ["surface", "panel", "raised", "text", "muted", "primary", "accent", "error", "s-instr", "s-directive", "s-string", "s-label", "s-number", "s-comment"];
  function currentTheme() {
    const css = getComputedStyle(document.documentElement);
    return { dark: document.documentElement.dataset.dark !== "0",
      colors: Object.fromEntries(COLOR_KEYS.map(k => [k, css.getPropertyValue("--" + k).trim()])),
      sans: css.getPropertyValue("--sans").trim(), mono: css.getPropertyValue("--mono").trim(),
      codeSize: parseFloat(css.getPropertyValue("--ed-fs")) || 14 };
  }
  let rendererSource;
  function rendererText() {
    if (!rendererSource) rendererSource = fetch(new URL("vendor/markdown.js", document.baseURI), { credentials: "omit" })
      .then(response => { if (!response.ok) throw new Error("Renderer unavailable"); return response.text(); })
      .catch(error => { rendererSource = null; throw error; });
    return rendererSource;
  }
  class MarkdownPreview {
    constructor(host, hooks) {
      this.host = host; this.hooks = hooks; this.id = 0; this.images = Object.create(null);
      this.receive = e => this.message(e); window.addEventListener("message", this.receive);
      this.frame = document.createElement("iframe");
      this.frame.className = "markdown-preview"; this.frame.title = "Markdown preview";
      this.frame.setAttribute("sandbox", "allow-scripts");
      this.frame.setAttribute("referrerpolicy", "no-referrer");
      host.append(this.frame); this.start();
    }
    async start() {
      clearTimeout(this.timeout); this.ready = false; this.busy = false;
      this.timeout = setTimeout(() => this.fail("Preview could not start. Reopen Preview to retry."), 15000);
      try {
        // Opaque frames cannot reliably use the IDE's service worker. Fetch in the parent,
        // where the offline cache applies, then grant just this trusted script a nonce.
        const script = (await rendererText()).replace(/<\/script/gi, "<\\/script"); if (this.dead) return;
        const nonce = document.querySelector('meta[name="mars-script-nonce"]')?.content || Array.from(crypto.getRandomValues(new Uint8Array(16)), n => n.toString(16).padStart(2, "0")).join("");
        const policy = `default-src 'none'; script-src 'nonce-${nonce}'; style-src 'unsafe-inline'; img-src data:; font-src 'none'; connect-src 'none'; base-uri 'none'; form-action 'none'`;
        const theme = this.theme || currentTheme();
        const colors = COLOR_KEYS.filter(k => /^#[a-f\d]{6}$/i.test(theme.colors[k])).map(k => `--${k}:${theme.colors[k]}`).join(";");
        this.frame.srcdoc = `<!doctype html><html style="${colors};color-scheme:${theme.dark ? "dark" : "light"}"><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="${MIPS.esc(policy)}"><meta name="referrer" content="no-referrer"><style>${STYLE}</style><main id="content">Loading preview…</main><script nonce="${nonce}">${script}</script>`;
      } catch (_) { this.fail("Preview renderer unavailable. Reopen Preview to retry."); }
    }
    update(path, text) {
      const theme = currentTheme(), themeKey = JSON.stringify(theme);
      if (path !== this.path) { this.images = Object.create(null); this.imageBytes = 0; this.remote = false; this.loading = new Set(); }
      if (path === this.path && text === this.text && themeKey === this.themeKey) return;
      this.path = path; this.text = text; this.theme = theme; this.themeKey = themeKey;
      clearTimeout(this.debounce); this.debounce = setTimeout(() => this.render(), 200);
    }
    render() {
      if (!this.ready || this.busy || this.dead) return;
      this.busy = true;
      this.renderedText = this.text; this.renderedPath = this.path; this.renderedTheme = this.themeKey;
      const id = ++this.id;
      this.frame.contentWindow.postMessage({ type: "render", id, path: this.path, text: this.text || "", theme: this.theme, images: this.images }, "*");
      clearTimeout(this.timeout);
      this.timeout = setTimeout(() => this.fail("Preview timed out. Source is still available; reopen Preview to retry."), 10000);
    }
    fail(text) {
      this.dead = true; this.frame.remove(); this.host.textContent = text;
      this.host.classList.add("preview-error"); this.host.setAttribute("role", "status");
      clearTimeout(this.timeout);
    }
    async message(e) {
      if (e.source !== this.frame.contentWindow || !e.data || typeof e.data !== "object" || this.dead) return;
      const d = e.data;
      if (d.type === "ready") { this.ready = true; clearTimeout(this.timeout); this.render(); return; }
      if (d.type === "key" && typeof d.key === "string") {
        const key = d.key.toLowerCase(), mod = d.ctrlKey === true || d.metaKey === true;
        // No simulation/execution commands or arbitrary engine messages cross this boundary.
        if (["Escape", "F10"].includes(d.key) || key === "v" && !mod || mod && (["s", "k", "\\"].includes(key) || d.shiftKey === true && key === "v") || d.altKey === true && d.shiftKey === true && ["m", "g"].includes(key)) {
          this.hooks.key({ key: d.key, ctrlKey: d.ctrlKey === true, metaKey: d.metaKey === true, altKey: d.altKey === true, shiftKey: d.shiftKey === true });
        }
        return;
      }
      if (d.id !== this.id) return;
      if (d.type === "focus") { this.hooks.focus(); return; }
      if (d.type === "rendered") {
        this.busy = false; clearTimeout(this.timeout);
        if (this.renderedText !== this.text || this.renderedPath !== this.path || this.renderedTheme !== this.themeKey || this.imagesChanged) {
          this.imagesChanged = false; this.render();
        }
      } else if (d.type === "link" && typeof d.url === "string" && d.url.length < 8192) {
        if (this.renderedPath === this.path) this.hooks.link(this.path, d.url);
      } else if (d.type === "image" && typeof d.url === "string" && d.url.length < 8192) {
        if (this.renderedPath !== this.path) return;
        const path = this.path, url = d.url;
        if (!this.loading) this.loading = new Set();
        if (this.loading.has(url) || this.loading.size >= 32 || this.imageBytes >= 28000000) return;
        this.loading.add(url);
        try {
          const data = await this.hooks.image(path, url, this.remote);
          if (!this.dead && data && path === this.path && this.imageBytes + data.length <= 28000000) { this.imageBytes += data.length; this.images[url] = data; this.imagesChanged = true; if (!this.busy) { this.imagesChanged = false; this.render(); } }
        } catch (_) { /* Missing/blocked resources retain their alt text. */ }
      }
    }
    allowRemote() {
      this.remote = true; this.loading = new Set(); this.render();
    }
    destroy() {
      this.dead = true;
      clearTimeout(this.timeout); clearTimeout(this.debounce);
      window.removeEventListener("message", this.receive); this.frame.remove();
    }
  }
  // Real document (not srcdoc): its network policy does not relax the IDE's connect-src 'self'.
  let downloader;
  window.fetchPreviewImage = async url => {
    if (!downloader) {
      const frame = document.createElement("iframe"); frame.hidden = true; frame.title = "Isolated image downloader";
      frame.setAttribute("sandbox", "allow-scripts"); frame.setAttribute("referrerpolicy", "no-referrer");
      const state = downloader = { frame, pending: new Map(), id: 0 };
      state.ready = new Promise((resolve, reject) => {
        const timeout = setTimeout(() => reject(new Error("Image downloader unavailable")), 15000);
        window.addEventListener("message", e => {
          if (e.source !== frame.contentWindow || !e.data) return;
          if (e.data.type === "ready") { clearTimeout(timeout); resolve(); return; }
          const pending = state.pending.get(e.data.id);
          if (e.data.type !== "image" || !pending) return;
          clearTimeout(pending.timeout); state.pending.delete(e.data.id);
          if (!e.data.error && e.data.bytes instanceof ArrayBuffer && e.data.bytes.byteLength <= 5000000) pending.resolve(new Uint8Array(e.data.bytes));
          else pending.reject(new Error("Image unavailable"));
        });
      });
      frame.src = new URL("remote-images.html", document.baseURI).href; document.body.append(frame);
    }
    await downloader.ready;
    const id = ++downloader.id;
    return new Promise((resolve, reject) => {
      const state = downloader;
      const timeout = setTimeout(() => { state.pending.delete(id); reject(new Error("Image timed out")); }, 10000);
      state.pending.set(id, { resolve, reject, timeout });
      state.frame.contentWindow.postMessage({ type: "image", id, url }, "*");
    });
  };
  window.MarkdownPreview = MarkdownPreview;
})();
