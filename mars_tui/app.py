"""MARS TUI — a terminal IDE for MIPS built on the real MARS 4.5 engine."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from rich.console import Group
from rich.padding import Padding
from rich.style import Style
from rich.text import Text
from textual import events, on, work
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.theme import Theme
from textual.widgets import ContentSwitcher, Input, Log, OptionList, Static
from textual.widgets.option_list import Option

from . import mips

CARD = json.loads((Path(__file__).with_name("refcard.json")).read_text(encoding="utf-8"))
CARD_BY = {i["m"]: i for i in CARD["instructions"]}
from .bridge import Bridge, BridgeError
from .editor import PALETTES, SYNTAX_THEMES, MipsEditor, highlight_text, syntax_for_ui
from .mips import ISA_DB, REG_NAMES, SYSCALLS, as_double, as_float, fmt_float, hex32, s32, u32
from .screens import DialogScreen, OpenScreen, PromptScreen, SettingsScreen
from .widgets import Bar, BitmapView, ConsoleHighlighter, KeyCapture, Table

# --------------------------------------------------------------------------- themes

CUSTOM_THEMES = [
    Theme(
        name="amoled", dark=True,
        primary="#3d8bff", secondary="#9b6bff", accent="#ffb02e", warning="#ffd24d", error="#ff3b5c", success="#2ee67a",
        foreground="#e6e6e6", background="#000000", surface="#000000", panel="#0b0b0b", boost="#ffffff0d",
        variables={"block-cursor-background": "#3d8bff", "footer-background": "#000000", "scrollbar": "#1a1a1a",
                   "scrollbar-background": "#000000", "input-selection-background": "#3d8bff55"},
    ),
    Theme(
        name="mars-midnight", dark=True,
        primary="#5b8cff", secondary="#a37cff", accent="#ffb454", warning="#ffcc66", error="#ff5f6d", success="#57d9a3",
        foreground="#d7def0", background="#0d1220", surface="#121829", panel="#182036",
    ),
    Theme(
        name="mars-classic", dark=False,
        primary="#2f5fbf", secondary="#6b4fbf", accent="#c05a00", warning="#b07800", error="#c62828", success="#2e7d32",
        foreground="#1b1b1b", background="#eef0f3", surface="#ffffff", panel="#dde2ea",
    ),
]

DEFAULTS: dict = {
    "pseudo": True, "delayed_branching": False, "self_modifying": False, "warnings_are_errors": False,
    "start_at_main": False, "bare_machine": False, "assemble_all": False, "auto_save": True,
    "exception_handler": "", "program_args": "", "memory_config": "Default",
    "ui_theme": "tokyo-night", "syntax_theme": "auto", "speed": 0,
    "mem_radix": "hex", "show_code": True,
    "bitmap": {"unit": 8, "w": 512, "h": 256, "base": "data"},
    "open_files": [],
    "show_status": True, "line_numbers": True, "zen": False, "panels": False,
}

SPEEDS = [0, 1000, 100, 30, 10, 5, 2, 1]  # instructions/second; 0 = max
VIEWS = [("edit", "Edit"), ("code", "Code"), ("regs", "Regs"), ("mem", "Mem"), ("io", "I/O"),
         ("labels", "Labels"), ("tools", "Tools"), ("help", "Help")]
MAIN_VIEWS = {"edit", "code", "mem", "labels", "tools", "help"}

TEMPLATE = """# {name}
        .data
msg:    .asciiz "Hello, MIPS!\\n"

        .text
        .globl main
main:
        li   $v0, 4          # print string
        la   $a0, msg
        syscall

        li   $v0, 10         # exit
        syscall
"""


def config_dir() -> Path:
    d = os.environ.get("MARS_TUI_CONFIG")
    if d:
        return Path(d)
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "mars-tui"


def rel(path: str | None) -> str:
    if not path:
        return "untitled"
    try:
        return os.path.relpath(path)
    except ValueError:
        return path


# --------------------------------------------------------------------------- app


class MarsApp(App):
    TITLE = "MARS TUI"
    CSS_PATH = "app.tcss"
    ENABLE_COMMAND_PALETTE = True

    BINDINGS = [
        Binding("f3,ctrl+b", "assemble", "Assemble", priority=True),
        Binding("f5,ctrl+r", "run", "Run/Pause", priority=True),
        Binding("f7,ctrl+t", "step", "Step", priority=True),
        Binding("f8,ctrl+g", "backstep", "Back", priority=True),
        Binding("f9", "pause", "Pause", priority=True),
        Binding("f11", "stop", "Stop", priority=True),
        Binding("f12,ctrl+l", "reset", "Reset", priority=True),
        Binding("f1", "lookup", "Help / look up", priority=True),
        Binding("f2", "settings", "Settings", priority=True),
        Binding("ctrl+s", "save", "Save", priority=True),
        Binding("ctrl+o", "open", "Open", priority=True),
        Binding("ctrl+n", "new", "New", priority=True),
        *[Binding(f"alt+{i + 1}", f"view('{v}')", show=False, priority=True) for i, (v, _) in enumerate(VIEWS)],
        Binding("ctrl+j", "toggle_panels", "Panels", priority=True),
        Binding("alt+left", "nav_back", "Back", priority=True),
        Binding("alt+right", "nav_forward", "Forward", priority=True),
        Binding("f10", "toggle_zen", "Zen", priority=True),
        Binding("alt+l", "toggle_setting('line_numbers')", "Line numbers", priority=True),
        Binding("f4,ctrl+e", "menu", "Menu", priority=True),
        Binding("escape", "escape", show=False),
        Binding("ctrl+pageup", "cycle_view('prev')", show=False, priority=True),
        Binding("ctrl+pagedown", "cycle_view('next')", show=False, priority=True),
    ]

    def __init__(self, files: list[str] | None = None) -> None:
        super().__init__()
        for t in CUSTOM_THEMES:
            self.register_theme(t)
        self.cfg_path = config_dir() / "settings.json"
        self.settings = self._load_settings()
        self.cli_files = files or []
        self.bridge = Bridge(self._on_bridge_event)
        self.view = "edit"
        self.narrow = False
        self.state: dict = {}
        self.prev_state: dict = {}
        self.assembled = False
        self.running = False
        self.finished = False
        self.waiting_input = False
        self.text_rows: list[dict] = []
        self.addr_index: dict[int, int] = {}
        self.labels: list[dict] = []
        self.segments: dict = {}
        self.configs: list[dict] = []
        self.breakpoints: set[tuple[str, int]] = set()
        self.pc_row: int | None = None
        self.mem_base: int | None = None
        self.mem_prev: dict[int, int] = {}
        self.unread: set[str] = set()
        self.flash_text: Text | None = None
        self.flash_until = 0.0
        self.editors: list[MipsEditor] = []
        self.ed_counter = 0
        self.regs_tab = "gpr"
        self.io_tab = "run"
        self.tools_tab = "bitmap"
        self.help_tab = "card"
        self.syntax = "tokyo-night"
        self._tick_state: dict | None = None
        self._dirty: set[str] = set()
        self.messages: list[dict] = []

    # ------------------------------------------------------------------ settings
    def _load_settings(self) -> dict:
        s = json.loads(json.dumps(DEFAULTS))
        try:
            s.update(json.loads(self.cfg_path.read_text()))
        except Exception:
            pass
        return s

    def save_settings(self) -> None:
        self.settings["open_files"] = [e.path for e in self.editors if e.path]
        try:
            self.cfg_path.parent.mkdir(parents=True, exist_ok=True)
            self.cfg_path.write_text(json.dumps(self.settings, indent=2))
        except Exception:
            pass

    # ------------------------------------------------------------------ layout
    def compose(self) -> ComposeResult:
        yield Bar(id="tabs")
        with Horizontal(id="body"):
            with ContentSwitcher(initial="edit", id="main"):
                with Vertical(id="edit"):
                    yield ContentSwitcher(id="editors")
                with Vertical(id="code"):
                    yield Table(id="code-table", cursor_type="row")
                with Vertical(id="mem"):
                    yield Bar(id="membar", classes="sub")
                    yield Table(id="mem-table", cursor_type="cell", rows_only=False)
                with Vertical(id="labels"):
                    yield Table(id="label-table", cursor_type="row")
                with Vertical(id="tools"):
                    yield Bar(id="toolbar", classes="sub")
                    with ContentSwitcher(initial="bitmap", id="tool-switch"):
                        with Vertical(id="bitmap"):
                            yield Bar(id="bmbar", classes="sub2")
                            yield BitmapView(id="bitmap-view")
                        with Vertical(id="mmio"):
                            yield Static("Display (writes to 0xffff000c)", classes="caption")
                            yield Log(id="mmio-log", max_lines=2000)
                            yield KeyCapture("⌨  Keyboard — tap/focus here and type; keys go to 0xffff0004 "
                                             "(ready bit in 0xffff0000)", id="keycap")
                with Vertical(id="help"):
                    yield Bar(id="helpbar", classes="sub")
                    yield Input(placeholder="filter… (e.g. add, syscall, .word)", id="help-filter")
                    yield OptionList(id="help-list")
            with Vertical(id="side"):
                yield Bar(id="regbar", classes="sub")
                with ContentSwitcher(initial="gpr", id="reg-switch"):
                    yield Table(id="gpr", cursor_type="row")
                    yield Table(id="fpr", cursor_type="row")
                    yield Table(id="cp0", cursor_type="row")
        with Vertical(id="bottom"):
            yield Bar(id="iobar", classes="sub")
            with ContentSwitcher(initial="run-io", id="io-switch"):
                with Vertical(id="run-io"):
                    yield Log(id="console", max_lines=5000, highlight=True)
                    yield Input(placeholder="program input ⏎", id="stdin")
                yield OptionList(id="messages")
        with Horizontal(id="status"):
            yield Static("", id="hint")
            yield Static("", id="pos")

    async def on_mount(self) -> None:
        self.theme = self.settings.get("ui_theme", "tokyo-night") if self.settings.get("ui_theme") in self.available_themes else "tokyo-night"
        self.query_one("#console", Log).highlighter = ConsoleHighlighter()
        self._apply_layout(self.size.width, self.size.height)
        self._setup_reg_tables()
        self._setup_label_table()
        self.render_bars()
        self.flash("Starting MARS engine…")
        self.start_engine()
        # open files
        files = [f for f in self.cli_files]
        if not files:
            files = [f for f in self.settings.get("open_files", []) if f and Path(f).exists()]
        for f in files:
            p = Path(f)
            if p.is_dir():
                for q in sorted(p.glob("*.asm")) + sorted(p.glob("*.s")):
                    self.open_file(str(q))
            else:
                self.open_file(str(p))
        if not self.editors:
            self.new_buffer()
        self.set_interval(0.07, self._ui_tick)

    @work(exclusive=True, group="engine")
    async def start_engine(self) -> None:
        try:
            await self.bridge.start()
            isa = await self.bridge.call("isa")
            ISA_DB.load(isa)
            for e in self.editors:
                e._line_cache_hl.clear()
                e._build_highlight_map()
                e.refresh()
            cfg = await self.bridge.call("configs")
            self.configs = cfg.get("configs", [])
            self.flash(f"MARS {self.bridge.version} engine ready · {len(ISA_DB.instructions)} mnemonics · "
                       "F3 assemble, F5 run, F7 step, ctrl+p commands", "ok")
            self.populate_help()
        except Exception as e:  # noqa: BLE001
            self.flash(f"Could not start MARS engine: {e}", "error")

    _closing = False

    async def on_unmount(self) -> None:
        self._closing = True
        self.save_settings()
        await self.bridge.close()

    def on_resize(self, event: events.Resize) -> None:
        self._apply_layout(event.size.width, event.size.height)

    def _apply_layout(self, w: int, h: int) -> None:
        narrow = w < 100 or h < 18
        changed = narrow != self.narrow
        self.narrow = narrow
        scr = self.screen
        scr.set_class(narrow, "-narrow")
        scr.set_class(not narrow, "-wide")
        if changed:
            if not narrow and self.view in ("regs", "io"):
                self.set_view("code" if self.assembled else "edit")
            self.render_bars()
            if self.text_rows:
                self.build_code_table()
        self._set_view_classes()
        self.call_after_refresh(self.refresh_memory)

    def _set_view_classes(self) -> None:
        scr = self.screen
        for v, _ in VIEWS:
            scr.set_class(self.view == v, f"-view-{v}")
        st = self.settings
        # focus mode: while editing, the registers and console step aside unless asked for
        scr.set_class(self.view == "edit" and not st.get("panels"), "-focus")
        scr.set_class(bool(st.get("zen")), "-zen")
        scr.set_class(not st.get("show_status", True), "-nostatus")
        for e in self.editors:
            e.show_line_numbers = bool(st.get("line_numbers", True))

    def show_panels(self, on: bool = True) -> None:
        if bool(self.settings.get("panels")) != on:
            self.settings["panels"] = on
            self._set_view_classes()
            if on:
                self.refresh_regs()

    def action_toggle_panels(self) -> None:
        self.show_panels(not self.settings.get("panels"))
        self.flash("Registers & console " + ("shown" if self.settings["panels"] else "hidden — ctrl+j brings them back"), "info", 3)

    def action_toggle_zen(self) -> None:
        self.settings["zen"] = not self.settings.get("zen")
        self._set_view_classes()
        if self.settings["zen"]:
            self.notify("Zen mode: only code. F10 or Esc to exit.", timeout=3)
        self.save_settings()

    def action_escape(self) -> None:
        if self.view == "help" and self._nav_back:
            self.action_nav_back()
        elif self.settings.get("zen"):
            self.action_toggle_zen()
        elif self.view == "edit" and self.settings.get("panels"):
            self.show_panels(False)

    def action_toggle_setting(self, key: str) -> None:
        self.settings[key] = not self.settings.get(key, True)
        self._set_view_classes()
        self.save_settings()

    # ------------------------------------------------------------------ theme
    def watch_theme(self, theme: str) -> None:
        self.settings["ui_theme"] = theme
        self.set_syntax_theme(self.settings.get("syntax_theme", "auto"))

    def set_syntax_theme(self, name: str) -> None:
        self.settings["syntax_theme"] = name
        if name == "auto" or name not in PALETTES:
            dark = self.current_theme.dark if self.current_theme else True
            name = syntax_for_ui(self.theme, dark)
        self.syntax = name
        for e in self.editors:
            e.theme = f"mips-{name}"
        t = self.current_theme
        if t:
            hl = Style(color=t.background or "#000000", bgcolor=t.accent or "#ffb02e", bold=True)
            self.changed_style = hl
            self.query_one("#console", Log).highlighter = ConsoleHighlighter({
                "meta": Style(color=t.secondary or "#888888", italic=True),
                "error": Style(color=t.error or "red", bold=True),
                "warn": Style(color=t.warning or "yellow"),
                "info": Style(color=t.primary or "cyan"),
            })
        if self.is_mounted:
            if self.text_rows:
                self.build_code_table()
            self.refresh_regs()
            self.populate_help()

    changed_style = Style(bold=True, reverse=True)

    # ------------------------------------------------------------------ bars
    def render_bars(self) -> None:
        if not self.is_mounted:
            return
        n = self.narrow
        w = self.size.width
        ed = self.current_editor()
        fname = (Path(ed.path).name if ed and ed.path else "untitled") + ("●" if ed and ed.modified else "")
        sp = self.settings.get("speed", 0)
        sp_label = "max" if sp == 0 else f"{sp}/s"
        can_back = bool(self.state.get("can_backstep")) and not self.running
        run = ("Pause", "app.run", "accent") if self.running else ("Run", "app.run", "off" if self.finished else "")
        items: list[tuple] = [("☰", "app.menu", "")]
        if n:
            cur = dict(VIEWS).get(self.view, "Edit")
            items.append((f"{cur}{'•' if self.unread else ''}▾", "app.menu('views')", "active"))
            items.append((fname, "app.menu('files')", ""))
            items += [("Asm", "app.assemble", ""), run,
                      ("Step", "app.step", "off" if self.running or self.finished else "")]
        else:
            for v, label in VIEWS:
                if v in ("regs", "io"):
                    continue
                lab = label + ("•" if v in self.unread else "")
                items.append((lab, f"app.view('{v}')", "active" if self.view == v else ("warn" if v in self.unread else "")))
            items.append(("│", "app.noop", "off"))
            items.append((fname, "app.menu('files')", ""))
            items.append(("│", "app.noop", "off"))
            items += [("Asm", "app.assemble", ""), run,
                      ("Step", "app.step", "off" if self.running or self.finished else ""),
                      ("Back", "app.backstep", "" if can_back else "off"),
                      ("Reset", "app.reset", "" if self.assembled else "off"),
                      (f"⏱{sp_label}", "app.speed", "")]
            if w >= 150:
                items.append(("Panels" if not self.settings.get("panels") else "Panels ✓", "app.toggle_panels", ""))
        right = self._state_label(short=n or w < 132)
        if self.state and self.assembled and not n and w >= 150:
            right = f"[$text-muted]pc[/] {hex32(self.state.get('pc', 0))} [$text-muted]·[/] {self.state.get('count', 0)}   " + right
        self.query_one("#tabs", Bar).set_items(items, right)
        self._render_sub_bars()

    def action_menu(self, section: str = "all") -> None:
        """One menu for everything — the way to reach every action without function keys."""
        from .screens import MenuScreen
        ed = self.current_editor()
        st = self.settings
        on = lambda b: "✓ " if b else "  "
        groups: list[tuple[str, list[tuple[str, str, str]]]] = []
        if section in ("all", "views"):
            groups.append(("View", [(f"{label}{' •' if v in self.unread else ''}", f"view('{v}')", f"alt+{i + 1}")
                                    for i, (v, label) in enumerate(VIEWS)]))
        if section in ("all", "files"):
            files = [(("● " if e is ed else "  ") + (Path(e.path).name if e.path else "untitled") + (" (modified)" if e.modified else ""),
                      f"select_editor('{e.id}')", "") for e in self.editors]
            files += [("New file", "new", "ctrl+n"), ("Open…", "open", "ctrl+o"), ("Save", "save", "ctrl+s"),
                      ("Save as…", "save_as", ""), ("Close file", "close_file", "")]
            groups.append(("Files", files))
        if section == "all":
            groups.append(("Run", [("Assemble", "assemble", "F3"), ("Run / Pause", "run", "F5"), ("Step", "step", "F7"),
                                   ("Step back", "backstep", "F8"), ("Stop", "stop", "F11"), ("Reset", "reset", "F12"),
                                   (f"Speed: {'max' if not st.get('speed') else str(st['speed']) + '/s'} (cycle)", "speed", ""),
                                   ("Toggle breakpoint", "toggle_bp", "b"), ("Clear breakpoints", "clear_bps", ""),
                                   ("Go to PC", "goto_pc", "")]))
            groups.append(("Layout", [(on(st.get("panels")) + "Registers & console while editing", "toggle_panels", "ctrl+j"),
                                      (on(st.get("zen")) + "Zen mode (only code)", "toggle_zen", "F10"),
                                      (on(st.get("show_status", True)) + "Status line", "toggle_setting('show_status')", ""),
                                      (on(st.get("line_numbers", True)) + "Line numbers", "toggle_setting('line_numbers')", "alt+l"),
                                      (on(st.get("show_code")) + "Machine code column", "toggle_code_col", "")]))
            groups.append(("More", [("Back", "nav_back", "alt+←"), ("Forward", "nav_forward", "alt+→"),
                                    ("Settings & themes", "settings", "F2"), ("Command palette", "command_palette", "ctrl+p"),
                                    ("Help", "view('help')", "F1"), ("Quit", "quit", "ctrl+q")]))

        def done(action: str | None) -> None:
            if action:
                self.call_later(self.run_action, action)
        self.push_screen(MenuScreen(groups), done)

    def _state_label(self, short: bool = False) -> str:
        if self.running:
            spin = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"[int(time.monotonic() * 8) % 10]
            lab = ("[b $warning]⌨", "input") if self.waiting_input else (f"[b $success]{spin}", "running")
        elif not self.assembled:
            lab = ("[$text-muted]○", "edit")
        elif self.finished:
            lab = ("[b $secondary]■", "done")
        elif self.state.get("count"):
            lab = ("[b $warning]‖", "paused")
        else:
            lab = ("[b $primary]✓", "ready")
        return f"{lab[0]}[/]" if short else f"{lab[0]} {lab[1]}[/]"

    def _render_sub_bars(self) -> None:
        q = self.query_one
        q("#regbar", Bar).set_items([
            ("Registers", "app.regtab('gpr')", "active" if self.regs_tab == "gpr" else ""),
            ("Coproc 1", "app.regtab('fpr')", "active" if self.regs_tab == "fpr" else ""),
            ("Coproc 0", "app.regtab('cp0')", "active" if self.regs_tab == "cp0" else ""),
        ])
        msg_n = len(self.messages)
        q("#iobar", Bar).set_items([
            ("Run I/O", "app.iotab('run')", "active" if self.io_tab == "run" else ""),
            (f"Messages{f' ({msg_n})' if msg_n else ''}", "app.iotab('msg')",
             "active" if self.io_tab == "msg" else ("warn" if any(not m.get('warning') for m in self.messages) else "")),
            ("Clear", "app.clear_console", ""),
        ])
        q("#toolbar", Bar).set_items([
            ("Bitmap Display", "app.tooltab('bitmap')", "active" if self.tools_tab == "bitmap" else ""),
            ("Keyboard & Display MMIO" if not self.narrow else "Kbd/Display MMIO", "app.tooltab('mmio')",
             "active" if self.tools_tab == "mmio" else ""),
        ])
        bm = self.settings["bitmap"]
        q("#bmbar", Bar).set_items([
            (f"unit {bm['unit']}px", "app.bitmap('unit')", ""),
            (f"display {bm['w']}×{bm['h']}", "app.bitmap('size')", ""),
            (f"base {self._bitmap_base_label()}", "app.bitmap('base')", ""),
            (f"→ {bm['w'] // bm['unit']}×{bm['h'] // bm['unit']} px", "app.noop", "off"),
        ])
        r = self.settings.get("mem_radix", "hex")
        segs = [(".data", "data"), ("$gp", "gp"), ("$sp", "sp"), ("heap", "heap"), (".extern", "extern"),
                (".text", "text"), (".kdata", "kdata"), (".ktext", "ktext"), ("MMIO", "mmio")]
        q("#membar", Bar).set_items(
            [(lab, f"app.mem_seg('{k}')", "") for lab, k in segs]
            + [("◀", "app.mem_page('prev')", ""), ("▶", "app.mem_page('next')", ""), ("Go to…", "app.mem_goto", ""),
               (r, "app.mem_radix", "accent")],
            "" if self.narrow else (hex32(self.mem_base) if self.mem_base is not None else ""))
        q("#helpbar", Bar).set_items([
            (lab, f"app.helptab('{k}')", "active" if self.help_tab == k else "")
            for k, lab in [("card", "Card"), ("basic", "Basic"), ("pseudo", "Pseudo"), ("dirs", "Directives"),
                           ("sys", "Syscalls"), ("keys", "Keys"), ("about", "About")]
        ])

    # ------------------------------------------------------------------ status line
    def flash(self, msg: str, kind: str = "info", secs: float = 6.0) -> None:
        t = self.current_theme
        color = {"error": t.error, "warn": t.warning, "ok": t.success}.get(kind, t.foreground) if t else None
        self.flash_text = Text(msg, style=Style(color=color, bold=kind in ("error", "ok")))
        self.flash_until = time.monotonic() + secs
        self._update_hint()

    def _update_hint(self) -> None:
        if not self.is_mounted or self._closing:
            return
        try:
            hint = self.query_one("#hint", Static)
        except Exception:
            return
        if self.flash_text is not None and time.monotonic() < self.flash_until:
            hint.update(self.flash_text)
            return
        self.flash_text = None
        hint.update(self._context_hint())

    def _context_hint(self) -> Text:
        ed = self.current_editor()
        if self.view == "edit" and ed is not None:
            row, col = ed.cursor_location
            mark = ed.marks.get(row)
            if mark:
                t = self.current_theme
                return Text(("✗ " if mark[0] == "error" else "⚠ ") + mark[2],
                            style=Style(color=(t.error if mark[0] == "error" else t.warning) if t else None))
            line = ed.document.get_line(row) if row < ed.document.line_count else ""
            mn, dr = mips.mnemonic_at(line, col)
            if mn and mn in CARD_BY:
                c = CARD_BY[mn]
                pal = PALETTES[self.syntax]
                txt = highlight_text(f"{mn} {c['ops']}".strip(), self.syntax)
                txt.append(f"  {c['op']}", style=Style(bold=True))
                txt.append(f"  {c['fmt']} {c['code']}", style=pal["number"])
                txt.append(f"  {c['name']} · F1 card", style=Style(dim=True))
                return txt
            if mn and mn in ISA_DB.instructions:
                info = ISA_DB.instructions[mn]
                fmt, desc, pseudo = info.formats[0]
                txt = highlight_text(fmt, self.syntax)
                if all(f[2] for f in info.formats):
                    txt.append("  pseudo", style=PALETTES[self.syntax]["pseudo"])
                more = f" (+{len(info.formats) - 1} forms, F1)" if len(info.formats) > 1 else ""
                txt.append(f"  {desc}{more}", style=Style(dim=True))
                return txt
            if dr and dr in ISA_DB.directives:
                txt = highlight_text(dr, self.syntax)
                txt.append(f"  {ISA_DB.directives[dr]}", style=Style(dim=True))
                return txt
        return Text("")

    def _update_pos(self) -> None:
        pos = self.query_one("#pos", Static)
        ed = self.current_editor()
        if self.view == "edit" and ed is not None:
            r, c = ed.cursor_location
            pos.update(f"Ln {r + 1}, Col {c + 1}")
        elif self.assembled and self.narrow:
            pos.update(f"pc {hex32(self.state.get('pc', 0))} · {self.state.get('count', 0)}")
        else:
            pos.update("")

    def _ui_tick(self) -> None:
        if self._closing:
            return
        try:
            self._ui_tick_inner()
        except Exception:  # widgets may be gone during shutdown
            pass

    _spin_t = 0.0

    def _ui_tick_inner(self) -> None:
        if self.running and not self.waiting_input and time.monotonic() - self._spin_t > 0.14:
            self._spin_t = time.monotonic()
            self.render_bars()
        if self.flash_text is not None and time.monotonic() >= self.flash_until:
            self._update_hint()
        if self._tick_state is not None:
            st, self._tick_state = self._tick_state, None
            self.apply_state(st, follow=True)
        self._update_pos()

    # ------------------------------------------------------------------ views
    # ---- navigation history (alt+← / alt+→, Esc in Help) -------------------------
    _nav_back: list = []
    _nav_fwd: list = []
    _nav_restoring = False

    def _nav_snapshot(self) -> dict:
        ed = self.current_editor()
        return {"view": self.view, "editor": ed.id if ed else None,
                "cursor": ed.cursor_location if ed else (0, 0),
                "mem": self.mem_base, "help": self.help_tab,
                "filter": self.query_one("#help-filter", Input).value if self.is_mounted else ""}

    def nav_mark(self) -> None:
        if self._nav_restoring or not self.is_mounted:
            return
        snap = self._nav_snapshot()
        if self._nav_back and self._nav_back[-1] == snap:
            return
        self._nav_back.append(snap)
        del self._nav_back[:-100]
        self._nav_fwd.clear()

    def _nav_restore(self, snap: dict) -> None:
        self._nav_restoring = True
        try:
            if snap["editor"] and any(e.id == snap["editor"] for e in self.editors):
                self.query_one("#editors", ContentSwitcher).current = snap["editor"]
            self.mem_base = snap["mem"]
            self.help_tab = snap["help"]
            self.query_one("#help-filter", Input).value = snap["filter"]
            self.set_view(snap["view"])
            ed = self.current_editor()
            if snap["view"] == "edit" and ed is not None:
                ed.cursor_location = snap["cursor"]
                ed.scroll_cursor_visible(center=True)
            if snap["view"] == "help":
                self.populate_help()
            self.render_bars()
        finally:
            self._nav_restoring = False

    def action_nav_back(self) -> None:
        if not self._nav_back:
            self.flash("Nothing to go back to.", "info", 2)
            return
        self._nav_fwd.append(self._nav_snapshot())
        self._nav_restore(self._nav_back.pop())

    def action_nav_forward(self) -> None:
        if not self._nav_fwd:
            return
        self._nav_back.append(self._nav_snapshot())
        self._nav_restore(self._nav_fwd.pop())

    def set_view(self, v: str) -> None:
        if v not in dict(VIEWS):
            return
        if v != self.view:
            self.nav_mark()
        if not self.narrow and v in ("regs", "io"):
            # those panes are always visible in the wide layout; just focus them
            if v == "regs":
                self.query_one(f"#{self.regs_tab}", Table).focus()
            else:
                self.query_one("#stdin", Input).focus()
            return
        self.view = v
        self.unread.discard(v)
        if v in MAIN_VIEWS:
            self.query_one("#main", ContentSwitcher).current = v
        self._set_view_classes()
        self.render_bars()
        self._update_hint()
        if v == "mem":
            self.refresh_memory()
        if v == "tools":
            self.refresh_bitmap()
        if v == "regs":
            self.refresh_regs()
        if v == "edit":
            ed = self.current_editor()
            if ed:
                ed.focus()
        elif v == "code":
            self.query_one("#code-table", Table).focus()
        elif v == "labels":
            self.query_one("#label-table", Table).focus()
        elif v == "io":
            self.query_one("#stdin", Input).focus()

    def action_view(self, v: str) -> None:
        self.set_view(v)

    def action_cycle_view(self, d: str) -> None:
        d = -1 if d == "prev" else 1
        order = [v for v, _ in VIEWS if self.narrow or v not in ("regs", "io")]
        i = order.index(self.view) if self.view in order else 0
        self.set_view(order[(i + d) % len(order)])

    def action_regtab(self, t: str) -> None:
        self.regs_tab = t
        self.query_one("#reg-switch", ContentSwitcher).current = t
        self.refresh_regs()
        self.render_bars()

    def action_iotab(self, t: str) -> None:
        self.io_tab = t
        self.query_one("#io-switch", ContentSwitcher).current = "run-io" if t == "run" else "messages"
        self.render_bars()

    def action_tooltab(self, t: str) -> None:
        self.tools_tab = t
        self.query_one("#tool-switch", ContentSwitcher).current = t
        if t == "mmio":
            self.query_one("#keycap").focus()
        self.render_bars()
        self.refresh_bitmap()

    def action_lookup(self) -> None:
        """F1: open the reference card at the instruction under the cursor (or Help)."""
        self.nav_mark()
        word = ""
        ed = self.current_editor()
        if self.view == "edit" and ed is not None:
            row, col = ed.cursor_location
            mn, _ = mips.mnemonic_at(ed.document.get_line(row), col)
            word = mn or ""
        self.help_tab = "card"
        self.query_one("#help-filter", Input).value = f"={word}" if word else ""
        self.set_view("help")
        self.populate_help()
        self.render_bars()

    def action_helptab(self, t: str) -> None:
        self.help_tab = t
        self.populate_help()
        self.render_bars()

    def action_noop(self) -> None:
        pass

    # ------------------------------------------------------------------ editors
    def current_editor(self) -> MipsEditor | None:
        if not self.editors:
            return None
        cur = self.query_one("#editors", ContentSwitcher).current
        for e in self.editors:
            if e.id == cur:
                return e
        return self.editors[0]

    def _add_editor(self, text: str, path: str | None) -> MipsEditor:
        self.ed_counter += 1
        ed = MipsEditor(text, path=path, id=f"ed{self.ed_counter}")
        ed.theme = f"mips-{self.syntax}"
        ed.show_line_numbers = bool(self.settings.get("line_numbers", True))
        self.editors.append(ed)
        sw = self.query_one("#editors", ContentSwitcher)
        sw.mount(ed)
        sw.current = ed.id
        self.render_bars()
        return ed

    def open_file(self, path: str) -> MipsEditor | None:
        p = Path(path).expanduser()
        ap = str(p.resolve())
        for e in self.editors:
            if e.path == ap:
                self.action_select_editor(e.id)
                return e
        try:
            text = p.read_text(encoding="utf-8", errors="replace") if p.exists() else TEMPLATE.format(name=p.name)
        except OSError as ex:
            self.flash(f"Cannot open {path}: {ex}", "error")
            return None
        # replace a pristine untitled buffer
        if len(self.editors) == 1 and self.editors[0].path is None and not self.editors[0].modified:
            old = self.editors.pop()
            old.remove()
        ed = self._add_editor(text, ap)
        if not p.exists():
            ed.saved_text = ""
            self.flash(f"New file {rel(ap)} — save with ctrl+s", "info")
        self.save_settings()
        return ed

    def new_buffer(self) -> None:
        self._add_editor(TEMPLATE.format(name="untitled.asm"), None)

    def action_new(self) -> None:
        self.new_buffer()
        self.set_view("edit")

    def action_select_editor(self, ed_id: str) -> None:
        if ed_id != self.query_one("#editors", ContentSwitcher).current:
            self.nav_mark()
        self.query_one("#editors", ContentSwitcher).current = ed_id
        self.render_bars()
        if self.view != "edit":
            self.set_view("edit")
        ed = self.current_editor()
        if ed:
            ed.focus()

    def action_open(self) -> None:
        def done(path: str | None) -> None:
            if path:
                self.open_file(path)
                self.set_view("edit")
        self.push_screen(OpenScreen(os.getcwd()), done)

    async def action_save(self) -> None:
        ed = self.current_editor()
        if ed is None:
            return
        if ed.path is None:
            self.action_save_as()
            return
        self._write(ed)

    def _write(self, ed: MipsEditor) -> bool:
        try:
            Path(ed.path).parent.mkdir(parents=True, exist_ok=True)
            Path(ed.path).write_text(ed.text, encoding="utf-8")
        except OSError as ex:
            self.flash(f"Save failed: {ex}", "error")
            return False
        ed.saved_text = ed.text
        self.flash(f"Saved {rel(ed.path)}", "ok", 3)
        self.render_bars()
        self.save_settings()
        return True

    def action_save_as(self, then=None) -> None:
        ed = self.current_editor()
        if ed is None:
            return

        def done(path: str | None) -> None:
            if not path:
                return
            p = Path(path).expanduser()
            if p.suffix == "":
                p = p.with_suffix(".asm")
            ed.path = str(p.resolve())
            if self._write(ed) and then:
                then()
        self.push_screen(PromptScreen("Save as", rel(ed.path) if ed.path else "untitled.asm",
                                      "file name (relative to the workspace)"), done)

    def action_close_file(self) -> None:
        ed = self.current_editor()
        if ed is None:
            return
        if ed.modified:
            def done(v: str | None) -> None:
                if v is not None and v.strip().lower() in ("y", "yes", "d", "discard"):
                    self._close(ed)
            self.push_screen(PromptScreen(f"{rel(ed.path)} has unsaved changes. Type 'yes' to discard.", ""), done)
            return
        self._close(ed)

    def _close(self, ed: MipsEditor) -> None:
        self.editors.remove(ed)
        ed.remove()
        if not self.editors:
            self.new_buffer()
        else:
            self.query_one("#editors", ContentSwitcher).current = self.editors[-1].id
        self.render_bars()
        self.save_settings()

    @on(MipsEditor.Changed)
    def _editor_changed(self, event: MipsEditor.Changed) -> None:
        ed = event.text_area
        if isinstance(ed, MipsEditor):
            was = getattr(ed, "_was_modified", None)
            if ed.marks:
                ed.marks = {}
                ed._build_highlight_map()
            if was != ed.modified:
                ed._was_modified = ed.modified
                self.render_bars()

    @on(MipsEditor.SelectionChanged)
    def _editor_cursor(self, event) -> None:
        self._update_hint()
        self._update_pos()

    # ------------------------------------------------------------------ assemble
    def _files_to_assemble(self, ed: MipsEditor) -> list[str]:
        if self.settings.get("assemble_all"):
            d = Path(ed.path).parent
            files = sorted(str(p.resolve()) for p in d.iterdir() if p.suffix.lower() in (".asm", ".s"))
            if ed.path in files:
                files.remove(ed.path)
            return [ed.path, *files]
        return [ed.path]

    async def action_assemble(self) -> bool:
        ed = self.current_editor()
        if ed is None:
            return False
        if ed.path is None:
            self.action_save_as(then=lambda: self.call_later(self.action_assemble))
            return False
        for e in self.editors:
            if e.path and e.modified:
                if self.settings.get("auto_save", True) or e is ed:
                    self._write(e)
        files = self._files_to_assemble(ed)
        try:
            res = await self.bridge.call("assemble", files=files, main=ed.path, settings={
                k: self.settings.get(k) for k in ("pseudo", "delayed_branching", "self_modifying",
                                                  "warnings_are_errors", "start_at_main", "bare_machine",
                                                  "exception_handler", "program_args", "memory_config")})
        except BridgeError as ex:
            self.flash(f"Assemble failed: {ex}", "error")
            return False
        self.running = False
        self.messages = res.get("messages", [])
        self._show_messages(res.get("success", False), files)
        if not res.get("success"):
            self.assembled = False
            self.render_bars()
            return False
        self.assembled = True
        self.finished = False
        self.text_rows = res.get("text", [])
        self.addr_index = {r["addr"]: i for i, r in enumerate(self.text_rows)}
        self.labels = res.get("labels", [])
        self.segments = res.get("segments", {})
        self.prev_state = {}
        self.clear_heat()
        self.state = {}
        self.state = res.get("state", {})
        self.mem_base = self.segments.get("data", 0x10010000)
        self.mem_prev = {}
        self.pc_row = None
        self.query_one("#mmio-log", Log).clear()
        self.build_code_table()
        self.fill_labels()
        self.apply_state(self.state, follow=True)
        warn = sum(1 for m in self.messages if m.get("warning"))
        self.flash(f"✓ Assembled {', '.join(rel(f) for f in files)}" + (f" · {warn} warning(s)" if warn else ""), "ok")
        self.set_view("code")
        return True

    def console_line(self, text: str) -> None:
        """Write a full line to the Run I/O log, starting on a fresh line."""
        log = self.query_one("#console", Log)
        if log.lines and log.lines[-1]:
            log.write("\n")
        log.write(text + "\n")

    def _show_messages(self, ok: bool, files: list[str]) -> None:
        console = self.query_one("#console", Log)
        ml = self.query_one("#messages", OptionList)
        ml.clear_options()
        marks: dict[str, dict[int, tuple[str, int, str]]] = {}
        t = self.current_theme
        for i, m in enumerate(self.messages):
            kind = "warning" if m.get("warning") else "error"
            fname = m.get("file") or ""
            line = int(m.get("line") or 0)
            col = int(m.get("col") or 0)
            label = Text()
            label.append("⚠ " if kind == "warning" else "✗ ", style=Style(color=(t.warning if kind == "warning" else t.error) if t else None, bold=True))
            label.append(f"{rel(fname) if fname else ''}" + (f":{line}:{col}" if line else ""), style=Style(bold=True))
            label.append("  " + str(m.get("message", "")).strip())
            ml.add_option(Option(label, id=f"m{i}"))
            if fname and line:
                marks.setdefault(str(Path(fname).resolve()), {})[line - 1] = (kind, col, str(m.get("message", "")).strip())
        for e in self.editors:
            e.set_marks(marks.get(e.path or "", {}))
        if ok:
            self.console_line(f"Assemble: {', '.join(rel(f) for f in files)} — operation completed successfully.")
        else:
            n = sum(1 for m in self.messages if not m.get("warning"))
            self.console_line(f"Error: assemble failed with {n} error(s) — see Messages")
            self.flash(f"✗ Assembly failed: {n} error(s) — first: {self.messages[0].get('message','') if self.messages else ''}", "error", 10)
            self.action_iotab("msg")
            self.show_panels(True)
            if self.messages:
                self._jump_to_message(self.messages[0])
        self.render_bars()

    def _jump_to_message(self, m: dict) -> None:
        self.nav_mark()
        fname, line, col = m.get("file"), int(m.get("line") or 0), int(m.get("col") or 0)
        if not fname or not line:
            return
        ed = self.open_file(fname)
        if ed is None:
            return
        self.set_view("edit")
        ed.cursor_location = (line - 1, max(0, col - 1))
        ed.scroll_cursor_visible(center=True)
        ed.focus()

    @on(OptionList.OptionSelected, "#messages")
    def _message_selected(self, event: OptionList.OptionSelected) -> None:
        i = int((event.option.id or "m0")[1:])
        if i < len(self.messages):
            self._jump_to_message(self.messages[i])

    # ------------------------------------------------------------------ execution
    def _bp_addrs(self) -> list[int]:
        out, seen = [], set()
        for r in self.text_rows:
            key = (r.get("file", ""), r.get("line", 0))
            if key in self.breakpoints and key not in seen:
                seen.add(key)
                out.append(r["addr"])
        return out

    async def _ensure_assembled(self) -> bool:
        if self.assembled:
            return True
        return await self.action_assemble()

    async def action_run(self) -> None:
        if self.running:
            await self.action_pause()
            return
        if not await self._ensure_assembled():
            return
        if self.finished:
            self.flash("Program has finished — F12 resets it, then F5 runs again.", "warn")
            return
        self.prev_state = self.state
        self.show_panels(True)
        try:
            await self.bridge.call("run", breakpoints=self._bp_addrs(), speed=int(self.settings.get("speed", 0)))
        except BridgeError as ex:
            self.flash(str(ex), "error")
            return
        self.running = True
        self.render_bars()
        if self.narrow and self.view not in ("io", "tools"):
            pass  # stay where the user is; I/O tab lights up on output

    async def action_pause(self) -> None:
        if self.running:
            try:
                await self.bridge.call("pause")
            except BridgeError:
                pass

    async def action_stop(self) -> None:
        await self.action_pause()

    async def action_step(self) -> None:
        if self.running:
            return
        if not await self._ensure_assembled():
            return
        if self.finished:
            self.flash("Program has finished — F12 resets it.", "warn")
            return
        prev = self.state
        self.show_panels(True)
        try:
            res = await self.bridge.call("step")
        except BridgeError as ex:
            self.flash(str(ex), "error")
            return
        self.prev_state = prev
        if res.get("finished"):
            self._finished(res.get("reason", "exit"), res.get("errors"))
        self.apply_state(res["state"], follow=True)

    async def action_backstep(self) -> None:
        if self.running or not self.assembled:
            return
        prev = self.state
        try:
            res = await self.bridge.call("backstep")
        except BridgeError as ex:
            self.flash(str(ex), "error")
            return
        if res.get("empty"):
            self.flash("Nothing to undo.", "warn", 3)
            return
        self.prev_state = prev
        self.finished = False
        self.apply_state(res["state"], follow=True)

    async def action_reset(self) -> None:
        if not self.assembled:
            return
        try:
            res = await self.bridge.call("reset")
        except BridgeError as ex:
            self.flash(str(ex), "error")
            return
        self.running = False
        self.finished = False
        self.prev_state = {}
        self.clear_heat()
        self.state = {}
        self.mem_prev = {}
        self.query_one("#mmio-log", Log).clear()
        self.console_line("-- reset --")
        self.apply_state(res["state"], follow=True)
        self.flash("Reset: memory and registers restored.", "ok", 3)

    def action_speed(self) -> None:
        sp = int(self.settings.get("speed", 0))
        i = SPEEDS.index(sp) if sp in SPEEDS else 0
        sp = SPEEDS[(i + 1) % len(SPEEDS)]
        self.settings["speed"] = sp
        self.run_worker(self.bridge.call("speed", value=sp), exit_on_error=False)
        self.flash("Run speed: " + ("maximum (no live updates)" if sp == 0 else f"{sp} instructions/second (live)"), "info", 3)
        self.render_bars()

    def _finished(self, reason: str, errors: list | None) -> None:
        console = self.query_one("#console", Log)
        self.finished = True
        if reason == "error":
            for e in errors or []:
                fname = e.get("file") or ""
                line = e.get("line") or 0
                where = f"{rel(fname)} line {line}: " if fname and line else ""
                self.console_line(f"Error in {where}{str(e.get('message', '')).strip()}")
            self.console_line("-- program is finished running (error) --")
            self.flash("✗ Runtime error — see Run I/O", "error", 10)
            self.unread.add("io")
        else:
            self.console_line("-- program is finished running --")
            self.flash("■ Program finished", "ok", 4)

    def _on_bridge_event(self, ev: dict) -> None:
        kind = ev.get("ev")
        if kind == "out":
            self.query_one("#console", Log).write(ev.get("text", ""))
            if self.narrow and self.view != "io":
                if "io" not in self.unread:
                    self.unread.add("io")
                    self.render_bars()
        elif kind == "input_request":
            self.waiting_input = True
            inp = self.query_one("#stdin", Input)
            inp.placeholder = f"program is waiting for {ev.get('kind', 'input')} input — type and press Enter"
            inp.add_class("-wanted")
            self.show_panels(True)
            if self.io_tab != "run":
                self.action_iotab("run")
            if self.narrow and self.view != "io":
                self.set_view("io")
            inp.focus()
            self.render_bars()
        elif kind == "dialog":
            token = ev.get("token")

            def answered(v: str | None, token=token) -> None:
                self.run_worker(self.bridge.call("dialog_reply", token=token, value=v), exit_on_error=False)
            self.push_screen(DialogScreen(ev.get("kind", "message"), ev.get("message", "")), answered)
        elif kind == "tone":
            self.bell()
        elif kind == "tick":
            self._tick_state = ev.get("state")
        elif kind == "stopped":
            self.running = False
            self.waiting_input = False
            self._tick_state = None
            inp = self.query_one("#stdin", Input)
            inp.remove_class("-wanted")
            inp.placeholder = "program input ⏎"
            reason = ev.get("reason")
            if reason in ("exit", "error"):
                self._finished(reason, ev.get("errors"))
            elif reason == "breakpoint":
                self.flash(f"‖ Breakpoint at {hex32(ev['state']['pc'])}", "warn", 5)
                if self.view not in ("code",) and not self.narrow:
                    self.set_view("code")
            elif reason == "paused":
                self.flash("‖ Paused", "warn", 3)
            self.apply_state(ev.get("state", {}), follow=True)
        elif kind == "mmio_out":
            c = int(ev.get("char", 0))
            log = self.query_one("#mmio-log", Log)
            if c == 12:
                log.clear()
            else:
                log.write(chr(c))
            if self.view != "tools":
                self.unread.add("tools")
                self.render_bars()
        elif kind == "dead":
            if self._closing or not self.is_running:
                return
            self.running = False
            self.assembled = False
            self.flash("MARS engine stopped unexpectedly — restarting…", "error", 10)
            self.bridge = Bridge(self._on_bridge_event)
            self.start_engine()
            self.render_bars()

    @on(Input.Submitted, "#stdin")
    def _stdin(self, event: Input.Submitted) -> None:
        text = event.value
        event.input.value = ""
        console = self.query_one("#console", Log)
        if self.waiting_input:
            console.write(text + "\n")
            self.waiting_input = False
            event.input.remove_class("-wanted")
            event.input.placeholder = "program input ⏎"
        self.run_worker(self.bridge.call("input", text=text + "\n"), exit_on_error=False)
        self.render_bars()

    @on(KeyCapture.Typed)
    def _key_typed(self, event: KeyCapture.Typed) -> None:
        self.run_worker(self.bridge.call("key", char=event.code), exit_on_error=False)

    def action_clear_console(self) -> None:
        if self.io_tab == "run":
            self.query_one("#console", Log).clear()
        else:
            self.messages = []
            self.query_one("#messages", OptionList).clear_options()
            self.render_bars()

    # ------------------------------------------------------------------ state → widgets
    # heat: a changed value glows, then fades over three steps; trail: last executed instructions
    step_no = 0
    heat: dict = {}
    trail: list = []

    def clear_heat(self) -> None:
        self.step_no = 0
        self.heat = {}
        self.trail = []

    def _track(self, prev: dict, st: dict) -> None:
        if not prev or not st or "gpr" not in prev:
            return
        if prev.get("pc") == st.get("pc") and prev.get("count") == st.get("count"):
            return
        self.step_no += 1
        n = self.step_no
        for i, v in enumerate(st.get("gpr", [])):
            if i < len(prev["gpr"]) and prev["gpr"][i] != v:
                self.heat[f"r{i}"] = n
        for i, v in enumerate(st.get("fpr", [])):
            if i < len(prev.get("fpr", [])) and prev["fpr"][i] != v:
                self.heat[f"f{i}"] = n
        for k in ("hi", "lo"):
            if prev.get(k) != st.get(k):
                self.heat[k] = n
        old = {c["num"]: c["value"] for c in prev.get("cop0", [])}
        for c in st.get("cop0", []):
            if c["num"] in old and old[c["num"]] != c["value"]:
                self.heat[f"c{c['num']}"] = n
        if prev.get("pc") != st.get("pc"):
            self.trail = [prev.get("pc"), *self.trail][:4]

    def age(self, key: str) -> int:
        n = self.heat.get(key)
        if n is None:
            return -1
        a = self.step_no - n
        return a if a <= 3 else -1

    def apply_state(self, st: dict, follow: bool = False) -> None:
        if not st:
            return
        self._track(self.state, st)
        self.state = st
        if not self.running:
            self.finished = bool(st.get("finished")) or self.finished
        self.refresh_regs()
        self.update_pc_marker(follow)
        self.refresh_memory()
        self.refresh_bitmap()
        self.render_bars()

    # registers -----------------------------------------------------------
    def _setup_reg_tables(self) -> None:
        g = self.query_one("#gpr", Table)
        g.add_column("Name", key="name", width=5)
        g.add_column("#", key="num", width=2)
        g.add_column("Hex", key="hex", width=10)
        g.add_column("Decimal", key="dec", width=11)
        for i, n in enumerate(REG_NAMES):
            g.add_row(n, str(i), "", "", key=f"r{i}")
        for n in ("pc", "hi", "lo"):
            g.add_row(n, "", "", "", key=n)
        f = self.query_one("#fpr", Table)
        f.add_column("Name", key="name", width=5)
        f.add_column("Float", key="float", width=11)
        f.add_column("Double", key="double", width=13)
        f.add_column("Hex", key="hex", width=10)
        for i in range(32):
            f.add_row(f"$f{i}", "", "", "", key=f"f{i}")
        f.add_row("cc", "", "", "", key="cc")
        c = self.query_one("#cp0", Table)
        c.add_column("Name", key="name", width=8)
        c.add_column("#", key="num", width=2)
        c.add_column("Hex", key="hex", width=10)
        c.add_column("Decimal", key="dec", width=11)
        for n, num in (("vaddr", 8), ("status", 12), ("cause", 13), ("epc", 14)):
            c.add_row(f"${n}", str(num), "", "", key=f"c{num}")

    def _cell(self, s: str, changed, style: Style | None = None) -> Text:
        age = (0 if changed else -1) if isinstance(changed, bool) else changed
        if age == 0:
            return Text(s, style=self.changed_style)
        t = self.current_theme
        acc = (t.accent if t else None) or "#ffb02e"
        if age == 1:
            return Text(s, style=Style(color=acc, bold=True))
        if age >= 2:
            return Text(s, style=Style(color=acc, dim=age == 3))
        return Text(s, style=style or Style())

    def refresh_regs(self) -> None:
        if not self.is_mounted or not self.state:
            return
        side_visible = (not self.narrow) or self.view == "regs"
        if not side_visible:
            return
        st, pv = self.state, self.prev_state or {}
        pal = PALETTES[self.syntax]
        reg_style = pal["register"]
        if self.regs_tab == "gpr":
            t = self.query_one("#gpr", Table)
            gpr, pgpr = st.get("gpr", []), pv.get("gpr", [])
            for i, v in enumerate(gpr):
                ch = self.age(f"r{i}")
                t.update_cell(f"r{i}", "name", Text(REG_NAMES[i], style=reg_style))
                t.update_cell(f"r{i}", "hex", self._cell(hex32(v), ch))
                t.update_cell(f"r{i}", "dec", self._cell(str(s32(v)), ch))
            for k in ("pc", "hi", "lo"):
                v = st.get(k, 0)
                ch = -1 if k == "pc" else self.age(k)
                t.update_cell(k, "hex", self._cell(hex32(v), ch))
                t.update_cell(k, "dec", self._cell(str(s32(v)), ch))
        elif self.regs_tab == "fpr":
            t = self.query_one("#fpr", Table)
            fpr, pf = st.get("fpr", []), pv.get("fpr", [])
            for i, v in enumerate(fpr):
                ch = self.age(f"f{i}")
                dbl = ""
                if i % 2 == 0 and i + 1 < len(fpr):
                    dbl = fmt_float(as_double(fpr[i], fpr[i + 1]))
                t.update_cell(f"f{i}", "name", Text(f"$f{i}", style=pal["fpregister"]))
                t.update_cell(f"f{i}", "hex", self._cell(hex32(v), ch))
                t.update_cell(f"f{i}", "float", self._cell(fmt_float(as_float(v)), ch))
                t.update_cell(f"f{i}", "double", self._cell(dbl, ch if i % 2 == 0 else -1))
            fl = st.get("flags", 0)
            t.update_cell("cc", "float", "flags 7…0")
            t.update_cell("cc", "double", "".join(str((fl >> b) & 1) for b in range(7, -1, -1)))
        else:
            t = self.query_one("#cp0", Table)
            prev = {c["num"]: c["value"] for c in pv.get("cop0", [])}
            for c in st.get("cop0", []):
                n, v = c["num"], c["value"]
                ch = self.age(f"c{n}")
                try:
                    t.update_cell(f"c{n}", "hex", self._cell(hex32(v), ch))
                    t.update_cell(f"c{n}", "dec", self._cell(str(s32(v)), ch))
                except Exception:
                    pass

    @on(Table.RowHighlighted, "#gpr")
    def _reg_highlighted(self, event: Table.RowHighlighted) -> None:
        """Explain the highlighted register in the hint line (role, syscall, pointer target, string…)."""
        key = str(event.row_key.value)
        if not self.state or not key.startswith("r") or not event.data_table.has_focus:
            return
        from . import meaning as mm
        n = int(key[1:])
        phrases, addr = mm.explain_gpr(n, self.state, self.segments or {}, self.labels, self.text_rows, self.addr_index)
        head = f"{REG_NAMES[n]}: " + " · ".join(p for p in phrases if p)
        self.flash(head, "info", 30)
        if addr is not None and self.assembled:
            async def fetch_string() -> None:
                try:
                    res = await self.bridge.call("memory", addr=s32(addr & ~3), words=16)
                except BridgeError:
                    return
                s = mm.c_string(res.get("words", []), addr)
                if s:
                    self.flash(head + " · " + s, "info", 30)
            self.run_worker(fetch_string(), exclusive=True, group="reghint", exit_on_error=False)

    @on(Table.RowSelected, "#gpr,#fpr,#cp0")
    def _reg_selected(self, event: Table.RowSelected) -> None:
        table = event.data_table
        if not isinstance(table, Table) or not table.take_tap():
            return
        if self.running or not self.assembled:
            self.flash("Registers can be edited while paused.", "warn", 3)
            return
        key = str(event.row_key.value)
        if key.startswith("r"):
            file, num, name = "gpr", int(key[1:]), REG_NAMES[int(key[1:])]
            cur = self.state["gpr"][num]
            if num == 0:
                self.flash("$zero is read-only", "warn", 3)
                return
        elif key in ("pc", "hi", "lo"):
            file, num, name = key, 0, key
            cur = self.state.get(key, 0)
        elif key.startswith("f"):
            file, num, name = "fpr", int(key[1:]), f"$f{key[1:]}"
            cur = self.state["fpr"][num]
        elif key.startswith("c"):
            file, num, name = "cop0", int(key[1:]), key
            cur = next((c["value"] for c in self.state.get("cop0", []) if c["num"] == num), 0)
        else:
            return

        def done(v: str | None) -> None:
            if v is None:
                return
            try:
                val = mips.parse_int(v)
            except ValueError:
                self.flash(f"Not a number: {v}", "error")
                return
            self.run_worker(self._setreg(file, num, val), exit_on_error=False)
        self.push_screen(PromptScreen(f"New value for {name}", hex32(cur),
                                      help="hex (0x…), decimal, binary (0b…) or 'c'"), done)

    async def _setreg(self, file: str, num: int, val: int) -> None:
        try:
            res = await self.bridge.call("setreg", file=file, num=num, value=s32(val))
            self.prev_state = self.state
            self.apply_state(res["state"], follow=file == "pc")
        except BridgeError as ex:
            self.flash(str(ex), "error")

    # code view -----------------------------------------------------------
    def build_code_table(self) -> None:
        t = self.query_one("#code-table", Table)
        t.clear(columns=True)
        narrow = self.narrow
        show_code = self.settings.get("show_code", True) and not narrow
        t.add_column(" ", key="bp", width=1)
        t.add_column("Address", key="addr", width=8 if narrow else 10)
        if show_code:
            t.add_column("Code", key="code", width=10)
        if narrow:
            t.add_column("Source", key="src")
            t.add_column("Basic", key="basic")
        else:
            t.add_column("Basic", key="basic")
            t.add_column("Source", key="src")
        self._code_cols = show_code
        self.pc_row = None
        bps = set(self._bp_addrs())
        last_key = None
        basic_w = max((len(r["basic"]) for r in self.text_rows), default=10)
        self._basic_w = basic_w
        self._src_w = max((len(r["source"].strip()) + 5 for r in self.text_rows), default=10)
        for r in self.text_rows:
            key = (r.get("file"), r.get("line"))
            first = key != last_key
            last_key = key
            t.add_row(*self._code_cells(r, r["addr"] in bps, False, first), key=str(r["addr"]))
        self.update_pc_marker(True)

    def _code_cells(self, r: dict, bp: bool, pc: bool, first: bool = True) -> list:
        pal = PALETTES[self.syntax]
        bg = pal["pcline"] if pc else None
        t = self.current_theme
        marker = Text(" ")
        if bp and pc:
            marker = Text("◉", style=Style(color=t.error if t else "red", bold=True))
        elif bp:
            marker = Text("●", style=Style(color=t.error if t else "red", bold=True))
        elif pc:
            marker = Text("▶", style=Style(color=t.success if t else "green", bold=True))
        elif r["addr"] in self.trail and not self.finished:
            k = self.trail.index(r["addr"])
            marker = Text("│┆┊·"[k], style=Style(color=t.success if t else "green", dim=k >= 2, bold=k == 0))
        addr = f"{r['addr'] & 0xffffffff:08x}" if self.narrow else hex32(r["addr"])
        cells = [marker, Text(addr, style=Style(dim=not pc, bold=pc))]
        if getattr(self, "_code_cols", True):
            cells.append(Text(hex32(r["code"]), style=Style(dim=True)))
        basic = highlight_text(r["basic"].ljust(getattr(self, "_basic_w", 0)), self.syntax)
        src = Text()
        if first and r.get("line"):
            src.append(f"{r['line']:>4} ", style=Style(dim=True))
            src.append_text(highlight_text(r["source"].strip(), self.syntax))
        else:
            src.append("     ")
        src.pad_right(max(0, getattr(self, "_src_w", 0) - len(src.plain)))
        cells += [src, basic] if self.narrow else [basic, src]
        if bg:
            for c in cells:
                c.stylize(bg)
        return cells

    def _refresh_code_row(self, idx: int) -> None:
        if not (0 <= idx < len(self.text_rows)):
            return
        t = self.query_one("#code-table", Table)
        r = self.text_rows[idx]
        bps = set(self._bp_addrs())
        prev_key = (self.text_rows[idx - 1].get("file"), self.text_rows[idx - 1].get("line")) if idx else None
        first = prev_key != (r.get("file"), r.get("line"))
        cells = self._code_cells(r, r["addr"] in bps, idx == self.pc_row, first)
        cols = ["bp", "addr"] + (["code"] if self._code_cols else []) + (["src", "basic"] if self.narrow else ["basic", "src"])
        for col, val in zip(cols, cells):
            try:
                t.update_cell(str(r["addr"]), col, val)
            except Exception:
                pass

    _trail_rows: set = set()

    def update_pc_marker(self, follow: bool) -> None:
        self._update_editor_exec()
        if not self.text_rows:
            return
        rows = {self.addr_index[a] for a in self.trail if a in self.addr_index}
        for i in rows | self._trail_rows:
            self._refresh_code_row(i)
        self._trail_rows = rows
        pc = self.state.get("pc")
        new = self.addr_index.get(pc) if pc is not None else None
        old = self.pc_row
        self.pc_row = new
        if old is not None and old != new:
            self._refresh_code_row(old)
        if new is not None:
            self._refresh_code_row(new)
            if follow:
                t = self.query_one("#code-table", Table)
                t.move_cursor(row=new, animate=False)

    def _update_editor_exec(self) -> None:
        """Highlight the executing source line in the editor of its file."""
        line, path = None, None
        if self.assembled and not self.finished and self.state and self.text_rows:
            i = self.addr_index.get(self.state.get("pc"))
            if i is not None:
                r = self.text_rows[i]
                line, path = r.get("line"), str(Path(r.get("file") or "").resolve())
        for e in self.editors:
            want = (line - 1) if (line and e.path == path) else None
            if e.exec_line != want:
                e.exec_line = want
                e._build_highlight_map()
                e.refresh()
                if want is not None and self.view == "edit":
                    e.scroll_to(y=max(0, want - e.size.height // 3), animate=False) if not (e.scroll_y <= want < e.scroll_y + e.size.height - 1) else None

    def action_goto_pc(self) -> None:
        self.update_pc_marker(True)
        self.set_view("code")

    @on(Table.RowSelected, "#code-table")
    def _code_selected(self, event: Table.RowSelected) -> None:
        t = event.data_table
        if isinstance(t, Table) and t.take_tap():
            self.toggle_bp_row(event.cursor_row)

    def action_toggle_bp(self) -> None:
        if self.view == "edit":
            ed = self.current_editor()
            if ed and ed.path:
                key = (ed.path, ed.cursor_location[0] + 1)
                if key in self.breakpoints:
                    self.breakpoints.discard(key)
                    self.flash(f"Breakpoint removed at line {key[1]}", "info", 3)
                else:
                    self.breakpoints.add(key)
                    self.flash(f"Breakpoint set at line {key[1]} (takes effect after assembling)", "info", 3)
                if self.text_rows:
                    self.build_code_table()
            return
        t = self.query_one("#code-table", Table)
        if self.text_rows:
            self.toggle_bp_row(t.cursor_row)

    def toggle_bp_row(self, idx: int) -> None:
        if not (0 <= idx < len(self.text_rows)):
            return
        r = self.text_rows[idx]
        key = (r.get("file"), r.get("line"))
        if key in self.breakpoints:
            self.breakpoints.discard(key)
        else:
            self.breakpoints.add(key)
        for i, rr in enumerate(self.text_rows):
            if (rr.get("file"), rr.get("line")) == key:
                self._refresh_code_row(i)
        self.render_bars()

    def action_clear_bps(self) -> None:
        self.breakpoints.clear()
        if self.text_rows:
            self.build_code_table()
        self.render_bars()

    def action_toggle_code_col(self) -> None:
        self.settings["show_code"] = not self.settings.get("show_code", True)
        if self.text_rows:
            self.build_code_table()
        self.render_bars()

    # labels ----------------------------------------------------------------
    def _setup_label_table(self) -> None:
        t = self.query_one("#label-table", Table)
        t.add_column("Label", key="name")
        t.add_column("Address", key="addr", width=10)
        t.add_column("Kind", key="kind", width=4)
        t.add_column("File", key="file")

    def fill_labels(self) -> None:
        t = self.query_one("#label-table", Table)
        t.clear()
        pal = PALETTES[self.syntax]
        for i, lab in enumerate(sorted(self.labels, key=lambda x: (x["data"], u32(x["addr"])))):
            t.add_row(Text(lab["name"], style=pal["label"]), hex32(lab["addr"]),
                      Text("data" if lab["data"] else "text", style=pal["directive"]),
                      Text(rel(lab["file"]) if lab["file"] != "(global)" else "global", style=Style(dim=True)),
                      key=f"{i}:{lab['addr']}:{int(lab['data'])}")

    @on(Table.RowSelected, "#label-table")
    def _label_selected(self, event: Table.RowSelected) -> None:
        t = event.data_table
        if not (isinstance(t, Table) and t.take_tap()):
            return
        _, addr, data = str(event.row_key.value).split(":")
        addr = int(addr)
        if data == "1":
            self.mem_base = addr & ~0x1F
            self.set_view("mem")
        else:
            idx = self.addr_index.get(addr)
            self.set_view("code")
            if idx is not None:
                self.query_one("#code-table", Table).move_cursor(row=idx, animate=False)

    # memory ----------------------------------------------------------------
    def _mem_layout(self) -> tuple[int, int]:
        t = self.query_one("#mem-table", Table)
        w = t.size.width or self.size.width
        h = t.size.height or 16
        radix = self.settings.get("mem_radix", "hex")
        cell = 11 if radix != "ascii" else 7
        ascii_col = radix == "hex"
        avail = w - 12
        wpr = 8
        for cand in (8, 4, 2, 1):
            need = cand * cell + (cand * 4 + 2 if ascii_col else 0)
            if need <= avail:
                wpr = cand
                break
        else:
            wpr = 1
        rows = max(8, h - 1)
        return wpr, rows

    @work(exclusive=True, group="mem")
    async def refresh_memory(self) -> None:
        if not self.is_mounted or not self.assembled or self.view != "mem":
            return
        if self.mem_base is None:
            self.mem_base = self.segments.get("data", 0x10010000)
        wpr, rows = self._mem_layout()
        base = u32(self.mem_base) & ~3
        try:
            res = await self.bridge.call("memory", addr=s32(base), words=wpr * rows)
        except BridgeError:
            return
        words = res.get("words", [])
        radix = self.settings.get("mem_radix", "hex")
        t = self.query_one("#mem-table", Table)
        cols_key = (wpr, radix)
        if getattr(self, "_mem_cols", None) != cols_key:
            t.clear(columns=True)
            t.add_column("Address", key="addr", width=10)
            for i in range(wpr):
                t.add_column(f"+{i * 4:x}", key=f"w{i}", width=10 if radix != "ascii" else 6)
            if radix == "hex":
                t.add_column("ASCII", key="ascii", width=wpr * 4)
            self._mem_cols = cols_key
        else:
            t.clear()
        prev = self.mem_prev
        new_prev: dict[int, int] = {}
        pal = PALETTES[self.syntax]
        for r in range(rows):
            a = base + r * wpr * 4
            cells: list = [Text(hex32(a), style=Style(dim=True))]
            asc = Text()
            for i in range(wpr):
                idx = r * wpr + i
                v = words[idx] if idx < len(words) else 0
                aa = u32(a + i * 4)
                new_prev[aa] = v
                ch = aa in prev and prev[aa] != v
                s = mips.fmt_word(v, radix)
                cell = self._cell(s, ch, pal["number"] if v and radix != "ascii" else (Style(dim=True) if not v else None))
                cells.append(cell)
                if radix == "hex":
                    for b in u32(v).to_bytes(4, "little"):
                        asc.append(chr(b) if 32 <= b < 127 else "·", style=pal["string"] if 32 <= b < 127 else Style(dim=True))
            if radix == "hex":
                cells.append(asc)
            t.add_row(*cells, key=str(a))
        self.mem_prev = new_prev
        self._render_sub_bars()

    def action_mem_seg(self, seg: str) -> None:
        sg = self.segments or {}
        gpr = self.state.get("gpr", [])
        if seg == "sp" and len(gpr) > 29:
            self.mem_base = u32(gpr[29]) & ~0x1F
        elif seg == "gp" and len(gpr) > 28:
            self.mem_base = u32(gpr[28]) & ~0x1F
        else:
            defaults = {"data": 0x10010000, "extern": 0x10000000, "heap": 0x10040000, "text": 0x00400000,
                        "kdata": 0x90000000, "ktext": 0x80000000, "mmio": 0xFFFF0000}
            self.mem_base = u32(sg.get(seg, defaults.get(seg, 0x10010000)))
        self.mem_prev = {}
        self.refresh_memory()

    def action_mem_page(self, d: str) -> None:
        d = -1 if d == "prev" else 1
        wpr, rows = self._mem_layout()
        self.mem_base = u32((self.mem_base or 0) + d * wpr * rows * 4)
        self.mem_prev = {}
        self.refresh_memory()

    def action_mem_radix(self) -> None:
        order = ["hex", "dec", "ascii"]
        r = self.settings.get("mem_radix", "hex")
        self.settings["mem_radix"] = order[(order.index(r) + 1) % 3] if r in order else "hex"
        self.refresh_memory()
        self._render_sub_bars()

    def action_mem_goto(self) -> None:
        def done(v: str | None) -> None:
            if not v:
                return
            v = v.strip()
            lab = next((l for l in self.labels if l["name"] == v), None)
            try:
                addr = lab["addr"] if lab else mips.parse_int(v)
            except ValueError:
                self.flash(f"Unknown address or label: {v}", "error")
                return
            self.mem_base = u32(addr) & ~0x1F
            self.mem_prev = {}
            self.set_view("mem")
            self.refresh_memory()
        self.push_screen(PromptScreen("Go to address or data label", hex32(self.mem_base or 0x10010000)), done)

    @on(Table.CellSelected, "#mem-table")
    def _mem_selected(self, event: Table.CellSelected) -> None:
        t = event.data_table
        if not (isinstance(t, Table) and t.take_tap()):
            return
        col = event.coordinate.column
        if col == 0:
            self.action_mem_goto()
            return
        wpr, _ = self._mem_layout()
        if col > wpr:
            return
        row_addr = int(str(event.cell_key.row_key.value))
        addr = u32(row_addr + (col - 1) * 4)
        if self.running:
            self.flash("Memory can be edited while paused.", "warn", 3)
            return

        def done(v: str | None) -> None:
            if v is None:
                return
            try:
                val = mips.parse_int(v)
            except ValueError:
                self.flash(f"Not a number: {v}", "error")
                return
            self.run_worker(self._setmem(addr, val), exit_on_error=False)
        cur = self.mem_prev.get(addr, 0)
        self.push_screen(PromptScreen(f"New word at {hex32(addr)}", hex32(cur)), done)

    async def _setmem(self, addr: int, val: int) -> None:
        try:
            await self.bridge.call("setmem", addr=s32(addr), value=s32(val))
        except BridgeError as ex:
            self.flash(str(ex), "error")
            return
        self.refresh_memory()
        self.refresh_bitmap()

    # bitmap ----------------------------------------------------------------
    BASES = [("data", "0x10010000 (static data)"), ("gp", "$gp"), ("extern", "0x10000000 (global data)"),
             ("heap", "0x10040000 (heap)"), ("mmio", "0xffff0000 (memory map)")]

    def _bitmap_base(self) -> int:
        b = self.settings["bitmap"].get("base", "data")
        sg = self.segments or {}
        if b == "gp":
            return u32(sg.get("gp", 0x10008000))
        defaults = {"data": 0x10010000, "extern": 0x10000000, "heap": 0x10040000, "mmio": 0xFFFF0000}
        return u32(sg.get(b, defaults.get(b, 0x10010000)))

    def _bitmap_base_label(self) -> str:
        b = self.settings["bitmap"].get("base", "data")
        return dict(self.BASES).get(b, b)

    def action_bitmap(self, what: str) -> None:
        bm = self.settings["bitmap"]
        if what == "unit":
            units = [1, 2, 4, 8, 16, 32]
            bm["unit"] = units[(units.index(bm["unit"]) + 1) % len(units)] if bm["unit"] in units else 8
        elif what == "size":
            sizes = [(512, 256), (256, 256), (512, 512), (256, 128), (128, 128), (1024, 512), (64, 64)]
            cur = (bm["w"], bm["h"])
            bm["w"], bm["h"] = sizes[(sizes.index(cur) + 1) % len(sizes)] if cur in sizes else sizes[0]
        elif what == "base":
            keys = [k for k, _ in self.BASES]
            bm["base"] = keys[(keys.index(bm["base"]) + 1) % len(keys)] if bm["base"] in keys else "data"
        self._render_sub_bars()
        self.refresh_bitmap()

    @work(exclusive=True, group="bitmap")
    async def refresh_bitmap(self) -> None:
        if not self.is_mounted or self.view != "tools" or self.tools_tab != "bitmap" or not self.assembled:
            return
        bm = self.settings["bitmap"]
        gw, gh = bm["w"] // bm["unit"], bm["h"] // bm["unit"]
        try:
            res = await self.bridge.call("memory", addr=s32(self._bitmap_base()), words=gw * gh)
        except BridgeError:
            return
        self.query_one("#bitmap-view", BitmapView).set_image(res.get("words", []), gw, gh)

    # periodic refresh while running at full speed
    def on_ready(self) -> None:
        self.set_interval(0.25, self._running_poll)

    async def _running_poll(self) -> None:
        if not self.running:
            return
        if self.settings.get("speed", 0) == 0:
            try:
                res = await self.bridge.call("state")
                st = res.get("state", {})
                self.state["count"] = st.get("count", 0)
                self.state["pc"] = st.get("pc", 0)
                self.render_bars()
            except BridgeError:
                pass
        if self.view == "tools":
            self.refresh_bitmap()
        elif self.view == "mem":
            self.refresh_memory()

    # help ------------------------------------------------------------------
    @on(Input.Changed, "#help-filter")
    def _help_filter(self, event: Input.Changed) -> None:
        self.populate_help()

    def populate_help(self) -> None:
        if not self.is_mounted:
            return
        ol = self.query_one("#help-list", OptionList)
        flt = self.query_one("#help-filter", Input).value.strip().lower()
        ol.clear_options()
        pal = PALETTES[self.syntax]
        dim = Style(dim=True)
        opts = []
        tab = self.help_tab
        if tab == "card":
            exact = flt[1:] if flt.startswith("=") else None
            def match(*xs):
                if not flt:
                    return True
                if exact is not None:
                    return xs[0] == exact
                return any(flt in str(x).lower() for x in xs)
            head = lambda t: Option(Text(t.upper(), style=Style(bold=True, dim=True)), disabled=True)
            fmt_style = {"R": pal["instruction"], "I": pal["number"], "J": pal["directive"]}
            ins = [i for i in CARD["instructions"] if match(i["m"], i["name"], i["op"], i["fmt"] + "-type", i["code"])]
            if ins:
                opts.append(head("Instructions"))
                for i in ins:
                    t = Text()
                    t.append(f"{i['m']:<8}", style=pal["instruction"])
                    t.append(f"{i['ops']:<13}", style=dim)
                    t.append(i["name"])
                    d = Text("  ")
                    d.append(i["op"], style=Style(bold=True))
                    d.append(f"   {i['fmt']}", style=fmt_style.get(i["fmt"]))
                    d.append(f" {i['code']}", style=dim)
                    fields = CARD["formats"].get(i["fmt"], [])
                    opc, _, fn = i["code"].partition("/")
                    enc = []
                    for fld in fields:
                        v = fld["f"]
                        if v == "op":
                            v = format(int(opc.strip(), 16), "06b")
                        elif v == "func" and fn.strip():
                            v = format(int(fn.strip(), 16), "06b")
                        enc.append(v)
                    d.append("   [" + " | ".join(enc) + "]", style=dim)
                    opts.append(Option(Group(t, d)))
            ps = [i for i in CARD["pseudo"] if match(i["m"], i["name"], "pseudo")]
            if ps:
                opts.append(head("Pseudo-instructions"))
                for i in ps:
                    t = Text()
                    t.append(f"{i['m']:<8}", style=pal["pseudo"])
                    t.append(f"{i['ops']:<13}", style=dim)
                    t.append(i["name"])
                    opts.append(Option(t))
            if not flt or match("formats", "r-type", "i-type", "j-type", "encoding"):
                opts.append(head("Instruction formats"))
                for k, fs in CARD["formats"].items():
                    t = Text(f"{k}  ", style=fmt_style.get(k))
                    t.append(" | ".join(f"{x['f']} ({x['bits']})" for x in fs))
                    opts.append(Option(t))
            regs = [r for r in CARD["registers"] if match(r["name"], r["num"], "register")]
            if regs:
                opts.append(head("Registers"))
                for k in range(0, len(regs), 3):
                    t = Text()
                    for r in regs[k:k + 3]:
                        t.append(f"{r['name']:<10}", style=pal["register"])
                        t.append(f"{r['num']:<9}", style=dim)
                    opts.append(Option(t))
            sc = [x for x in CARD["syscalls"] if match(x["name"], str(x["n"]), "syscall")]
            if sc:
                opts.append(head("Syscall codes (MARS/SPIM)"))
                for k in range(0, len(sc), 2):
                    t = Text()
                    for x in sc[k:k + 2]:
                        t.append(f"{x['n']:>3} ", style=pal["number"])
                        t.append(f"{x['name']:<22}")
                    opts.append(Option(t))
            ex = [x for x in CARD["exceptions"] if match(x["name"], x["code"], "exception", "cause")]
            if ex:
                opts.append(head("Exception causes"))
                for k in range(0, len(ex), 2):
                    t = Text()
                    for x in ex[k:k + 2]:
                        t.append(f"{x['code']:>3} ", style=pal["number"])
                        t.append(f"{x['name']:<22}")
                    opts.append(Option(t))
            if not flt:
                opts.append(head("Notes"))
                for n in CARD["notes"]:
                    opts.append(Option(Text(n, style=dim)))
            if not opts:
                opts.append(Option(Text(f"Nothing on the card matches '{exact or flt}' — try the Basic/Pseudo tabs.", style=dim), disabled=True))
        elif tab in ("basic", "pseudo"):
            want_pseudo = tab == "pseudo"
            for name in ISA_DB.sorted_names:
                for fmt, desc, pseudo in ISA_DB.instructions[name].formats:
                    if pseudo != want_pseudo:
                        continue
                    if flt and flt not in fmt.lower() and flt not in desc.lower():
                        continue
                    opts.append(Option(Group(highlight_text(fmt, self.syntax), Padding(Text(desc, style=dim), (0, 0, 0, 2)))))
        elif tab == "dirs":
            for name, desc in sorted(ISA_DB.directives.items()):
                if flt and flt not in name and flt not in desc.lower():
                    continue
                opts.append(Option(Group(Text(name, style=pal["directive"]), Padding(Text(desc, style=dim), (0, 0, 0, 2)))))
        elif tab == "sys":
            for num, name, args, result in SYSCALLS:
                line = f"{num} {name} {args} {result}".lower()
                if flt and flt not in line:
                    continue
                t = Text()
                t.append(f"{num:>3}  ", style=pal["number"])
                t.append(name, style=Style(bold=True))
                if args:
                    t.append("\n     in:  ", style=dim)
                    t.append_text(highlight_text(args, self.syntax))
                if result:
                    t.append("\n     out: ", style=dim)
                    t.append_text(highlight_text(result, self.syntax))
                opts.append(Option(t))
            opts.append(Option(Text("Load the service number into $v0, arguments into $a0–$a3/$f12, then 'syscall'.", style=dim)))
        elif tab == "keys":
            for k, d in [
                ("F3 · ctrl+b", "Assemble current file (saves first)"), ("F5 · ctrl+r", "Run / continue · pause while running"),
                ("F7 · ctrl+t", "Step one instruction"), ("F8 · ctrl+g", "Step backwards (undo)"),
                ("F9", "Pause"), ("F11", "Stop"), ("F12 · ctrl+l", "Reset program (re-assemble memory)"),
                ("F1", "Reference card — at the instruction under the cursor"), ("F2", "Settings & themes"), ("ctrl+p", "Command palette (every action, themes)"),
                ("ctrl+s / ctrl+o / ctrl+n", "Save / open / new file"),
                ("alt+1…8 · ctrl+pgup/pgdn", "Switch views"), ("F4 · ctrl+e · ☰", "Menu with every action"),
                ("ctrl+j / Esc", "Show / hide registers & console while editing"),
                ("alt+← / alt+→", "Back / forward to where you were (views, files, cursor, jumps); Esc leaves Help"), ("F10", "Zen mode — only code"), ("Tab or → (editor)", "Accept the grey completion"),
                ("Enter / tap again", "Code: toggle breakpoint · Regs/Mem: edit value · Labels: jump"),
                ("ctrl+z / ctrl+y", "Undo / redo in the editor"), ("ctrl+q", "Quit"),
            ]:
                if flt and flt not in (k + d).lower():
                    continue
                opts.append(Option(Group(Text(k, style=Style(bold=True)), Padding(Text(d, style=dim), (0, 0, 0, 2)))))
        else:
            t = Text()
            t.append("MARS TUI", style=Style(bold=True))
            t.append(f" — terminal IDE for MIPS on the MARS {self.bridge.version} engine\n", style=dim)
            t.append("MARS (MIPS Assembler and Runtime Simulator) © 2003-2014 Pete Sanderson and Kenneth Vollmar, MIT license.\n"
                     "https://dpetersanderson.github.io/\n\n", style=dim)
            t.append("Headless notes: MIDI syscalls are silent and dialog syscalls (50-59) are unavailable.\n"
                     "Tools: Bitmap Display and Keyboard & Display MMIO are built in (Tools tab).", style=dim)
            opts.append(Option(t))
        ol.add_options(opts)

    # settings ---------------------------------------------------------------
    def action_settings(self) -> None:
        ui = [t for t in ("amoled", "mars-midnight", "tokyo-night", "dracula", "nord", "gruvbox", "catppuccin-mocha",
                          "monokai", "textual-dark", "mars-classic", "textual-light", "catppuccin-latte", "solarized-light")
              if t in self.available_themes]

        def done(s: dict | None) -> None:
            if s:
                self.settings.update(s)
                self.save_settings()
                self.flash("Settings saved — they apply on the next assemble.", "ok", 3)
        self.push_screen(SettingsScreen(self.settings, self.configs, SYNTAX_THEMES, ui), done)

    def get_system_commands(self, screen):
        yield from super().get_system_commands(screen)
        cmds = [
            ("Assemble", "F3 — assemble the current file", self.action_assemble),
            ("Run / Continue", "F5 — run until exit, breakpoint or pause", self.action_run),
            ("Step", "F7 — execute one instruction", self.action_step),
            ("Step back", "F8 — undo the last instruction", self.action_backstep),
            ("Pause", "F9", self.action_pause),
            ("Reset", "F12 — reset memory and registers", self.action_reset),
            ("Cycle run speed", "max → 1000/s → … → 1/s", self.action_speed),
            ("Toggle breakpoint", "at the cursor (editor) or selected row (code)", self.action_toggle_bp),
            ("Clear all breakpoints", "", self.action_clear_bps),
            ("Settings", "F2 — assembler, simulator, themes", self.action_settings),
            ("New file", "ctrl+n", self.action_new),
            ("Open file", "ctrl+o", self.action_open),
            ("Save", "ctrl+s", self.action_save),
            ("Save as…", "", self.action_save_as),
            ("Close file", "", self.action_close_file),
            ("Memory: go to address", "", self.action_mem_goto),
            ("Memory: cycle hex/dec/ascii", "", self.action_mem_radix),
            ("Clear console", "", self.action_clear_console),
        ]
        for title, help, cb in cmds:
            yield SystemCommand(title, help, cb)
        for v, label in VIEWS:
            yield SystemCommand(f"View: {label}", f"switch to the {label} view", lambda v=v: self.set_view(v))
        for name in SYNTAX_THEMES:
            yield SystemCommand(f"Syntax theme: {name}", "editor colours", lambda n=name: self.set_syntax_theme(n))
        yield SystemCommand("Syntax theme: auto", "match the UI theme", lambda: self.set_syntax_theme("auto"))
        yield SystemCommand("AMOLED black theme", "pure black UI", lambda: setattr(self, "theme", "amoled"))
