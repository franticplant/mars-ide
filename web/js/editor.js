/* Lightweight MIPS code editor: native <textarea> (great on phones) over a highlighted layer. */
(function (global) {
  "use strict";
  const { highlight, esc, ISA } = global.MIPS;

  class CodeEditor {
    constructor(host, opts = {}) {
      this.opts = opts;
      this.host = host;
      host.classList.add("ed");
      host.innerHTML = `
        <div class="ed-gutter"><div class="ed-gutter-inner"></div></div>
        <div class="ed-main">
          <div class="ed-layer"><div class="ed-curline"></div><pre class="ed-hl" aria-hidden="true"></pre></div>
          <textarea class="ed-input" wrap="off" spellcheck="false" autocapitalize="off" autocomplete="off"
                    autocorrect="off" data-gramm="false" aria-label="MIPS source code"></textarea>
          <div class="ed-complete" hidden></div>
        </div>`;
      this.ta = host.querySelector(".ed-input");
      this.hl = host.querySelector(".ed-hl");
      this.layer = host.querySelector(".ed-layer");
      this.cur = host.querySelector(".ed-curline");
      this.gutter = host.querySelector(".ed-gutter-inner");
      this.gutterBox = host.querySelector(".ed-gutter");
      this.pop = host.querySelector(".ed-complete");
      this.lines = [];
      this.lineEls = [];
      this.gutEls = [];
      this.marks = new Map();       // line(1-based) -> {kind, col, msg}
      this.bps = new Set();         // lines (1-based)
      this.exec = null;             // 1-based line being executed
      this.trail = new Map();       // line -> 1..5 (recently executed, fading)
      this.items = [];
      this.sel = 0;
      this.ta.addEventListener("input", () => { this.render(); this.updateCompletion(); this.opts.onChange && this.opts.onChange(); });
      this.ta.addEventListener("scroll", () => this.syncScroll());
      this.ta.addEventListener("keydown", (e) => this.onKey(e));
      this.ta.addEventListener("keyup", () => this.cursorMoved());
      this.ta.addEventListener("click", () => { this.cursorMoved(); this.hideCompletion(); });
      this.ta.addEventListener("blur", () => setTimeout(() => this.hideCompletion(), 150));
      document.addEventListener("selectionchange", () => { if (document.activeElement === this.ta) this.cursorMoved(); });
      this.gutterBox.addEventListener("click", (e) => {
        const el = e.target.closest(".g");
        if (el && this.opts.onToggleBreakpoint) this.opts.onToggleBreakpoint(+el.dataset.line);
      });
      this.pop.addEventListener("mousedown", (e) => {
        const it = e.target.closest(".ci");
        if (it) { e.preventDefault(); this.sel = +it.dataset.i; this.acceptCompletion(); }
      });
      new ResizeObserver(() => this.measure()).observe(host);
      this.measure();
    }

    measure() {
      const cs = getComputedStyle(this.ta);
      this.lh = parseFloat(cs.lineHeight) || 20;
      const probe = document.createElement("span");
      probe.textContent = "0000000000";
      probe.style.cssText = `font:${cs.font};position:absolute;visibility:hidden;white-space:pre`;
      document.body.appendChild(probe);
      this.cw = probe.getBoundingClientRect().width / 10 || 8;
      probe.remove();
      this.padTop = parseFloat(cs.paddingTop) || 0;
      this.padLeft = parseFloat(cs.paddingLeft) || 0;
      this.cursorMoved();
    }

    // ------------------------------------------------------------ content
    get value() { return this.ta.value; }
    set value(v) {
      this.ta.value = v;
      this.render();
      this.ta.scrollTop = 0;
      this.ta.scrollLeft = 0;
      this.syncScroll();
    }
    focus() { this.ta.focus({ preventScroll: true }); }

    setMarks(marks) { this.marks = marks || new Map(); this.render(true); }
    setBreakpoints(lines) { this.bps = new Set(lines); this.renderGutter(true); }
    setExecLine(line) {
      if (line === this.exec) return;
      const old = this.exec;
      this.exec = line;
      [old, line].forEach(l => { if (l) this.renderLine(l - 1, true); });
      this.renderGutter(true);
      if (line) this.revealLine(line);
    }

    setTrail(map) {
      const old = this.trail;
      this.trail = map || new Map();
      const lines = new Set([...old.keys(), ...this.trail.keys()]);
      for (const l of lines) this.renderLine(l - 1, true);
    }

    render(force = false) {
      const text = this.ta.value;
      const lines = text.split("\n");
      const n = lines.length;
      for (let i = 0; i < n; i++) {
        if (force || lines[i] !== this.lines[i] || !this.lineEls[i]) {
          this.lines[i] = lines[i];
          this.renderLine(i, false);
        }
      }
      for (let i = this.lineEls.length - 1; i >= n; i--) { this.lineEls[i].remove(); this.lineEls.pop(); }
      this.lines.length = n;
      this.renderGutter(force);
      this.cursorMoved();
    }

    renderLine(i, refreshText) {
      if (i < 0 || i >= this.lines.length) return;
      let el = this.lineEls[i];
      if (!el) {
        el = document.createElement("div");
        el.className = "l";
        this.hl.appendChild(el);
        this.lineEls[i] = el;
      }
      const line = this.lines[i];
      const mark = this.marks.get(i + 1);
      let html = line.length ? highlight(line) : "";
      if (mark && mark.kind === "error" && mark.col > 0 && line.length) {
        // underline the offending token
        const s = mark.col - 1;
        let e = s;
        while (e < line.length && !/[\s,()]/.test(line[e])) e++;
        if (e === s) e = Math.min(line.length, s + 1);
        html = highlight(line.slice(0, s)) + `<span class="errtok">${highlight(line.slice(s, e))}</span>` + highlight(line.slice(e));
      }
      el.innerHTML = html || "&#8203;";
      const tr = this.exec !== i + 1 ? this.trail.get(i + 1) : 0;
      el.className = "l" + (mark ? (mark.kind === "error" ? " err" : " warn") : "") + (this.exec === i + 1 ? " exec" : "") + (tr ? " trail" + tr : "");
      if (mark) el.title = mark.msg; else el.removeAttribute("title");
    }

    renderGutter() {
      const n = this.lines.length;
      const digits = Math.max(2, String(n).length);
      this.gutterBox.style.width = `calc(${digits}ch + 2.1em)`;
      for (let i = 0; i < n; i++) {
        let g = this.gutEls[i];
        if (!g) {
          g = document.createElement("div");
          g.className = "g";
          g.dataset.line = i + 1;
          this.gutter.appendChild(g);
          this.gutEls[i] = g;
        }
        const ln = i + 1;
        const mark = this.marks.get(ln);
        const cls = "g" + (this.bps.has(ln) ? " bp" : "") + (this.exec === ln ? " exec" : "") +
          (mark ? (mark.kind === "error" ? " err" : " warn") : "");
        if (g.className !== cls) g.className = cls;
        if (g.dataset.n !== String(ln)) { g.dataset.n = ln; g.textContent = ln; }
      }
      for (let i = this.gutEls.length - 1; i >= n; i--) { this.gutEls[i].remove(); this.gutEls.pop(); }
    }

    syncScroll() {
      const x = this.ta.scrollLeft, y = this.ta.scrollTop;
      this.layer.style.transform = `translate(${-x}px, ${-y}px)`;
      this.gutter.style.transform = `translateY(${-y}px)`;
      this.hideCompletion();
    }

    // ------------------------------------------------------------ cursor
    get cursor() {
      const pos = this.ta.selectionStart;
      const before = this.ta.value.slice(0, pos);
      const line = before.split("\n").length;
      const col = pos - before.lastIndexOf("\n");
      return { line, col, pos };
    }

    cursorMoved() {
      if (!this.lh) return;
      const { line, col } = this.cursor;
      this.cur.style.transform = `translateY(${this.padTop + (line - 1) * this.lh}px)`;
      this.cur.style.height = this.lh + "px";
      if (this._lastCursor !== line + ":" + col) {
        this._lastCursor = line + ":" + col;
        this.opts.onCursor && this.opts.onCursor(line, col, this.lines[line - 1] || "");
      }
    }

    goTo(line, col = 1) {
      const lines = this.ta.value.split("\n");
      line = Math.max(1, Math.min(line, lines.length));
      let pos = 0;
      for (let i = 0; i < line - 1; i++) pos += lines[i].length + 1;
      pos += Math.min(Math.max(0, col - 1), lines[line - 1].length);
      this.ta.focus({ preventScroll: true });
      this.ta.setSelectionRange(pos, pos);
      this.revealLine(line, true);
      this.cursorMoved();
    }

    revealLine(line, center = false) {
      const top = (line - 1) * this.lh, h = this.ta.clientHeight;
      if (center || top < this.ta.scrollTop || top + this.lh > this.ta.scrollTop + h)
        this.ta.scrollTop = Math.max(0, top - h / 2);
    }

    // ------------------------------------------------------------ editing
    insert(text) {
      this.ta.focus({ preventScroll: true });
      if (!document.execCommand("insertText", false, text)) {
        this.ta.setRangeText(text, this.ta.selectionStart, this.ta.selectionEnd, "end");
        this.ta.dispatchEvent(new Event("input"));
      }
    }

    selectedLineRange() {
      const v = this.ta.value;
      const s = v.lastIndexOf("\n", this.ta.selectionStart - 1) + 1;
      let e = v.indexOf("\n", this.ta.selectionEnd === this.ta.selectionStart ? this.ta.selectionEnd : this.ta.selectionEnd - 1);
      if (e < 0) e = v.length;
      return [s, e];
    }

    transformLines(fn) {
      const [s, e] = this.selectedLineRange();
      const block = this.ta.value.slice(s, e);
      const out = block.split("\n").map(fn).join("\n");
      this.ta.setSelectionRange(s, e);
      this.insert(out);
      this.ta.setSelectionRange(s, s + out.length);
    }

    toggleComment() {
      const [s, e] = this.selectedLineRange();
      const lines = this.ta.value.slice(s, e).split("\n");
      const all = lines.filter(l => l.trim()).every(l => /^\s*#/.test(l));
      this.transformLines(l => all ? l.replace(/^(\s*)# ?/, "$1") : (l.trim() ? l.replace(/^(\s*)/, "$1# ") : l));
    }

    onKey(e) {
      const mod = e.ctrlKey || e.metaKey;
      if (!this.pop.hidden) {
        if (e.key === "ArrowDown") { e.preventDefault(); this.sel = (this.sel + 1) % this.items.length; this.drawCompletion(); return; }
        if (e.key === "ArrowUp") { e.preventDefault(); this.sel = (this.sel - 1 + this.items.length) % this.items.length; this.drawCompletion(); return; }
        if (e.key === "Tab" || e.key === "Enter") { e.preventDefault(); this.acceptCompletion(); return; }
        if (e.key === "Escape") { e.preventDefault(); this.hideCompletion(); return; }
      }
      if (e.key === "Tab" && !mod) {
        e.preventDefault();
        if (e.shiftKey) this.transformLines(l => l.replace(/^( {1,4}|\t)/, ""));
        else if (this.ta.selectionStart !== this.ta.selectionEnd && this.ta.value.slice(this.ta.selectionStart, this.ta.selectionEnd).includes("\n"))
          this.transformLines(l => "    " + l);
        else this.insert("    ");
        return;
      }
      if (e.key === "Enter" && !mod && !e.shiftKey && !e.altKey) {
        const v = this.ta.value, pos = this.ta.selectionStart;
        const ls = v.lastIndexOf("\n", pos - 1) + 1;
        const cur = v.slice(ls, pos);
        let indent = (cur.match(/^\s*/) || [""])[0];
        if (/^\s*[A-Za-z_][\w.$]*:\s*$/.test(cur)) indent = "        ";   // after "label:" indent the body
        e.preventDefault();
        this.insert("\n" + indent);
        return;
      }
      if (mod && e.key === "/") { e.preventDefault(); this.toggleComment(); return; }
      if (mod && (e.key === " " || e.code === "Space")) { e.preventDefault(); this.updateCompletion(true); return; }
    }

    // ------------------------------------------------------------ completion
    wordAtCursor() {
      const v = this.ta.value, pos = this.ta.selectionStart;
      if (pos !== this.ta.selectionEnd) return null;
      const ls = v.lastIndexOf("\n", pos - 1) + 1;
      const head = v.slice(ls, pos);
      if (head.includes("#")) return null;
      let body = head;
      while (/^\s*[A-Za-z_][\w.$]*\s*:/.test(body)) body = body.replace(/^\s*[A-Za-z_][\w.$]*\s*:/, "");
      const word = body.replace(/^\s+/, "");
      if (!word || /\s/.test(word)) return null;
      const nextCh = v[pos] || "";
      if (/[\w.]/.test(nextCh)) return null;
      return word;
    }

    updateCompletion(force = false) {
      if (this.opts.completion === false) return;
      const w = this.wordAtCursor();
      if (!w || (!force && w.length < 2 && !w.startsWith("."))) { this.hideCompletion(); return; }
      this.items = ISA.complete(w, 8);
      this.prefix = w;
      if (!this.items.length) { this.hideCompletion(); return; }
      this.sel = 0;
      this.drawCompletion();
    }

    drawCompletion() {
      const { line, col } = this.cursor;
      const gw = this.gutterBox.getBoundingClientRect().width;
      const x = gw + this.padLeft + (col - 1 - this.prefix.length) * this.cw - this.ta.scrollLeft;
      const y = this.padTop + line * this.lh - this.ta.scrollTop + 2;
      this.pop.innerHTML = this.items.map((it, i) =>
        `<div class="ci${i === this.sel ? " sel" : ""}" data-i="${i}"><span class="ci-f">${highlight(it.format)}</span>` +
        `<span class="ci-d">${it.pseudo ? '<span class="t-pseudo">pseudo · </span>' : ""}${esc(it.desc || "")}</span></div>`).join("");
      this.pop.hidden = false;
      const maxX = this.host.clientWidth - Math.min(this.pop.offsetWidth, this.host.clientWidth) - 4;
      this.pop.style.left = Math.max(4, Math.min(x - gw, maxX)) + "px";
      const below = y + this.pop.offsetHeight < this.host.clientHeight;
      this.pop.style.top = (below ? y : Math.max(0, y - this.lh - this.pop.offsetHeight - 4)) + "px";
      const el = this.pop.children[this.sel];
      if (el) el.scrollIntoView({ block: "nearest" });
    }

    acceptCompletion() {
      const it = this.items[this.sel];
      if (it) {
        const rest = it.name.slice(this.prefix.length);
        this.insert(rest + (it.name.startsWith(".") ? " " : " "));
      }
      this.hideCompletion();
    }

    hideCompletion() { this.pop.hidden = true; }
  }

  global.CodeEditor = CodeEditor;
})(window);
