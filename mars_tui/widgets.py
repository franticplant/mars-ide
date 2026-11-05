"""Small borderless widgets used throughout the UI."""
from __future__ import annotations

from math import ceil

from rich.color import Color
from rich.highlighter import Highlighter
from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual import events
from textual.containers import Horizontal
from textual.markup import escape
from textual.message import Message
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import DataTable, Static


class Bar(Horizontal):
    """One-line (wrapping) bar of tappable items with an optional right-hand status."""

    DEFAULT_CSS = """
    Bar { height: auto; background: $panel; }
    Bar > .bar-left { width: 1fr; height: auto; padding: 0 0; }
    Bar > .bar-right { width: auto; height: 1; padding: 0 1; color: $text-muted; }
    """

    def __init__(self, id: str | None = None, classes: str = "") -> None:
        super().__init__(id=id, classes=classes)
        self._left = Static("", classes="bar-left", markup=True)
        self._right = Static("", classes="bar-right", markup=True)

    def compose(self):
        yield self._left
        yield self._right

    def set_items(self, items: list[tuple], right: str = "") -> None:
        """items: (label, action, state) where state in {"", "active", "off", "warn"}."""
        parts = []
        for item in items:
            label, action, state = (item + ("",))[:3]
            lab = escape(label)
            if state == "active":
                parts.append(f"[@click={action}][b $text on $primary-muted] {lab} [/][/]")
            elif state == "off":
                parts.append(f"[@click={action}][$text-disabled] {lab} [/][/]")
            elif state == "warn":
                parts.append(f"[@click={action}][b $warning] {lab} [/][/]")
            elif state == "accent":
                parts.append(f"[@click={action}][b $accent] {lab} [/][/]")
            else:
                parts.append(f"[@click={action}] {lab} [/]")
        self._left.update("".join(parts))
        self._right.update(right)


class Table(DataTable):
    """DataTable without chrome; distinguishes 'tap to move' from 'tap again to activate'."""

    DEFAULT_CSS = """
    Table { border: none; padding: 0; background: $surface; scrollbar-size-vertical: 1; scrollbar-size-horizontal: 1; }
    Table:focus { border: none; background-tint: transparent; }
    Table > .datatable--header { background: $panel; color: $text-muted; text-style: bold; }
    Table > .datatable--cursor { background: $primary 40%; color: $text; }
    Table:focus > .datatable--cursor { background: $primary 60%; }
    Table > .datatable--hover { background: $boost; }
    """

    def __init__(self, rows_only: bool = True, **kw) -> None:
        super().__init__(**kw)
        self.rows_only = rows_only
        self._pre = None
        self._clicked = False

    async def _on_click(self, event: events.Click) -> None:
        self._pre = self.cursor_coordinate
        self._clicked = True
        await super()._on_click(event)

    def take_tap(self) -> bool:
        """True if the selection event should activate (Enter key, or tap on the already-selected cell)."""
        if not self._clicked:
            return True
        self._clicked = False
        pre, now = self._pre, self.cursor_coordinate
        if pre is None:
            return False
        return pre.row == now.row if self.rows_only else pre == now


class ConsoleHighlighter(Highlighter):
    def __init__(self, styles: dict[str, Style] | None = None) -> None:
        self.styles = styles or {}

    def highlight(self, text: Text) -> None:
        s = text.plain
        st = self.styles
        if s.startswith("-- ") and s.endswith(" --"):
            text.stylize(st.get("meta", Style(dim=True, italic=True)))
        elif s.startswith(("Error", "Runtime", "✗")):
            text.stylize(st.get("error", Style(color="red", bold=True)))
        elif s.startswith(("Warning", "⚠")):
            text.stylize(st.get("warn", Style(color="yellow")))
        elif s.startswith(("Assemble:", "✓", "▸")):
            text.stylize(st.get("info", Style(color="cyan")))


class BitmapView(Widget):
    """Renders the MARS Bitmap Display with half-block characters (2 pixels per cell)."""

    DEFAULT_CSS = "BitmapView { height: 1fr; background: $background; }"

    def __init__(self, **kw) -> None:
        super().__init__(**kw)
        self.pixels: list[int] = []
        self.gw = 64
        self.gh = 32
        self._styles: dict[tuple[int, int], Style] = {}

    def set_image(self, pixels: list[int], gw: int, gh: int) -> None:
        self.pixels, self.gw, self.gh = pixels, gw, gh
        self.refresh()

    def _style(self, top: int, bot: int) -> Style:
        key = (top, bot)
        st = self._styles.get(key)
        if st is None:
            if len(self._styles) > 8192:
                self._styles.clear()
            st = Style.from_color(
                Color.from_rgb((top >> 16) & 255, (top >> 8) & 255, top & 255),
                Color.from_rgb((bot >> 16) & 255, (bot >> 8) & 255, bot & 255),
            )
            self._styles[key] = st
        return st

    def _scale(self) -> int:
        w, h = max(1, self.size.width), max(1, self.size.height)
        return max(1, ceil(self.gw / w), ceil(self.gh / (2 * h)))

    def render_line(self, y: int) -> Strip:
        w = self.size.width
        step = self._scale()
        ow = ceil(self.gw / step)
        oh = ceil(self.gh / step)
        if 2 * y >= oh or not self.pixels:
            return Strip.blank(w)
        pad = max(0, (w - ow) // 2)
        segs = [Segment(" " * pad)] if pad else []
        px, gw, n = self.pixels, self.gw, len(self.pixels)
        r0 = (2 * y) * step
        r1 = (2 * y + 1) * step
        for x in range(ow):
            c = x * step
            i0 = r0 * gw + c
            i1 = r1 * gw + c
            top = px[i0] & 0xFFFFFF if i0 < n else 0
            bot = px[i1] & 0xFFFFFF if (i1 < n and r1 < self.gh) else 0
            segs.append(Segment("▀", self._style(top, bot)))
        return Strip(segs).adjust_cell_length(w)


class KeyCapture(Static, can_focus=True):
    """Focus it and type: each key is delivered to the MMIO keyboard."""

    DEFAULT_CSS = """
    KeyCapture { height: auto; padding: 0 1; background: $boost; color: $text-muted; }
    KeyCapture:focus { background: $primary 30%; color: $text; }
    """

    class Typed(Message):
        def __init__(self, code: int) -> None:
            self.code = code
            super().__init__()

    def on_key(self, event: events.Key) -> None:
        key = event.key
        if key.startswith("f") and key[1:].isdigit():
            return  # leave function keys to the app
        if key.startswith("ctrl+") or key.startswith("alt+"):
            return
        code = None
        if key == "enter":
            code = 10
        elif key == "tab":
            code = 9
        elif key == "backspace":
            code = 8
        elif key == "escape":
            return
        elif event.character and len(event.character) == 1 and ord(event.character) < 256:
            code = ord(event.character)
        if code is not None:
            event.stop()
            event.prevent_default()
            self.post_message(self.Typed(code))
