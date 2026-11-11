/* MIPS language support shared by the web UI: lexer, ISA tables, formatting, themes. */
(function (global) {
  "use strict";

  const REG_NAMES = ["$zero", "$at", "$v0", "$v1", "$a0", "$a1", "$a2", "$a3",
    "$t0", "$t1", "$t2", "$t3", "$t4", "$t5", "$t6", "$t7",
    "$s0", "$s1", "$s2", "$s3", "$s4", "$s5", "$s6", "$s7",
    "$t8", "$t9", "$k0", "$k1", "$gp", "$sp", "$fp", "$ra"];
  const REG_SET = new Set(REG_NAMES.map(r => r.slice(1)));

  const ISA = {
    instructions: new Map(),   // name -> [{format, desc, pseudo}]
    directives: new Map([".data", ".text", ".word", ".ascii", ".asciiz", ".byte", ".align", ".half", ".space",
      ".double", ".float", ".extern", ".kdata", ".ktext", ".globl", ".set", ".eqv", ".macro", ".end_macro", ".include"].map(d => [d, ""])),
    names: [],
    load(data) {
      this.instructions.clear();
      for (const it of data.instructions || []) {
        if (!this.instructions.has(it.name)) this.instructions.set(it.name, []);
        this.instructions.get(it.name).push({ format: it.format, desc: it.desc, pseudo: !!it.pseudo });
      }
      if (data.directives && data.directives.length) this.directives = new Map(data.directives.map(d => [d.name, d.desc]));
      this.names = [...this.instructions.keys()].sort();
    },
    kind(word) {
      const f = this.instructions.get(word.toLowerCase());
      if (!f) return null;
      return f.some(x => !x.pseudo) ? "instr" : "pseudo";
    },
    complete(prefix, limit = 8) {
      const p = prefix.toLowerCase();
      const out = [];
      if (p.startsWith(".")) {
        for (const [d, desc] of this.directives) if (d.startsWith(p) && d !== p) out.push({ name: d, format: d, desc });
        return out.slice(0, limit);
      }
      for (const n of this.names) {
        if (n.startsWith(p) && n !== p) {
          const f = this.instructions.get(n)[0];
          out.push({ name: n, format: f.format, desc: f.desc, pseudo: f.pseudo });
          if (out.length >= limit) break;
        }
      }
      return out;
    },
  };

  const TOKEN = /(#.*$)|("(?:\\.|[^"\\])*"?)|('(?:\\.|[^'\\])'?)|(\$(?:f[0-9]{1,2}|[a-z]+[0-9]?|[0-9]{1,2})\b)|(%[A-Za-z_]\w*)|(\.[A-Za-z_]\w*)|([-+]?(?:0[xX][0-9a-fA-F]+|\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\b)|([A-Za-z_][\w.$]*)|(:)|([(),+\-])|(\s+)|(.)/g;
  const GROUPS = [null, "comment", "string", "string", "register", "macroarg", "directive", "number", "ident", "colon", "punct", "ws", "other"];

  /** Tokenize one line → [{s, e, k}] where k is a token class. */
  function lex(line) {
    const raw = [];
    TOKEN.lastIndex = 0;
    let m;
    while ((m = TOKEN.exec(line)) !== null) {
      let g = 1;
      while (m[g] === undefined) g++;
      raw.push([GROUPS[g], m.index, m.index + m[0].length, m[0]]);
      if (m[0].length === 0) TOKEN.lastIndex++;
    }
    const out = [];
    let expectOp = true;
    for (let i = 0; i < raw.length; i++) {
      const [kind, s, e, text] = raw[i];
      if (kind === "ws") continue;
      if (kind === "ident") {
        let j = i + 1;
        while (j < raw.length && raw[j][0] === "ws") j++;
        if (j < raw.length && raw[j][0] === "colon" && expectOp) {
          out.push({ s, e, k: "label" });
          out.push({ s: raw[j][1], e: raw[j][2], k: "punct" });
          i = j;
          continue;
        }
        if (expectOp) {
          const k = ISA.kind(text);
          out.push({ s, e, k: k || "macro" });
          expectOp = false;
        } else out.push({ s, e, k: "symbol" });
      } else if (kind === "register") {
        const n = text.slice(1);
        if (/^f\d{1,2}$/.test(n) && +n.slice(1) < 32) out.push({ s, e, k: "fpreg" });
        else if (REG_SET.has(n) || (/^\d{1,2}$/.test(n) && +n < 32)) out.push({ s, e, k: "register" });
        else out.push({ s, e, k: "invalid" });
        expectOp = false;
      } else if (kind === "directive") {
        out.push({ s, e, k: ISA.directives.has(text.toLowerCase()) ? "directive" : "invalid" });
        expectOp = false;
      } else if (kind === "string" || kind === "number" || kind === "macroarg") {
        out.push({ s, e, k: kind });
        expectOp = false;
      } else if (kind === "comment") {
        out.push({ s, e, k: "comment" });
      } else if (kind === "punct" || kind === "colon") {
        out.push({ s, e, k: "punct" });
      } else expectOp = false;
    }
    return out;
  }

  const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  const esc = s => s.replace(/[&<>"]/g, c => ESC[c]);

  /** Highlight a line to HTML. */
  function highlight(line) {
    let html = "", pos = 0;
    for (const t of lex(line)) {
      if (t.s > pos) html += esc(line.slice(pos, t.s));
      html += `<span class="t-${t.k}">${esc(line.slice(t.s, t.e))}</span>`;
      pos = t.e;
    }
    if (pos < line.length) html += esc(line.slice(pos));
    return html;
  }

  /** The mnemonic or directive on a line (for the hint bar). */
  function mnemonicOf(line) {
    for (const t of lex(line)) {
      const txt = line.slice(t.s, t.e).toLowerCase();
      if (t.k === "instr" || t.k === "pseudo") return { type: "instr", name: txt };
      if (t.k === "directive") return { type: "dir", name: txt };
      if (t.k === "macro") return null;
    }
    return null;
  }

  const SYSCALLS = [
    [1, "print integer", "$a0 = integer", ""], [2, "print float", "$f12 = float", ""],
    [3, "print double", "$f12 = double", ""], [4, "print string", "$a0 = address of null-terminated string", ""],
    [5, "read integer", "", "$v0 = integer read"], [6, "read float", "", "$f0 = float read"],
    [7, "read double", "", "$f0 = double read"], [8, "read string", "$a0 = buffer, $a1 = max chars", "buffer filled"],
    [9, "sbrk (allocate heap)", "$a0 = bytes", "$v0 = address"], [10, "exit", "", ""],
    [11, "print character", "$a0 = character", ""], [12, "read character", "", "$v0 = character"],
    [13, "open file", "$a0 = filename, $a1 = flags, $a2 = mode", "$v0 = descriptor"],
    [14, "read from file", "$a0 = fd, $a1 = buffer, $a2 = max", "$v0 = chars read"],
    [15, "write to file", "$a0 = fd, $a1 = buffer, $a2 = count", "$v0 = chars written"],
    [16, "close file", "$a0 = descriptor", ""], [17, "exit2 (with value)", "$a0 = result", ""],
    [30, "system time", "", "$a0 = low, $a1 = high 32 bits (ms)"],
    [31, "MIDI out", "$a0 = pitch, $a1 = ms, $a2 = instrument, $a3 = volume", "plays a tone"],
    [32, "sleep", "$a0 = ms", ""], [33, "MIDI out synchronous", "$a0 = pitch, $a1 = ms, $a2 = instrument, $a3 = volume", "plays, then waits"],
    [34, "print int hex", "$a0 = integer", ""], [35, "print int binary", "$a0 = integer", ""],
    [36, "print int unsigned", "$a0 = integer", ""], [40, "set seed", "$a0 = id, $a1 = seed", ""],
    [41, "random int", "$a0 = id", "$a0 = value"], [42, "random int range", "$a0 = id, $a1 = upper bound", "$a0 = value"],
    [43, "random float", "$a0 = id", "$f0 = value"], [44, "random double", "$a0 = id", "$f0 = value"],
    [50, "ConfirmDialog", "$a0 = message", "$a0 = 0 yes / 1 no / 2 cancel"],
    [51, "InputDialogInt", "$a0 = message", "$a0 = int, $a1 = status"],
    [52, "InputDialogFloat", "$a0 = message", "$f0 = float, $a1 = status"],
    [53, "InputDialogDouble", "$a0 = message", "$f0 = double, $a1 = status"],
    [54, "InputDialogString", "$a0 = message, $a1 = buffer, $a2 = max", "$a1 = status"],
    [55, "MessageDialog", "$a0 = message, $a1 = type", ""], [56, "MessageDialogInt", "$a0 = message, $a1 = int", ""],
    [57, "MessageDialogFloat", "$a0 = message, $f12 = float", ""], [58, "MessageDialogDouble", "$a0 = message, $f12 = double", ""],
    [59, "MessageDialogString", "$a0 = message, $a1 = string", ""],
  ];

  // ---------------------------------------------------------------- numbers
  const u32 = v => v >>> 0;
  const s32 = v => v | 0;
  const hex = v => "0x" + u32(v).toString(16).padStart(8, "0");
  const f32buf = new DataView(new ArrayBuffer(8));
  function asFloat(v) { f32buf.setUint32(0, u32(v)); return f32buf.getFloat32(0); }
  function asDouble(lo, hi) { f32buf.setUint32(0, u32(hi)); f32buf.setUint32(4, u32(lo)); return f32buf.getFloat64(0); }
  function fmtFloat(x) {
    if (Number.isNaN(x)) return "NaN";
    if (!Number.isFinite(x)) return x > 0 ? "∞" : "-∞";
    return String(Number(x.toPrecision(8)));
  }
  function ascii(v) {
    let s = "";
    for (let i = 0; i < 4; i++) {
      const c = (u32(v) >>> (8 * i)) & 255;
      s += c === 0 ? "\\0" : c === 10 ? "\\n" : c === 9 ? "\\t" : c >= 32 && c < 127 ? String.fromCharCode(c) : ".";
    }
    return s;
  }
  function fmtWord(v, radix) {
    if (radix === "hex") return hex(v);
    if (radix === "ascii") return ascii(v);
    return String(s32(v));
  }
  function parseNum(text) {
    let t = String(text).trim().replace(/_/g, "");
    if (!t) throw new Error("empty value");
    if (/^'.'$/.test(t)) return t.charCodeAt(1);
    let neg = false;
    if (t[0] === "-") { neg = true; t = t.slice(1); }
    let v;
    if (/^0x[0-9a-f]+$/i.test(t)) v = parseInt(t.slice(2), 16);
    else if (/^0b[01]+$/i.test(t)) v = parseInt(t.slice(2), 2);
    else if (/^\d+$/.test(t)) v = parseInt(t, 10);
    else throw new Error("not a number: " + text);
    return s32(neg ? -v : v);
  }

  // ---------------------------------------------------------------- themes
  // ui: bg surface panel raised text muted primary accent success warning error
  // syn: instr pseudo directive register fpreg label symbol number string comment punct macro invalid errbg warnbg pcbg
  const THEMES = {
    "amoled": { dark: true, name: "AMOLED Black",
      ui: ["#000000", "#000000", "#0a0a0a", "#141414", "#e8e8e8", "#7d8590", "#3d8bff", "#ffb02e", "#2ee67a", "#ffd24d", "#ff3b5c"],
      syn: ["#5fb3ff", "#5ee8c0", "#d68bff", "#ff5c8a", "#ff8fb0", "#ffd24d", "#4dffc3", "#ff9b4d", "#a8ff60", "#5c6370", "#9aa5b1", "#e6e6e6", "#ff3b5c", "#2a0010", "#241c00", "#002a12"] },
    "midnight": { dark: true, name: "Midnight",
      ui: ["#0d1220", "#111827", "#161f33", "#1d2840", "#d7def0", "#8592b0", "#5b8cff", "#ffb454", "#57d9a3", "#ffcc66", "#ff5f6d"],
      syn: ["#7aa2f7", "#2ac3de", "#bb9af7", "#f7768e", "#ff9e9e", "#e0af68", "#73daca", "#ff9e64", "#9ece6a", "#5f6b8a", "#89ddff", "#c0caf5", "#ff5370", "#3d1f2a", "#3a3320", "#1f3a2c"] },
    "tokyo-night": { dark: true, name: "Tokyo Night",
      ui: ["#1a1b26", "#1f2030", "#24283b", "#2c3149", "#c0caf5", "#787c99", "#7aa2f7", "#ff9e64", "#9ece6a", "#e0af68", "#f7768e"],
      syn: ["#7aa2f7", "#2ac3de", "#bb9af7", "#f7768e", "#ff9e9e", "#e0af68", "#73daca", "#ff9e64", "#9ece6a", "#565f89", "#89ddff", "#c0caf5", "#ff5370", "#3d1f2a", "#3a3320", "#1f3a2c"] },
    "dracula": { dark: true, name: "Dracula",
      ui: ["#282a36", "#2b2d3a", "#313443", "#3a3d4f", "#f8f8f2", "#8b8fa8", "#bd93f9", "#ffb86c", "#50fa7b", "#f1fa8c", "#ff5555"],
      syn: ["#ff79c6", "#8be9fd", "#bd93f9", "#ffb86c", "#ffca8c", "#50fa7b", "#8be9fd", "#bd93f9", "#f1fa8c", "#6272a4", "#f8f8f2", "#f8f8f2", "#ff5555", "#4a2433", "#45422a", "#25432f"] },
    "nord": { dark: true, name: "Nord",
      ui: ["#2e3440", "#323946", "#3b4252", "#434c5e", "#eceff4", "#8f9bb3", "#88c0d0", "#ebcb8b", "#a3be8c", "#ebcb8b", "#bf616a"],
      syn: ["#81a1c1", "#5fb8a8", "#b48ead", "#d08770", "#e0a080", "#ebcb8b", "#8fbcbb", "#b48ead", "#a3be8c", "#616e88", "#eceff4", "#d8dee9", "#bf616a", "#43303a", "#45413a", "#2f4436"] },
    "gruvbox": { dark: true, name: "Gruvbox",
      ui: ["#282828", "#2c2c2c", "#32302f", "#3c3836", "#ebdbb2", "#a89984", "#83a598", "#fe8019", "#b8bb26", "#fabd2f", "#fb4934"],
      syn: ["#fb4934", "#fe8019", "#d3869b", "#83a598", "#8ec07c", "#fabd2f", "#8ec07c", "#d3869b", "#b8bb26", "#928374", "#ebdbb2", "#ebdbb2", "#fb4934", "#4a2622", "#4a4022", "#32402a"] },
    "catppuccin": { dark: true, name: "Catppuccin Mocha",
      ui: ["#1e1e2e", "#212131", "#262637", "#313244", "#cdd6f4", "#9399b2", "#89b4fa", "#fab387", "#a6e3a1", "#f9e2af", "#f38ba8"],
      syn: ["#89b4fa", "#94e2c5", "#cba6f7", "#f38ba8", "#eba0ac", "#f9e2af", "#94e2d5", "#fab387", "#a6e3a1", "#7f849c", "#89dceb", "#cdd6f4", "#f38ba8", "#45273a", "#45402f", "#27402f"] },
    "light": { dark: false, name: "Paper Light",
      ui: ["#f6f7f9", "#ffffff", "#eef0f4", "#e3e6ec", "#1f2328", "#667085", "#2563eb", "#c2410c", "#15803d", "#a16207", "#dc2626"],
      syn: ["#1d4ed8", "#0e7490", "#7e22ce", "#c2410c", "#be123c", "#a16207", "#0f766e", "#b45309", "#15803d", "#7c8593", "#475569", "#334155", "#dc2626", "#fde2e2", "#fdf3d0", "#dcfce7"] },
    "mars-classic": { dark: false, name: "MARS Classic",
      ui: ["#e9ecf1", "#ffffff", "#dde2ea", "#cfd6e2", "#111111", "#5b6575", "#2f5fbf", "#c05a00", "#2e7d32", "#b07800", "#c62828"],
      syn: ["#0000ff", "#007a7a", "#ff00ff", "#ff0000", "#c00040", "#000000", "#004080", "#000000", "#008000", "#008000", "#000000", "#202020", "#ff0000", "#ffd0d0", "#fff0c0", "#ffff99"] },
  };
  const UI_VARS = ["bg", "surface", "panel", "raised", "text", "muted", "primary", "accent", "success", "warning", "error"];
  const SYN_VARS = ["instr", "pseudo", "directive", "register", "fpreg", "label", "symbol", "number", "string", "comment", "punct", "macro", "invalid", "errbg", "warnbg", "pcbg"];

  function applyTheme(name, syntaxName) {
    const t = THEMES[name] || THEMES["amoled"];
    const s = THEMES[syntaxName] || t;
    const root = document.documentElement;
    UI_VARS.forEach((v, i) => root.style.setProperty(`--${v}`, t.ui[i]));
    SYN_VARS.forEach((v, i) => root.style.setProperty(`--s-${v}`, s.syn[i]));
    root.dataset.dark = t.dark ? "1" : "0";
    root.style.colorScheme = t.dark ? "dark" : "light";
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", t.ui[2]);
  }

  global.MIPS = { REG_NAMES, ISA, lex, highlight, esc, mnemonicOf, SYSCALLS, u32, s32, hex, asFloat, asDouble, fmtFloat, fmtWord, parseNum, THEMES, applyTheme };
})(window);
