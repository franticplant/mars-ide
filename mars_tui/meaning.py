"""What a register value means right now (shared ideas with web/js/meaning.js)."""
from __future__ import annotations

from .mips import REG_NAMES, SYSCALLS, u32

ROLE = {
    0: "constant zero", 1: "assembler temporary (pseudo-instructions)", 2: "return value · syscall number",
    3: "second return value", 4: "argument 1", 5: "argument 2", 6: "argument 3", 7: "argument 4",
    26: "kernel reserved", 27: "kernel reserved", 28: "global pointer", 29: "stack pointer",
    30: "frame pointer", 31: "return address",
}
for _i in (8, 9, 10, 11, 12, 13, 14, 15, 24, 25):
    ROLE[_i] = "temporary (caller-saved)"
for _i in range(16, 24):
    ROLE[_i] = "saved (callee-saved)"

SYS = {n: (name, args, res) for n, name, args, res in SYSCALLS}
STACK_TOP = 0x7FFFEFFC


def region(a: int, segments: dict, sp: int) -> str | None:
    a = u32(a)
    heap = u32(segments.get("heap", 0x10040000))
    data = u32(segments.get("data", 0x10010000))
    ext = u32(segments.get("extern", 0x10000000))
    text = u32(segments.get("text", 0x00400000))
    if a >= 0xFFFF0000:
        return "MMIO"
    if a >= 0x90000000:
        return "kernel data"
    if a >= 0x80000000:
        return "kernel text"
    if 0x7F000000 <= a <= 0x7FFFFFFF:
        return "stack" if a >= u32(sp) else "below $sp"
    if heap <= a < 0x10400000:
        return "heap"
    if data <= a < heap:
        return ".data"
    if ext <= a < data:
        return ".extern"
    if text <= a < 0x10000000:
        return ".text"
    return None


def label_for(a: int, labels: list[dict]) -> str | None:
    a = u32(a)
    best = None
    for lab in labels:
        la = u32(lab["addr"])
        if la <= a and a - la < 4096 and (best is None or la > u32(best["addr"])):
            best = lab
    if not best:
        return None
    off = a - u32(best["addr"])
    return best["name"] + (f"+{off}" if off else "")


def syscall_arg(reg: str, v0: int) -> str | None:
    s = SYS.get(v0)
    if not s or not s[1]:
        return None
    for part in s[1].split(", $"):
        part = part if part.startswith("$") else "$" + part
        name, _, desc = part.partition(" = ")
        if name.strip() == reg:
            return f"{desc} for syscall {v0} ({s[0]})"
    return None


def explain_gpr(n: int, st: dict, segments: dict, labels: list[dict], rows: list[dict], addr_index: dict) -> tuple[list[str], int | None]:
    """Returns (phrases, address-to-read-a-string-from or None)."""
    v = st["gpr"][n]
    out = [ROLE.get(n, "")]
    pc_i = addr_index.get(st.get("pc"))
    next_sys = pc_i is not None and rows[pc_i]["basic"].startswith("syscall")
    v0 = st["gpr"][2]
    if n == 2 and v in SYS:
        name, _, res = SYS[v]
        out.append(f"syscall {v} = {name}" + (f" → {res}" if res else "") + (" (next!)" if next_sys else ""))
    if 4 <= n <= 7:
        a = syscall_arg(REG_NAMES[n], v0)
        if a:
            out.append(a)
    if n == 31:
        i = addr_index.get(v)
        lab = label_for(v, labels)
        if i is not None or lab:
            src = f" ({rows[i]['file']}:{rows[i]['line']})" if i is not None and rows[i].get("line") else ""
            out.append(f"returns to {lab or hex(u32(v))}{src}")
        return out, None
    if n in (29, 30):
        depth = STACK_TOP - u32(v)
        if 0 <= depth < 0x1000000:
            out.append(f"{depth} bytes ({depth // 4} words) on the stack" if depth else "stack empty")
        return out, None
    if n in (0, 28):
        return out, None
    reg = region(v, segments, st["gpr"][29]) if u32(v) > 0x1000 else None
    if reg:
        lab = label_for(v, labels)
        out.append(f"→ {reg}" + (f" · {lab}" if lab else ""))
        if reg in (".text", "kernel text"):
            i = addr_index.get(v)
            if i is not None:
                out.append(rows[i]["basic"])
            return out, None
        if reg != "MMIO":
            return out, u32(v)
    elif 32 <= u32(v) < 127:
        out.append(f"char '{chr(u32(v))}'")
    return out, None


def c_string(words: list[int], start: int) -> str | None:
    bs = bytearray()
    for w in words:
        bs += u32(w).to_bytes(4, "little")
    s = []
    for c in bs[start & 3:]:
        if c == 0:
            break
        if c == 10:
            s.append("\\n")
        elif 32 <= c < 127:
            s.append(chr(c))
        else:
            return None
    t = "".join(s)
    if not t:
        return None
    return '"' + (t[:50] + "…" if len(t) > 50 else t) + '"'
