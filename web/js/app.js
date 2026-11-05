/* MARS IDE — web/Android front end. */
(function () {
  "use strict";
  const M = window.MIPS;
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const esc = M.esc;

  // ------------------------------------------------------------------ icons
  const IC = {
    menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
    goback: '<path d="M15 18l-6-6 6-6"/>',
    upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>',
    download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/>',
    gear: '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>',
    build: '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18v3h3l6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4z"/>',
    run: '<path d="M7 4v16l13-8z" class="f"/>',
    pause: '<path d="M7 4h4v16H7zM14 4h4v16h-4z"/>',
    step: '<path d="M5 4v16l10-8zM17 4v16"/>',
    back: '<path d="M19 4v16L9 12zM7 4v16"/>',
    stop: '<rect x="5" y="5" width="14" height="14" rx="2"/>',
    reset: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5"/>',
    file: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/>',
    folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    newfile: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M12 12v6M9 15h6"/>',
    newdir: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM12 10v6M9 13h6"/>',
    refresh: '<path d="M21 12a9 9 0 1 1-3-6.7L21 8M21 3v5h-5"/>',
    x: '<path d="M6 6l12 12M18 6L6 18"/>',
    edit: '<path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
    exec: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
    regs: '<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M9 9h6v6H9zM9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3"/>',
    mem: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M3 15h18M9 4v16M15 4v16"/>',
    term: '<path d="M4 17l6-6-6-6M12 19h8"/>',
    more: '<circle cx="5" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="19" cy="12" r="1.5"/>',
    tag: '<path d="M20.6 13.4l-7.2 7.2a2 2 0 0 1-2.8 0L2 12V2h10l8.6 8.6a2 2 0 0 1 0 2.8zM7 7h.01"/>',
    tools: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    help: '<circle cx="12" cy="12" r="9"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01"/>',
    save: '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><path d="M17 21v-8H7v8M7 3v5h8"/>',
    trash: '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>',
    rename: '<path d="M4 20h4L18.5 9.5a2.8 2.8 0 0 0-4-4L4 16zM13.5 6.5l4 4"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
    zen: '<path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3M16 21h3a2 2 0 0 0 2-2v-3"/>',
    fs: '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
    fsexit: '<path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5"/>',
    panels: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 14h12M15 4v16"/>',
  };
  const icon = (n, cls = "") => `<svg class="i ${cls}" viewBox="0 0 24 24">${(IC[n] || "").replace('class="f"', 'fill="currentColor"')}</svg>`;

  // ------------------------------------------------------------------ state
  const LS = "marside.v1";
  const DEFAULTS = {
    theme: "amoled", syntax: "auto", fontSize: 14, speed: 0, regRadix: "hex", memRadix: "hex",
    pseudo: true, delayed_branching: false, self_modifying: false, warnings_are_errors: false, start_at_main: false,
    bare_machine: false, assemble_all: false, autosave: true, program_args: "", exception_handler: "", memory_config: "Default",
    bitmap: { uw: 8, uh: 8, w: 512, h: 256, base: "data" }, regsW: 330, consoleH: 32, side: false, panels: false, zen: false, hideZero: false, kbSize: "m", kbRows: 1, statusbar: true, lineNumbers: true, keybarOn: true,
    open: [], current: null, bps: {}, view: "edit", m: "edit",
  };
  const saved = (() => { try { return JSON.parse(localStorage.getItem(LS) || "{}"); } catch (e) { return {}; } })();
  const S = Object.assign(JSON.parse(JSON.stringify(DEFAULTS)), saved);
  S.bitmap = Object.assign({}, DEFAULTS.bitmap, saved.bitmap || {});
  const persist = () => {
    const keep = {};
    for (const k of Object.keys(DEFAULTS)) keep[k] = S[k];
    try { localStorage.setItem(LS, JSON.stringify(keep)); } catch (e) { }
  };

  const R = {                       // runtime state (not persisted)
    files: new Map(),               // path -> {text, saved, view: {top, sel}}
    tree: [], fs: false,
    program: null, rows: [], addrIdx: new Map(), lineAddr: new Map(),
    state: null, prev: null,
    assembled: false, running: false, finished: false, waiting: null, error: false,
    messages: [], marks: new Map(),  // path -> Map(line -> mark)
    memBase: null, memPrev: new Map(), configs: [],
    regTab: "gpr", ioTab: "run", toolTab: "bitmap", helpTab: "card",
    unread: new Set(), cursorRow: -1, dialog: null, version: "", busyStep: false,
  };
  const engine = new window.MarsEngineClient();
  const isNarrow = () => window.matchMedia("(max-width: 899px)").matches;
  const isTouch = () => window.matchMedia("(pointer: coarse)").matches || window.matchMedia("(any-pointer: coarse)").matches ||
    (navigator.maxTouchPoints || 0) > 0 || "ontouchstart" in window;
  /** Focus mode: while editing on a wide screen, the console and registers collapse. */
  function updateFocus() {
    const on = !isNarrow() && S.view === "edit" && !S.panels;
    const app = document.getElementById("app");
    if (app.classList.contains("focus") !== on) {
      app.classList.toggle("focus", on);
      setTimeout(() => { ed.measure(); renderRegs(); }, 0);
    }
    const b = document.getElementById("btn-panels");
    if (b) b.style.color = S.panels ? "var(--primary)" : "";
  }
  const fsSupported = () => !!(document.documentElement.requestFullscreen || document.documentElement.webkitRequestFullscreen);
  const isFs = () => !!(document.fullscreenElement || document.webkitFullscreenElement);
  function setFullscreen(on) {
    try {
      if (on && !isFs()) (document.documentElement.requestFullscreen || document.documentElement.webkitRequestFullscreen).call(document.documentElement)?.catch?.(() => { });
      else if (!on && isFs()) (document.exitFullscreen || document.webkitExitFullscreen).call(document)?.catch?.(() => { });
    } catch (e) { }
  }
  let zenFs = false;
  function setZen(v) {
    S.zen = v; persist(); applyTheme();
    if (v) { zenFs = !isFs(); if (zenFs) setFullscreen(true); toast("Zen mode — F10, Esc or ⤢ to exit", "", 1800); }
    else if (zenFs) { zenFs = false; setFullscreen(false); }
    setTimeout(() => ed.measure(), 150);
  }
  document.addEventListener("fullscreenchange", () => {
    const b = document.getElementById("btn-fs");
    if (b) b.innerHTML = icon(isFs() ? "fsexit" : "fs");
    if (!isFs() && S.zen && zenFs) { zenFs = false; setZen(false); }   // Esc left fullscreen → leave zen too
    setTimeout(() => ed.measure(), 150);
  });
  function showPanels(v = true) { if (S.panels !== v) { S.panels = v; persist(); updateFocus(); } }

  // ------------------------------------------------------------------ toasts / modals
  function toast(msg, kind = "", ms = 3200) {
    for (const t of $$("#toasts .toast")) if (t.textContent === msg) t.parentNode.removeChild(t);
    const el = document.createElement("div");
    el.className = "toast " + kind;
    el.textContent = msg;
    $("#toasts").appendChild(el);
    setTimeout(() => el.remove(), ms);
  }

  function modal({ title, body, buttons = [], sheet = false, onClose, wide = false }) {
    const bg = document.createElement("div");
    bg.className = "modal-bg" + (sheet ? " sheet" : "");
    bg.innerHTML = `<div class="modal" role="dialog" aria-modal="true" ${wide ? 'style="width:min(760px,100%)"' : ""}>
      ${title ? `<header><span class="grow">${title}</span><button class="icon-btn" data-close aria-label="Close">${icon("x")}</button></header>` : ""}
      <div class="body"></div><footer></footer></div>`;
    const b = $(".body", bg);
    if (typeof body === "string") b.innerHTML = body; else if (body) b.appendChild(body);
    const f = $("footer", bg);
    if (!buttons.length) f.remove();
    let closed = false;
    const close = (v, fromBack) => {
      if (closed) return; closed = true; bg.remove();
      if (!fromBack) overlayClosed(closer);
      onClose && onClose(fromBack ? null : v);
    };
    const closer = (fromBack) => close(null, fromBack);
    overlayOpened(closer);
    for (const btn of buttons) {
      const el = document.createElement("button");
      el.className = "btn" + (btn.primary ? " primary" : "");
      el.textContent = btn.label;
      el.onclick = () => close(btn.value !== undefined ? btn.value : (btn.get ? btn.get(bg) : undefined));
      f.appendChild(el);
    }
    bg.addEventListener("mousedown", (e) => { if (e.target === bg) close(null); });
    bg.addEventListener("keydown", (e) => {
      if (e.key === "Escape") { e.stopPropagation(); close(null); }
      if (e.key === "Enter" && e.target.tagName === "INPUT") {
        const p = buttons.find(x => x.primary);
        if (p) { e.preventDefault(); close(p.value !== undefined ? p.value : (p.get ? p.get(bg) : undefined)); }
      }
    });
    $$("[data-close]", bg).forEach(el => el.onclick = () => close(null));
    $("#modals").appendChild(bg);
    setTimeout(() => { const i = $("input,select,button.primary", bg); if (i) i.focus(); }, 30);
    return { el: bg, close };
  }

  function prompt(title, value = "", placeholder = "") {
    return new Promise(res => {
      modal({
        title, body: `<input class="text" value="${esc(value)}" placeholder="${esc(placeholder)}" autocapitalize="off" autocomplete="off" spellcheck="false">`,
        buttons: [{ label: "Cancel", value: null }, { label: "OK", primary: true, get: bg => $("input", bg).value }],
        onClose: res,
      });
      setTimeout(() => { const i = $(".modal input"); if (i) { i.focus(); i.select(); } }, 40);
    });
  }
  function confirmBox(title, text, ok = "OK") {
    return new Promise(res => modal({ title, body: `<div class="msgtext">${esc(text)}</div>`,
      buttons: [{ label: "Cancel", value: false }, { label: ok, primary: true, value: true }], onClose: v => res(!!v) }));
  }

  // ------------------------------------------------------------------ navigation history
  // Every jump records where you were; back/forward (Android gesture, browser, mouse, Alt+←/→, ‹ button)
  // returns there. Overlays (dialogs, inspector, sheets) are closed by back first.
  const NAV = { stack: [], cur: 0, restoring: false, lastPush: 0, ignorePop: 0, exitArmed: 0 };
  function navSnapshot() {
    return {
      view: S.view, m: S.m, file: S.current,
      sel: ed && ed.ta ? ed.ta.selectionStart : 0, top: ed && ed.ta ? ed.ta.scrollTop : 0,
      memStart: R.mem ? R.mem.start : null, memTarget: R.mem ? R.mem.target : null,
      help: R.helpTab, helpFilter: ($("#help-filter") || {}).value || "",
      execTop: ($("#exec-wrap") || {}).scrollTop || 0,
    };
  }
  const navKey = (l) => l ? [l.view, isNarrow() ? l.m : "", l.file, l.view === "mem" ? l.memTarget : "", l.view === "help" ? l.help + l.helpFilter : "",
    l.view === "edit" ? Math.floor((l.sel || 0) / 400) : ""].join("|") : "";
  /** Call at the start of any navigation: remembers the current place and opens a new history entry. */
  function navMark() {
    if (NAV.restoring || !NAV.ready) return;
    const now = Date.now();
    if (NAV.pendingBack) {
      // an overlay was just closed by a tap that also navigates: reuse its history entry instead of back+push
      clearTimeout(NAV.pendingBack); NAV.pendingBack = null;
      NAV.stack[NAV.cur] = NAV.beforeOverlay || navSnapshot();
      NAV.cur += 1; NAV.stack.length = NAV.cur; NAV.lastPush = now;
      history.replaceState({ mars: 1, navI: NAV.cur }, "");
      updateBackBtn();
      return;
    }
    NAV.stack[NAV.cur] = navSnapshot();
    if (now - NAV.lastPush < 250) return;          // one entry per gesture (jumps call several setters)
    NAV.lastPush = now;
    NAV.cur += 1;
    NAV.stack.length = NAV.cur;
    history.pushState({ mars: 1, navI: NAV.cur }, "");
    updateBackBtn();
  }
  async function navRestore(loc) {
    if (!loc) return;
    NAV.restoring = true;
    try {
      if (loc.file && loc.file !== S.current) {
        if (R.files.has(loc.file)) switchFile(loc.file); else await openFile(loc.file);
      }
      if (loc.view === "mem" && R.mem) { R.mem.start = loc.memStart; R.mem.target = loc.memTarget; R.mem.scrollPending = loc.memTarget != null; }
      if (loc.view === "help") { R.helpTab = loc.help; const f = $("#help-filter"); if (f) f.value = loc.helpFilter; renderSubTabs(); }
      if (isNarrow() && ["regs", "io", "files"].includes(loc.m)) { setView(loc.view); if (loc.m === "files") { S.m = "files"; $("#app").dataset.m = "files"; renderBottomNav(); } else setM(loc.m); }
      else setView(loc.view);
      if (loc.view === "edit" && loc.file === S.current) {
        ed.ta.setSelectionRange(loc.sel, loc.sel);
        ed.ta.scrollTop = loc.top; ed.syncScroll(); ed.cursorMoved();
      }
      if (loc.view === "exec") setTimeout(() => { $("#exec-wrap").scrollTop = loc.execTop; }, 0);
    } finally { NAV.restoring = false; updateBackBtn(); }
  }
  function updateBackBtn() {
    const b = document.getElementById("btn-back");
    if (b) b.classList.toggle("hidden", NAV.cur <= 0);
  }
  /** Overlays register themselves so that "back" closes them instead of navigating. */
  const OVERLAYS = [];
  function overlayOpened(close) {
    if (!OVERLAYS.length) NAV.beforeOverlay = navSnapshot();
    OVERLAYS.push(close);
    history.pushState({ mars: 1, navI: NAV.cur, overlay: true }, "");
  }
  function overlayClosed(close) {
    const i = OVERLAYS.lastIndexOf(close);
    if (i < 0) return;                       // already removed (closed by back)
    OVERLAYS.splice(i, 1);
    if (history.state && history.state.overlay) {
      clearTimeout(NAV.pendingBack);
      NAV.pendingBack = setTimeout(() => { NAV.pendingBack = null; NAV.ignorePop++; history.back(); }, 0);
    }
  }
  window.addEventListener("popstate", (e) => {
    if (NAV.ignorePop) { NAV.ignorePop--; return; }
    if (OVERLAYS.length) { const close = OVERLAYS.pop(); close(true); return; }
    const st = e.state || {};
    if (st.root) {                           // at the very start: don't leave the IDE by accident
      if (Date.now() - NAV.exitArmed < 2500) { history.back(); return; }
      NAV.exitArmed = Date.now();
      history.pushState({ mars: 1, navI: 0 }, "");
      toast("Press back again to leave the IDE", "", 2200);
      return;
    }
    if (typeof st.navI !== "number") return;
    if (st.navI === NAV.cur) return;
    NAV.stack[NAV.cur] = navSnapshot();      // so forward can come back here
    const target = NAV.stack[st.navI];
    NAV.cur = st.navI;
    if (target && navKey(target) === navKey(navSnapshot())) { updateBackBtn(); return; }
    navRestore(target);
  });

  // ------------------------------------------------------------------ chrome
  const VIEWS = [["edit", "Edit", "edit"], ["exec", "Execute", "exec"], ["mem", "Memory", "mem"],
    ["labels", "Labels", "tag"], ["tools", "Tools", "tools"], ["help", "Help", "help"]];
  const MNAV = [["edit", "Code", "edit"], ["exec", "Execute", "exec"], ["regs", "Registers", "regs"],
    ["mem", "Memory", "mem"], ["io", "Console", "term"], ["more", "More", "more"]];

  function renderChrome() {
    $("#btn-side").innerHTML = icon("menu");
    $("#btn-back").innerHTML = icon("goback");
    $("#btn-settings").innerHTML = icon("gear");
    $("#btn-panels").innerHTML = icon("panels");
    $("#btn-zen").innerHTML = icon("zen");
    $("#btn-fs").innerHTML = icon(isFs() ? "fsexit" : "fs");
    if (!fsSupported()) $("#btn-fs").style.display = "none";
    $("#btn-newfile").innerHTML = icon("newfile");
    $("#btn-newdir").innerHTML = icon("newdir");
    $("#btn-refresh").innerHTML = icon("refresh");
    $("#btn-import").innerHTML = icon("upload");
    $("#btn-export").innerHTML = icon("download");
    renderRunbar();
    renderTabs();
    renderBottomNav();
    renderSubTabs();
    renderKeybar();
  }

  function renderRunbar() {
    const st = R.state || {};
    const can = R.assembled && !R.running && !R.finished;
    const items = [
      ["assemble", "build", "Assemble", "F3", false, ""],
      R.running ? ["pause", "pause", "Pause", "F9", false, "pause"] : ["run", "run", R.assembled && st.count && !R.finished ? "Continue" : "Run", "F5", R.finished, "run"],
      ["step", "step", "Step", "F7", R.running || R.finished, ""],
      R.running ? ["stop", "stop", "Stop", "F11", false, ""] : ["back", "back", "Back", "F8", !(st.can_backstep && R.assembled), "opt"],
      ["reset", "reset", "Reset", "F12", !R.assembled, "opt"],
    ];
    $("#runbar").innerHTML = items.map(([a, ic, lbl, k, dis, cls]) =>
      `<button class="btn ${cls}" data-act="${a}" ${dis ? "disabled" : ""} title="${lbl} (${k})">${icon(ic, ic === "run" ? "fill" : "")}<span class="lbl">${lbl}</span></button>`).join("") +
      `<select class="speed opt" id="speed" title="Run speed">${[0, 1000, 100, 30, 10, 5, 2, 1].map(v =>
        `<option value="${v}" ${S.speed === v ? "selected" : ""}>${v ? v + "/s" : "max"}</option>`).join("")}</select>`;
    $$("#runbar [data-act]").forEach(b => b.onclick = () => ACT[b.dataset.act]());
    $("#speed").onchange = (e) => setSpeed(+e.target.value);
    const pill = $("#pill");
    let cls = "", txt = "edit";
    if (!engine.connected) { cls = "error"; txt = "offline"; }
    else if (R.running) { cls = R.waiting ? "input" : "running"; txt = R.waiting ? "input" : "running"; }
    else if (R.error) { cls = "error"; txt = "error"; }
    else if (R.finished) { cls = "done"; txt = "done"; }
    else if (R.assembled && st.count) { cls = "paused"; txt = "paused"; }
    else if (R.assembled) { cls = "ready"; txt = "ready"; }
    pill.className = "pill " + cls;
    const app = document.getElementById("app");
    for (const c of ["running", "paused", "error", "input", "done", "ready"]) app.classList.toggle("st-" + c, cls === c);
    pill.textContent = txt;
    $("#pcinfo").textContent = R.assembled && st ? `pc ${M.hex(st.pc || 0)} · ${st.count || 0} steps` : "";
    const cur = S.current;
    $("#mtitle").innerHTML = cur ? `${esc(cur.split("/").pop())}${isDirty(cur) ? " •" : ""}` : "MARS";
  }

  function renderTabs() {
    $("#tabs").innerHTML = VIEWS.map(([v, l]) => {
      let extra = "";
      if (v === "exec" && R.unread.has("exec")) extra = '<span class="dotb"></span>';
      if (v === "tools" && R.unread.has("tools")) extra = '<span class="dotb"></span>';
      return `<button class="tab ${S.view === v ? "active" : ""}" data-v="${v}">${l}${extra}</button>`;
    }).join("");
    $$("#tabs .tab").forEach(t => t.onclick = () => setView(t.dataset.v));
  }

  function renderBottomNav() {
    $("#bottomnav").innerHTML = MNAV.map(([v, l, ic]) =>
      `<button data-m="${v}" class="${currentM() === v ? "active" : ""}">${icon(ic)}<span>${l}</span>${R.unread.has(v) ? '<span class="dotb"></span>' : ""}</button>`).join("");
    $$("#bottomnav button").forEach(b => b.onclick = () => b.dataset.m === "more" ? moreSheet() : setM(b.dataset.m));
  }
  const currentM = () => ["edit", "exec", "regs", "mem", "io"].includes(S.m) ? S.m : "more";

  function setView(v) {
    if (v !== S.view || (isNarrow() && S.m !== v)) navMark();
    S.view = v;
    if (isNarrow()) S.m = v;
    R.unread.delete(v);
    $$(".view").forEach(el => el.classList.toggle("active", el.dataset.view === v));
    $("#app").dataset.m = S.m;
    renderTabs(); renderBottomNav();
    if (v === "mem") refreshMemory();
    if (v === "tools") renderTools();
    if (v === "labels") renderLabels();
    if (v === "help") renderHelp();
    if (v === "exec") scrollExecToPc();
    if (v === "edit" && !isNarrow()) setTimeout(() => ed.focus(), 0);
    updateFocus();
    updateHint();
    persist();
  }

  function setM(m) {
    if (m !== S.m) navMark();
    S.m = m;
    R.unread.delete(m);
    if (["edit", "exec", "mem", "labels", "tools", "help"].includes(m)) { setView(m); return; }
    $("#app").dataset.m = m;
    renderBottomNav();
    if (m === "regs") renderRegs();
    if (m === "io") { const out = $("#out"); out.scrollTop = out.scrollHeight; }
    persist();
  }

  function moreSheet() {
    const items = [["labels", "Labels", "tag"], ["tools", "Tools", "tools"], ["help", "Help & card", "help"],
      ["files", "Files", "folder"], ["settings", "Settings", "gear"], ["save", "Save", "save"], ["zen", "Zen mode", "zen"], ["fs", "Fullscreen", "fs"], ["lines", "Line numbers", "exec"], ["kb", "Key row", "edit"],
      ["import", "Import files", "upload"], ["exportf", "Download file", "download"], ["exportw", "Export all (.zip)", "download"]];
    const m = modal({
      sheet: true, title: "More",
      body: `<div class="sheet-grid">${items.map(([k, l, ic]) => `<button data-k="${k}">${icon(ic)}${l}</button>`).join("")}</div>`,
    });
    $$(".sheet-grid button", m.el).forEach(b => b.onclick = () => {
      m.close();
      const k = b.dataset.k;
      if (k === "settings") openSettings();
      else if (k === "zen") setZen(true);
      else if (k === "fs") setFullscreen(!isFs());
      else if (k === "import") pickFiles();
      else if (k === "exportf") exportFile();
      else if (k === "exportw") exportWorkspace();
      else if (k === "kb") { S.keybarOn = !S.keybarOn; persist(); applyTheme(); toast("Key row " + (S.keybarOn ? "on" : "off"), "", 1200); }
      else if (k === "lines") { S.lineNumbers = !S.lineNumbers; persist(); applyTheme(); toast("Line numbers " + (S.lineNumbers ? "on" : "off — code uses the full width"), "", 1600); }
      else if (k === "save") saveCurrent();
      else if (k === "files") { navMark(); S.m = "files"; $("#app").dataset.m = "files"; renderBottomNav(); refreshTree(); }
      else setM(k);
    });
  }

  function renderSubTabs() {
    const chips = (el, items, cur, fn, extra = "") => {
      el.innerHTML = items.map(([k, l, badge]) => `<button class="chip ${cur === k ? "active" : ""}" data-k="${k}">${l}${badge ? ` <b>${badge}</b>` : ""}</button>`).join("") + extra;
      $$(".chip[data-k]", el).forEach(c => c.onclick = () => fn(c.dataset.k));
    };
    if (!$("#reg-filter")) regBar();
    const errs = R.messages.filter(m => !m.warning).length, warns = R.messages.length - errs;
    chips($("#io-tabs"), [["run", "Run I/O"], ["msg", "Messages", errs || warns || ""]], R.ioTab,
      k => { R.ioTab = k; renderSubTabs(); showIoTab(); },
      `<span class="grow"></span><button class="chip" data-clear>Clear</button>`);
    $("[data-clear]", $("#io-tabs")).onclick = () => { if (R.ioTab === "run") $("#out").textContent = ""; else { R.messages = []; renderMessages(); } };
    chips($("#tool-tabs"), [["bitmap", "Bitmap Display"], ["mmio", "Keyboard & Display MMIO"]], R.toolTab,
      k => { R.toolTab = k; renderSubTabs(); renderTools(); });
    chips($("#help-tabs"), [["card", "Card"], ["instr", "Instructions"], ["pseudo", "Pseudo"], ["dirs", "Directives"], ["sys", "Syscalls"], ["keys", "Shortcuts"], ["about", "About"]],
      R.helpTab, k => { R.helpTab = k; renderSubTabs(); renderHelp(); });
  }

  function showIoTab() {
    $("#out").classList.toggle("hidden", R.ioTab !== "run");
    $("#inrow").classList.toggle("hidden", R.ioTab !== "run");
    $("#msgs").classList.toggle("hidden", R.ioTab !== "msg");
  }

  // editing key row that sits on top of the on-screen keyboard
  const KB_KEYS = [
    ["kbd", "⌄", "Hide keyboard"], ["tab", "⇥", "Indent"], ["untab", "⇤", "Dedent"],
    ["left", "←", "Cursor left"], ["right", "→", "Cursor right"], ["up", "↑", "Cursor up"], ["down", "↓", "Cursor down"],
    ["home", "⇱", "Line start"], ["end", "⇲", "Line end"],
    ["$", "$"], [",", ","], ["#", "#"], [":", ":"], ["(", "("], [")", ")"], [".", "."], ["\"", "\""], ["-", "-"], ["+", "+"], ["0x", "0x"],
    ["comment", "#⇄", "Toggle comment"], ["undo", "↶", "Undo"], ["redo", "↷", "Redo"],
    ["size", "Aa", "Key size"], ["rows", "⇕", "One / two rows"], ["hide", "✕", "Hide this row"],
  ];
  function moveCursor(dir) {
    const ta = ed.ta, v = ta.value;
    let p = ta.selectionStart;
    const ls = v.lastIndexOf("\n", p - 1) + 1;
    if (dir === "left") p = Math.max(0, p - 1);
    else if (dir === "right") p = Math.min(v.length, p + 1);
    else if (dir === "home") { const ind = (v.slice(ls).match(/^\s*/) || [""])[0].length; p = p === ls + ind ? ls : ls + ind; }
    else if (dir === "end") { const le = v.indexOf("\n", p); p = le < 0 ? v.length : le; }
    else {
      const col = p - ls;
      if (dir === "up") { if (ls === 0) return; const ps = v.lastIndexOf("\n", ls - 2) + 1; p = Math.min(ps + col, ls - 1); }
      else { const le = v.indexOf("\n", p); if (le < 0) return; const ne = v.indexOf("\n", le + 1); p = Math.min(le + 1 + col, ne < 0 ? v.length : ne); }
    }
    ta.setSelectionRange(p, p);
    ed.cursorMoved();
    const line = v.slice(0, p).split("\n").length;
    ed.revealLine(line);
  }
  function keyAction(k) {
    const ta = ed.ta;
    switch (k) {
      case "kbd": ta.blur(); return;
      case "tab": ed.insert("    "); break;
      case "untab": ed.transformLines(l => l.replace(/^( {1,4}|\t)/, "")); break;
      case "left": case "right": case "up": case "down": case "home": case "end": moveCursor(k); break;
      case "comment": ed.toggleComment(); break;
      case "undo": document.execCommand("undo"); break;
      case "redo": document.execCommand("redo"); break;
      case "size": S.kbSize = { s: "m", m: "l", l: "s" }[S.kbSize || "m"]; persist(); applyTheme(); toast("Key size " + S.kbSize.toUpperCase(), "", 900); break;
      case "rows": S.kbRows = S.kbRows === 2 ? 1 : 2; persist(); applyTheme(); break;
      case "hide": S.keybarOn = false; persist(); applyTheme(); toast("Key row hidden — More › Key row brings it back", "", 2500); return;
      default: ed.insert(k);
    }
    ta.focus({ preventScroll: true });
  }
  function renderKeybar() {
    const bar = $("#keybar");
    bar.innerHTML = KB_KEYS.map(([k, label, title]) =>
      `<button data-k="${esc(k)}" ${title ? `title="${esc(title)}" aria-label="${esc(title)}"` : ""} class="${/^(left|right|up|down|home|end)$/.test(k) ? "nav" : ""}${["size", "rows", "hide", "kbd"].includes(k) ? " meta" : ""}">${esc(label)}</button>`).join("");
    let repeat = null, delay = null;
    const stop = () => { clearTimeout(delay); clearInterval(repeat); delay = repeat = null; };
    $$("button", bar).forEach(b => {
      // keep focus (and the keyboard) in the editor; arrows auto-repeat while held
      b.addEventListener("pointerdown", (e) => {
        e.preventDefault();
        const k = b.dataset.k;
        if (R.kbScrolling) return;
        b.classList.add("down");
        if (b.classList.contains("nav")) {
          keyAction(k);
          delay = setTimeout(() => { repeat = setInterval(() => keyAction(k), 55); }, 380);
          b._handled = true;
        } else b._handled = false;
      });
      b.addEventListener("pointerup", () => { b.classList.remove("down"); stop(); if (!b._handled && !R.kbMoved) keyAction(b.dataset.k); });
      b.addEventListener("pointerleave", () => { b.classList.remove("down"); stop(); });
      b.addEventListener("pointercancel", () => { b.classList.remove("down"); stop(); });
      b.addEventListener("click", (e) => e.preventDefault());
    });
    // distinguish a horizontal swipe (scroll the row) from a tap
    let sx = 0;
    bar.addEventListener("pointerdown", (e) => { sx = e.clientX; R.kbMoved = false; }, true);
    bar.addEventListener("pointermove", (e) => { if (Math.abs(e.clientX - sx) > 10) { R.kbMoved = true; stop(); } }, true);
    bar.addEventListener("scroll", () => updateKbFade(), { passive: true });
    bar.classList.toggle("show", isTouch() || !!S.kbDesktop);
    updateKbFade();
  }
  function updateKbFade() {
    const bar = $("#keybar");
    bar.classList.toggle("more-left", bar.scrollLeft > 4);
    bar.classList.toggle("more-right", bar.scrollLeft + bar.clientWidth < bar.scrollWidth - 4);
  }

  // keep the app exactly inside the visible area — works whether the browser
  // shrinks the page for the keyboard or only the visual viewport
  const VK = navigator.virtualKeyboard;
  if (VK) { try { VK.overlaysContent = true; } catch (e) { } }   // we lay out around the keyboard ourselves
  const LAYOUT = { mode: "", kb: 0, h: 0 };
  function fitViewport() {
    const app = document.getElementById("app");
    const vv = window.visualViewport;
    let h = window.innerHeight, top = 0, mode = "window";
    const r = VK && VK.boundingRect;
    if (VK && r && r.height > 0) {
      // exact: the app ends where the keyboard starts (correct in fullscreen too)
      h = Math.round(r.top); mode = "virtualKeyboard";
    } else if (VK) {
      h = window.innerHeight; mode = "virtualKeyboard (closed)";
    } else if (vv) {
      h = Math.round(vv.height); top = Math.round(vv.offsetTop); mode = "visualViewport";
    }
    app.style.height = h + "px";
    app.style.transform = top ? `translateY(${top}px)` : "";
    LAYOUT.mode = mode; LAYOUT.kb = r ? Math.round(r.height) : 0; LAYOUT.h = h;
    if (window.scrollY) window.scrollTo(0, 0);
    requestAnimationFrame(() => {
      updateKbFade();
      if (document.activeElement === ed.ta) { const c = ed.cursor; ed.revealLine(c.line); }
    });
  }
  if (VK) VK.addEventListener("geometrychange", fitViewport);
  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", fitViewport);
    window.visualViewport.addEventListener("scroll", fitViewport);
  }
  window.addEventListener("resize", fitViewport);
  document.addEventListener("fullscreenchange", () => setTimeout(fitViewport, 120));

  // ------------------------------------------------------------------ editor & files
  const ed = new CodeEditor($("#editor"), {
    onChange: () => {
      const f = R.files.get(S.current);
      if (!f) return;
      const was = f.text !== f.saved;
      f.text = ed.value;
      if (R.marks.has(S.current)) { R.marks.delete(S.current); ed.setMarks(new Map()); }
      if (was !== (f.text !== f.saved)) { renderFileTabs(); renderRunbar(); }
      saveDraftSoon();
    },
    onCursor: (line, col, text) => { $("#pos").textContent = `Ln ${line}, Col ${col}`; R.cursor = { line, col, text }; updateHint(); },
    onToggleBreakpoint: (line) => toggleBp(S.current, line),
  });

  let draftTimer = null;
  function saveDraftSoon() {
    clearTimeout(draftTimer);
    draftTimer = setTimeout(() => {
      const drafts = {};
      for (const [p, f] of R.files) if (f.text !== f.saved) drafts[p] = f.text;
      try { localStorage.setItem(LS + ".drafts", JSON.stringify(drafts)); } catch (e) { }
    }, 600);
  }
  const loadDrafts = () => { try { return JSON.parse(localStorage.getItem(LS + ".drafts") || "{}"); } catch (e) { return {}; } };
  const isDirty = p => { const f = R.files.get(p); return f && f.text !== f.saved; };

  function renderFileTabs() {
    $("#filetabs").innerHTML = S.open.map(p => `<div class="ftab ${p === S.current ? "active" : ""}" data-p="${esc(p)}" title="${esc(p)}">
        <span>${esc(p.split("/").pop())}</span>${isDirty(p) ? '<span class="dot"></span>' : ""}<button class="x" data-close="${esc(p)}" aria-label="Close">${icon("x")}</button></div>`).join("");
    $$("#filetabs .ftab").forEach(t => t.onclick = (e) => { if (!e.target.closest(".x")) switchFile(t.dataset.p); });
    $$("#filetabs .x").forEach(x => x.onclick = (e) => { e.stopPropagation(); closeFile(x.dataset.close); });
    renderTree();
  }

  function stashView() {
    const f = R.files.get(S.current);
    if (f) f.view = { top: ed.ta.scrollTop, sel: ed.ta.selectionStart };
  }

  function switchFile(p) {
    if (p !== S.current) navMark();
    if (!R.files.has(p)) { openFile(p); return; }
    stashView();
    S.current = p;
    const f = R.files.get(p);
    ed.value = f.text;
    if (f.view) { ed.ta.scrollTop = f.view.top; ed.ta.setSelectionRange(f.view.sel, f.view.sel); ed.syncScroll(); }
    ed.setMarks(R.marks.get(p) || new Map());
    ed.setBreakpoints(S.bps[p] || []);
    ed.setExecLine(execLineFor(p));
    updateTrail();
    renderFileTabs(); renderRunbar(); persist();
    if (S.view !== "edit") setView("edit");
  }

  async function openFile(p, { focus = true } = {}) {
    if (R.files.has(p)) { if (focus) switchFile(p); return true; }
    try {
      const r = await engine.call("fs_read", { path: p });
      const drafts = loadDrafts();
      R.files.set(p, { text: drafts[p] !== undefined ? drafts[p] : r.text, saved: r.text });
      if (!S.open.includes(p)) S.open.push(p);
      if (focus) switchFile(p); else renderFileTabs();
      return true;
    } catch (e) {
      S.open = S.open.filter(x => x !== p);
      if (focus) toast(`Cannot open ${p}: ${e.message}`, "error");
      return false;
    }
  }

  async function closeFile(p) {
    if (isDirty(p) && !(await confirmBox("Unsaved changes", `${p} has unsaved changes. Close it anyway?`, "Discard"))) return;
    R.files.delete(p);
    S.open = S.open.filter(x => x !== p);
    if (S.current === p) {
      S.current = S.open[S.open.length - 1] || null;
      if (S.current) switchFile(S.current); else { ed.value = ""; renderFileTabs(); }
    } else renderFileTabs();
    saveDraftSoon(); persist();
  }

  async function saveFile(p) {
    const f = R.files.get(p);
    if (!f) return false;
    try {
      await engine.call("fs_write", { path: p, text: f.text });
      f.saved = f.text;
      renderFileTabs(); renderRunbar(); saveDraftSoon();
      return true;
    } catch (e) { toast(`Save failed: ${e.message}`, "error"); return false; }
  }
  async function saveCurrent() { if (S.current && await saveFile(S.current)) toast(`Saved ${S.current}`, "ok", 1600); }

  const TEMPLATE = (name) => `# ${name}\n        .data\nmsg:    .asciiz "Hello, MIPS!\\n"\n\n        .text\n        .globl main\nmain:\n        li   $v0, 4          # print string\n        la   $a0, msg\n        syscall\n\n        li   $v0, 10         # exit\n        syscall\n`;

  async function newFile(dir = "") {
    let name = await prompt("New file", dir ? dir + "/" : "", "name.asm");
    if (!name) return;
    name = name.trim().replace(/^\/+/, "");
    if (!/\.\w+$/.test(name)) name += ".asm";
    name = normPath(name);
    try {
      await refreshTree();
      if (treeNode(name)) { toast(`${name} already exists`, "warn"); if (!treeNode(name).dir) await openFile(name); return; }
      await engine.call("fs_write", { path: name, text: TEMPLATE(name.split("/").pop()) });
      revealPath(name, { open: false });
      await refreshTree();
      await openFile(name);
      setView("edit");
    } catch (e) { toast(e.message, "error"); }
  }
  async function newDir() {
    const name = await prompt("New folder", "", "folder");
    if (!name) return;
    try { const p = normPath(name); await engine.call("fs_mkdir", { path: p }); revealPath(p); refreshTree(); } catch (e) { toast(e.message, "error"); }
  }

  // ------------------------------------------------------------------ paths: rename / move / delete
  const parentOf = p => p.includes("/") ? p.slice(0, p.lastIndexOf("/")) : "";
  const baseName = p => p.split("/").pop();
  const joinPath = (d, n) => d && n ? d + "/" + n : (d || n);
  const normPath = p => String(p || "").replace(/\\/g, "/").split("/").map(s => s.trim()).filter(s => s && s !== ".").join("/");
  const under = (k, p) => k === p || k.startsWith(p + "/");
  const treeNode = p => R.tree.find(n => n.path === p);
  /** Follow a rename/move (from → to, files or whole folders) in tabs, current file, breakpoints, marks, folder state. */
  function remapPaths(from, to) {
    const map = k => under(k, from) ? to + k.slice(from.length) : k;
    for (const [k, f] of [...R.files]) if (under(k, from)) { R.files.delete(k); R.files.set(map(k), f); }
    S.open = S.open.map(map);
    if (S.current) S.current = map(S.current);
    for (const k of Object.keys(S.bps)) if (under(k, from)) { const v = S.bps[k]; delete S.bps[k]; S.bps[map(k)] = v; }
    for (const [k, v] of [...R.marks]) if (under(k, from)) { R.marks.delete(k); R.marks.set(map(k), v); }
    for (const c of [...collapsed]) if (under(c, from)) { collapsed.delete(c); collapsed.add(map(c)); }
    saveCollapsed(); saveDraftSoon(); persist();
  }
  /** Drop UI state of a deleted path (file or folder). */
  function forgetPaths(p) {
    for (const k of [...R.files.keys()]) if (under(k, p)) { R.files.delete(k); S.open = S.open.filter(x => x !== k); }
    for (const k of Object.keys(S.bps)) if (under(k, p)) delete S.bps[k];
    for (const c of [...collapsed]) if (under(c, p)) collapsed.delete(c);
    if (S.current && !R.files.has(S.current)) { S.current = S.open[0] || null; if (S.current) switchFile(S.current); else ed.value = ""; }
    saveCollapsed(); saveDraftSoon(); persist();
  }
  /** Rename/move with the engine's fs_rename (creates parent folders), then update the UI state. */
  async function movePath(from, to) {
    await engine.call("fs_rename", { from, to });
    remapPaths(from, to);
    // the browser store has no real folders: keep the source folder like a disk would
    const src = parentOf(from);
    if (src && !under(src, to)) { try { await engine.call("fs_mkdir", { path: src }); } catch (e) { } }
  }
  async function renamePath(p) {
    let to = await prompt("Rename", p);
    to = normPath(to);
    if (!to || to === p) return;
    try {
      await movePath(p, to);
      revealPath(to, { open: false });
      persist(); await refreshTree(); renderFileTabs(); renderRunbar();
    } catch (e) { toast(e.message, "error"); }
  }
  async function deletePath(p) {
    if (!(await confirmBox("Delete", `Delete ${p}? This cannot be undone.`, "Delete"))) return;
    try {
      await engine.call("fs_delete", { path: p });
      forgetPaths(p);
      refreshTree(); renderFileTabs();
    } catch (e) { toast(e.message, "error"); }
  }
  /** Why src cannot be moved into folder dir ("" = workspace root): "" if it can, "same" for a no-op. */
  function moveProblem(src, dir) {
    if (!src) return "Nothing to move";
    if (under(dir, src)) return "A folder cannot be moved into itself";
    if (parentOf(src) === dir) return "same";
    return "";
  }
  /** Move a file or folder (with everything in it) into folder dir; asks on name clashes. */
  async function moveInto(src, dir) {
    dir = normPath(dir);
    if (dir.split("/").includes("..")) { toast("Path outside the workspace", "error"); return false; }
    const why = moveProblem(src, dir);
    if (why === "same") { toast(`${baseName(src)} is already in ${dir || "the workspace root"}`, "", 1800); return false; }
    if (why) { toast(why, "warn"); return false; }
    await refreshTree();
    if (!treeNode(src)) { toast(`${src} no longer exists`, "error"); return false; }
    const dn = dir && treeNode(dir);
    if (dn && !dn.dir) { toast(`${dir} is a file, not a folder`, "error"); return false; }
    let to = joinPath(dir, baseName(src));
    const clash = treeNode(to);
    if (clash) {
      const dirty = R.tree.some(n => !n.dir && under(n.path, to) && isDirty(n.path));
      const choice = await new Promise(res => modal({
        title: "Name already in use",
        body: `<div class="msgtext">${esc(dir || "The workspace root")} already has ${clash.dir ? "a folder" : "a file"} named “${esc(baseName(to))}”.${dirty ? "\nIt has unsaved changes." : ""}</div>`,
        buttons: [{ label: "Cancel", value: null }, { label: "Keep both", value: "both" }, { label: "Replace", primary: true, value: "replace" }],
        onClose: res,
      }));
      if (!choice) return false;
      if (choice === "both") to = uniquePath(to, new Set(R.tree.map(n => n.path)));
      else {
        try { await engine.call("fs_delete", { path: to }); forgetPaths(to); }
        catch (e) { toast(e.message, "error"); return false; }
      }
    }
    try { await movePath(src, to); }
    catch (e) { toast(e.message, "error"); await refreshTree(); return false; }
    revealPath(to, { open: false });
    await refreshTree(); renderFileTabs(); renderRunbar();
    toast(`Moved ${baseName(src)} to ${dir ? dir + "/" : "the workspace root"}`, "ok", 1800);
    return true;
  }
  /** "Move to…" picker: works everywhere, the touch alternative to dragging. */
  async function moveDialog(src) {
    await refreshTree();
    if (!treeNode(src)) return;
    const cur = parentOf(src);
    const dirs = ["", ...R.tree.filter(n => n.dir && !under(n.path, src)).map(n => n.path)];
    const body = document.createElement("div");
    body.innerHTML = `<div class="msgtext">Move <b>${esc(src)}</b> into:</div>
      <input class="text" value="${esc(cur)}" placeholder="workspace root (or type a new folder)" autocapitalize="off" autocomplete="off" spellcheck="false">
      <div class="dir-pick">${dirs.map(d => `<button data-d="${esc(d)}" class="${d === cur ? "on cur" : ""}" style="padding-left:${10 + (d ? d.split("/").length : 0) * 14}px">${icon("folder")}<span class="nm">${d ? esc(baseName(d)) : "Workspace root"}</span>${d === cur ? '<span class="tag">current</span>' : ""}</button>`).join("")}</div>`;
    const inp = $("input", body);
    $$(".dir-pick button", body).forEach(b => b.onclick = () => {
      $$(".dir-pick button", body).forEach(x => x.classList.toggle("on", x === b));
      inp.value = b.dataset.d;
    });
    inp.oninput = () => $$(".dir-pick button", body).forEach(x => x.classList.toggle("on", x.dataset.d === normPath(inp.value)));
    const dest = await new Promise(res => modal({ title: "Move to…", body,
      buttons: [{ label: "Cancel", value: null }, { label: "Move", primary: true, get: bg => $("input", bg).value }], onClose: res }));
    if (dest !== null && dest !== undefined) await moveInto(src, dest);
  }
  /** Actions of one tree item (buttons, long-press / right-click menu). */
  function nodeAction(p, k) {
    const n = treeNode(p), isDir = !!(n && n.dir);
    if (k === "ren") renamePath(p); else if (k === "del") deletePath(p);
    else if (k === "dl") isDir ? exportWorkspace(p) : exportFile(p);
    else if (k === "imp") pickFiles(p);
    else if (k === "move") moveDialog(p);
    else if (k === "menu") nodeMenu(p);
    else if (k === "new") newFile(p);
    else if (k === "toggle") { collapsed.has(p) ? collapsed.delete(p) : collapsed.add(p); saveCollapsed(); renderTree(); }
    else if (k === "open") openFile(p).then(ok => { if (ok && isNarrow()) setM("edit"); });
  }
  let lastMenu = 0;
  function nodeMenu(p) {
    if (Date.now() - lastMenu < 700) return;
    const n = treeNode(p);
    if (!n) return;
    lastMenu = Date.now();
    const items = n.dir
      ? [["toggle", collapsed.has(p) ? "Expand" : "Collapse", "folder"], ["new", "New file here", "newfile"], ["imp", "Import here", "upload"],
        ["move", "Move to…", "move"], ["ren", "Rename", "rename"], ["dl", "Download .zip", "download"], ["del", "Delete", "trash"]]
      : [["open", "Open", "file"], ["move", "Move to…", "move"], ["ren", "Rename", "rename"], ["dl", "Download", "download"], ["del", "Delete", "trash"]];
    const m = modal({ sheet: true, title: esc(p),
      body: `<div class="sheet-grid node-menu">${items.map(([k, l, ic]) => `<button data-k="${k}">${icon(ic)}${l}</button>`).join("")}</div>` });
    $$(".sheet-grid button", m.el).forEach(b => b.onclick = () => { m.close(); nodeAction(p, b.dataset.k); });
  }

  async function refreshTree() {
    if (!R.fs) return;
    try { R.tree = (await engine.call("fs_list")).entries; } catch (e) { R.tree = []; }
    if (R.tree.length) {          // forget the state of folders that are gone
      const dirs = new Set(R.tree.filter(n => n.dir).map(n => n.path));
      let changed = false;
      for (const c of [...collapsed]) if (!dirs.has(c)) { collapsed.delete(c); changed = true; }
      if (changed) saveCollapsed();
    }
    renderTree();
  }
  // folder open/closed state: survives tree refreshes and reloads
  const COLLAPSED_KEY = LS + ".collapsed";
  const collapsed = new Set((() => { try { return JSON.parse(localStorage.getItem(COLLAPSED_KEY) || "[]"); } catch (e) { return []; } })());
  const saveCollapsed = () => { try { localStorage.setItem(COLLAPSED_KEY, JSON.stringify([...collapsed])); } catch (e) { } };
  let flash = null;               // {path, until}: item to highlight and scroll to on the next render
  let dragSrc = null, dropMark = null;   // tree drag & drop: path being dragged, highlighted drop folder
  /** Expand the folders leading to p (and p itself when it is a folder and open is set); highlight it. */
  function revealPath(p, { open = true, mark = true } = {}) {
    p = normPath(p);
    if (!p) return;
    const parts = p.split("/");
    for (let i = 1; i <= parts.length; i++) if (i < parts.length || open) collapsed.delete(parts.slice(0, i).join("/"));
    saveCollapsed();
    if (mark) flash = { path: p, until: Date.now() + 4000 };
  }
  Object.assign(IC, {
    chev: '<path d="M9 6l6 6-6 6"/>',
    move: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 13h6M12.5 10.5L15 13l-2.5 2.5"/>',
  });
  function renderTree() {
    const el = $("#tree");
    if (!R.fs) { el.innerHTML = `<div class="empty">No workspace attached.</div>`; return; }
    if (!R.tree.length) { el.innerHTML = `<div class="empty">Empty workspace.<br><button class="btn primary" id="tree-new">New file</button> <button class="btn" id="tree-imp">Import…</button><br><span class="dim">or drop files here</span></div>`; const b = $("#tree-new"); if (b) b.onclick = () => newFile(); const bi = $("#tree-imp"); if (bi) bi.onclick = () => pickFiles(); return; }
    const drag = !window.matchMedia("(pointer: coarse)").matches;   // touch: long-press › Move to…
    let html = "";
    for (const n of R.tree) {
      let hidden = false;
      for (let q = parentOf(n.path); q; q = parentOf(q)) if (collapsed.has(q)) { hidden = true; break; }
      if (hidden) continue;
      const open = n.dir && !collapsed.has(n.path);
      const pad = 4 + n.depth * 14;
      html += `<div class="node${n.path === S.current ? " active" : ""}${n.dir ? " dir" + (open ? " open" : "") : ""}${n.path === dragSrc ? " dragging" : ""}" data-p="${esc(n.path)}" data-dir="${n.dir ? 1 : 0}" draggable="${drag}" role="treeitem"${n.dir ? ` aria-expanded="${open}"` : ""} style="padding-left:${pad}px">
        <span class="tw">${n.dir ? icon("chev") : ""}</span>${icon(n.dir ? "folder" : "file")}<span class="nm">${esc(n.name)}</span>${!n.dir && isDirty(n.path) ? ' <span style="color:var(--accent)">•</span>' : ""}
        <span class="acts">${n.dir ? `<button data-a="new" title="New file here">${icon("newfile")}</button><button data-a="imp" title="Import into this folder (files or .zip)">${icon("upload")}</button>` : ""}<button data-a="dl" title="${n.dir ? "Download folder as .zip" : "Download"}">${icon("download")}</button><button data-a="move" title="Move to… (or drag it onto a folder)">${icon("move")}</button><button data-a="ren" title="Rename">${icon("rename")}</button><button data-a="del" title="Delete">${icon("trash")}</button></span><button class="more" data-a="menu" title="Actions" aria-label="Actions">${icon("more")}</button></div>`;
    }
    el.innerHTML = html;
    if (dropMark !== null) markDrop(dropMark, true);
    if (flash) {
      const n = flash.until > Date.now() && $$(".node", el).find(x => x.dataset.p === flash.path);
      if (n) { n.classList.add("flash"); n.scrollIntoView({ block: "nearest" }); flash = null; }
      else if (flash.until <= Date.now()) flash = null;
    }
  }
  // clicks, long-press (touch) and right-click on tree items
  {
    const el = $("#tree");
    let lp = null, lpFired = 0;
    el.addEventListener("click", (e) => {
      const n = e.target.closest(".node");
      if (!n) return;
      if (Date.now() - lpFired < 700) { e.preventDefault(); return; }     // the click that ends a long-press
      const p = n.dataset.p, a = e.target.closest("[data-a]");
      if (a) { e.stopPropagation(); nodeAction(p, a.dataset.a); return; }
      nodeAction(p, n.dataset.dir === "1" ? "toggle" : "open");
    });
    el.addEventListener("contextmenu", (e) => {
      const n = e.target.closest(".node");
      if (!n) return;
      e.preventDefault();
      nodeMenu(n.dataset.p);
    });
    const cancel = () => { if (lp) { clearTimeout(lp.t); lp = null; } };
    el.addEventListener("pointerdown", (e) => {
      const n = e.target.closest(".node");
      if (!n || e.pointerType === "mouse" || e.target.closest("[data-a]")) return;
      cancel();
      lp = { x: e.clientX, y: e.clientY, t: setTimeout(() => { lp = null; lpFired = Date.now(); nodeMenu(n.dataset.p); }, 520) };
    });
    el.addEventListener("pointermove", (e) => { if (lp && Math.hypot(e.clientX - lp.x, e.clientY - lp.y) > 10) cancel(); });
    for (const t of ["pointerup", "pointercancel", "scroll"]) el.addEventListener(t, cancel, { passive: true });
    // no emulated mouse events after a long-press (they would close the menu again)
    el.addEventListener("touchend", (e) => { if (Date.now() - lpFired < 700 && e.cancelable) e.preventDefault(); });
  }

  // ------------------------------------------------------------------ import / export
  const FX = window.MarsFiles;
  const looksText = (bytes) => { const n = Math.min(bytes.length, 4096); for (let i = 0; i < n; i++) { const c = bytes[i]; if (c === 0 || (c < 9) || (c > 13 && c < 32 && c !== 27)) return false; } return true; };
  const JUNK = /(^|\/)(\.|__MACOSX(\/|$))/;
  /** The single top folder all entries of a zip live in, or null. */
  function zipTop(entries) {
    const tops = new Set(entries.map(e => e.path.split("/")[0]));
    return tops.size === 1 && entries.every(e => e.path.includes("/")) ? [...tops][0] : null;
  }
  /** Where shall the zip go? Resolves to a folder path ("" = workspace root) or null (skip this zip). */
  function askZipDest(zipName, entries, base, explicit) {
    const zname = baseName(zipName).replace(/\.zip$/i, "") || "archive";
    const fresh = joinPath(base, zname), top = zipTop(entries);
    const def = explicit ? base : fresh;   // dropped on / imported into a folder: that folder; otherwise a new folder
    const folders = R.tree.filter(n => n.dir).map(n => n.path);
    const body = document.createElement("div");
    body.innerHTML = `<div class="msgtext">${entries.length} file${entries.length === 1 ? "" : "s"}${top ? ` in folder <b>${esc(top)}/</b>` : ""}</div>
      <label class="zip-lbl">Extract to</label>
      <input class="text" list="zip-dirs" value="${esc(def)}" placeholder="workspace root" autocapitalize="off" autocomplete="off" spellcheck="false">
      <datalist id="zip-dirs">${folders.map(d => `<option value="${esc(d)}">`).join("")}</datalist>
      <div class="zip-chips"><button data-d="${esc(base)}">${icon("folder")}Here · ${base ? esc(base) + "/" : "workspace root"}</button><button data-d="${esc(fresh)}">${icon("newdir")}New folder · ${esc(fresh)}/</button></div>
      <div class="zip-prev"></div>`;
    const inp = $("input", body), prev = $(".zip-prev", body);
    const show = () => {
      const d = normPath(inp.value), strip = top && d && baseName(d).toLowerCase() === top.toLowerCase();
      const paths = entries.slice(0, 3).map(e => joinPath(d, strip ? e.path.slice(top.length + 1) : e.path));
      prev.innerHTML = `${d && !treeNode(d) ? '<span class="tag">new folder</span> ' : ""}→ ${paths.map(esc).join(", ")}${entries.length > 3 ? ` … (+${entries.length - 3})` : ""}`;
      $$(".zip-chips button", body).forEach(b => b.classList.toggle("on", b.dataset.d === d));
    };
    inp.oninput = show;
    $$(".zip-chips button", body).forEach(b => b.onclick = () => { inp.value = b.dataset.d; show(); inp.focus(); });
    show();
    return new Promise(res => modal({
      title: `Extract ${esc(baseName(zipName))}`, body,
      buttons: [{ label: "Cancel", value: null }, { label: "Extract here", value: { here: true } }, { label: "Extract", primary: true, get: bg => ({ to: $("input", bg).value }) }],
      onClose: v => res(!v ? null : v.here ? base : normPath(v.to)),
    }));
  }
  function uniquePath(p, taken) {
    if (!taken.has(p)) return p;
    const m = p.match(/^(.*?)(\.[^./]*)?$/);
    for (let i = 2; ; i++) { const q = `${m[1]} (${i})${m[2] || ""}`; if (!taken.has(q)) return q; }
  }
  /** Import [{path, file|bytes}] into the workspace (optionally under dir); a .zip asks where to extract. */
  async function importEntries(input, dir = "") {
    if (!R.fs) { toast("No workspace to import into", "error"); return; }
    dir = normPath(dir);
    await refreshTree();
    const list = [], dests = [];          // list: [{path (final), file|bytes}]
    for (const it of input) {
      const rel = normPath(it.path);
      if (!rel || JUNK.test(rel)) continue;
      if (!/\.zip$/i.test(rel)) { list.push(Object.assign({}, it, { path: joinPath(dir, rel) })); continue; }
      let entries;
      try {
        const bytes = it.bytes || new Uint8Array(await it.file.arrayBuffer());
        entries = (await FX.unzip(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength)))
          .map(e => ({ path: normPath(e.path), bytes: e.bytes })).filter(e => e.path && !JUNK.test(e.path));
      } catch (e) { toast(`${rel}: ${e.message}`, "error", 5000); continue; }
      if (!entries.length) { toast(`${rel}: the zip is empty`, "warn"); continue; }
      const dest = await askZipDest(rel, entries, joinPath(dir, parentOf(rel)), !!dir);
      if (dest === null) continue;
      // a zip whose only top folder is named like the destination is not nested twice (lab1.zip: lab1/… → lab1/…)
      const top = zipTop(entries), strip = top && dest && baseName(dest).toLowerCase() === top.toLowerCase();
      for (const e of entries) list.push({ path: joinPath(dest, strip ? e.path.slice(top.length + 1) : e.path), bytes: e.bytes });
      dests.push(dest);
    }
    const bad = list.filter(it => it.path.split("/").includes(".."));
    if (bad.length) toast(`Skipped ${bad.length} file(s) outside the workspace`, "warn", 4000);
    for (const b of bad) list.splice(list.indexOf(b), 1);
    if (!list.length) return;
    for (const d of dests) if (d && !treeNode(d)) { try { await engine.call("fs_mkdir", { path: d }); } catch (e) { } }
    const existing = new Set(R.tree.filter(n => !n.dir).map(n => n.path));
    const target = (it) => it.path;
    const clashes = list.filter(it => existing.has(target(it)));
    let replace = true;
    if (clashes.length) {
      replace = await new Promise(res => modal({
        title: "Files already exist",
        body: `<div class="msgtext">${clashes.length} file(s) already exist: ${esc(clashes.slice(0, 5).map(target).join(", "))}${clashes.length > 5 ? "…" : ""}</div>`,
        buttons: [{ label: "Keep both", value: false }, { label: "Replace", primary: true, value: true }],
        onClose: v => res(v !== false && v !== null),
      }));
    }
    let n = 0, first = null;
    for (const it of list) {
      let path = target(it);
      if (!replace && existing.has(path)) path = uniquePath(path, existing);
      existing.add(path);
      const bytes = it.bytes || new Uint8Array(await it.file.arrayBuffer());
      try {
        if (FX.TEXT_EXT.test(path) || looksText(bytes)) {
          const text = FX.dec.decode(bytes);
          await engine.call("fs_write", { path, text });
          const f = R.files.get(path);
          if (f && f.text === f.saved) { f.text = f.saved = text; if (path === S.current) ed.value = text; }
        } else {
          let bin = ""; for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
          await engine.call("fs_write", { path, b64: btoa(bin) });
        }
        n++;
        if (!first && /\.(asm|s)$/i.test(path)) first = path;
      } catch (e) { toast(`${path}: ${e.message}`, "error", 5000); }
    }
    // show where things landed: open the destination folders, highlight the first program
    const where = dests.length ? dests : [dir];
    for (const d of where) revealPath(d);
    if (first) revealPath(first);
    await refreshTree();
    renderFileTabs();
    const into = where.length === 1 && where[0] ? " into " + where[0] + "/" : "";
    toast(`Imported ${n} file${n === 1 ? "" : "s"}${into}`, "ok", 2500);
    if (first) { await openFile(first); if (isNarrow()) setM("edit"); else setView("edit"); }
  }
  function pickFiles(dir = "") {
    const inp = $("#file-input");
    inp.value = "";
    inp.onchange = () => importEntries([...inp.files].map(f => ({ path: f.name, file: f })), dir);
    inp.click();
  }
  async function exportFile(p = S.current) {
    if (!p) return;
    const f = R.files.get(p);
    if (f) { FX.download(p.split("/").pop(), f.text); return; }
    try {
      const r = await engine.call("fs_read", { path: p, binary: true });
      const raw = atob(r.b64), u8 = new Uint8Array(raw.length);
      for (let i = 0; i < raw.length; i++) u8[i] = raw.charCodeAt(i);
      FX.download(p.split("/").pop(), new Blob([u8]));
    } catch (e) { toast(e.message, "error"); }
  }
  async function exportWorkspace(dir = "") {
    await refreshTree();
    const files = R.tree.filter(n => !n.dir && (!dir || n.path.startsWith(dir + "/")));
    if (!files.length) { toast("Nothing to export", "warn"); return; }
    const out = [];
    for (const n of files) {
      const open = R.files.get(n.path);
      if (open) { out.push({ path: n.path, text: open.text }); continue; }
      const r = await engine.call("fs_read", { path: n.path, binary: true });
      const raw = atob(r.b64), u8 = new Uint8Array(raw.length);
      for (let i = 0; i < raw.length; i++) u8[i] = raw.charCodeAt(i);
      out.push({ path: n.path, text: u8 });
    }
    const stamp = new Date().toISOString().slice(0, 10);
    FX.download(`${dir ? dir.split("/").pop() : "mars-workspace"}-${stamp}.zip`, FX.zip(out));
    toast(`Exported ${out.length} file${out.length === 1 ? "" : "s"}`, "ok", 2000);
  }
  // drag & drop: tree items move inside the workspace (marked with MARS_DND), OS files import anywhere
  const MARS_DND = "application/x-mars-path";
  const dtTypes = (e) => e.dataTransfer ? [...(e.dataTransfer.types || [])] : [];
  const isInternal = (e) => !!dragSrc || dtTypes(e).includes(MARS_DND);
  const hasFiles = (e) => !isInternal(e) && dtTypes(e).includes("Files");
  /** Folder a drop at the event's target lands in: a folder row → it, a file row → its folder,
   *  empty tree space or the Workspace header → "" (root); null outside the sidebar. */
  function treeDropDir(e) {
    const t = e.target && e.target.nodeType === 1 ? e.target : e.target && e.target.parentElement;
    if (!t || !t.closest("#sidebar")) return null;
    const n = t.closest(".node");
    return !n ? "" : n.dataset.dir === "1" ? n.dataset.p : parentOf(n.dataset.p);
  }
  /** Highlight the drop target (folder row and its visible contents, or the whole tree for the root). */
  function markDrop(dir, force) {
    if (dir === dropMark && !force) return;
    dropMark = dir;
    $$("#tree .drop-target, #tree .drop-inside").forEach(x => x.classList.remove("drop-target", "drop-inside"));
    $("#sidebar").classList.toggle("drop-root", dir === "");
    if (dir) for (const n of $$("#tree .node")) {
      if (n.dataset.p === dir) n.classList.add("drop-target");
      else if (n.dataset.p.startsWith(dir + "/")) n.classList.add("drop-inside");
    }
  }
  let hoverOpen = null;           // {dir, t}: dragging over a closed folder opens it after a moment
  function hoverExpand(dir) {
    if (hoverOpen && hoverOpen.dir === dir) return;
    if (hoverOpen) clearTimeout(hoverOpen.t);
    hoverOpen = dir && collapsed.has(dir) ? { dir, t: setTimeout(() => { collapsed.delete(dir); saveCollapsed(); renderTree(); }, 650) } : null;
  }
  function endDrag() {
    dragSrc = null; hoverExpand(null); markDrop(null);
    $$("#tree .dragging").forEach(x => x.classList.remove("dragging"));
  }
  {
    const side = $("#sidebar");
    side.addEventListener("dragstart", (e) => {
      const n = e.target.closest && e.target.closest(".node");
      if (!n || !e.dataTransfer) return;
      dragSrc = n.dataset.p;
      e.dataTransfer.setData(MARS_DND, dragSrc);
      e.dataTransfer.effectAllowed = "move";
      n.classList.add("dragging");
      n.addEventListener("dragend", endDrag, { once: true });   // also when the row was re-rendered meanwhile
    });
    side.addEventListener("dragover", (e) => {
      if (!isInternal(e)) return;
      const dir = treeDropDir(e);
      const ok = dir !== null && (!dragSrc || !moveProblem(dragSrc, dir));
      if (ok) { e.preventDefault(); e.dataTransfer.dropEffect = "move"; } else e.dataTransfer.dropEffect = "none";
      markDrop(ok ? dir : null);
      const n = e.target.closest && e.target.closest(".node[data-dir='1']");
      hoverExpand(ok && n ? n.dataset.p : null);
    });
    side.addEventListener("dragleave", (e) => { if (isInternal(e) && !side.contains(e.relatedTarget)) { markDrop(null); hoverExpand(null); } });
    side.addEventListener("drop", (e) => {
      if (!isInternal(e)) return;
      e.preventDefault(); e.stopPropagation();
      const src = dragSrc || e.dataTransfer.getData(MARS_DND), dir = treeDropDir(e);
      endDrag();
      if (src && dir !== null) moveInto(src, dir);
    });
    document.addEventListener("dragend", endDrag);
  }
  let dragDepth = 0;
  const dropDir = (e) => { const d = treeDropDir(e); return d === null ? "" : d; };
  document.addEventListener("dragenter", (e) => { if (!hasFiles(e)) return; e.preventDefault(); dragDepth++; $("#dropzone").classList.add("on"); });
  document.addEventListener("dragover", (e) => {
    if (!hasFiles(e)) return; e.preventDefault(); e.dataTransfer.dropEffect = "copy";
    const d = dropDir(e); $("#drop-dir").textContent = d ? d + "/" : "the workspace";
    markDrop(treeDropDir(e));
  });
  document.addEventListener("dragleave", (e) => { if (!hasFiles(e)) return; if (--dragDepth <= 0) { dragDepth = 0; $("#dropzone").classList.remove("on"); markDrop(null); } });
  document.addEventListener("drop", async (e) => {
    if (!hasFiles(e)) return;
    e.preventDefault(); dragDepth = 0; $("#dropzone").classList.remove("on");
    const dir = dropDir(e);
    markDrop(null);
    importEntries(await FX.dropped(e.dataTransfer), dir);
  });

  // ------------------------------------------------------------------ reference card
  const CARD = window.REFCARD || { instructions: [], pseudo: [], formats: {}, registers: [], syscalls: [], exceptions: [], notes: [] };
  const CARD_BY = new Map([...CARD.instructions.map(i => [i.m, i]), ...CARD.pseudo.map(i => [i.m, Object.assign({ pseudo: true }, i)])]);
  function lookup(word) {
    navMark();
    R.helpTab = "card";
    if (isNarrow()) setM("help"); else setView("help");
    const f = $("#help-filter");
    f.value = word ? `=${word}` : "";
    renderSubTabs(); renderHelp();
    if (word) setTimeout(() => { const r = $(`#help-list tr[data-m="${word}"]`); if (r) { r.click(); r.scrollIntoView({ block: "center" }); } }, 30);
  }
  function encoding(i) {
    const fields = CARD.formats[i.fmt] || [];
    const [op, fn] = i.code.split("/").map(x => x.trim());
    const bin = (hex, w) => parseInt(hex, 16).toString(2).padStart(w, "0");
    return `<div class="enc">${fields.map(f => {
      let val = f.f;
      if (f.f === "op") val = bin(op, 6);
      else if (f.f === "func" && fn !== undefined) val = bin(fn, 6);
      return `<div class="encf" style="flex:${f.bits}"><span class="eb">${f.bits}</span><span class="ev ${/^[01]+$/.test(val) ? "t-number" : ""}">${val}</span><span class="en">${f.f}</span></div>`;
    }).join("")}</div>`;
  }
  function renderCard(f) {
    const exact = f.startsWith("=") ? f.slice(1) : null;
    const match = (...xs) => !f || (exact ? xs[0] === exact : xs.some(x => String(x).toLowerCase().includes(f)));
    let h = `<div class="card-top"><b>${esc(CARD.title || "Reference card")}</b><span class="grow"></span>
      <a class="chip" href="ref/MIPS_Reference.pdf" target="_blank" rel="noopener">Open original PDF ↗</a></div>`;
    const ins = CARD.instructions.filter(i => match(i.m, i.name, i.op, i.fmt + "-type", i.code));
    if (ins.length) {
      h += `<div class="card-sec">Instructions <span>tap a row for its encoding</span></div><table class="grid cardtab"><tbody>` +
        ins.map(i => `<tr data-m="${i.m}"><td class="t-instr">${i.m}</td><td class="dim ops">${esc(i.ops)}</td><td class="nm">${esc(i.name)}</td>
          <td class="opx">${esc(i.op)}</td><td><span class="fmt fmt-${i.fmt}">${i.fmt}</span></td><td class="dim num">${esc(i.code)}</td></tr>
          <tr class="encrow hidden" data-for="${i.m}"><td colspan="6">${encoding(i)}</td></tr>`).join("") + `</tbody></table>`;
    }
    const ps = CARD.pseudo.filter(i => match(i.m, i.name, "pseudo"));
    if (ps.length) h += `<div class="card-sec">Pseudo-instructions <span>expanded by the assembler</span></div><table class="grid cardtab"><tbody>` +
      ps.map(i => `<tr data-m="${i.m}"><td class="t-pseudo">${i.m}</td><td class="dim ops">${esc(i.ops)}</td><td class="nm" colspan="4">${esc(i.name)}</td></tr>`).join("") + `</tbody></table>`;
    if (!f || match("formats", "r-type", "i-type", "j-type", "encoding")) {
      h += `<div class="card-sec">Instruction formats</div>` + Object.entries(CARD.formats).map(([k, fs]) =>
        `<div class="fmtrow"><span class="fmt fmt-${k}">${k}</span><div class="enc">${fs.map(x => `<div class="encf" style="flex:${x.bits}"><span class="eb">${x.bits} bits</span><span class="ev">${x.f}</span></div>`).join("")}</div></div>`).join("");
    }
    const grid = (title, items) => items.length ? `<div class="card-sec">${title}</div><div class="cardgrid">${items.join("")}</div>` : "";
    h += `<div class="card-cols">`;
    h += grid("Registers", CARD.registers.filter(r => match(r.name, r.num, "register")).map(r => `<div><span class="t-register">${esc(r.name)}</span><span class="dim">${esc(r.num)}</span></div>`));
    h += grid("Syscall codes (MARS/SPIM)", CARD.syscalls.filter(x => match(x.name, String(x.n), "syscall")).map(x => `<div><span class="t-number">${x.n}</span><span>${esc(x.name)}</span></div>`));
    h += grid("Exception causes", CARD.exceptions.filter(x => match(x.name, x.code, "exception", "cause")).map(x => `<div><span class="t-number">${x.code}</span><span>${esc(x.name)}</span></div>`));
    h += `</div>`;
    if (!f) h += `<div class="card-notes">${CARD.notes.map(n => `<div>${esc(n)}</div>`).join("")}</div>`;
    if (f && !ins.length && !ps.length && !h.includes("cardgrid")) h += `<div class="empty">Nothing on the card matches “${esc(exact || f)}”. Try the Instructions tab for MARS's full list.</div>`;
    return h;
  }

  // ------------------------------------------------------------------ hints
  function updateHint() {
    const h = $("#hint");
    requestAnimationFrame(() => $(".statusbar").classList.toggle("has-hint", !!h.textContent));
    if (S.view === "edit" && R.cursor) {
      const mk = (R.marks.get(S.current) || new Map()).get(R.cursor.line);
      if (mk) { h.innerHTML = `<span style="color:var(--${mk.kind === "error" ? "error" : "warning"})">${mk.kind === "error" ? "✗" : "⚠"} ${esc(mk.msg)}</span>`; return; }
      const mn = M.mnemonicOf(R.cursor.text);
      if (mn && mn.type === "instr" && M.ISA.instructions.has(mn.name)) {
        const fs = M.ISA.instructions.get(mn.name);
        const pseudo = fs.every(f => f.pseudo);
        const c = CARD_BY.get(mn.name);
        h.innerHTML = c && !c.pseudo
          ? `<span class="f">${M.highlight(mn.name + (c.ops ? " " + c.ops : ""))}</span><span class="cardop">${esc(c.op)}</span><span class="fmt fmt-${c.fmt}">${c.fmt}</span> <span class="dim">${esc(c.code)}</span> · ${esc(c.name)}`
          : `<span class="f">${M.highlight(fs[0].format)}</span>${pseudo ? '<span class="t-pseudo" style="margin-right:8px">pseudo</span>' : ""}${esc(fs[0].desc)}${fs.length > 1 ? ` <span style="opacity:.7">(+${fs.length - 1} forms)</span>` : ""}`;
        h.dataset.word = mn.name;
        return;
      }
      if (mn && mn.type === "dir") { h.innerHTML = `<span class="f">${M.highlight(mn.name)}</span>${esc(M.ISA.directives.get(mn.name) || "")}`; return; }
    }
    h.textContent = "";
    delete h.dataset.word;
  }
  $("#hint").addEventListener("click", () => { const w = $("#hint").dataset.word; if (w) lookup(w); });

  // ------------------------------------------------------------------ breakpoints
  function toggleBp(path, line) {
    if (!path) return;
    const set = new Set(S.bps[path] || []);
    set.has(line) ? set.delete(line) : set.add(line);
    S.bps[path] = [...set].sort((a, b) => a - b);
    if (!S.bps[path].length) delete S.bps[path];
    if (path === S.current) ed.setBreakpoints(S.bps[path] || []);
    markExecBps();
    persist();
  }
  function bpAddrs() {
    const out = [], seen = new Set();
    for (const r of R.rows) {
      const k = r.file + ":" + r.line;
      if (!seen.has(k) && (S.bps[r.file] || []).includes(r.line)) { seen.add(k); out.push(r.addr); }
    }
    return out;
  }

  // ------------------------------------------------------------------ assemble & run
  function engineSettings() {
    const k = ["pseudo", "delayed_branching", "self_modifying", "warnings_are_errors", "start_at_main", "bare_machine",
      "exception_handler", "program_args", "memory_config"];
    const o = {};
    k.forEach(x => o[x] = S[x]);
    return o;
  }

  async function assemble() {
    if (!S.current) { toast("Open or create a file first", "warn"); return false; }
    for (const p of S.open) if (isDirty(p) && (S.autosave || p === S.current)) await saveFile(p);
    let files = [S.current];
    if (S.assemble_all) {
      const dir = S.current.includes("/") ? S.current.slice(0, S.current.lastIndexOf("/")) : "";
      await refreshTree();
      files = [S.current, ...R.tree.filter(n => !n.dir && /\.(asm|s)$/i.test(n.name) && n.path !== S.current &&
        (n.path.includes("/") ? n.path.slice(0, n.path.lastIndexOf("/")) : "") === dir).map(n => n.path)];
    }
    let res;
    try { res = await engine.call("assemble", { files, main: S.current, settings: engineSettings() }); }
    catch (e) { toast("Assemble failed: " + e.message, "error"); return false; }
    R.messages = res.messages || [];
    R.marks = new Map();
    for (const m of R.messages) {
      if (!m.file || !m.line) continue;
      if (!R.marks.has(m.file)) R.marks.set(m.file, new Map());
      R.marks.get(m.file).set(m.line, { kind: m.warning ? "warning" : "error", col: m.col, msg: m.message.trim() });
    }
    ed.setMarks(R.marks.get(S.current) || new Map());
    renderMessages();
    R.running = false; R.error = false; R.waiting = null;
    if (!res.success) {
      R.assembled = false;
      const n = R.messages.filter(m => !m.warning).length;
      consoleLine(`Error: assemble failed with ${n} error(s)`, "err");
      R.ioTab = "msg"; renderSubTabs(); showIoTab();
      showPanels(true);
      const first = R.messages.find(m => !m.warning);
      if (first) {
        toast(`✗ ${first.file}:${first.line} — ${first.message.trim()}`, "error", 5000);
        jumpTo(first.file, first.line, first.col);
      }
      renderRunbar();
      return false;
    }
    loadProgram(res);
    R.assembled = true; R.finished = false;
    R.prev = null;
    applyState(res.state);
    const w = R.messages.length;
    consoleLine(`Assemble: ${files.join(", ")} — operation completed successfully.${w ? ` (${w} warning${w > 1 ? "s" : ""})` : ""}`, "ok");
    if (w) { R.ioTab = "msg"; renderSubTabs(); showIoTab(); }
    setView("exec");
    return true;
  }

  function loadProgram(p) {
    R.program = p;
    R.rows = p.text || [];
    R.addrIdx = new Map(R.rows.map((r, i) => [r.addr, i]));
    R.labels = p.labels || [];
    R.segments = p.segments || {};
    R.memBase = R.segments.data != null ? R.segments.data : 0x10010000;
    R.memPrev = new Map();
    R.mem.start = null; R.mem.rows = 96; R.mem.target = null;
    clearHeat(); R.state = null;
    updateMemDatalist();
    $("#mmio-out") && ($("#mmio-out").textContent = "");
    buildExecTable();
    renderLabels();
  }

  async function ensureAssembled() { return R.assembled || await assemble(); }

  const ACT = {
    async assemble() { await assemble(); },
    async run() {
      if (R.running) return ACT.pause();
      if (!(await ensureAssembled())) return;
      if (R.finished) { toast("Program finished — Reset (F12) to run again", "warn"); return; }
      R.prev = R.state;
      showPanels(true);
      try { await engine.call("run", { breakpoints: bpAddrs(), speed: S.speed }); }
      catch (e) { toast(e.message, "error"); return; }
      R.running = true; R.error = false;
      renderRunbar();
    },
    async pause() { if (R.running) try { await engine.call("pause"); } catch (e) { } },
    async stop() { try { await engine.call("stop"); } catch (e) { } },
    async step() {
      if (R.running || R.busyStep) return;
      if (!(await ensureAssembled())) return;
      if (R.finished) { toast("Program finished — Reset (F12) to run again", "warn"); return; }
      R.busyStep = true;
      showPanels(true);
      const prev = R.state;
      try {
        const res = await engine.call("step", {}, 24 * 3600 * 1000);
        R.prev = prev;
        if (res.finished) finished(res.reason, res.errors);
        applyState(res.state, true);
      } catch (e) { toast(e.message, "error"); }
      finally { R.busyStep = false; }
    },
    async back() {
      if (R.running || !R.assembled) return;
      const prev = R.state;
      try {
        const res = await engine.call("backstep");
        if (res.empty) { toast("Nothing to undo", "warn", 1500); return; }
        R.prev = prev; R.finished = false; R.error = false;
        applyState(res.state, true);
      } catch (e) { toast(e.message, "error"); }
    },
    async reset() {
      if (!R.assembled) return;
      try {
        const res = await engine.call("reset");
        R.running = false; R.finished = false; R.error = false; R.prev = null; R.memPrev = new Map(); R.waiting = null;
        clearHeat(); R.state = null;
        const mo = $("#mmio-out"); if (mo) mo.textContent = "";
        consoleLine("-- reset --", "meta");
        applyState(res.state, true);
        setWaiting(null);
      } catch (e) { toast(e.message, "error"); }
    },
  };

  async function setSpeed(v) {
    S.speed = v; persist();
    try { await engine.call("speed", { value: v }); } catch (e) { }
  }

  function finished(reason, errors) {
    R.finished = true;
    if (reason === "error") {
      R.error = true;
      for (const e of errors || []) consoleLine(`Error in ${e.file ? e.file + " line " + e.line + ": " : ""}${String(e.message || "").trim()}`, "err");
      consoleLine("-- program is finished running (error) --", "meta");
      const e0 = (errors || [])[0];
      toast("✗ Runtime error" + (e0 ? ": " + String(e0.message).trim() : ""), "error", 6000);
      if (isNarrow() && S.m !== "io") { R.unread.add("io"); renderBottomNav(); }
    } else if (reason === "stopped") {
      consoleLine("-- program stopped --", "meta");
    } else {
      consoleLine("-- program is finished running --", "meta");
    }
  }

  // ------------------------------------------------------------------ console
  const out = $("#out");
  let outLen = 0;
  function consoleWrite(text, cls = "") {
    const atBottom = out.scrollTop + out.clientHeight >= out.scrollHeight - 30;
    if (cls) { const s = document.createElement("span"); s.className = cls; s.textContent = text; out.appendChild(s); }
    else {
      const last = out.lastChild;
      if (last && last.nodeType === 3) last.appendData(text); else out.appendChild(document.createTextNode(text));
    }
    outLen += text.length;
    if (outLen > 400000) { while (out.firstChild && outLen > 300000) { outLen -= out.firstChild.textContent.length; out.firstChild.remove(); } }
    if (atBottom) out.scrollTop = out.scrollHeight;
  }
  function consoleLine(text, cls) {
    const t = out.textContent;
    if (t && !t.endsWith("\n")) consoleWrite("\n");
    consoleWrite(text + "\n", cls);
  }

  function setWaiting(kind) {
    R.waiting = kind;
    const row = $("#inrow");
    row.classList.toggle("wanted", !!kind);
    $("#inprompt").textContent = kind ? `${kind} ▸` : "stdin";
    $("#stdin").placeholder = kind ? `Program is waiting for ${kind} input — type and press Enter` : "Program input — press Enter";
    if (kind) {
      if (S.zen) setZen(false);
      showPanels(true);
      if (isNarrow()) setM("io");
      else if (R.ioTab !== "run") { R.ioTab = "run"; renderSubTabs(); showIoTab(); }
      setTimeout(() => $("#stdin").focus(), 0);
    }
    renderRunbar();
  }

  $("#stdin").addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    const v = e.target.value;
    e.target.value = "";
    if (R.waiting) consoleWrite(v + "\n", "echo");
    engine.call("input", { text: v + "\n" }).catch(() => { });
    setWaiting(null);
  });

  function renderMessages() {
    const el = $("#msgs");
    if (!R.messages.length) el.innerHTML = `<div class="empty">No messages.</div>`;
    else el.innerHTML = R.messages.map((m, i) => `<div class="msg ${m.warning ? "warning" : "error"}" data-i="${i}">
        <span class="k">${m.warning ? "⚠" : "✗"}</span><span class="loc">${esc(m.file || "")}${m.line ? ":" + m.line + ":" + m.col : ""}</span>
        <span>${esc(String(m.message).trim())}</span></div>`).join("");
    $$(".msg", el).forEach(d => d.onclick = () => { const m = R.messages[+d.dataset.i]; jumpTo(m.file, m.line, m.col); });
    renderSubTabs(); showIoTab();
  }

  async function jumpTo(file, line, col) {
    navMark();
    if (!file || !line) return;
    if (!(await openFile(file))) return;
    if (isNarrow()) setM("edit"); else setView("edit");
    setTimeout(() => ed.goTo(line, col || 1), 30);
  }

  // ------------------------------------------------------------------ state → UI
  let tickPending = null;
  // change tracking for the "heat" glow (fades over 3 steps) and the executed-line trail
  R.step = 0; R.heat = new Map(); R.trail = []; R.memHeat = new Map();
  function clearHeat() { R.step = 0; R.heat = new Map(); R.trail = []; R.memHeat = new Map(); }
  function trackChanges(prev, st) {
    if (!prev || !st || !prev.gpr || !st.gpr) return;
    if (prev.pc === st.pc && prev.count === st.count) return;
    R.step++;
    st.gpr.forEach((v, i) => { if (prev.gpr[i] !== v) R.heat.set("g" + i, R.step); });
    (st.fpr || []).forEach((v, i) => { if (prev.fpr && prev.fpr[i] !== v) R.heat.set("f" + i, R.step); });
    for (const k of ["hi", "lo"]) if (prev[k] !== st[k]) R.heat.set(k, R.step);
    for (const c of st.cop0 || []) { const p0 = (prev.cop0 || []).find(x => x.num === c.num); if (p0 && p0.value !== c.value) R.heat.set("c" + c.num, R.step); }
    if (prev.pc !== st.pc) { R.trail.unshift(prev.pc); if (R.trail.length > 5) R.trail.length = 5; }
  }
  function heatOf(key) { const s0 = R.heat.get(key); if (s0 === undefined) return -1; const age = R.step - s0; return age <= 3 ? age : -1; }
  const heatCls = (age) => age < 0 ? "" : `heat${age}${age === 0 ? " flash" : ""}`;

  function applyState(st, follow = true) {
    if (!st) return;
    trackChanges(R.state, st);
    R.state = st;
    if (!R.running) R.finished = R.finished || !!st.finished;
    renderRegs();
    updatePc(follow);
    if (S.view === "mem") refreshMemory();
    if (S.view === "tools" && R.toolTab === "bitmap") refreshBitmap();
    renderRunbar();
  }

  // address expressions: 0x…, decimal, label, $reg, pc, combined with + / -   e.g. "msg+4", "$sp-8"
  const REG_INDEX = new Map(M.REG_NAMES.map((n, i) => [n, i]));
  function evalAddr(expr) {
    const t = String(expr).replace(/\s+/g, "");
    if (!t) throw new Error("enter an address, label or register");
    const parts = t.match(/[+-]?[^+-]+/g) || [];
    let sum = 0;
    for (let p of parts) {
      let sign = 1;
      if (p[0] === "+") p = p.slice(1); else if (p[0] === "-") { sign = -1; p = p.slice(1); }
      let v;
      if (p[0] === "$") {
        const st = R.state;
        if (!st) throw new Error("registers are available after assembling");
        const name = p.toLowerCase();
        if (REG_INDEX.has(name)) v = st.gpr[REG_INDEX.get(name)];
        else if (/^\$\d{1,2}$/.test(name) && +name.slice(1) < 32) v = st.gpr[+name.slice(1)];
        else throw new Error(`unknown register ${p}`);
      } else if (p.toLowerCase() === "pc") v = R.state ? R.state.pc : 0;
      else if (/^(0x|0b|\d)/i.test(p)) v = M.parseNum(p);
      else {
        const lab = (R.labels || []).find(l => l.name === p);
        if (!lab) throw new Error(`unknown label "${p}"`);
        v = lab.addr;
      }
      sum += sign * v;
    }
    return sum >>> 0;
  }
  const labelAt = (a) => (R.labels || []).filter(l => (l.addr >>> 0) === (a >>> 0)).map(l => l.name);

  // ------------------------------------------------------------------ value inspector
  let inspectorEl = null;
  let inspectorCloser = null;
  function closeInspector(fromBack) {
    if (!inspectorEl) return;
    inspectorEl.remove(); inspectorEl = null;
    if (fromBack !== true && inspectorCloser) overlayClosed(inspectorCloser);
    inspectorCloser = null;
  }
  function binary(v) { return (M.u32(v)).toString(2).padStart(32, "0").replace(/(.{4})(?!$)/g, "$1 "); }
  function chars(v) {
    let s = "";
    for (let i = 0; i < 4; i++) { const c = (M.u32(v) >>> (8 * i)) & 255; s += c >= 32 && c < 127 ? String.fromCharCode(c) : "·"; }
    return s;
  }
  /** Show every interpretation of a 32-bit value, with edit + "show in memory". */
  const meaningCtx = () => ({ state: R.state, segments: R.segments, labels: R.labels, addrIdx: R.addrIdx, rows: R.rows, engine });
  function inspect(anchor, { title, sub, value, onSave, pointer = true, extra = "", meaning = null }) {
    closeInspector();
    const v = value | 0;
    const labs = labelAt(v);
    const rows = [["hex", M.hex(v)], ["signed", String(M.s32(v))], ["unsigned", String(M.u32(v))],
      ["binary", binary(v)], ["float", M.fmtFloat(M.asFloat(v))], ["chars", chars(v)]];
    const el = document.createElement("div");
    el.className = "inspector" + (isNarrow() ? " sheet" : "");
    el.innerHTML = `<div class="ins-h"><span class="ins-t">${title}</span><span class="ins-s">${sub || ""}</span>
        <button class="icon-btn ins-x" aria-label="Close">${icon("x")}</button></div>
      ${meaning ? `<div class="ins-meaning"><div class="dim">…</div></div>` : ""}
      <div class="ins-grid">${rows.map(([k, x]) => `<span class="k">${k}</span><span class="v" title="Click to copy">${esc(x)}</span>`).join("")}
        ${labs.length ? `<span class="k">label</span><span class="v t-label">${esc(labs.join(", "))}</span>` : ""}${extra}</div>
      ${onSave ? `<div class="ins-edit"><input value="${esc(M.hex(v))}" autocapitalize="off" autocomplete="off" spellcheck="false" aria-label="New value">
        <button class="btn primary ins-save">Set</button></div>` : ""}
      <div class="ins-acts">${pointer ? `<button class="chip ins-mem">Show memory at ${esc(M.hex(v))}</button>` : ""}</div>`;
    document.body.appendChild(el);
    inspectorEl = el;
    inspectorCloser = (fromBack) => closeInspector(fromBack === true ? true : false);
    overlayOpened(inspectorCloser);
    if (!isNarrow()) {
      const r = anchor.getBoundingClientRect();
      const w = el.offsetWidth, h = el.offsetHeight;
      let x = Math.min(window.innerWidth - w - 8, Math.max(8, r.left - w / 2 + r.width / 2));
      let y = r.bottom + 6;
      if (y + h > window.innerHeight - 8) y = Math.max(8, r.top - h - 6);
      el.style.left = x + "px"; el.style.top = y + "px";
    }
    $(".ins-x", el).onclick = () => closeInspector();
    if (meaning) Promise.resolve(meaning).then(rows => {
      const box = $(".ins-meaning", el);
      if (!box || inspectorEl !== el) return;
      rows = (rows || []).filter(r => r && r[1]);
      if (!rows.length) { box.remove(); return; }
      box.innerHTML = rows.map(([k, v]) => `<span class="k">${esc(k)}</span><span class="v">${v}</span>`).join("");
      if (!isNarrow()) {   // keep the popover on screen after it grew
        const rr = el.getBoundingClientRect();
        if (rr.bottom > window.innerHeight - 8) el.style.top = Math.max(8, window.innerHeight - 8 - rr.height) + "px";
      }
    }).catch(() => { const box = $(".ins-meaning", el); if (box) box.remove(); });
    $$(".ins-grid .v", el).forEach(s => s.onclick = () => { navigator.clipboard && navigator.clipboard.writeText(s.textContent); toast("Copied " + s.textContent, "", 1200); });
    const mem = $(".ins-mem", el);
    if (mem) mem.onclick = () => { closeInspector(); memGoto(v); };
    if (onSave) {
      const inp = $(".ins-edit input", el);
      const save = async () => {
        if (R.running) { toast("Pause the program to edit values", "warn"); return; }
        let nv;
        try { nv = M.parseNum(inp.value); } catch (e) { toast(e.message, "error"); return; }
        closeInspector();
        await onSave(nv);
      };
      $(".ins-save", el).onclick = save;
      inp.addEventListener("keydown", e => { if (e.key === "Enter") save(); if (e.key === "Escape") closeInspector(); e.stopPropagation(); });
      if (!isNarrow()) setTimeout(() => { inp.focus(); inp.select(); }, 0);
    }
  }
  document.addEventListener("mousedown", (e) => {
    if (inspectorEl && !inspectorEl.contains(e.target) && !e.target.closest("td.editable,.regrow")) closeInspector();
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && inspectorEl) { e.stopPropagation(); closeInspector(); } }, true);

  // registers ---------------------------------------------------------
  const REG_GROUPS = [["", [0, 1]], ["Results", [2, 3]], ["Arguments", [4, 5, 6, 7]],
    ["Temporaries", [8, 9, 10, 11, 12, 13, 14, 15, 24, 25]], ["Saved", [16, 17, 18, 19, 20, 21, 22, 23]],
    ["Pointers", [28, 29, 30, 31]], ["Kernel", [26, 27]]];
  function regBar() {
    $("#reg-tabs").innerHTML = [["gpr", "GPR", "General purpose registers"], ["fpr", "FPU", "Coprocessor 1 (floating point)"], ["cp0", "CP0", "Coprocessor 0 (exceptions)"]].map(([k, l, t]) =>
      `<button class="chip ${R.regTab === k ? "active" : ""}" data-k="${k}" title="${t}">${l}</button>`).join("") +
      `<span class="grow"></span><input class="regfilter" id="reg-filter" placeholder="filter" value="${esc(R.regFilter || "")}" autocapitalize="off" spellcheck="false">
       <button class="chip ${S.hideZero ? "active" : ""}" id="reg-nz" title="Hide registers that are zero">≠0</button>`;
    $$("#reg-tabs [data-k]").forEach(c => c.onclick = () => { R.regTab = c.dataset.k; regBar(); renderRegs(); });
    $("#reg-nz").onclick = () => { S.hideZero = !S.hideZero; persist(); regBar(); renderRegs(); };
    const f = $("#reg-filter");
    f.oninput = () => { R.regFilter = f.value; renderRegs(); };
  }
  function regRow(name, num, v, age, attrs, fp = false) {
    const hc = heatCls(age);
    const role = typeof num === "number" && window.MipsMeaning ? window.MipsMeaning.ROLE[num] : "";
    return `<tr class="regrow" ${attrs} ${role && attrs.includes('data-f="gpr"') ? `title="${esc(role)} — click for details"` : ""}><td class="regname${fp ? " fp" : ""}">${name}${num !== "" ? `<span class="rn">${num}</span>` : ""}</td>` +
      `<td class="num ${hc || (v === 0 ? "zero" : "")}">${M.hex(v)}</td><td class="num ${hc ? "heatfg" : v === 0 ? "zero" : "dim"}">${M.s32(v)}</td></tr>`;
  }
  function renderRegs() {
    const wrap = $("#reg-wrap");
    if (isNarrow() && S.m !== "regs") return;
    if (!$("#reg-filter")) regBar();
    const st = R.state, pv = R.prev;
    if (!st) { wrap.innerHTML = `<div class="empty">Assemble a program to see registers.<br><span class="kbdk">F3</span></div>`; return; }
    const flt = (R.regFilter || "").trim().toLowerCase();
    const keep = (name, v) => (!flt || name.toLowerCase().includes(flt)) && (!S.hideZero || v !== 0);
    let h = `<table class="grid regtable"><thead><tr><th>Name</th><th class="num">Hex</th><th class="num">Decimal</th></tr></thead><tbody>`;
    let shown = 0;
    if (R.regTab === "gpr") {
      for (const [g, idxs] of REG_GROUPS) {
        const rows = idxs.filter(i => keep(M.REG_NAMES[i], st.gpr[i]));
        if (!rows.length) continue;
        if (g && !flt) h += `<tr class="grp"><td colspan="3">${g}</td></tr>`;
        for (const i of rows) { h += regRow(M.REG_NAMES[i], i, st.gpr[i], heatOf("g" + i), `data-f="gpr" data-n="${i}"`); shown++; }
      }
      const sp = ["pc", "hi", "lo"].filter(k => keep(k, st[k] || 0));
      if (sp.length) {
        if (!flt) h += `<tr class="grp"><td colspan="3">Special</td></tr>`;
        for (const k of sp) { h += regRow(k, "", st[k] || 0, k === "pc" ? -1 : heatOf(k), `data-f="${k}" data-n="0"`); shown++; }
      }
    } else if (R.regTab === "fpr") {
      h = `<table class="grid regtable"><thead><tr><th>Name</th><th class="num">Float</th><th class="num">Double</th></tr></thead><tbody>`;
      st.fpr.forEach((v, i) => {
        if (!keep(`$f${i}`, v)) return;
        const hc = heatCls(heatOf("f" + i));
        const dbl = i % 2 === 0 ? M.fmtFloat(M.asDouble(st.fpr[i], st.fpr[i + 1])) : "";
        h += `<tr class="regrow" data-f="fpr" data-n="${i}"><td class="regname fp">$f${i}</td><td class="num ${hc || (v === 0 ? "zero" : "")}">${M.fmtFloat(M.asFloat(v))}</td><td class="num ${dbl === "0" ? "zero" : "dim"}">${dbl}</td></tr>`;
        shown++;
      });
      const fl = st.flags || 0;
      h += `<tr class="grp"><td colspan="3">Condition flags 7…0: <span class="t-number">${[7, 6, 5, 4, 3, 2, 1, 0].map(b => (fl >> b) & 1).join(" ")}</span></td></tr>`;
    } else {
      const prev = new Map(((pv && pv.cop0) || []).map(c => [c.num, c.value]));
      for (const c of st.cop0) {
        const name = c.name.replace(/^\$\d+ \((\w+)\)$/, "$$$1");
        if (!keep(name, c.value)) continue;
        h += regRow(esc(name), c.num, c.value, heatOf("c" + c.num), `data-f="cop0" data-n="${c.num}"`);
        shown++;
      }
      const cause = st.cop0.find(c => c.num === 13);
      if (cause) {
        const code = (cause.value >> 2) & 31;
        const names = { 0: "interrupt", 4: "address error (load/fetch)", 5: "address error (store)", 8: "syscall", 9: "breakpoint", 10: "reserved instruction", 12: "arithmetic overflow", 13: "trap", 15: "divide by zero" };
        h += `<tr class="grp"><td colspan="3">Cause: exception code ${code}${names[code] ? " — " + names[code] : ""}</td></tr>`;
      }
    }
    if (!shown && R.regTab !== "fpr") h += `<tr><td colspan="3" class="dim" style="padding:14px 10px">No register matches${S.hideZero ? " (zero registers hidden)" : ""}.</td></tr>`;
    const top = wrap.scrollTop;
    wrap.innerHTML = h + "</tbody></table>";
    wrap.scrollTop = top;
  }

  $("#reg-wrap").addEventListener("click", (e) => {
    const tr = e.target.closest("tr.regrow");
    if (!tr || !R.state) return;
    const f = tr.dataset.f, n = +tr.dataset.n, st = R.state;
    let v, title, sub;
    if (f === "gpr") { v = st.gpr[n]; title = M.REG_NAMES[n]; sub = `register ${n}`; }
    else if (f === "fpr") { v = st.fpr[n]; title = `$f${n}`; sub = "coprocessor 1"; }
    else if (f === "cop0") { const c = st.cop0.find(x => x.num === n); v = c.value; title = c.name; sub = `coprocessor 0 · ${n}`; }
    else { v = st[f] || 0; title = f; sub = "special register"; }
    const MM = window.MipsMeaning, ctx = meaningCtx();
    const meaning = !MM ? null : f === "gpr" ? MM.gprMeaning(n, ctx) : f === "fpr" ? MM.fprMeaning(n, ctx)
      : f === "cop0" ? MM.cop0Meaning(n, v, ctx) : MM.specialMeaning(f, ctx);
    const extra = f === "fpr" && n % 2 === 0 ? `<span class="k">double</span><span class="v">${esc(M.fmtFloat(M.asDouble(st.fpr[n], st.fpr[n + 1])))}</span>` : "";
    inspect(tr, {
      title, sub, value: v, extra, pointer: f !== "fpr", meaning,
      onSave: (f === "gpr" && n === 0) ? null : async (nv) => {
        try {
          const res = await engine.call("setreg", { file: f, num: n, value: nv });
          R.prev = R.state;
          applyState(res.state, f === "pc");
        } catch (err) { toast(err.message, "error"); }
      },
    });
  });

  function inlineEdit(td, commit) {
    const old = td.textContent;
    td.innerHTML = `<input class="cell" value="${esc(old)}" autocapitalize="off" autocomplete="off" spellcheck="false">`;
    const i = $("input", td);
    i.focus(); i.select();
    let done = false;
    const finish = (ok) => {
      if (done) return; done = true;
      if (ok && i.value.trim() !== old) commit(i.value); else td.textContent = old;
    };
    i.addEventListener("keydown", (e) => { if (e.key === "Enter") finish(true); if (e.key === "Escape") finish(false); e.stopPropagation(); });
    i.addEventListener("blur", () => finish(true));
  }

  // execute view ---------------------------------------------------------
  function buildExecTable() {
    const wrap = $("#exec-wrap");
    $("#exec-bar").innerHTML = `<button class="chip" id="x-pc">Go to PC</button><button class="chip" id="x-clear">Clear breakpoints</button>
      <span class="grow"></span><span class="dim" style="font-size:12px;color:var(--muted)">Tap ● to set a breakpoint · ${R.rows.length} instructions</span>`;
    $("#x-pc").onclick = () => scrollExecToPc(true);
    $("#x-clear").onclick = () => { S.bps = {}; persist(); ed.setBreakpoints([]); markExecBps(); };
    if (!R.rows.length) { wrap.innerHTML = `<div class="empty">Nothing assembled yet.</div>`; return; }
    let h = `<table class="grid exec"><thead><tr><th></th><th>Address</th><th class="c-code">Code</th><th>Basic</th><th>Source</th></tr></thead><tbody>`;
    let lastKey = null;
    R.rows.forEach((r, i) => {
      const key = r.file + ":" + r.line;
      const first = key !== lastKey;
      lastKey = key;
      h += `<tr data-i="${i}"><td class="bp"></td><td class="addr dim">${M.hex(r.addr)}</td><td class="c-code dim">${M.hex(r.code)}</td>` +
        `<td>${M.highlight(r.basic)}</td><td class="src">${first && r.line ? `<span class="ln">${r.line}</span>${M.highlight(r.source.trim())}` : ""}</td></tr>`;
    });
    wrap.innerHTML = h + "</tbody></table>";
    R.trs = $$("tbody tr", wrap);
    R.pcRow = -1;
    markExecBps();
    updatePc(true);
  }

  $("#exec-wrap").addEventListener("click", (e) => {
    const tr = e.target.closest("tr[data-i]");
    if (!tr) return;
    const r = R.rows[+tr.dataset.i];
    if (e.target.closest("td.bp") || e.detail === 2) toggleBp(r.file, r.line);
    else {
      R.trs && R.trs.forEach(t => t.classList.remove("cursor"));
      tr.classList.add("cursor");
    }
  });
  $("#exec-wrap").addEventListener("dblclick", (e) => {
    const tr = e.target.closest("tr[data-i]");
    if (tr && !e.target.closest("td.bp")) { const r = R.rows[+tr.dataset.i]; jumpTo(r.file, r.line, 1); }
  });

  function markExecBps() {
    if (!R.trs) return;
    const addrs = new Set(bpAddrs());
    R.rows.forEach((r, i) => R.trs[i].classList.toggle("isbp", addrs.has(r.addr)));
  }

  function execLineFor(path) {
    if (!R.state || !R.assembled || R.finished) return null;
    const i = R.addrIdx.get(R.state.pc);
    if (i === undefined) return null;
    const r = R.rows[i];
    return r.file === path ? r.line : null;
  }

  function updateTrail() {
    if (R.trailRows) for (const tr of R.trailRows) tr.classList.remove("trail1", "trail2", "trail3", "trail4", "trail5");
    R.trailRows = [];
    const lines = new Map();
    const live = R.assembled && !R.finished;
    if (live) R.trail.forEach((pc, k) => {
      const i = R.addrIdx.get(pc);
      if (i === undefined) return;
      if (R.trs && R.trs[i] && i !== R.pcRow) { R.trs[i].classList.add("trail" + (k + 1)); R.trailRows.push(R.trs[i]); }
      const r = R.rows[i];
      if (r.file === S.current && !lines.has(r.line)) lines.set(r.line, k + 1);
    });
    ed.setTrail(lines);
  }

  function updatePc(follow) {
    ed.setExecLine(execLineFor(S.current));
    if (!R.trs) return;
    const i = R.state ? R.addrIdx.get(R.state.pc) : undefined;
    const ni = i === undefined ? -1 : i;
    if (R.pcRow >= 0 && R.trs[R.pcRow]) R.trs[R.pcRow].classList.remove("pc");
    R.pcRow = ni;
    if (ni >= 0) { R.trs[ni].classList.add("pc"); if (follow) scrollExecToPc(); }
    updateTrail();
  }
  function scrollExecToPc(force) {
    if (R.pcRow < 0 || !R.trs) return;
    const tr = R.trs[R.pcRow], wrap = $("#exec-wrap");
    const top = tr.offsetTop, h = wrap.clientHeight;
    if (force || top < wrap.scrollTop + 30 || top > wrap.scrollTop + h - 40) wrap.scrollTop = Math.max(0, top - h / 3);
  }

  // memory ---------------------------------------------------------
  const SEGS = [["data", ".data (static data)"], ["gp", "$gp (global pointer)"], ["sp", "$sp (stack)"], ["heap", "heap"],
    ["extern", ".extern"], ["text", ".text (code)"], ["kdata", ".kdata"], ["ktext", ".ktext"], ["mmio", "MMIO"]];
  const SEG_DEF = { data: 0x10010000, extern: 0x10000000, heap: 0x10040000, text: 0x00400000, kdata: 0x90000000, ktext: 0x80000000, mmio: 0xffff0000, gp: 0x10008000, sp: 0x7fffeffc };
  const MEM_PTRS = [[29, "$sp"], [30, "$fp"], [28, "$gp"], [4, "$a0"], [5, "$a1"]];
  // window of rows currently shown: start address + row count (grows as you scroll)
  R.mem = { start: null, rows: 96, target: null };

  function memLayout() {
    const w = $("#mem-wrap").clientWidth || 800;
    const cell = S.memRadix === "ascii" ? 62 : 96;
    const ascii = S.memRadix === "hex" && w > 520;
    let wpr = 1;
    for (const c of [8, 4, 2, 1]) if (96 + 92 + c * cell + (ascii ? c * 4 * 8.4 + 24 : 0) <= w) { wpr = c; break; }
    return { wpr, ascii };
  }

  function renderMemBar() {
    if ($("#mem-go")) return;   // built once; values update in place
    const dl = `<datalist id="mem-dl">${M.REG_NAMES.map(r => `<option value="${r}">`).join("")}</datalist>`;
    $("#mem-bar").innerHTML = `
      <span class="field"><select id="mem-seg" aria-label="Segment"><option value="">Jump to…</option>${SEGS.map(([k, l]) => `<option value="${k}">${l}</option>`).join("")}</select></span>
      <span class="field grow-field">${icon("search")}<input id="mem-go" list="mem-dl" placeholder="address, label, $reg, msg+4 …" autocapitalize="off" spellcheck="false" enterkeyhint="go"></span>${dl}
      <span class="seg"><button data-r="hex">hex</button><button data-r="dec">dec</button><button data-r="ascii">ascii</button></span>`;
    $("#mem-seg").onchange = (e) => {
      const k = e.target.value;
      e.target.value = "";
      if (!k) return;
      const st = R.state;
      let a;
      if (k === "sp" && st) a = st.gpr[29];
      else if (k === "gp" && st) a = st.gpr[28];
      else a = (R.segments && R.segments[k] != null) ? R.segments[k] : SEG_DEF[k];
      memGoto(a, k !== "sp");
    };
    $("#mem-go").addEventListener("keydown", (e) => {
      if (e.key !== "Enter") return;
      try { memGoto(evalAddr(e.target.value)); e.target.blur(); } catch (err) { toast(err.message, "error"); }
    });
    $("#mem-go").addEventListener("change", (e) => { if ((R.labels || []).some(l => l.name === e.target.value) || REG_INDEX.has(e.target.value)) { try { memGoto(evalAddr(e.target.value)); } catch (err) { } } });
    $$("#mem-bar .seg button").forEach(b => b.onclick = () => { S.memRadix = b.dataset.r; persist(); markRadix(); R.memPrev = new Map(); refreshMemory(); });
    markRadix();
  }
  function markRadix() { $$("#mem-bar .seg button").forEach(b => b.classList.toggle("on", b.dataset.r === S.memRadix)); }
  function updateMemDatalist() {
    const dl = $("#mem-dl");
    if (dl) dl.innerHTML = [...(R.labels || []).filter(l => l.data).map(l => l.name), ...M.REG_NAMES].map(x => `<option value="${esc(x)}">`).join("");
  }

  /** Scroll memory so `addr` is visible (a few rows from the top) and flash it. */
  function memGoto(addr, top = false) {
    navMark();
    const { wpr } = memLayout();
    const rowBytes = wpr * 4;
    const a = addr >>> 0;
    const row = (a - (a % rowBytes)) >>> 0;
    R.mem.start = top ? row : Math.max(0, row - 4 * rowBytes) >>> 0;
    R.mem.rows = 96;
    R.mem.target = a & ~3;
    R.memPrev = new Map();
    R.mem.scrollPending = true;
    if (S.view !== "mem") setView("mem"); else refreshMemory(true);
  }

  let memBusy = false, memAgain = false;
  async function refreshMemory(scrollToTarget = false) {
    if (S.view !== "mem") return;
    if (R.mem.scrollPending) { scrollToTarget = true; R.mem.scrollPending = false; }
    renderMemBar();
    const wrap = $("#mem-wrap");
    if (!R.assembled) { wrap.innerHTML = `<div class="empty">Assemble a program to inspect memory.</div>`; return; }
    if (memBusy) { memAgain = true; return; }
    memBusy = true;
    try {
      const { wpr, ascii } = memLayout();
      const rowBytes = wpr * 4;
      if (R.mem.start == null) R.mem.start = ((R.memBase != null ? R.memBase : (R.segments.data || 0x10010000)) >>> 0);
      R.mem.start = (R.mem.start - (R.mem.start % rowBytes)) >>> 0;
      const rows = R.mem.rows;
      const base = R.mem.start;
      const res = await engine.call("memory", { addr: base | 0, words: wpr * rows });
      const words = res.words;
      const labs = new Map();
      for (const l of R.labels || []) { const a = l.addr >>> 0; if (!labs.has(a)) labs.set(a, []); labs.get(a).push(l.name); }
      const ptrs = new Map();
      if (R.state) for (const [i, n] of MEM_PTRS) { const a = (R.state.gpr[i] >>> 0) & ~3; if (!ptrs.has(a)) ptrs.set(a, []); ptrs.get(a).push(n); }
      let h = `<table class="grid memtable"><thead><tr><th></th><th>Address</th>${Array.from({ length: wpr }, (_, i) => `<th class="num">+${(i * 4).toString(16)}</th>`).join("")}${ascii ? "<th>ASCII</th>" : ""}</tr></thead><tbody>`;
      const prev = R.memPrev, next = new Map();
      for (let r = 0; r < rows; r++) {
        const a = (base + r * rowBytes) >>> 0;
        let tags = "", cells = "", asc = "";
        for (let i = 0; i < wpr; i++) {
          const aa = (a + i * 4) >>> 0, v = words[r * wpr + i] | 0;
          next.set(aa, v);
          if (prev.has(aa) && prev.get(aa) !== v) R.memHeat.set(aa, R.step);
          const mh = R.memHeat.has(aa) ? R.step - R.memHeat.get(aa) : -1;
          const ch = mh >= 0 && mh <= 3;
          const ln = labs.get(aa), pn = ptrs.get(aa);
          if (ln) tags += ln.map(n => `<span class="tag lab">${esc(n)}</span>`).join("");
          if (pn) tags += pn.map(n => `<span class="tag ptr">${n}</span>`).join("");
          const cls = (ch ? heatCls(mh) + " " : v === 0 ? "zero " : "t-number ") + (ln ? "haslab " : "") + (pn ? "hasptr " : "") + (aa === R.mem.target ? "target " : "");
          cells += `<td class="num editable ${cls}" data-a="${aa}" title="${M.hex(aa)}${ln ? " · " + esc(ln.join(", ")) : ""}${pn ? " · " + pn.join(", ") : ""}">${esc(M.fmtWord(v, S.memRadix))}</td>`;
          if (ascii) for (let b = 0; b < 4; b++) { const c = (v >>> (8 * b)) & 255; asc += c >= 32 && c < 127 ? esc(String.fromCharCode(c)) : '<span class="zero">·</span>'; }
        }
        h += `<tr data-row="${a}"><td class="tags">${tags}</td><td class="dim addr">${M.hex(a)}</td>${cells}${ascii ? `<td class="t-string">${asc}</td>` : ""}</tr>`;
      }
      R.memPrev = next;
      const top = wrap.scrollTop;
      wrap.innerHTML = h + "</tbody></table>";
      if (scrollToTarget && R.mem.target != null) {
        const t = $("td.target", wrap);
        wrap.scrollTop = t ? Math.max(0, t.parentElement.offsetTop - 4 * t.parentElement.offsetHeight) : 0;
      } else wrap.scrollTop = top;
      if (R.mem.pendingShift) { wrap.scrollTop += R.mem.pendingShift * (($("tbody tr", wrap) || {}).offsetHeight || 22); R.mem.pendingShift = 0; }
    } catch (e) { /* engine busy */ }
    finally {
      memBusy = false;
      if (memAgain) { memAgain = false; refreshMemory(); }
    }
  }

  // continuous scrolling: grow the window when nearing either end
  let memScrollTimer = null;
  $("#mem-wrap").addEventListener("scroll", () => {
    clearTimeout(memScrollTimer);
    memScrollTimer = setTimeout(() => {
      const w = $("#mem-wrap");
      if (!R.assembled || R.mem.start == null) return;
      const { wpr } = memLayout();
      const rowBytes = wpr * 4, add = 64;
      if (w.scrollTop + w.clientHeight > w.scrollHeight - 300 && R.mem.rows < 2048) {
        R.mem.rows += add;
        refreshMemory();
      } else if (w.scrollTop < 200 && R.mem.start > 0) {
        const n = Math.min(add, Math.floor(R.mem.start / rowBytes));
        if (n > 0) { R.mem.start = (R.mem.start - n * rowBytes) >>> 0; R.mem.rows += n; R.mem.pendingShift = n; refreshMemory(); }
      }
    }, 60);
  }, { passive: true });

  $("#mem-wrap").addEventListener("click", (e) => {
    const td = e.target.closest("td.editable");
    if (!td) return;
    const a = +td.dataset.a;
    const v = R.memPrev.get(a) || 0;
    const ln = labelAt(a);
    inspect(td, {
      title: M.hex(a), sub: "word" + (ln.length ? " · " + esc(ln.join(", ")) : ""), value: v,
      meaning: window.MipsMeaning ? window.MipsMeaning.memMeaning(a, v, meaningCtx()) : null,
      onSave: async (nv) => {
        try { await engine.call("setmem", { addr: a | 0, value: nv }); refreshMemory(); refreshBitmap(); }
        catch (err) { toast(err.message, "error"); }
      },
    });
  });

  // labels ---------------------------------------------------------
  function renderLabels() {
    const wrap = $("#label-wrap");
    const f = ($("#label-filter").value || "").toLowerCase();
    const list = (R.labels || []).filter(l => !f || l.name.toLowerCase().includes(f)).sort((a, b) => (a.data - b.data) || ((a.addr >>> 0) - (b.addr >>> 0)));
    if (!list.length) { wrap.innerHTML = `<div class="empty">${R.assembled ? "No labels." : "Assemble a program to list its labels."}</div>`; return; }
    wrap.innerHTML = `<table class="grid"><thead><tr><th>Label</th><th>Address</th><th>Segment</th><th>File</th></tr></thead><tbody>` +
      list.map((l, i) => `<tr data-a="${l.addr}" data-d="${l.data ? 1 : 0}" style="cursor:pointer"><td class="t-label">${esc(l.name)}</td><td class="dim">${M.hex(l.addr)}</td>
        <td class="${l.data ? "t-directive" : "t-instr"}">${l.data ? ".data" : ".text"}</td><td class="dim">${esc(l.file === "(global)" ? "global" : l.file)}</td></tr>`).join("") + "</tbody></table>";
  }
  $("#label-filter").addEventListener("input", renderLabels);
  $("#label-wrap").addEventListener("click", (e) => {
    const tr = e.target.closest("tr[data-a]");
    if (!tr) return;
    const a = +tr.dataset.a;
    if (tr.dataset.d === "1") memGoto(a);
    else {
      setView("exec");
      const i = R.addrIdx.get(a);
      if (i !== undefined && R.trs) { R.trs.forEach(t => t.classList.remove("cursor")); R.trs[i].classList.add("cursor"); R.trs[i].scrollIntoView({ block: "center" }); }
    }
  });

  // tools ---------------------------------------------------------
  function renderTools() {
    const body = $("#tool-body");
    if (R.toolTab === "bitmap") {
      const b = S.bitmap;
      const opt = (vals, cur) => vals.map(v => `<option ${v == cur ? "selected" : ""}>${v}</option>`).join("");
      body.innerHTML = `<div class="toolbar">
        <span class="field">unit w<select data-k="uw">${opt([1, 2, 4, 8, 16, 32], b.uw)}</select></span>
        <span class="field">unit h<select data-k="uh">${opt([1, 2, 4, 8, 16, 32], b.uh)}</select></span>
        <span class="field">width<select data-k="w">${opt([64, 128, 256, 512, 1024], b.w)}</select></span>
        <span class="field">height<select data-k="h">${opt([64, 128, 256, 512, 1024], b.h)}</select></span>
        <span class="field">base<select data-k="base">${[["data", "0x10010000 (static data)"], ["gp", "$gp"], ["extern", "0x10000000 (global)"], ["heap", "0x10040000 (heap)"], ["mmio", "0xffff0000 (MMIO)"]]
          .map(([k, l]) => `<option value="${k}" ${b.base === k ? "selected" : ""}>${l}</option>`).join("")}</select></span>
        <span class="grow"></span><span class="dim" style="font-size:12px;color:var(--muted)">${b.w / b.uw}×${b.h / b.uh} px · live</span></div>
        <div class="bitmap-wrap"><canvas class="bitmap" id="bitmap"></canvas></div>`;
      $$("select[data-k]", body).forEach(s => s.onchange = () => { const k = s.dataset.k; b[k] = k === "base" ? s.value : +s.value; persist(); renderTools(); });
      refreshBitmap();
    } else {
      const prevText = $("#mmio-out") ? $("#mmio-out").textContent : (R.mmioText || "");
      body.innerHTML = `<div class="mmio"><div class="cap">Display — characters the program writes to 0xffff000c (transmitter data)</div>
        <pre id="mmio-out" class="scroll"></pre>
        <div class="cap">Keyboard — type here; each key goes to 0xffff0004 and sets the ready bit in 0xffff0000</div>
        <div class="kbd"><input id="mmio-in" placeholder="Tap here and type…" autocapitalize="off" autocomplete="off" spellcheck="false"></div></div>`;
      $("#mmio-out").textContent = prevText;
      const inp = $("#mmio-in");
      inp.addEventListener("keydown", (e) => {
        const map = { Enter: 10, Tab: 9, Backspace: 8 };
        if (map[e.key] !== undefined) { e.preventDefault(); engine.call("key", { char: map[e.key] }).catch(() => { }); }
      });
      inp.addEventListener("input", (e) => {
        for (const ch of inp.value) engine.call("key", { char: ch.charCodeAt(0) & 255 }).catch(() => { });
        inp.value = "";
      });
    }
  }
  function bitmapBase() {
    const k = S.bitmap.base;
    return ((R.segments && R.segments[k] != null) ? R.segments[k] : SEG_DEF[k]) >>> 0;
  }
  let bmBusy = false;
  async function refreshBitmap() {
    const cv = $("#bitmap");
    if (!cv || S.view !== "tools" || R.toolTab !== "bitmap") return;
    const b = S.bitmap, gw = b.w / b.uw, gh = b.h / b.uh;
    if (cv.width !== gw || cv.height !== gh) { cv.width = gw; cv.height = gh; }
    const wrap = cv.parentElement;
    const scale = Math.max(1, Math.min((wrap.clientWidth - 20) / gw, (wrap.clientHeight - 20) / gh));
    cv.style.width = Math.floor(gw * scale) + "px";
    cv.style.height = Math.floor(gh * scale) + "px";
    if (!R.assembled || bmBusy) return;
    bmBusy = true;
    try {
      const res = await engine.call("memory", { addr: bitmapBase() | 0, words: gw * gh });
      const ctx = cv.getContext("2d");
      const img = ctx.createImageData(gw, gh);
      const d = img.data, w = res.words;
      for (let i = 0; i < gw * gh; i++) {
        const v = w[i] | 0;
        d[i * 4] = (v >> 16) & 255; d[i * 4 + 1] = (v >> 8) & 255; d[i * 4 + 2] = v & 255; d[i * 4 + 3] = 255;
      }
      ctx.putImageData(img, 0, 0);
    } catch (e) { } finally { bmBusy = false; }
  }

  // help ---------------------------------------------------------
  function renderHelp() {
    const el = $("#help-list");
    const f = ($("#help-filter").value || "").toLowerCase();
    $("#help-search").classList.toggle("hidden", ["keys", "about"].includes(R.helpTab));
    if (R.helpTab === "card") {
      el.innerHTML = renderCard(f);
      return;
    }
    const match = (...xs) => !f || xs.some(x => String(x).toLowerCase().includes(f));
    let h = "";
    if (R.helpTab === "instr" || R.helpTab === "pseudo") {
      const pseudo = R.helpTab === "pseudo";
      let n = 0;
      for (const name of M.ISA.names) for (const it of M.ISA.instructions.get(name)) {
        if (it.pseudo !== pseudo || !match(it.format, it.desc)) continue;
        if (++n > 700) break;
        h += `<div class="hitem"><div class="f">${M.highlight(it.format)}</div><div class="d">${esc(it.desc)}</div></div>`;
      }
      if (!n) h = `<div class="empty">${M.ISA.names.length ? "No match." : "Connecting to the engine…"}</div>`;
    } else if (R.helpTab === "dirs") {
      for (const [d, desc] of M.ISA.directives) if (match(d, desc)) h += `<div class="hitem"><div class="f t-directive">${esc(d)}</div><div class="d">${esc(desc)}</div></div>`;
    } else if (R.helpTab === "sys") {
      h += `<div class="hitem"><div class="d">Put the service number in <span class="t-register">$v0</span>, arguments in <span class="t-register">$a0</span>–<span class="t-register">$a3</span> / <span class="t-fpreg">$f12</span>, then <span class="t-instr">syscall</span>.</div></div>`;
      for (const [n, name, args, res] of M.SYSCALLS) if (match(n, name, args, res))
        h += `<div class="hitem"><div class="f"><span class="t-number">${n}</span> &nbsp;<b>${esc(name)}</b></div><div class="d">${args ? "in: " + M.highlight(args) : ""}${args && res ? " &nbsp;·&nbsp; " : ""}${res ? "out: " + M.highlight(res) : ""}</div></div>`;
    } else if (R.helpTab === "keys") {
      const keys = [["F3 · Ctrl+Shift+A", "Assemble (saves first)"], ["F5", "Run / continue — pauses while running"], ["F7", "Step one instruction"],
        ["F8", "Step back (undo)"], ["F9", "Pause"], ["F11", "Stop"], ["F12", "Reset"], ["Ctrl+S", "Save"], ["Ctrl+/", "Toggle comment"],
        ["Tab / Shift+Tab", "Indent / dedent (or accept completion)"], ["Ctrl+Space", "Show completions"], ["Ctrl+B", "Toggle file sidebar"],
        ["Alt+1…6", "Switch view"], ["Ctrl+J / Esc", "Show / hide console & registers while editing"], ["F10", "Zen mode (only code, fullscreen)"], ["Alt+L", "Line numbers on/off"], ["Ctrl+O · drop files anywhere", "Import files, folders or a .zip"], ["Ctrl+Shift+S", "Download the current file"],
        ["Alt+← / Alt+→ · back gesture · ‹", "Go back / forward to where you were (jumps, views, files)"], ["F1 · tap the hint bar", "Look up the instruction under the cursor on the reference card"], ["Click a register / memory word", "What it means now (syscall, pointer target, string, return address…), all formats, edit"],
        ["Memory go-to box", "0x10010000 · msg · msg+4 · $sp-8 · pc"], ["Click gutter / ●", "Toggle breakpoint"], ["Double-click instruction", "Jump to its source line"]];
      h = keys.map(([k, d]) => `<div class="hitem"><span class="kbdk">${k}</span> &nbsp; <span class="d" style="display:inline">${d}</span></div>`).join("");
    } else {
      h = `<div class="about"><h2>MARS IDE</h2>
        A modern front end for <b>MARS ${esc(R.version || "4.5")}</b> — the MIPS Assembler and Runtime Simulator by Pete Sanderson and Kenneth Vollmar (MIT license,
        <a href="https://dpetersanderson.github.io/" target="_blank" rel="noopener" style="color:var(--primary)">dpetersanderson.github.io</a>).
        The original MARS engine assembles and simulates your code; this UI talks to it over a small JSON protocol, the same one used by the terminal (TUI) version.<br><br>
        Dialog syscalls (50–59) open dialogs here; MIDI syscalls (31, 33) play through your speakers.
        <div style="margin-top:18px;color:var(--muted);font-size:12px">
        Source and issues: <a href="https://github.com/franticplant/mars-ide" target="_blank" rel="noopener" style="color:inherit">github.com/franticplant/mars-ide</a><br>
        Contact: <a href="mailto:franticplant@protonmail.com" style="color:inherit">franticplant@protonmail.com</a></div></div>`;
    }
    el.innerHTML = h;
  }
  $("#help-filter").addEventListener("input", renderHelp);
  $("#help-list").addEventListener("click", (e) => {
    const tr = e.target.closest("tr[data-m]");
    if (!tr) return;
    const enc = $(`tr.encrow[data-for="${tr.dataset.m}"]`, $("#help-list"));
    if (enc) enc.classList.toggle("hidden");
  });

  // ------------------------------------------------------------------ settings
  function openSettings() {
    const themeCards = Object.entries(M.THEMES).map(([k, t]) => `<button class="theme-card ${S.theme === k ? "active" : ""}" data-t="${k}" style="background:${t.ui[1]};color:${t.ui[4]}">
        <div class="sw" style="background:${t.ui[0]}"><span style="color:${t.syn[0]};font-weight:700">addi</span><span style="color:${t.syn[3]}">$t0</span><span style="color:${t.syn[7]}">42</span><span style="color:${t.syn[9]}">#</span></div>
        <div class="nm">${esc(t.name)}</div></button>`).join("");
    const chk = (k, l) => `<label class="check"><input type="checkbox" data-k="${k}" ${S[k] ? "checked" : ""}><span>${l}</span></label>`;
    const body = `
      <div class="set-sec">Theme</div><div class="themes">${themeCards}</div>
      <div class="row"><label>Syntax colours</label><select data-s="syntax"><option value="auto">Match theme</option>${Object.entries(M.THEMES).map(([k, t]) => `<option value="${k}" ${S.syntax === k ? "selected" : ""}>${esc(t.name)}</option>`).join("")}</select></div>
      <div class="row"><label>Editor font size</label><select data-s="fontSize">${[11, 12, 13, 14, 15, 16, 18, 20].map(v => `<option ${S.fontSize == v ? "selected" : ""}>${v}</option>`).join("")}</select></div>
      <div class="set-sec">Layout</div>
      ${chk("statusbar", "Show status bar (instruction hints, cursor position)")}
      ${chk("lineNumbers", "Show line numbers (off: code uses the full width; set breakpoints in Execute) — Alt+L")}
      ${chk("keybarOn", "Show editing key row above the on-screen keyboard")}
      <div class="row"><label>Key row size</label><select data-s="kbSize">${[["s", "Small"], ["m", "Medium"], ["l", "Large"]].map(([v, l]) => `<option value="${v}" ${(S.kbSize || "m") === v ? "selected" : ""}>${l}</option>`).join("")}</select></div>
      <div class="row"><label>Key row lines</label><select data-s="kbRows">${[[1, "One (scrolls sideways)"], [2, "Two (all keys visible)"]].map(([v, l]) => `<option value="${v}" ${(S.kbRows || 1) == v ? "selected" : ""}>${l}</option>`).join("")}</select></div>
      ${chk("side", "Show file sidebar (Ctrl+B)")}
      ${chk("zen", "Zen mode — hide all chrome, only code (F10)")}
      <details class="diag"><summary>Layout diagnostics</summary><pre id="diag"></pre></details>
      <div class="set-sec">Assembler</div>
      ${chk("pseudo", "Permit extended (pseudo) instructions and formats")}
      ${chk("warnings_are_errors", "Assembler warnings are considered errors")}
      ${chk("assemble_all", "Assemble all files in the current file's folder")}
      ${chk("start_at_main", "Initialize program counter to global 'main' if defined")}
      ${chk("autosave", "Save open files automatically before assembling")}
      <div class="set-sec">Simulator</div>
      ${chk("delayed_branching", "Delayed branching")}
      ${chk("self_modifying", "Self-modifying code")}
      ${chk("bare_machine", "Bare machine (no pseudo-instructions or register names)")}
      <div class="row"><label>Memory configuration</label><select data-s="memory_config">${(R.configs.length ? R.configs : [{ id: "Default", name: "Default" }]).map(c => `<option value="${esc(c.id)}" ${S.memory_config === c.id ? "selected" : ""}>${esc(c.name)}</option>`).join("")}</select></div>
      <div class="row"><label>Program arguments</label><input type="text" data-s="program_args" value="${esc(S.program_args)}" placeholder="arg1 arg2"></div>
      <div class="row"><label>Exception handler</label><input type="text" data-s="exception_handler" value="${esc(S.exception_handler)}" placeholder="handler.asm"></div>
      <div class="dim" style="color:var(--muted);font-size:12px;margin-top:8px">Assembler and simulator settings apply on the next assemble.</div>`;
    const m = modal({ title: "Settings", body, buttons: [{ label: "Done", primary: true, value: true }], wide: true });
    const dg = $("#diag", m.el);
    const showDiag = () => {
      const vv = window.visualViewport, r = VK && VK.boundingRect;
      dg.textContent = [
        `window ${window.innerWidth}×${window.innerHeight}  dpr ${window.devicePixelRatio}`,
        `visualViewport ${vv ? `${Math.round(vv.width)}×${Math.round(vv.height)} @${Math.round(vv.offsetTop)}` : "n/a"}`,
        `virtualKeyboard ${VK ? (r ? `top ${Math.round(r.top)} h ${Math.round(r.height)}` : "no rect") : "n/a"}`,
        `app height ${LAYOUT.h} via ${LAYOUT.mode}`,
        `touch ${isTouch()}  coarse ${window.matchMedia("(pointer: coarse)").matches}  maxTouchPoints ${navigator.maxTouchPoints}`,
        `fullscreen ${isFs()}  key row ${S.keybarOn ? "on" : "off"} (${S.kbSize}, ${S.kbRows} row)`,
        `ua ${navigator.userAgent}`,
      ].join("\n");
    };
    showDiag();
    $(".diag", m.el).addEventListener("toggle", showDiag);
    $$(".theme-card", m.el).forEach(c => c.onclick = () => {
      S.theme = c.dataset.t; applyTheme(); persist();
      $$(".theme-card", m.el).forEach(x => x.classList.toggle("active", x === c));
    });
    $$("input[type=checkbox][data-k]", m.el).forEach(c => c.onchange = () => { S[c.dataset.k] = c.checked; persist(); applyTheme(); });
    $$("[data-s]", m.el).forEach(c => c.oninput = c.onchange = () => {
      const k = c.dataset.s;
      S[k] = (k === "fontSize" || k === "kbRows") ? +c.value : c.value;
      persist(); applyTheme();
    });
  }

  function applyTheme() {
    M.applyTheme(S.theme, S.syntax === "auto" ? S.theme : S.syntax);
    document.documentElement.style.setProperty("--ed-fs", (isNarrow() ? Math.min(S.fontSize, 15) : S.fontSize) + "px");
    document.documentElement.style.setProperty("--regs-w", S.regsW + "px");
    document.documentElement.style.setProperty("--console-h", S.consoleH + "%");
    const app = $("#app");
    app.classList.toggle("no-side", !S.side);
    app.classList.toggle("zen", !!S.zen);
    app.classList.toggle("no-status", !S.statusbar);
    app.classList.toggle("no-lines", !S.lineNumbers);
    app.classList.toggle("no-keybar", !S.keybarOn);
    app.dataset.kb = S.kbSize || "m";
    app.classList.toggle("kb2", S.kbRows === 2);
    requestAnimationFrame(() => { if (typeof updateKbFade === "function") updateKbFade(); });
    setTimeout(() => ed.measure(), 0);
  }

  // ------------------------------------------------------------------ splitters
  function splitter(el, onMove) {
    el.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      el.setPointerCapture(e.pointerId);
      el.classList.add("dragging");
      const move = (ev) => onMove(ev);
      const up = () => { el.classList.remove("dragging"); el.removeEventListener("pointermove", move); el.removeEventListener("pointerup", up); persist(); ed.measure(); };
      el.addEventListener("pointermove", move);
      el.addEventListener("pointerup", up);
    });
  }
  splitter($("#split-v"), (e) => { S.regsW = Math.max(220, Math.min(window.innerWidth * 0.5, window.innerWidth - e.clientX)); applyTheme(); });
  splitter($("#split-h"), (e) => {
    const c = $(".center").getBoundingClientRect();
    S.consoleH = Math.max(12, Math.min(75, ((c.bottom - e.clientY) / c.height) * 100));
    applyTheme();
  });

  // ------------------------------------------------------------------ audio for MIDI syscalls
  let audio = null;
  function tone(ev) {
    try {
      audio = audio || new (window.AudioContext || window.webkitAudioContext)();
      const t = audio.currentTime, dur = Math.max(0.03, (ev.duration || 500) / 1000);
      const o = audio.createOscillator(), g = audio.createGain();
      const inst = ev.instrument || 0;
      o.type = inst < 8 ? "triangle" : inst < 32 ? "sine" : inst < 64 ? "sawtooth" : "square";
      o.frequency.value = 440 * Math.pow(2, ((ev.pitch || 60) - 69) / 12);
      const vol = Math.max(0, Math.min(1, (ev.volume == null ? 100 : ev.volume) / 127)) * 0.25;
      g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vol, t + 0.01);
      g.gain.setValueAtTime(vol, t + dur * 0.8); g.gain.linearRampToValueAtTime(0, t + dur);
      o.connect(g).connect(audio.destination); o.start(t); o.stop(t + dur + 0.02);
    } catch (e) { }
  }

  // ------------------------------------------------------------------ engine events
  function showDialog(ev) {
    const input = ["int", "float", "double", "string"].includes(ev.kind);
    let buttons;
    if (ev.kind === "confirm") buttons = [{ label: "Cancel", value: "2" }, { label: "No", value: "1" }, { label: "Yes", primary: true, value: "0" }];
    else if (input) buttons = [{ label: "Cancel", value: null }, { label: "OK", primary: true, get: bg => $("input", bg).value }];
    else buttons = [{ label: "OK", primary: true, value: "" }];
    const icons = { 0: "✗ ", 1: "ℹ ", 2: "⚠ ", 3: "? " };
    modal({
      title: ev.kind === "message" ? (icons[ev.type] || "") + "Message" : "Program asks",
      body: `<div class="msgtext">${esc(ev.message || "")}</div>${input ? `<input class="text" placeholder="${ev.kind} value" inputmode="${ev.kind === "string" ? "text" : "decimal"}" autocapitalize="off" autocomplete="off">` : ""}`,
      buttons,
      onClose: (v) => engine.call("dialog_reply", { token: ev.token, value: v === undefined ? null : (ev.kind === "confirm" && v === null ? "2" : v) }).catch(() => { }),
    });
  }

  let pollTimer = null;
  function onEvent(ev) {
    switch (ev.ev) {
      case "connected":
        $("#conn").classList.remove("off");
        $("#conn").textContent = engine.native ? "engine" : "engine";
        const b = $(".conn-banner"); if (b) b.remove();
        hello();
        break;
      case "disconnected":
        $("#conn").classList.add("off");
        if (!$(".conn-banner")) { const d = document.createElement("div"); d.className = "conn-banner"; d.textContent = "Reconnecting to the engine…"; document.body.appendChild(d); }
        renderRunbar();
        break;
      case "unauthorized":
        modal({ title: "Access token required", body: `<div class="msgtext">Open the link printed by the server (it contains <span class="kbdk">?token=…</span>) once in this browser.</div>` });
        break;
      case "replay_begin": out.textContent = ""; outLen = 0; break;
      case "replay_end": break;
      case "out": consoleWrite(ev.text, ev.stream === "stderr" ? "stderr" : ""); if (isNarrow() && S.m !== "io" && !R.unread.has("io")) { R.unread.add("io"); renderBottomNav(); } break;
      case "input_request": setWaiting(ev.kind); break;
      case "dialog": showDialog(ev); break;
      case "tone": tone(ev); break;
      case "tick": tickPending = ev.state; scheduleFrame(); break;
      case "mmio_out": {
        const c = ev.char;
        const o = $("#mmio-out");
        if (o) { if (c === 12) o.textContent = ""; else { o.textContent += String.fromCharCode(c); o.scrollTop = o.scrollHeight; } }
        if (S.view !== "tools") { R.unread.add("tools"); renderTabs(); }
        break;
      }
      case "stopped": {
        R.running = false; tickPending = null;
        setWaiting(null);
        const r = ev.reason;
        if (r === "exit" || r === "error" || r === "stopped") finished(r, ev.errors);
        else if (r === "breakpoint") { toast(`Breakpoint at ${M.hex(ev.state.pc)}`, "warn", 2200); if (!isNarrow() && S.view !== "edit") setView("exec"); }
        else if (r === "paused") toast("Paused", "", 1200);
        applyState(ev.state, true);
        if (!engine.local && R.fs) refreshTree();     // file syscalls may have written to the workspace
        break;
      }
      case "fs_changed": {                             // static build: files the program wrote were saved
        refreshTree();
        for (const p of ev.paths || []) {
          const f = R.files.get(p);
          if (f && f.text === f.saved) {               // reload open, unmodified files
            engine.call("fs_read", { path: p }).then(rr => {
              f.text = f.saved = rr.text;
              if (p === S.current) ed.value = rr.text;
            }).catch(() => { });
          }
        }
        break;
      }
    }
  }

  async function hello() {
    try {
      const h = await engine.call("hello");
      R.version = h.version; R.fs = !!h.fs;
      if (!M.ISA.names.length) {
        const isa = await engine.call("isa");
        M.ISA.load(isa);
        ed.render(true);
      }
      try { R.configs = (await engine.call("configs")).configs; } catch (e) { }
      await refreshTree();
      // restore files
      if (!R.files.size) {
        const want = S.open.slice();
        S.open = [];
        for (const p of want) await openFile(p, { focus: false });
        if (!S.open.length) {
          const first = R.tree.find(n => !n.dir && /\.(asm|s)$/i.test(n.name));
          if (first) await openFile(first.path, { focus: false });
        }
        const cur = S.open.includes(S.current) ? S.current : S.open[0];
        if (cur) switchFile(cur);
      }
      // restore a program that is already loaded in the engine (page reload / second tab)
      if (h.assembled && !R.assembled) {
        const p = await engine.call("program");
        if (p.text) { loadProgram(p); R.assembled = true; }
      }
      if (h.state) { R.running = !!h.state.running; R.finished = !!h.state.finished; applyState(h.state, true); }
      if (h.waiting_input) setWaiting("input");
      if (h.speed !== undefined && h.speed !== S.speed) engine.call("speed", { value: S.speed }).catch(() => { });
      renderHelp(); renderRunbar(); updateHint();
    } catch (e) {
      toast("Engine: " + e.message, "error");
    } finally {
      NAV.ready = true;      // start recording navigation only after the initial restore
    }
  }

  // draw state updates at most once per frame, and only when there is something to draw (no idle frames)
  let framePending = false;
  function scheduleFrame() {
    if (framePending) return;
    framePending = true;
    requestAnimationFrame(() => {
      framePending = false;
      if (tickPending) { const st = tickPending; tickPending = null; applyState(st, true); }
    });
  }


  async function poll() {
    if (R.running && engine.connected) {
      if (!S.speed) {
        try { const s = await engine.call("state", {}, 5000); if (R.running) { R.state = Object.assign({}, R.state, { count: s.state.count, pc: s.state.pc }); renderRunbar(); } } catch (e) { }
      }
      if (S.view === "tools") refreshBitmap();
      else if (S.view === "mem") refreshMemory();
    }
  }

  // ------------------------------------------------------------------ keys
  document.addEventListener("keydown", (e) => {
    if (e.key === "F10") { e.preventDefault(); if (!$(".modal-bg")) setZen(!S.zen); return; }
    if (e.key === "F1") {
      e.preventDefault();
      const mn = S.view === "edit" && R.cursor ? M.mnemonicOf(R.cursor.text) : null;
      lookup(mn && mn.type === "instr" ? mn.name : "");
      return;
    }
    if ($(".modal-bg")) return;
    const mod = e.ctrlKey || e.metaKey;
    const map = { F3: "assemble", F5: "run", F7: "step", F8: "back", F9: "pause", F11: "stop", F12: "reset" };
    if (map[e.key]) { e.preventDefault(); ACT[map[e.key]](); return; }
    if (mod && e.shiftKey && e.key.toLowerCase() === "s") { e.preventDefault(); exportFile(); return; }
    if (mod && e.key.toLowerCase() === "s") { e.preventDefault(); saveCurrent(); return; }
    if (mod && e.key.toLowerCase() === "o") { e.preventDefault(); pickFiles(); return; }
    if (mod && e.shiftKey && e.key.toLowerCase() === "a") { e.preventDefault(); ACT.assemble(); return; }
    if (mod && e.key.toLowerCase() === "j") { e.preventDefault(); showPanels(!S.panels); return; }
    if (e.key === "Escape" && S.zen) { setZen(false); return; }
    if (e.key === "Escape" && document.activeElement === ed.ta && $(".ed-complete").hidden && S.panels && S.view === "edit") { showPanels(false); return; }
    if (mod && e.key.toLowerCase() === "b") { e.preventDefault(); S.side = !S.side; applyTheme(); persist(); return; }
    if (e.altKey && e.key === "ArrowLeft") { e.preventDefault(); history.back(); return; }
    if (e.altKey && e.key === "ArrowRight") { e.preventDefault(); history.forward(); return; }
    if (e.altKey && e.key.toLowerCase() === "l") { e.preventDefault(); S.lineNumbers = !S.lineNumbers; persist(); applyTheme(); return; }
    if (e.altKey && /^[1-6]$/.test(e.key)) { e.preventDefault(); setView(VIEWS[+e.key - 1][0]); return; }
    if (e.key === "Enter" && mod) { e.preventDefault(); ACT.run(); }
  });

  // ------------------------------------------------------------------ boot
  $("#btn-side").onclick = () => { if (isNarrow()) { S.m = S.m === "files" ? "edit" : "files"; $("#app").dataset.m = S.m; renderBottomNav(); refreshTree(); } else { S.side = !S.side; applyTheme(); persist(); } };
  $("#btn-settings").onclick = openSettings;
  $("#btn-back").onclick = () => history.back();
  $("#btn-panels").onclick = () => showPanels(!S.panels);
  $("#btn-zen").onclick = () => setZen(true);
  $("#btn-fs").onclick = () => setFullscreen(!isFs());
  $("#zen-exit").onclick = () => setZen(false);
  ed.ta.addEventListener("focus", () => { $("#app").classList.add("typing"); $("#keybar").classList.toggle("show", isTouch() || !!S.kbDesktop); setTimeout(fitViewport, 250); });
  ed.ta.addEventListener("blur", () => setTimeout(() => { if (document.activeElement !== ed.ta) $("#app").classList.remove("typing"); }, 120));
  $("#btn-newfile").onclick = () => newFile();
  $("#btn-newdir").onclick = newDir;
  $("#btn-refresh").onclick = refreshTree;
  $("#btn-import").onclick = () => pickFiles();
  $("#btn-export").onclick = () => exportWorkspace();
  let resizeT = null;
  window.addEventListener("resize", () => {
    clearTimeout(resizeT);
    resizeT = setTimeout(() => { renderRegs(); if (S.view === "tools") refreshBitmap(); if (S.view === "mem") refreshMemory(); closeInspector(); }, 120);
  });
  window.matchMedia("(max-width: 899px)").addEventListener("change", () => { setView(S.view); applyTheme(); renderRegs(); updateFocus(); });
  window.addEventListener("beforeunload", (e) => { if (S.open.some(isDirty)) saveDraftSoon(); });

  applyTheme();
  renderChrome();
  fitViewport();
  showIoTab();
  renderMessages();
  if (isNarrow() && !["edit", "exec", "mem", "labels", "tools", "help", "regs", "io"].includes(S.m)) S.m = "edit";
  if (isNarrow() && ["regs", "io"].includes(S.m)) { setView("edit"); setM(S.m); } else setView(isNarrow() ? (["regs", "io"].includes(S.m) ? "edit" : S.m) : S.view);
  renderRegs();
  history.replaceState({ mars: 1, root: true }, "");
  history.pushState({ mars: 1, navI: 0 }, "");
  updateBackBtn();
  engine.on(onEvent);
  engine.start();
  setInterval(poll, 300);
  window.MarsIDE = { S, R, engine, ACT };   // handy for debugging
})();
