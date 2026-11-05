"""MIPS language knowledge: lexer, register names, syscalls, number formatting."""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field

REG_NAMES = [
    "$zero", "$at", "$v0", "$v1", "$a0", "$a1", "$a2", "$a3",
    "$t0", "$t1", "$t2", "$t3", "$t4", "$t5", "$t6", "$t7",
    "$s0", "$s1", "$s2", "$s3", "$s4", "$s5", "$s6", "$s7",
    "$t8", "$t9", "$k0", "$k1", "$gp", "$sp", "$fp", "$ra",
]
REG_SET = {r[1:] for r in REG_NAMES}

# Built-in fallback lists, replaced at runtime by the authoritative tables from MARS.
DIRECTIVES = {
    ".data", ".text", ".word", ".ascii", ".asciiz", ".byte", ".align", ".half",
    ".space", ".double", ".float", ".extern", ".kdata", ".ktext", ".globl",
    ".set", ".eqv", ".macro", ".end_macro", ".include",
}


@dataclass
class InstrInfo:
    name: str
    formats: list[tuple[str, str, bool]] = field(default_factory=list)  # (format, desc, pseudo)

    @property
    def basic(self) -> bool:
        return any(not p for _, _, p in self.formats)


class ISA:
    """Instruction/directive tables, filled from the MARS engine."""

    def __init__(self) -> None:
        self.instructions: dict[str, InstrInfo] = {}
        self.directives: dict[str, str] = {d: "" for d in DIRECTIVES}
        self.sorted_names: list[str] = []

    def load(self, data: dict) -> None:
        self.instructions.clear()
        for item in data.get("instructions", []):
            info = self.instructions.setdefault(item["name"], InstrInfo(item["name"]))
            info.formats.append((item["format"], item["desc"], bool(item["pseudo"])))
        if data.get("directives"):
            self.directives = {d["name"]: d["desc"] for d in data["directives"]}
        self.sorted_names = sorted(self.instructions)

    def kind(self, word: str) -> str | None:
        info = self.instructions.get(word.lower())
        if info is None:
            return None
        return "basic" if info.basic else "pseudo"

    def complete(self, prefix: str) -> str | None:
        p = prefix.lower()
        if not p:
            return None
        import bisect
        i = bisect.bisect_left(self.sorted_names, p)
        if i < len(self.sorted_names) and self.sorted_names[i].startswith(p):
            name = self.sorted_names[i]
            if name != p:
                return name
        return None

    def complete_directive(self, prefix: str) -> str | None:
        p = prefix.lower()
        for d in sorted(self.directives):
            if d.startswith(p) and d != p:
                return d
        return None


ISA_DB = ISA()

# --------------------------------------------------------------------------- lexer

_TOKEN = re.compile(
    r"""
    (?P<comment>\#.*$)
  | (?P<string>"(?:\\.|[^"\\])*"?)
  | (?P<char>'(?:\\.|[^'\\])'?)
  | (?P<register>\$(?:f[0-9]{1,2}|[a-z]+[0-9]?|[0-9]{1,2})\b)
  | (?P<macroarg>%[A-Za-z_]\w*)
  | (?P<directive>\.[A-Za-z_]\w*)
  | (?P<number>[-+]?(?:0[xX][0-9a-fA-F]+|\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\b)
  | (?P<ident>[A-Za-z_][\w.$]*)
  | (?P<colon>:)
  | (?P<punct>[(),+\-])
  | (?P<ws>\s+)
  | (?P<other>.)
    """,
    re.VERBOSE,
)


@dataclass(slots=True)
class Token:
    start: int  # character offset
    end: int
    kind: str  # highlight name without the "mips." prefix
    text: str


def lex_line(line: str, isa: ISA = ISA_DB) -> list[Token]:
    toks: list[Token] = []
    raw = [(m.lastgroup, m.start(), m.end(), m.group()) for m in _TOKEN.finditer(line)]
    expecting_op = True  # next identifier is in mnemonic position
    i = 0
    n = len(raw)
    while i < n:
        kind, s, e, text = raw[i]
        if kind == "ws":
            i += 1
            continue
        if kind == "ident":
            # label definition?  ident followed by optional ws and ':'
            j = i + 1
            while j < n and raw[j][0] == "ws":
                j += 1
            if j < n and raw[j][0] == "colon" and expecting_op:
                toks.append(Token(s, e, "label", text))
                toks.append(Token(raw[j][1], raw[j][2], "punct", ":"))
                i = j + 1
                continue
            if expecting_op:
                k = isa.kind(text)
                toks.append(Token(s, e, "instruction" if k == "basic" else "pseudo" if k == "pseudo" else "macro", text))
                expecting_op = False
            else:
                toks.append(Token(s, e, "symbol", text))
        elif kind == "register":
            name = text[1:]
            if name.startswith("f") and name[1:].isdigit() and int(name[1:]) < 32:
                toks.append(Token(s, e, "fpregister", text))
            elif name in REG_SET or (name.isdigit() and int(name) < 32):
                toks.append(Token(s, e, "register", text))
            else:
                toks.append(Token(s, e, "invalid", text))
            expecting_op = False
        elif kind == "directive":
            toks.append(Token(s, e, "directive" if text.lower() in isa.directives else "invalid", text))
            expecting_op = False
        elif kind in ("string", "char"):
            toks.append(Token(s, e, "string", text))
            expecting_op = False
        elif kind == "number":
            toks.append(Token(s, e, "number", text))
            expecting_op = False
        elif kind == "comment":
            toks.append(Token(s, e, "comment", text))
        elif kind == "macroarg":
            toks.append(Token(s, e, "macroarg", text))
            expecting_op = False
        elif kind in ("punct", "colon"):
            toks.append(Token(s, e, "punct", text))
        else:
            expecting_op = False
        i += 1
    return toks


def mnemonic_at(line: str, col: int) -> tuple[str | None, str | None]:
    """Return (mnemonic, directive) relevant for a cursor position on a line."""
    mn = dr = None
    for t in lex_line(line):
        if t.kind in ("instruction", "pseudo", "macro") and mn is None:
            mn = t.text.lower()
        if t.kind == "directive" and dr is None:
            dr = t.text.lower()
    return mn, dr


# --------------------------------------------------------------------------- syscalls

SYSCALLS: list[tuple[int, str, str, str]] = [
    (1, "print integer", "$a0 = integer to print", ""),
    (2, "print float", "$f12 = float to print", ""),
    (3, "print double", "$f12 = double to print", ""),
    (4, "print string", "$a0 = address of null-terminated string", ""),
    (5, "read integer", "", "$v0 contains integer read"),
    (6, "read float", "", "$f0 contains float read"),
    (7, "read double", "", "$f0 contains double read"),
    (8, "read string", "$a0 = buffer address, $a1 = max chars", "buffer filled"),
    (9, "sbrk (allocate heap memory)", "$a0 = number of bytes", "$v0 = address of allocated memory"),
    (10, "exit (terminate execution)", "", ""),
    (11, "print character", "$a0 = character (low byte)", ""),
    (12, "read character", "", "$v0 contains character read"),
    (13, "open file", "$a0 = filename address, $a1 = flags, $a2 = mode", "$v0 = file descriptor (negative if error)"),
    (14, "read from file", "$a0 = fd, $a1 = buffer, $a2 = max chars", "$v0 = chars read (0 eof, <0 error)"),
    (15, "write to file", "$a0 = fd, $a1 = buffer, $a2 = chars", "$v0 = chars written (<0 error)"),
    (16, "close file", "$a0 = file descriptor", ""),
    (17, "exit2 (terminate with value)", "$a0 = termination result", ""),
    (30, "system time", "", "$a0 = low 32 bits, $a1 = high 32 bits of ms since epoch"),
    (31, "MIDI out", "$a0 = pitch, $a1 = duration ms, $a2 = instrument, $a3 = volume", "(no audio in the TUI)"),
    (32, "sleep", "$a0 = milliseconds", ""),
    (33, "MIDI out synchronous", "$a0 = pitch, $a1 = duration, $a2 = instrument, $a3 = volume", "(no audio in the TUI)"),
    (34, "print integer in hex", "$a0 = integer", ""),
    (35, "print integer in binary", "$a0 = integer", ""),
    (36, "print integer as unsigned", "$a0 = integer", ""),
    (40, "set seed", "$a0 = generator id, $a1 = seed", ""),
    (41, "random int", "$a0 = generator id", "$a0 = random int"),
    (42, "random int range", "$a0 = generator id, $a1 = upper bound", "$a0 = random int in [0, bound)"),
    (43, "random float", "$a0 = generator id", "$f0 = float in [0, 1)"),
    (44, "random double", "$a0 = generator id", "$f0 = double in [0, 1)"),
    (50, "ConfirmDialog", "$a0 = message address", "$a0 = 0 yes, 1 no, 2 cancel (headless: dialogs unavailable)"),
    (51, "InputDialogInt", "$a0 = message address", "(headless: dialogs unavailable)"),
    (52, "InputDialogFloat", "$a0 = message address", "(headless: dialogs unavailable)"),
    (53, "InputDialogDouble", "$a0 = message address", "(headless: dialogs unavailable)"),
    (54, "InputDialogString", "$a0 = message, $a1 = buffer, $a2 = max chars", "(headless: dialogs unavailable)"),
    (55, "MessageDialog", "$a0 = message address, $a1 = type", "(headless: dialogs unavailable)"),
    (56, "MessageDialogInt", "$a0 = message, $a1 = int", "(headless: dialogs unavailable)"),
    (57, "MessageDialogFloat", "$a0 = message, $f12 = float", "(headless: dialogs unavailable)"),
    (58, "MessageDialogDouble", "$a0 = message, $f12 = double", "(headless: dialogs unavailable)"),
    (59, "MessageDialogString", "$a0 = message, $a1 = string", "(headless: dialogs unavailable)"),
]

# --------------------------------------------------------------------------- formatting


def u32(v: int) -> int:
    return v & 0xFFFFFFFF


def s32(v: int) -> int:
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def hex32(v: int) -> str:
    return f"0x{u32(v):08x}"


def fmt_word(v: int, mode: str) -> str:
    if mode == "hex":
        return hex32(v)
    if mode == "ascii":
        b = u32(v).to_bytes(4, "little")
        return "".join(ch(c) for c in b)
    return str(s32(v))


def ch(c: int) -> str:
    if c == 0:
        return "\\0"
    if c == 10:
        return "\\n"
    if c == 9:
        return "\\t"
    if 32 <= c < 127:
        return chr(c)
    return "."


def as_float(v: int) -> float:
    return struct.unpack("<f", struct.pack("<I", u32(v)))[0]


def as_double(lo: int, hi: int) -> float:
    return struct.unpack("<d", struct.pack("<II", u32(lo), u32(hi)))[0]


def fmt_float(x: float) -> str:
    if x != x:
        return "NaN"
    if x in (float("inf"), float("-inf")):
        return "∞" if x > 0 else "-∞"
    s = f"{x:.7g}"
    return s


def parse_int(text: str) -> int:
    t = text.strip().replace("_", "")
    if not t:
        raise ValueError("empty value")
    if t.lower().startswith(("0x", "-0x")):
        neg = t.startswith("-")
        v = int(t.lstrip("-")[2:], 16)
        return -v if neg else v
    if t.lower().startswith("0b"):
        return int(t[2:], 2)
    if len(t) == 3 and t[0] == t[2] == "'":
        return ord(t[1])
    return int(t, 10)
