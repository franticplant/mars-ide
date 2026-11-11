/* Editor groups: a binary split tree; document text belongs to the app, never to a view. */
(function () {
  "use strict";
  const esc = MIPS.esc;
  const MD = p => /\.(md|markdown)$/i.test(p || "");
  const DND = "application/x-mars-view";
  class EditorGroups {
    constructor(host, editor, hooks) {
      this.host = host; this.hooks = hooks; this.groups = []; this.next = 0;
      const group = this.create(editor); this.active = group;
      this.tree = { group }; this.mount();
      this.resize = () => this.paint(); window.addEventListener("resize", this.resize);
    }
    create(editor) {
      const g = { id: ++this.next, tabs: [], index: 0 };
      g.host = document.createElement("section"); g.host.className = "editor-group"; g.host.dataset.group = g.id;
      g.bar = document.createElement("div"); g.bar.className = "group-bar";
      g.tabsEl = document.createElement("div"); g.tabsEl.className = "group-tabs"; g.tabsEl.setAttribute("role", "tablist"); g.tabsEl.setAttribute("aria-label", "Editor group " + g.id);
      g.actions = document.createElement("div"); g.actions.className = "group-actions";
      g.bar.append(g.tabsEl, g.actions);
      g.body = document.createElement("div"); g.body.className = "group-body";
      const source = editor ? editor.host : document.createElement("div");
      g.editor = editor || this.hooks.editor(source);
      g.body.append(source); g.host.append(g.bar, g.body);
      g.host.addEventListener("focusin", e => { if (g.body.contains(e.target) && this.active !== g) this.activate(g); });
      g.host.addEventListener("pointerdown", e => { if (g.body.contains(e.target) && this.active !== g) this.activate(g); }, true);
      g.host.addEventListener("dragover", e => {
        if (!this.drag || !Array.from(e.dataTransfer.types).includes(DND)) return;
        e.preventDefault(); e.stopPropagation(); e.dataTransfer.dropEffect = "move";
        const edge = this.edge(g, e); g.host.dataset.drop = edge;
      });
      g.host.addEventListener("dragleave", e => { if (!g.host.contains(e.relatedTarget)) delete g.host.dataset.drop; });
      g.host.addEventListener("drop", e => {
        if (!this.drag) return;
        e.preventDefault(); e.stopPropagation();
        const { group: from, tab } = this.drag, edge = this.edge(g, e);
        this.endDrag();
        const target = edge === "center" ? g : this.split(g, edge, null);
        if (!target) return;
        if (target === from && edge === "center" && from.tabs.includes(tab)) {
          const at = e.target.closest("[data-tab]");
          if (at) { const i = from.tabs.indexOf(tab), j = +at.dataset.tab; from.tabs.splice(i, 1); from.tabs.splice(j, 0, tab); }
          from.index = from.tabs.indexOf(tab);
        } else {
          from.tabs = from.tabs.filter(t => t !== tab);
          const existing = target.tabs.find(t => t.path === tab.path && t.mode === tab.mode);
          if (!existing) target.tabs.push(tab);
          target.index = target.tabs.indexOf(existing || tab);
        }
        if (!from.tabs.length && from !== target) this.remove(from);
        this.activate(target); this.changed();
      });
      this.groups.push(g); return g;
    }
    tab(g = this.active) { return g.tabs[g.index] || g.tabs[0]; }
    edge(g, e) {
      if (e.target.closest(".group-bar")) return "center";
      const r = g.body.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
      const n = Math.min(x, 1 - x, y, 1 - y);
      return n > .23 ? "center" : n === x ? "left" : n === 1 - x ? "right" : n === y ? "top" : "bottom";
    }
    endDrag() { this.drag = null; for (const g of this.groups) { delete g.host.dataset.drop; g.body.style.pointerEvents = ""; } }
    captureView(g = this.active) {
      const t = this.tab(g), ta = g.editor.ta;
      if (t && g.editor.documentPath === t.path) t.view = { top: ta.scrollTop, left: ta.scrollLeft, sel: ta.selectionStart, end: ta.selectionEnd };
    }
    activate(g, index = g.index) {
      if (!this.restoring) this.captureView();
      this.hooks.stash(); this.active = g; g.index = Math.max(0, Math.min(index, g.tabs.length - 1));
      const t = this.tab(g);
      const restoreView = this.restoring || g.editor.documentPath !== t?.path;
      if (t) this.hooks.activate(g.editor, t.path);
      if (restoreView && t?.view) {
        g.editor.ta.setSelectionRange(t.view.sel || 0, t.view.end ?? t.view.sel ?? 0);
        g.editor.ta.scrollTop = t.view.top || 0; g.editor.ta.scrollLeft = t.view.left || 0; g.editor.syncScroll();
      }
      this.paint(); this.changed();
    }
    sync(path) {
      // Reconcile global file closes/deletes without duplicating or discarding documents.
      const emptied = [];
      for (const g of this.groups) {
        const hadTabs = g.tabs.length > 0;
        const t = this.tab(g);
        g.tabs = g.tabs.filter(t => this.hooks.file(t.path));
        g.index = Math.max(0, t ? g.tabs.indexOf(t) : 0);
        if (hadTabs && !g.tabs.length) emptied.push(g);
      }
      // A closed file may have been the last tab of the active pane. Remove that
      // pane before reconciling the current file, rather than opening the remaining
      // file into the empty pane and leaving a duplicate split behind.
      for (const g of emptied) {
        if (!this.groups.includes(g) || this.groups.length <= 1) continue;
        const wasActive = g === this.active;
        this.remove(g);
        if (wasActive) path = this.tab(this.active)?.path || null;
      }
      for (const g of [...this.groups]) if (g !== this.active && !g.tabs.length) this.remove(g);
      const g = this.active;
      if (path && this.hooks.file(path) && this.tab(g)?.path !== path) {
        let i = g.tabs.findIndex(t => t.path === path && t.mode === "source");
        if (i < 0) { i = g.tabs.length; g.tabs.push({ path, mode: "source" }); }
        g.index = i;
      }
      this.refresh();
      this.changed();
    }
    refresh() { for (const g of this.groups) this.render(g); this.paint(); }
    render(g) {
      const tab = this.tab(g), f = tab && this.hooks.file(tab.path);
      g.tabsEl.innerHTML = g.tabs.map((t, i) => `<div class="group-tab ${i === g.index ? "selected" : ""}" draggable="true" data-tab="${i}"><button role="tab" aria-selected="${i === g.index}" title="${esc(t.path)}" data-select="${i}">${esc(t.path.split("/").pop())}${t.mode === "preview" ? " · Preview" : ""}${this.hooks.dirty(t.path) ? " •" : ""}</button><button data-close="${i}" aria-label="Close view">×</button></div>`).join("");
      g.tabsEl.querySelectorAll("[data-select]").forEach(b => b.onclick = () => this.activate(g, +b.dataset.select));
      g.tabsEl.querySelectorAll("[data-close]").forEach(b => b.onclick = e => { e.stopPropagation(); this.close(g, +b.dataset.close); });
      g.tabsEl.querySelectorAll("[data-tab]").forEach(b => b.ondragstart = e => {
        this.drag = { group: g, tab: g.tabs[+b.dataset.tab] };
        e.dataTransfer.setData(DND, "view"); e.dataTransfer.effectAllowed = "move";
        // Let drops hit a pane rather than the opaque-origin preview's document.
        for (const item of this.groups) item.body.style.pointerEvents = "none";
        b.ondragend = () => this.endDrag();
      });
      g.tabsEl.querySelectorAll("[data-tab]").forEach(b => {
        b.addEventListener("mousedown", e => { if (e.button === 1) e.preventDefault(); });
        b.addEventListener("auxclick", e => { if (e.button === 1) { e.preventDefault(); this.close(g, +b.dataset.tab); } });
      });
      g.actions.replaceChildren();
      const button = (label, title, fn) => {
        const b = document.createElement("button"); b.textContent = label; b.title = title; b.setAttribute("aria-label", title); b.onclick = fn; g.actions.append(b);
      };
      if (MD(tab?.path)) {
        button(tab.mode === "preview" ? "Source" : "Preview", "Toggle Markdown source / preview (Ctrl+Shift+V)", () => { this.activate(g); this.mode(); });
        button("◫", "Open preview beside (Ctrl+K, V)", () => this.split(g, "right", { path: tab.path, mode: "preview" }));
        if (tab.mode === "preview") button("Images", "Load remote images for this preview (contacts external servers)", async () => {
          if (await this.hooks.remote()) g.preview?.allowRemote();
        });
      }
      if (tab?.mode === "source" && this.hooks.canInspect?.(tab.path)) {
        button("Values", "Inspect the current source line's runtime values", () => { this.activate(g); this.hooks.inspectLine(g.editor); });
      }
      if (tab && this.hooks.history) button("History", "File history", () => this.hooks.history(tab.path));
      button("⋯", "Editor group actions", () => this.menu(g));
      const documentChanged = g.editor.documentPath !== (tab?.path || null);
      if (g.editor.value !== (f?.text || "") || documentChanged) {
        const view = documentChanged && tab?.view || { top: g.editor.ta.scrollTop, left: g.editor.ta.scrollLeft, sel: g.editor.ta.selectionStart, end: g.editor.ta.selectionEnd };
        g.editor.value = f?.text || ""; g.editor.ta.setSelectionRange(view.sel || 0, view.end ?? view.sel ?? 0);
        g.editor.ta.scrollTop = view.top || 0; g.editor.ta.scrollLeft = view.left || 0; g.editor.syncScroll();
      }
      g.editor.documentPath = tab?.path || null;
      const preview = tab?.mode === "preview";
      const plainText = MD(tab?.path);
      if (g.editor.plainText !== plainText) { g.editor.plainText = plainText; g.editor.render(true); }
      g.editor.ta.setAttribute("aria-label", plainText ? "Document source" : "MIPS source code");
      g.editor.ta.disabled = !f;
      g.editor.ta.placeholder = f ? "" : "Open or create a file to start editing";
      this.hooks.decorate(g.editor, tab?.path);
      g.editor.host.hidden = preview;
      g.editor.host.style.display = preview ? "none" : "";
      if (preview && f) {
        if (!g.preview) {
          g.previewHost = document.createElement("div"); g.previewHost.className = "preview-host"; g.body.append(g.previewHost);
          g.preview = new MarkdownPreview(g.previewHost, { ...this.hooks.preview,
            focus: () => { if (this.active !== g) this.activate(g); },
            link: (path, url) => { this.activate(g); this.hooks.preview.link(path, url); },
            key: key => { this.activate(g); this.hooks.key(key); } });
        }
        g.preview.update(tab.path, f.text);
      } else if (g.preview) { g.preview.destroy(); g.previewHost.remove(); g.preview = null; }
    }
    mode() {
      const t = this.tab(); if (!MD(t?.path)) return;
      const mode = t.mode === "preview" ? "source" : "preview";
      const existing = this.active.tabs.findIndex(v => v.path === t.path && v.mode === mode);
      if (existing >= 0) this.activate(this.active, existing);
      else { t.mode = mode; this.refresh(); this.changed(); }
    }
    split(g = this.active, edge = "right", tab = this.tab(g) && { ...this.tab(g) }) {
      if (this.groups.length >= 8) { this.hooks.toast("At most eight editor groups."); return null; }
      const fresh = this.create(); if (tab) fresh.tabs.push(tab);
      const replace = node => {
        if (node.group === g) {
          const before = edge === "left" || edge === "top";
          return { axis: edge === "left" || edge === "right" ? "row" : "column", ratio: .5,
            first: before ? { group: fresh } : node, second: before ? node : { group: fresh } };
        }
        if (!node.group) { node.first = replace(node.first); node.second = replace(node.second); }
        return node;
      };
      this.tree = replace(this.tree); this.maximized = false; this.mount();
      if (tab) this.activate(fresh); this.changed(); return fresh;
    }
    remove(g) {
      if (this.groups.length === 1) return;
      const prune = node => {
        if (node.group) return node.group === g ? null : node;
        const a = prune(node.first), b = prune(node.second);
        return !a ? b : !b ? a : { ...node, first: a, second: b };
      };
      this.tree = prune(this.tree); this.groups = this.groups.filter(x => x !== g);
      g.preview?.destroy(); g.editor.destroy?.(); g.host.remove();
      if (this.active === g) { this.active = this.groups[0]; this.hooks.activate(this.active.editor, this.tab()?.path || null); }
      this.mount();
    }
    async close(g, index, options = {}) {
      const t = g.tabs[index]; if (!t) return;
      const refs = this.groups.reduce((n, x) => n + x.tabs.filter(v => v.path === t.path).length, 0);
      if (refs === 1 && !(await this.hooks.close(t.path, options))) return;
      g.tabs = g.tabs.filter(v => v !== t); g.index = Math.max(0, Math.min(g.index, g.tabs.length - 1));
      if (!g.tabs.length && this.groups.length > 1) this.remove(g);
      this.activate(this.groups.includes(g) ? g : this.active); this.refresh(); this.changed();
    }
    menu(g) {
      this.activate(g);
      const actions = [
        ["Split right", () => this.split(g, "right")], ["Split down", () => this.split(g, "bottom")],
        [this.maximized ? "Restore all panes" : "Maximize active pane", () => this.maximize()],
        ["Next group", () => this.nextGroup()],
      ];
      if (this.groups.length > 1) actions.push(["Move view to next group", () => {
        const t = this.tab(g), next = this.groups[(this.groups.indexOf(g) + 1) % this.groups.length];
        if (!t) return;
        if (!next.tabs.some(x => x.path === t.path && x.mode === t.mode)) next.tabs.push(t);
        next.index = next.tabs.findIndex(x => x.path === t.path && x.mode === t.mode);
        g.tabs = g.tabs.filter(x => x !== t); if (!g.tabs.length) this.remove(g);
        this.activate(next); this.refresh();
      }], ["Join group into next", () => {
        const next = this.groups[(this.groups.indexOf(g) + 1) % this.groups.length];
        for (const t of g.tabs) if (!next.tabs.some(x => x.path === t.path && x.mode === t.mode)) next.tabs.push(t);
        this.remove(g); this.activate(next); this.refresh();
      }]);
      this.hooks.menu(actions);
    }
    nextGroup() { this.activate(this.groups[(this.groups.indexOf(this.active) + 1) % this.groups.length]); }
    maximize() { this.maximized = !this.maximized; this.paint(); }
    mount() {
      const build = node => {
        if (node.group) return node.group.host;
        const box = document.createElement("div"); box.className = "group-split split-" + node.axis;
        const a = build(node.first), b = build(node.second), handle = document.createElement("div");
        handle.className = "group-divider"; handle.tabIndex = 0; handle.setAttribute("role", "separator");
        handle.setAttribute("aria-label", "Resize editor groups"); handle.setAttribute("aria-orientation", node.axis === "row" ? "vertical" : "horizontal");
        const size = () => { a.style.flex = `${node.ratio} 1 0`; b.style.flex = `${1 - node.ratio} 1 0`; handle.setAttribute("aria-valuenow", Math.round(node.ratio * 100)); };
        a.style.flex = ""; b.style.flex = ""; size();
        handle.onpointerdown = e => {
          e.preventDefault(); handle.setPointerCapture(e.pointerId);
          const move = e => { const r = box.getBoundingClientRect(); node.ratio = Math.max(.15, Math.min(.85, node.axis === "row" ? (e.clientX - r.left) / r.width : (e.clientY - r.top) / r.height)); size(); };
          handle.onpointermove = move;
          handle.onpointerup = handle.onpointercancel = () => { handle.onpointermove = null; this.changed(); };
        };
        handle.onkeydown = e => {
          if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)) return;
          e.preventDefault(); node.ratio = Math.max(.15, Math.min(.85, node.ratio + (["ArrowLeft", "ArrowUp"].includes(e.key) ? -.05 : .05))); size(); this.changed();
        };
        box.append(a, handle, b); return box;
      };
      const root = build(this.tree);
      // A former split child may still have an inline fraction such as
      // `flex: .5 1 0`. At the root that leaves unused workspace instead of
      // filling it. Nested children get their ratios from their parent above.
      root.style.flex = "";
      this.host.replaceChildren(root); this.refresh();
    }
    paint() {
      const narrow = window.matchMedia("(max-width: 899px)").matches;
      this.host.classList.toggle("single-group", narrow || !!this.maximized);
      for (const g of this.groups) g.host.classList.toggle("active-group", g === this.active);
      for (const g of this.groups) if (g === this.active || !narrow) g.editor.measure();
    }
    remap(map) { for (const g of this.groups) for (const t of g.tabs) t.path = map(t.path); this.refresh(); this.changed(); }
    changed() { if (this.restoring) return; this.hooks.persist(this.serialize()); }
    serialize() {
      const walk = node => node.group ? { tabs: node.group.tabs, index: node.group.index, active: node.group === this.active } : { axis: node.axis, ratio: node.ratio, first: walk(node.first), second: walk(node.second) };
      return walk(this.tree);
    }
    restore(layout) {
      if (!layout) return;
      this.restoring = true;
      const original = this.groups[0]; let count = 0, usedOriginal = false;
      const walk = (node, depth = 0) => {
        if (!node || depth > 7 || ++count > 15) throw new Error("Invalid group layout");
        if (Array.isArray(node.tabs)) {
          const g = usedOriginal ? this.create() : original; usedOriginal = true;
          g.tabs = node.tabs.filter(t => t && typeof t.path === "string" && this.hooks.file(t.path)).slice(0, 100).map(t => ({ path: t.path, mode: t.mode === "preview" && MD(t.path) ? "preview" : "source",
            view: t.view && Object.fromEntries(["top", "left", "sel", "end"].map(k => [k, Number.isFinite(t.view[k]) ? Math.max(0, t.view[k]) : 0])) }));
          g.index = Number.isInteger(node.index) ? Math.max(0, Math.min(node.index, g.tabs.length - 1)) : 0;
          if (node.active) this.active = g;
          return { group: g };
        }
        if (!["row", "column"].includes(node.axis)) throw new Error("Invalid split axis");
        return { axis: node.axis, ratio: Number.isFinite(node.ratio) ? Math.max(.15, Math.min(.85, node.ratio)) : .5, first: walk(node.first, depth + 1), second: walk(node.second, depth + 1) };
      };
      try {
        // Reuse the primary editor for the first restored leaf.
        original.tabs = []; this.tree = walk(layout);
        if (!this.groups.includes(this.active)) this.active = this.groups[0];
        // Older saved layouts can already contain a stranded empty split.
        for (const g of [...this.groups]) if (!g.tabs.length && this.groups.length > 1) this.remove(g);
        this.mount(); this.activate(this.active);
      } catch (_) {
        for (const g of [...this.groups]) if (g !== original) { g.preview?.destroy(); g.editor.destroy?.(); g.host.remove(); }
        this.groups = [original]; this.active = original; this.tree = { group: original }; this.mount();
      } finally { this.restoring = false; }
    }
  }
  window.EditorGroups = EditorGroups;
})();
