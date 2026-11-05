"""MIPS-aware editor: regex highlighting, error marks, inline mnemonic completion."""
from __future__ import annotations

from collections import defaultdict

from rich.style import Style
from rich.text import Text
from textual.widgets import TextArea
from textual.widgets.text_area import TextAreaTheme

from .mips import ISA_DB, lex_line

# IDE-like syntax palettes.  Each maps token kinds -> colour; weights are added below.
_P = {
    #               instr      pseudo     directive  register   fpreg      label      symbol     number     string     comment    punct      macro      error      errbg      warnbg     pcbg
    "tokyo-night": ("#7aa2f7", "#2ac3de", "#bb9af7", "#f7768e", "#ff9e9e", "#e0af68", "#73daca", "#ff9e64", "#9ece6a", "#6b7394", "#89ddff", "#c0caf5", "#ff5370", "#3d1f2a", "#3a3320", "#1f3a2c"),
    "dracula":     ("#ff79c6", "#8be9fd", "#bd93f9", "#ffb86c", "#ffca8c", "#50fa7b", "#8be9fd", "#bd93f9", "#f1fa8c", "#6272a4", "#f8f8f2", "#f8f8f2", "#ff5555", "#4a2433", "#45422a", "#25432f"),
    "monokai":     ("#f92672", "#66d9ef", "#ae81ff", "#fd971f", "#fdb54f", "#a6e22e", "#66d9ef", "#ae81ff", "#e6db74", "#75715e", "#f8f8f2", "#f8f8f2", "#f92672", "#47212c", "#45412a", "#2d3f20"),
    "nord":        ("#81a1c1", "#5fb8a8", "#b48ead", "#d08770", "#e0a080", "#ebcb8b", "#8fbcbb", "#b48ead", "#a3be8c", "#616e88", "#eceff4", "#d8dee9", "#bf616a", "#43303a", "#45413a", "#2f4436"),
    "gruvbox":     ("#fb4934", "#fe8019", "#d3869b", "#83a598", "#8ec07c", "#fabd2f", "#8ec07c", "#d3869b", "#b8bb26", "#928374", "#ebdbb2", "#ebdbb2", "#fb4934", "#4a2622", "#4a4022", "#32402a"),
    "catppuccin":  ("#89b4fa", "#94e2c5", "#cba6f7", "#f38ba8", "#eba0ac", "#f9e2af", "#94e2d5", "#fab387", "#a6e3a1", "#7f849c", "#89dceb", "#cdd6f4", "#f38ba8", "#45273a", "#45402f", "#27402f"),
    "amoled":      ("#5fb3ff", "#5ee8c0", "#d68bff", "#ff5c8a", "#ff8fb0", "#ffd24d", "#4dffc3", "#ff9b4d", "#a8ff60", "#5c6370", "#9aa5b1", "#e6e6e6", "#ff3b5c", "#2a0010", "#241c00", "#002a12"),
    "light":       ("#1d4ed8", "#0e7490", "#7e22ce", "#c2410c", "#be123c", "#a16207", "#0f766e", "#b45309", "#15803d", "#7c8593", "#475569", "#334155", "#dc2626", "#fde2e2", "#fdf3d0", "#dcfce7"),
    "mars-classic":("#0000ff", "#007a7a", "#ff00ff", "#ff0000", "#c00040", "#000000", "#004080", "#000000", "#008000", "#008000", "#000000", "#202020", "#ff0000", "#ffd0d0", "#fff0c0", "#ffff99"),
}
_KINDS = ("instruction", "pseudo", "directive", "register", "fpregister", "label", "symbol", "number",
          "string", "comment", "punct", "macro", "invalid")


def _build(colors: tuple) -> dict[str, Style]:
    c = dict(zip(_KINDS, colors[:13]))
    errbg, warnbg, pcbg = colors[13:16]
    pal = {
        "instruction": Style(color=c["instruction"], bold=True),
        "pseudo": Style(color=c["pseudo"]),          # real instructions bold, pseudo regular
        "directive": Style(color=c["directive"]),
        "register": Style(color=c["register"]),
        "fpregister": Style(color=c["fpregister"], italic=True),
        "label": Style(color=c["label"], bold=True),
        "symbol": Style(color=c["symbol"]),
        "number": Style(color=c["number"]),
        "string": Style(color=c["string"]),
        "comment": Style(color=c["comment"], italic=True),
        "punct": Style(color=c["punct"]),
        "macro": Style(color=c["macro"], italic=True),
        "macroarg": Style(color=c["macro"], italic=True, underline=True),
        "invalid": Style(color=c["invalid"], underline=True),
        "errorline": Style(bgcolor=errbg),
        "warnline": Style(bgcolor=warnbg),
        "errortok": Style(color="#ffffff", bgcolor=c["invalid"], bold=True),
        "pcline": Style(bgcolor=pcbg),
    }
    return pal


PALETTES: dict[str, dict[str, Style]] = {name: _build(cols) for name, cols in _P.items()}
SYNTAX_THEMES = list(PALETTES)

# Which syntax palette goes with which Textual UI theme ("auto" mode).
UI_TO_SYNTAX = {
    "tokyo-night": "tokyo-night", "textual-dark": "tokyo-night", "dracula": "dracula",
    "monokai": "monokai", "nord": "nord", "gruvbox": "gruvbox", "flexoki": "gruvbox",
    "catppuccin-mocha": "catppuccin", "catppuccin-frappe": "catppuccin", "catppuccin-macchiato": "catppuccin",
    "rose-pine": "catppuccin", "rose-pine-moon": "catppuccin", "atom-one-dark": "tokyo-night",
    "mars-classic": "mars-classic", "mars-midnight": "tokyo-night", "amoled": "amoled",
}


def syntax_for_ui(ui_theme: str, dark: bool) -> str:
    return UI_TO_SYNTAX.get(ui_theme, "tokyo-night" if dark else "light")


def make_textarea_theme(name: str) -> TextAreaTheme:
    return TextAreaTheme(
        name=f"mips-{name}",
        syntax_styles={f"mips.{k}": v for k, v in PALETTES[name].items()},
    )


def highlight_text(line: str, mode: str = "tokyo-night") -> Text:
    """Rich Text with MIPS highlighting (for tables and logs)."""
    pal = PALETTES[mode]
    text = Text(line, no_wrap=True, overflow="ellipsis")
    for t in lex_line(line):
        st = pal.get(t.kind)
        if st:
            text.stylize(st, t.start, t.end)
    return text


class MipsEditor(TextArea):
    """TextArea with a pure-Python MIPS highlighter (no tree-sitter needed)."""

    DEFAULT_CSS = """
    MipsEditor { border: none; padding: 0; }
    MipsEditor:focus { border: none; }
    """

    def __init__(self, text: str = "", path: str | None = None, **kw) -> None:
        self._line_cache_hl: dict[str, list[tuple[int, int | None, str]]] = {}
        self.exec_line: int | None = None
        self.marks: dict[int, tuple[str, int, str]] = {}  # row -> (kind, col, msg)
        super().__init__(
            text,
            show_line_numbers=True,
            tab_behavior="indent",
            soft_wrap=False,
            highlight_cursor_line=True,
            **kw,
        )
        self.path = path
        self.saved_text = text
        self.indent_type = "spaces"
        self.indent_width = 4
        for m in SYNTAX_THEMES:
            self.register_theme(make_textarea_theme(m))
        self.theme = "mips-tokyo-night"

    # --------------------------------------------------------------- state
    @property
    def modified(self) -> bool:
        return self.text != self.saved_text

    def set_marks(self, marks: dict[int, tuple[str, int, str]]) -> None:
        self.marks = marks
        self._build_highlight_map()
        self.refresh()

    # --------------------------------------------------------- highlighting
    def _build_highlight_map(self) -> None:  # noqa: D401 - overrides TextArea internals
        self._line_cache.clear()
        highlights = self._highlights
        highlights.clear()
        cache = self._line_cache_hl
        if len(cache) > 20000:
            cache.clear()
        doc = self.document
        for row in range(doc.line_count):
            line = doc.get_line(row)
            spans = cache.get(line)
            if spans is None:
                spans = []
                if line.isascii():
                    for t in lex_line(line):
                        spans.append((t.start, t.end, f"mips.{t.kind}"))
                else:
                    for t in lex_line(line):
                        s = len(line[: t.start].encode())
                        e = s + len(line[t.start : t.end].encode())
                        spans.append((s, e, f"mips.{t.kind}"))
                cache[line] = spans
            mark = self.marks.get(row)
            if row == self.exec_line and not mark:
                highlights[row] = [(0, None, "mips.pcline"), *spans]
                continue
            if mark:
                kind, col, _ = mark
                lst = [(0, None, "mips.errorline" if kind == "error" else "mips.warnline")]
                lst.extend(spans)
                if kind == "error" and col > 0:
                    # mark the offending token
                    b = len(line[: col - 1].encode())
                    end = b
                    while end < len(line) and not line[end].isspace() and line[end] not in ",()":
                        end += 1
                    if end == b:
                        end = min(len(line), b + 1)
                    lst.append((b, end, "mips.errortok"))
                highlights[row] = lst
            elif spans:
                highlights[row] = list(spans)

    # ----------------------------------------------------------- completion
    def update_suggestion(self) -> None:
        """Offer ghost-text completion for the mnemonic/directive being typed."""
        self.suggestion = ""
        if self.selection.start != self.selection.end:
            return
        row, col = self.cursor_location
        line = self.document.get_line(row)
        if col != len(line):
            return
        head = line[:col]
        stripped = head.split("#", 1)[0]
        if stripped != head:
            return
        # strip leading labels
        body = stripped
        while ":" in body:
            body = body.split(":", 1)[1]
        word = body.lstrip()
        if not word or " " in word or "\t" in word:
            return
        if word.startswith("."):
            c = ISA_DB.complete_directive(word)
        elif word[0].isalpha() and len(word) >= 2:
            c = ISA_DB.complete(word)
        else:
            c = None
        if c:
            self.suggestion = c[len(word):]

    async def _on_key(self, event) -> None:  # Tab accepts a pending completion, IDE-style
        if event.key == "escape" and hasattr(self.app, "action_escape"):
            st = getattr(self.app, "settings", {})
            if st.get("zen") or st.get("panels"):
                event.stop()
                event.prevent_default()
                self.app.action_escape()
                return
        if event.key == "tab" and self.suggestion and not self.read_only:
            event.stop()
            event.prevent_default()
            self.insert(self.suggestion)
            self.suggestion = ""
            return
        await super()._on_key(event)
