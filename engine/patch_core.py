#!/usr/bin/env python3
"""Build headless MARS core sources from the official MARS 4.5 jar.

  python3 engine/patch_core.py vendor/Mars4_5.jar build/core-src

Extracts the MIT-licensed MARS sources (minus the Swing IDE and tools), removes every
java.awt / javax.swing / javax.sound dependency, and lays engine/overlay/ on top.
The result compiles against plain java.base, so it runs on desktop JVMs and compiles to JavaScript with TeaVM.
"""
from __future__ import annotations

import re
import shutil
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

SKIP_PREFIX = ("mars/venus/", "mars/tools/")
SKIP_FILES = {
    "mars/MarsLaunch.java", "mars/MarsSplashScreen.java", "mars/util/EditorFont.java",
    "mars/Settings.java", "mars/mips/instructions/syscalls/ToneGenerator.java",
}
RESOURCES = ["PseudoOps.txt", "Config.properties", "Syscall.properties", "Settings.properties", "MARSlicense.txt"]


def remove_block(src: str, start_pattern: str) -> str:
    """Remove every member starting at a regex match through its balanced closing brace."""
    while True:
        m = re.search(start_pattern, src)
        if not m:
            return src
        i = m.end() - 1  # patterns end with the opening brace
        depth = 0
        j = i
        while j < len(src):
            if src[j] == "{":
                depth += 1
            elif src[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        src = src[:m.start()] + src[j + 1:]


def patch(path: str, src: str, syscalls: list[str]) -> str:
    src = re.sub(r"(?m)^\s*import\s+(javax\.swing|java\.awt|javax\.sound)[\w.]*(\.\*)?\s*;\s*$", "", src)
    # portability (TeaVM): no System.exit, console via mars.ext.IO, resources compiled in
    src = src.replace("System.exit(", "mars.ext.IO.exit(")
    src = re.sub(r"this\.getClass\(\)\.getResourceAsStream\(", "mars.ext.IO.resource(", src)
    src = re.sub(r"PropertiesFile\.class\.getResourceAsStream\(", "mars.ext.IO.resource(", src)
    if path == "mars/util/SystemIO.java":
        src = re.sub(r"\bSystem\.(in|out|err)\b", r"mars.ext.IO.\1", src)
        # file syscalls: relative names resolve against the IDE workspace, not the process's working directory
        src = src.replace("new FileInputStream(filename)", "new FileInputStream(mars.ext.IO.resolve(filename))")
        src = src.replace("new FileOutputStream(filename,", "new FileOutputStream(mars.ext.IO.resolve(filename),")
        assert src.count("mars.ext.IO.resolve(") == 2
        for sig in ("public static int readInteger(", "public static float readFloat(", "public static double readDouble(",
                    "public static String readString(", "public static int readChar("):
            i = src.index("{", src.index(sig))
            src = src[:i + 1] + "\n         mars.ext.IO.beforeRead();" + src[i + 1:]
        k = src.rindex("}")
        src = src[:k] + ("\n   /** Forget buffered console input (new program run). */\n   public static void resetInputReader() { inputReader = null; }\n"
                         "   /** True if a complete read can be served from already-buffered input. */\n"
                         "   public static boolean inputReady() { try { return inputReader != null && inputReader.ready(); } catch (java.io.IOException e) { return false; } }\n}\n")
    if path in ("mars/MIPSprogram.java", "mars/simulator/Simulator.java", "mars/simulator/ProgramArgumentList.java"):
        src = re.sub(r"\bAbstractAction\b", "Object", src)
    if path == "mars/simulator/Simulator.java":
        i = src.index("public void finished() {")
        src = src[:i] + ("public void finished() { }\n      }\n\n"
                         "      private class UpdateGUI implements Runnable { public void run() { } }\n   }\n")
        src = src.replace("SwingUtilities.invokeLater(interactiveGUIUpdater);", "interactiveGUIUpdater.run();")
        src = src.replace("""                     instruction.getSimulationCode().simulate(statement);""", """                     try {
                        instruction.getSimulationCode().simulate(statement);
                     } catch (mars.ext.IO.Suspend sus) {
                        if (sus.retry) RegisterFile.setProgramCounter(pc);          // re-run once the host has input
                        else if (Memory.inTextSegment(pc)) mars.ext.IO.ticks++;
                        this.constructReturnReason = PAUSE_OR_STOP;
                        this.done = false;
                        Simulator.getInstance().notifyObserversOfExecutionStop(maxSteps, pc);
                        return new Boolean(done);
                     }
                     if (Memory.inTextSegment(pc)) mars.ext.IO.ticks++;""")
        assert "IO.ticks++" in src
        # race fix: stopExecution() nulls simulatorThread while simulate() still waits on it → keep a local reference
        src = src.replace("simulatorThread = new SimThread(p,pc,maxSteps,breakPoints,actor);",
                          "final SimThread st = new SimThread(p,pc,maxSteps,breakPoints,actor);\n         simulatorThread = st;")
        src = src.replace("simulatorThread.start();", "st.start();", 1)
        src = src.replace("Object dun = simulatorThread.get();", "Object dun = st.get();")
        src = src.replace("ProcessingException pe = simulatorThread.pe;", "ProcessingException pe = st.pe;")
        src = src.replace("boolean done = simulatorThread.done;", "boolean done = st.done;")
        src = src.replace("            this.simulatorThread = null;\r\n            if (pe != null) {", "            if (this.simulatorThread == st) this.simulatorThread = null;\r\n            if (pe != null) {")
        assert "st.get()" in src and "boolean done = st.done;" in src and "this.simulatorThread == st" in src
        # MARS counts every fetched instruction, including the one that exits or faults
        src = re.sub(r"(catch \(ProcessingException pe\) \{\r?\n)(\s*)(if \(pe\.errors\(\) == null\) \{)",
                     r"\1\2if (Memory.inTextSegment(pc)) mars.ext.IO.ticks++;\n\2\3", src, count=1)
        assert src.count("IO.ticks++") == 3
        src = re.sub(r"try \{ Thread\.sleep\(\(int\)\(1000/RunSpeedPanel\.getInstance\(\)\.getRunSpeed\(\)\)\);[^}]*\}\s*catch \(InterruptedException e\) \{\}",
                     "/* run speed is controlled by the host */", src)
        assert "Thread.sleep" not in src
    if path == "mars/mips/instructions/syscalls/SyscallPrintFloat.java":
        src = src.replace("new Float(Float.intBitsToFloat(", "mars.ext.IO.floatText(Float.intBitsToFloat(").replace(".toString());", ");")
        assert "IO.floatText" in src and ".toString()" not in src
    if path == "mars/mips/instructions/syscalls/SyscallPrintDouble.java":
        src = src.replace("new Double(Double.longBitsToDouble(", "mars.ext.IO.doubleText(Double.longBitsToDouble(").replace(".toString());", ");")
        assert "IO.doubleText" in src and ".toString()" not in src
    if path.startswith("mars/mips/instructions/syscalls/SyscallRand"):
        src = src.replace("import java.util.Random;", "import mars.ext.JRandom;")
        src = re.sub(r"\bRandom\b", "JRandom", src)
    if path == "mars/mips/hardware/Memory.java":
        # fast path: skip observer bookkeeping for addresses no observer watches (every fetch used to walk the list)
        src = src.replace("""         observables.add(new MemoryObservable(obs, startAddr, endAddr));
      }""", """         observables.add(new MemoryObservable(obs, startAddr, endAddr));
         int lo = startAddr ^ 0x80000000, hi = (endAddr + 3) ^ 0x80000000;   // unsigned order via sign flip (no longs: cheap in JS)
         if (lo < observedLo) observedLo = lo;
         if (hi > observedHi) observedHi = hi;
      }
      private int observedLo = Integer.MAX_VALUE, observedHi = Integer.MIN_VALUE;""")
        src = src.replace("""       private void notifyAnyObservers(int type, int address, int length, int value) {
""", """       private void notifyAnyObservers(int type, int address, int length, int value) {
         int fa = address ^ 0x80000000;
         if (fa + length - 1 < observedLo || fa > observedHi) return;
""")
        src = src.replace("""         observables = getNewMemoryObserversCollection();
      }""", """         observables = getNewMemoryObserversCollection();
         observedLo = Integer.MAX_VALUE; observedHi = Integer.MIN_VALUE;
      }""")
        assert "observedLo" in src and "fa > observedHi" in src
    if path == "mars/mips/instructions/syscalls/SyscallSleep.java":
        src = re.sub(r"try\s*\{\s*Thread\.sleep\(RegisterFile\.getValue\(4\)\);.*?\}\s*catch \(InterruptedException e\)\s*\{[^}]*\}",
                     "mars.ext.IO.sleepMs = Math.max(0, RegisterFile.getValue(4));\n               throw new mars.ext.IO.Suspend(\"sleep\", false);", src, flags=re.S)
        assert "Thread.sleep" not in src
    if path == "mars/simulator/SwingWorker.java":
        src = src.replace("SwingUtilities.invokeLater(doFinished)", "doFinished.run()")
    if path == "mars/mips/instructions/SyscallLoader.java":
        # no class-path scanning or reflection: construct every syscall directly
        news = ", ".join(f"new mars.mips.instructions.syscalls.{n}()" for n in syscalls)
        i = src.index("void loadSyscalls() {")
        j = src.index("syscallList = processSyscallNumberOverrides(syscallList);", i)
        src = (src[:i] + "void loadSyscalls() {\n         syscallList = new ArrayList();\n"
               f"         Syscall[] all = {{ {news} }};\n"
               "         for (int k = 0; k < all.length; k++) {\n"
               "            if (findSyscall(all[k].getNumber()) == null) syscallList.add(all[k]);\n"
               "         }\n         " + src[j:])
    if path == "mars/util/FilenameFinder.java":
        src = remove_block(src, r"public\s+static\s+FileFilter\s+getFileFilter\s*\([^)]*\)\s*\{")
        src = remove_block(src, r"(private|public)?\s*static\s+class\s+\w+\s+extends\s+FileFilter\s*\{")
        src = re.sub(r"FileFilter\s+filter\s*=\s*getFileFilter\(([^,]+),\s*\"\",\s*NO_DIRECTORIES\);",
                     r"java.io.FileFilter filter = headlessFilter(\1);", src)
        k = src.rindex("}")
        src = src[:k] + """
   private static java.io.FileFilter headlessFilter(final Object ext) {
      return new java.io.FileFilter() {
         public boolean accept(File f) {
            if (f.isDirectory()) return false;
            if (ext instanceof ArrayList) {
               for (Object e : (ArrayList) ext) if (fileExtensionMatch(f.getName(), (String) e)) return true;
               return false;
            }
            return fileExtensionMatch(f.getName(), (String) ext);
         }
      };
   }
}
"""
    if path == "mars/Globals.java":
        # never touch java.util.prefs; settings are in-memory in this build
        pass
    return src


def java_string_chunks(text: str, size: int = 8000) -> list[str]:
    out = []
    for i in range(0, len(text), size):
        chunk = text[i:i + size]
        esc = []
        for ch in chunk:
            o = ord(ch)
            if ch == "\\": esc.append("\\\\")
            elif ch == '"': esc.append('\\"')
            elif ch == "\n": esc.append("\\n")
            elif ch == "\r": esc.append("\\r")
            elif ch == "\t": esc.append("\\t")
            elif o < 32 or o > 126: esc.append("\\u%04x" % o)
            else: esc.append(ch)
        out.append('"' + "".join(esc) + '"')
    return out


def write_embedded(path: Path, res: dict) -> None:
    """Compile MARS's resource files into a class (works where class-path resources don't)."""
    lines = ["package mars.ext;", "", "/** Generated by engine/patch_core.py from the MARS 4.5 jar. */",
             "final class EmbeddedResources {", "   private EmbeddedResources() { }", "",
             "   static String get(String name) {", "      switch (name) {"]
    for i, name in enumerate(sorted(res)):
        lines.append(f'         case "{name}": return r{i}();')
    lines += ["         default: return null;", "      }", "   }", ""]
    for i, name in enumerate(sorted(res)):
        chunks = java_string_chunks(res[name], 8000)
        lines.append(f"   private static String r{i}() {{")
        lines.append(f"      StringBuilder sb = new StringBuilder({len(res[name])});")
        for c in chunks:
            lines.append(f"      sb.append({c});")
        lines.append("      return sb.toString();")
        lines.append("   }")
    lines.append("}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def main(jar: str, out: str) -> None:
    out_dir = Path(out)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "java").mkdir(parents=True)
    (out_dir / "resources").mkdir(parents=True)
    overlay = HERE / "overlay"
    overlay_files = {str(p.relative_to(overlay)) for p in overlay.rglob("*.java")}
    with zipfile.ZipFile(jar) as z:
        names = z.namelist()
        syscalls = sorted(
            Path(n).stem for n in names
            if n.startswith("mars/mips/instructions/syscalls/Syscall") and n.endswith(".java")
            and Path(n).stem not in ("Syscall", "SyscallNumberOverride")
        )
        for n in names:
            if not n.endswith(".java") or not n.startswith("mars/"):
                continue
            if n.startswith(SKIP_PREFIX) or n in SKIP_FILES or n in overlay_files:
                continue
            if "/syscalls/Syscall" in n and "Dialog" in n:
                continue  # replaced by overlay versions
            src = z.read(n).decode("latin-1")
            dest = out_dir / "java" / n
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(patch(n, src, syscalls), encoding="latin-1")
        res = {}
        for r in RESOURCES:
            data = z.read(r)
            (out_dir / "resources" / r).write_bytes(data)
            res[r] = data.decode("latin-1")
    write_embedded(out_dir / "java" / "mars" / "ext" / "EmbeddedResources.java", res)
    for p in overlay.rglob("*.java"):
        dest = out_dir / "java" / p.relative_to(overlay)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(p, dest)
    print(f"core sources: {sum(1 for _ in (out_dir / 'java').rglob('*.java'))} files, {len(syscalls)} syscalls")


if __name__ == "__main__":
    main(*sys.argv[1:3])
