"""Modal screens: prompt, open file, settings."""
from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Checkbox, DirectoryTree, Input, Static

from .widgets import Bar

MODAL_CSS = """
ModalScreen { align: center top; background: $background 70%; }
.dialog { width: 100%; max-width: 76; height: auto; max-height: 100%; background: $panel; padding: 1 2; margin-top: 1; }
.dialog .title { text-style: bold; color: $accent; margin-bottom: 1; }
.dialog .hint { color: $text-muted; margin-top: 1; }
.dialog Input { border: none; height: 1; padding: 0 1; background: $surface; margin-bottom: 1; }
.dialog Input:focus { border: none; background: $boost; }
.dialog Checkbox { border: none; padding: 0; height: 1; background: transparent; margin: 0; }
.dialog Checkbox:focus { border: none; background: $boost; }
.dialog Checkbox > .toggle--button { background: $surface; }
.dialog .section { color: $text-muted; text-style: bold; margin-top: 1; }
.dialog .label { color: $text-muted; }
"""


class PromptScreen(ModalScreen[str | None]):
    DEFAULT_CSS = MODAL_CSS
    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    def __init__(self, title: str, value: str = "", placeholder: str = "", help: str = "") -> None:
        super().__init__()
        self._title, self._value, self._ph, self._help = title, value, placeholder, help

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Static(self._title, classes="title", markup=False)
            yield Input(self._value, placeholder=self._ph, id="prompt-input")
            hint = "[@click=screen.ok]Enter ✓ ok[/]   [@click=screen.cancel]Esc ✗ cancel[/]"
            if self._help:
                hint = self._help + "\n" + hint
            yield Static(hint, classes="hint")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def action_ok(self) -> None:
        self.dismiss(self.query_one(Input).value)

    def action_cancel(self) -> None:
        self.dismiss(None)


class AsmTree(DirectoryTree):
    EXT = {".asm", ".s", ".inc", ".mips", ".txt"}
    DEFAULT_CSS = "AsmTree { height: 1fr; border: none; background: $surface; padding: 0; }"

    def filter_paths(self, paths):
        return [p for p in paths if not p.name.startswith(".") and (p.is_dir() or p.suffix.lower() in self.EXT)]


class OpenScreen(ModalScreen[str | None]):
    DEFAULT_CSS = MODAL_CSS + """
    OpenScreen .dialog { height: 90%; }
    """
    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    def __init__(self, root: str, title: str = "Open file") -> None:
        super().__init__()
        self.root = root
        self._title = title

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Static(self._title, classes="title")
            yield Input(self.root.rstrip("/") + "/", placeholder="path/to/file.asm (new files are created)", id="path")
            yield AsmTree(self.root)
            yield Static("Tap a file, or type a path and press Enter.   [@click=screen.cancel]Esc ✗ cancel[/]", classes="hint")

    def on_mount(self) -> None:
        self.query_one(AsmTree).focus()

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self.dismiss(str(event.path))

    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        self.query_one("#path", Input).value = str(event.path).rstrip("/") + "/"

    def on_input_submitted(self, event: Input.Submitted) -> None:
        v = event.value.strip()
        if v and not v.endswith("/"):
            self.dismiss(v)

    def action_cancel(self) -> None:
        self.dismiss(None)


BOOL_SETTINGS = [
    ("pseudo", "Permit extended (pseudo) instructions and formats"),
    ("delayed_branching", "Delayed branching"),
    ("self_modifying", "Self-modifying code"),
    ("warnings_are_errors", "Assembler warnings are considered errors"),
    ("start_at_main", "Initialize program counter to global 'main' if defined"),
    ("assemble_all", "Assemble all files in directory"),
    ("bare_machine", "Bare machine (no pseudo-ops, no $ names) — not recommended"),
    ("auto_save", "Save files automatically before assembling"),
]


class SettingsScreen(ModalScreen[dict | None]):
    DEFAULT_CSS = MODAL_CSS + """
    SettingsScreen .dialog { height: auto; max-height: 95%; }
    SettingsScreen VerticalScroll { height: auto; max-height: 100%; }
    SettingsScreen Bar { background: $panel; }
    """
    BINDINGS = [Binding("escape", "close", "Close", show=False), Binding("f2", "close", show=False)]

    def __init__(self, settings: dict, configs: list[dict], syntax_themes: list[str], ui_themes: list[str]) -> None:
        super().__init__()
        self.s = dict(settings)
        self.configs = configs or [{"id": "Default", "name": "Default"}]
        self.syntax_themes = ["auto", *syntax_themes]
        self.ui_themes = ui_themes

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Static("Settings", classes="title")
            with VerticalScroll():
                yield Static("Assembler & simulator", classes="section")
                for key, label in BOOL_SETTINGS:
                    yield Checkbox(label, bool(self.s.get(key)), id=f"cb-{key}")
                yield Static("Memory configuration", classes="section")
                yield Bar(id="memcfg")
                yield Static("Program arguments (passed to main in $a0/$a1)", classes="label")
                yield Input(self.s.get("program_args", ""), id="in-program_args", placeholder="arg1 arg2 …")
                yield Static("Exception handler file (merged into every assembly)", classes="label")
                yield Input(self.s.get("exception_handler", ""), id="in-exception_handler", placeholder="path/to/handler.asm")
                yield Static("Appearance", classes="section")
                yield Bar(id="uitheme")
                yield Bar(id="syntheme")
            yield Static("Changes apply on the next assemble.   [@click=screen.close]Esc ✓ close[/]", classes="hint")

    def on_mount(self) -> None:
        self._render_bars()
        self.query_one(Checkbox).focus()

    def _render_bars(self) -> None:
        cur = self.s.get("memory_config", "Default")
        self.query_one("#memcfg", Bar).set_items(
            [(c["name"], f"screen.memcfg('{c['id']}')", "active" if c["id"] == cur else "") for c in self.configs])
        ui = self.s.get("ui_theme")
        self.query_one("#uitheme", Bar).set_items(
            [("UI:", "screen.noop", "off")] + [(t, f"screen.uitheme('{t}')", "active" if t == ui else "") for t in self.ui_themes])
        st = self.s.get("syntax_theme", "auto")
        self.query_one("#syntheme", Bar).set_items(
            [("Syntax:", "screen.noop", "off")] + [(t, f"screen.syntheme('{t}')", "active" if t == st else "") for t in self.syntax_themes])

    def action_noop(self) -> None:
        pass

    def action_memcfg(self, ident: str) -> None:
        self.s["memory_config"] = ident
        self._render_bars()

    def action_uitheme(self, name: str) -> None:
        self.s["ui_theme"] = name
        self.app.theme = name
        self._render_bars()

    def action_syntheme(self, name: str) -> None:
        self.s["syntax_theme"] = name
        self.app.set_syntax_theme(name)  # type: ignore[attr-defined]
        self._render_bars()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        key = (event.checkbox.id or "")[3:]
        self.s[key] = event.value

    def on_input_changed(self, event: Input.Changed) -> None:
        key = (event.input.id or "")[3:]
        self.s[key] = event.value

    def action_close(self) -> None:
        self.dismiss(self.s)


class DialogScreen(ModalScreen[str | None]):
    """Front end for MARS dialog syscalls (50-59)."""
    DEFAULT_CSS = MODAL_CSS
    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    def __init__(self, kind: str, message: str) -> None:
        super().__init__()
        self.kind, self.message = kind, message

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Static("Program dialog", classes="title")
            yield Static(self.message, markup=False)
            if self.kind in ("int", "float", "double", "string"):
                yield Input(placeholder=f"{self.kind} value", id="dlg-input")
                yield Static("[@click=screen.ok]Enter ✓ OK[/]   [@click=screen.cancel]Esc ✗ Cancel[/]", classes="hint")
            elif self.kind == "confirm":
                yield Static("[@click=screen.answer('0')] Yes [/]   [@click=screen.answer('1')] No [/]   "
                             "[@click=screen.answer('2')] Cancel [/]   (y / n / Esc)", classes="hint")
            else:
                yield Static("[@click=screen.ok]Enter ✓ OK[/]", classes="hint")

    def on_mount(self) -> None:
        for i in self.query(Input):
            i.focus()

    def on_key(self, event) -> None:
        if self.kind == "confirm" and event.key in ("y", "n"):
            self.dismiss("0" if event.key == "y" else "1")
        elif self.kind == "message" and event.key == "enter":
            self.dismiss("")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def action_answer(self, v: str) -> None:
        self.dismiss(v)

    def action_ok(self) -> None:
        inp = self.query(Input)
        self.dismiss(inp.first().value if inp else "")

    def action_cancel(self) -> None:
        self.dismiss("2" if self.kind == "confirm" else None)


class MenuScreen(ModalScreen[str | None]):
    """Grouped action menu (☰): every command reachable by tap or arrow keys."""
    DEFAULT_CSS = MODAL_CSS + """
    MenuScreen { align: left top; }
    MenuScreen .dialog { max-width: 52; height: auto; max-height: 100%; margin: 1 0 0 0; padding: 0 1; }
    MenuScreen OptionList { border: none; background: $panel; height: auto; max-height: 100%; padding: 0; }
    MenuScreen OptionList:focus { border: none; }
    """
    BINDINGS = [Binding("escape", "cancel", show=False), Binding("f4", "cancel", show=False)]

    def __init__(self, groups) -> None:
        super().__init__()
        self.groups = groups
        self.actions: list[str] = []

    def compose(self) -> ComposeResult:
        from rich.text import Text
        from textual.widgets import OptionList
        from textual.widgets.option_list import Option
        opts = []
        for title, items in self.groups:
            opts.append(Option(Text(title.upper(), style="bold dim"), disabled=True))
            for label, action, key in items:
                t = Text("  " + label)
                if key:
                    t.append("  " + key, style="dim")
                opts.append(Option(t, id=f"a{len(self.actions)}"))
                self.actions.append(action)
        with Vertical(classes="dialog"):
            yield OptionList(*opts)

    def on_mount(self) -> None:
        from textual.widgets import OptionList
        ol = self.query_one(OptionList)
        ol.focus()
        for i in range(ol.option_count):
            if not ol.get_option_at_index(i).disabled:
                ol.highlighted = i
                break

    def on_option_list_option_selected(self, event) -> None:
        self.dismiss(self.actions[int(event.option.id[1:])])

    def on_click(self, event) -> None:
        if event.widget is self:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)
