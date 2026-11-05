/* Semantic hints for register / memory values: what a value *means* right now. */
(function (global) {
  "use strict";
  const M = global.MIPS;
  const esc = M.esc;

  const ROLE = {
    0: "constant zero — writes are ignored",
    1: "assembler temporary — used by pseudo-instructions, avoid it",
    2: "return value · syscall service number", 3: "second return value",
    4: "argument 1", 5: "argument 2", 6: "argument 3", 7: "argument 4",
    26: "reserved for the OS kernel", 27: "reserved for the OS kernel",
    28: "global pointer — base for small globals (±32 KB)",
    29: "stack pointer — top of the stack (grows down)",
    30: "frame pointer — base of the current stack frame",
    31: "return address — set by jal/jalr, used by jr $ra",
  };
  for (const i of [8, 9, 10, 11, 12, 13, 14, 15, 24, 25]) ROLE[i] = "temporary — not preserved across calls (caller-saved)";
  for (let i = 16; i <= 23; i++) ROLE[i] = "saved — functions must preserve it (callee-saved)";

  const SYS = new Map(M.SYSCALLS.map(([n, name, args, res]) => [n, { name, args, res }]));
  const STACK_TOP = 0x7fffeffc;

  /** Which syscall argument description mentions this register, for the service in $v0. */
  function syscallArg(reg, v0) {
    const s = SYS.get(v0);
    if (!s || !s.args) return null;
    for (const part of s.args.split(/,\s*(?=\$)/)) {
      const m = part.match(/^(\$\w+)\s*=\s*(.+)$/);
      if (m && m[1] === reg) return `${m[2]} <span class="dim">for syscall ${v0} (${esc(s.name)})</span>`;
    }
    return null;
  }

  function region(a, ctx) {
    a = a >>> 0;
    const sg = ctx.segments || {};
    const sp = ctx.state ? ctx.state.gpr[29] >>> 0 : STACK_TOP;
    if (a >= 0xffff0000) return "memory-mapped I/O";
    if (a >= 0x90000000) return "kernel data";
    if (a >= 0x80000000) return "kernel text";
    if (a >= 0x7f000000 && a <= 0x7fffffff) return a >= sp ? "stack (in use)" : "stack (below $sp)";
    const heap = (sg.heap != null ? sg.heap : 0x10040000) >>> 0;
    const data = (sg.data != null ? sg.data : 0x10010000) >>> 0;
    const ext = (sg.extern != null ? sg.extern : 0x10000000) >>> 0;
    const text = (sg.text != null ? sg.text : 0x00400000) >>> 0;
    if (a >= heap && a < 0x10400000) return "heap";
    if (a >= data && a < heap) return ".data";
    if (a >= ext && a < data) return ".extern / $gp area";
    if (a >= text && a < 0x10000000) return ".text (code)";
    return null;
  }

  function labelFor(a, ctx) {
    a = a >>> 0;
    let best = null;
    for (const l of ctx.labels || []) {
      const la = l.addr >>> 0;
      if (la <= a && a - la < 4096 && (!best || la > (best.addr >>> 0))) best = l;
    }
    if (!best) return null;
    const off = a - (best.addr >>> 0);
    return `<span class="t-label">${esc(best.name)}</span>${off ? `<span class="dim">+${off}</span>` : ""}`;
  }

  function instrAt(a, ctx) {
    const i = ctx.addrIdx && ctx.addrIdx.get(a | 0);
    if (i === undefined) return null;
    const r = ctx.rows[i];
    return `${M.highlight(r.basic)}${r.line ? ` <span class="dim">· ${esc(r.file)}:${r.line}</span> ${M.highlight(r.source.trim())}` : ""}`;
  }

  async function cString(a, ctx) {
    try {
      const res = await ctx.engine.call("memory", { addr: (a & ~3) | 0, words: 20 }, 4000);
      const bytes = [];
      for (const w of res.words) for (let b = 0; b < 4; b++) bytes.push((w >>> (8 * b)) & 255);
      let s = "", ok = true;
      for (let i = a & 3; i < bytes.length; i++) {
        const c = bytes[i];
        if (c === 0) break;
        if (c === 10) { s += "\\n"; continue; }
        if (c === 9) { s += "\\t"; continue; }
        if (c < 32 || c > 126) { ok = false; break; }
        s += String.fromCharCode(c);
      }
      if (!ok || s.length < 1) return null;
      return `<span class="t-string">"${esc(s.length > 60 ? s.slice(0, 60) + "…" : s)}"</span>`;
    } catch (e) { return null; }
  }

  /** Lines that describe what `v` means as a pointer / plain number. */
  async function valueMeaning(v, ctx, out) {
    const u = v >>> 0;
    const reg = u > 0x1000 ? region(u, ctx) : null;
    if (reg) {
      const lab = labelFor(u, ctx);
      out.push(["points to", `${reg}${lab ? " · " + lab : ""}`]);
      if (reg.startsWith(".text") || reg === "kernel text") {
        const ins = instrAt(u, ctx);
        if (ins) out.push(["code", ins]);
      } else if (reg !== "memory-mapped I/O") {
        const str = await cString(u, ctx);
        if (str) out.push(["string", str]);
      }
    } else if (u >= 32 && u < 127) {
      out.push(["char", `<span class="t-string">'${esc(String.fromCharCode(u))}'</span>`]);
    }
  }

  /** Meaning of a general-purpose register (index n) — async because it may read memory. */
  async function gprMeaning(n, ctx) {
    const st = ctx.state;
    const v = st.gpr[n] | 0;
    const out = [["role", esc(ROLE[n] || "")]];
    const pcIdx = ctx.addrIdx ? ctx.addrIdx.get(st.pc) : undefined;
    const nextIsSyscall = pcIdx !== undefined && /^syscall/.test(ctx.rows[pcIdx].basic);
    const v0 = st.gpr[2] | 0;
    if (n === 2) {
      const s = SYS.get(v);
      if (s) out.push(["syscall", `<span class="t-number">${v}</span> = <b>${esc(s.name)}</b>${s.res ? ` → ${M.highlight(s.res)}` : ""}${nextIsSyscall ? ` <span class="pill-mini">next instruction</span>` : ""}`]);
      else if (nextIsSyscall) out.push(["syscall", `<span style="color:var(--error)">${v} is not a valid service number</span>`]);
    }
    if (n >= 4 && n <= 7) {
      const a = syscallArg(M.REG_NAMES[n], v0);
      if (a && (nextIsSyscall || SYS.has(v0))) out.push(["as argument", a]);
    }
    if (n === 31) {
      const ins = instrAt(v, ctx);
      const lab = labelFor(v, ctx);
      if (ins || lab) out.push(["returns to", `${lab || M.hex(v)}${ins ? " · " + ins : ""}`]);
      return out;
    }
    if (n === 29 || n === 30) {
      const depth = STACK_TOP - (v >>> 0);
      if (depth >= 0 && depth < 0x1000000) out.push(["stack", depth ? `${depth} bytes (${Math.floor(depth / 4)} words) in use below the initial $sp` : "empty (initial value)"]);
      return out;
    }
    if (n === 28) { out.push(["globals", `${M.hex(v)} ± 32 KB is reachable with one lw/sw`]); return out; }
    if (n !== 0) await valueMeaning(v, ctx, out);
    return out;
  }

  function specialMeaning(k, ctx) {
    const st = ctx.state, out = [];
    if (k === "pc") {
      out.push(["role", "program counter — address of the next instruction"]);
      const ins = instrAt(st.pc, ctx);
      if (ins) out.push(["next", ins]);
    } else {
      out.push(["role", k === "hi" ? "upper half of mult / remainder of div" : "lower half of mult / quotient of div"]);
      const hi = BigInt.asIntN(32, BigInt(st.hi | 0)), lo = BigInt(st.lo >>> 0);
      const prod = (hi << 32n) | lo;
      out.push(["after mult", `hi:lo = <span class="t-number">${prod}</span>`]);
      out.push(["after div", `quotient (lo) <span class="t-number">${st.lo | 0}</span>, remainder (hi) <span class="t-number">${st.hi | 0}</span>`]);
    }
    return out;
  }

  const EXC = { 0: "interrupt", 4: "address error on load / instruction fetch", 5: "address error on store", 6: "bus error (fetch)", 7: "bus error (load/store)",
    8: "syscall", 9: "breakpoint", 10: "reserved instruction", 11: "coprocessor unusable", 12: "arithmetic overflow", 13: "trap", 15: "floating point" };
  function cop0Meaning(num, v, ctx) {
    const out = [];
    if (num === 13) {
      const code = (v >> 2) & 31;
      out.push(["role", "Cause — why the last exception happened"]);
      out.push(["exception", `code <span class="t-number">${code}</span> — ${esc(EXC[code] || "unknown")}`]);
      const pend = (v >> 8) & 0xff;
      if (pend) out.push(["pending", `interrupt bits ${pend.toString(2).padStart(8, "0")}`]);
      if (v & 0x80000000) out.push(["delay slot", "exception in a branch delay slot"]);
    } else if (num === 12) {
      out.push(["role", "Status — interrupt mask and mode"]);
      out.push(["bits", `IE (interrupts) ${v & 1 ? "on" : "off"} · EXL (in handler) ${v & 2 ? "yes" : "no"} · mask ${((v >> 8) & 0xff).toString(2).padStart(8, "0")}`]);
    } else if (num === 14) {
      out.push(["role", "EPC — address of the instruction that caused the exception"]);
      const ins = instrAt(v, ctx);
      if (ins) out.push(["instruction", ins]);
    } else if (num === 8) {
      out.push(["role", "BadVAddr — address that caused an address error"]);
      const r = region(v, ctx);
      if (r) out.push(["region", r]);
    }
    return out;
  }

  function fprMeaning(n, ctx) {
    const out = [];
    const v0 = ctx.state.gpr[2] | 0;
    if (n === 0) out.push(["role", "result of float/double read syscalls (6, 7) and random 43/44"]);
    if (n === 12) {
      out.push(["role", "argument for print float / print double (syscalls 2, 3)"]);
      const a = syscallArg("$f12", v0);
      if (a) out.push(["as argument", a]);
    }
    if (n % 2 === 0) out.push(["pair", `$f${n}:$f${n + 1} hold one double`]);
    return out;
  }

  async function memMeaning(addr, v, ctx) {
    const out = [];
    const r = region(addr, ctx), lab = labelFor(addr, ctx);
    out.push(["location", `${r || "memory"}${lab ? " · " + lab : ""}`]);
    if (r && r.startsWith(".text")) { const ins = instrAt(addr, ctx); if (ins) out.push(["instruction", ins]); return out; }
    await valueMeaning(v, ctx, out);
    return out;
  }

  global.MipsMeaning = { gprMeaning, specialMeaning, cop0Meaning, fprMeaning, memMeaning, ROLE };
})(window);
