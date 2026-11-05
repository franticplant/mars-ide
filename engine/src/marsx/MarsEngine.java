package marsx;

import mars.*;
import mars.assembler.*;
import mars.ext.Host;
import mars.mips.hardware.*;
import mars.simulator.*;
import mars.util.*;

import java.io.*;
import java.nio.charset.Charset;
import java.util.*;
import mars.ext.IO;

/**
 * Transport-independent MARS engine. Feed it JSON command lines with {@link #handle(String)};
 * replies and events come back through the {@link Sink}.
 *
 *   command: {"id":X,"cmd":"...", ...}
 *   reply:   {"id":X,"ok":true,...}  /  {"id":X,"ok":false,"error":"..."}
 *   event:   {"ev":"out"|"input_request"|"dialog"|"tone"|"tick"|"stopped"|"mmio_out", ...}
 *
 * MARS keeps its state in static fields, so there is one engine per process.
 */
public final class MarsEngine {

    public interface Sink { void send(String json); }

    public static final String PROTOCOL = "marsx/1";
    /** Instructions per uninterrupted run slice, and pause between slices (-1 = none). Browser builds use small slices. */
    public static int CHUNK = 1_000_000;
    public static int YIELD_MS = -1;
    private static final Charset UTF8 = Charset.forName("UTF-8");

    private final Sink sink;
    private final File root;
    /** Single simulator thread (portable: plain Thread + Mailbox, no java.util.concurrent). */
    private final Mailbox<Runnable> simQueue = new Mailbox<>();
    private final Thread simThread = new Thread(() -> {
        while (true) {
            Runnable r;
            try { r = simQueue.take(); } catch (InterruptedException e) { return; }
            try { r.run(); } catch (Throwable t) { /* reported by the task itself */ }
        }
    }, "marsx-sim");
    private void submit(Runnable r) { simQueue.put(r); }

    // ------------------------------------------------------------ state
    private ArrayList<String> files = new ArrayList<>();
    private String mainFile, exceptionHandler, programArgs = "";
    private boolean pseudo = true, warningsAreErrors = false, startAtMain = false;
    private volatile boolean assembled = false, finished = false, busy = false, running = false;
    private volatile boolean stopRequested = false, inChunk = false;
    private volatile int speed = 0;
    private volatile List<Object> lastError = null;
    private ArrayList lastPrograms = new ArrayList();

    private final InputFeed input = new InputFeed();
    private final EventStream out = new EventStream("stdout"), err = new EventStream("stderr");

    // dialogs
    private final Mailbox<Object[]> dialogReplies = new Mailbox<>();
    /** Signalled by input, dialog replies and pause/stop — what a suspended run loop waits for. */
    private final Mailbox<Boolean> wake = new Mailbox<>();

    /** After a Suspend: wait (outside instruction execution) until the program can continue. false = stop requested. */
    private boolean awaitResume() throws InterruptedException {
        String why = IO.suspended;
        IO.suspended = null;
        if ("sleep".equals(why)) {
            int ms = IO.sleepMs; IO.sleepMs = 0;
            long until = System.currentTimeMillis() + ms;
            while (!stopRequested && System.currentTimeMillis() < until) Thread.sleep(Math.min(50, Math.max(1, until - System.currentTimeMillis())));
            return !stopRequested;
        }
        while (!stopRequested) {
            if ("input".equals(why) && input.q.size() > 0) return true;
            if ("dialog".equals(why) && dialogReplies.size() > 0) return true;
            wake.take();
        }
        return false;
    }
    private int dialogSeq = 0;
    private volatile String pendingDialog = null;

    static final int RCR = 0xffff0000, RDR = 0xffff0004, TCR = 0xffff0008, TDR = 0xffff000c;

    public MarsEngine(Sink sink, File workspaceRoot) {
        this.sink = sink;
        this.root = workspaceRoot == null ? null : canonical(workspaceRoot);
        PrintStream po = new PrintStream(out, false), pe = new PrintStream(err, false);
        IO.out = po; IO.err = pe; IO.in = input;
        try { System.setOut(po); System.setErr(pe); } catch (Throwable ignored) { }
        simThread.setDaemon(true);
        simThread.start();
        Globals.initialize(false);
        Globals.getSettings().setBooleanSettingNonPersistent(Settings.EXTENDED_ASSEMBLER_ENABLED, true);
        try {
            Globals.memory.addObserver(new MmioObserver(), RCR, TDR);
        } catch (AddressErrorException e) { throw new RuntimeException(e); }
        Host.Registry.set(new EngineHost());
        IO.readGuard = input::ensureReadable;
        IO.baseDir = this.root;
        Thread fl = new Thread(() -> {
            while (true) {
                try { Thread.sleep(40); } catch (InterruptedException e) { return; }
                flushOutput();
            }
        }, "marsx-flush");
        fl.setDaemon(true);
        fl.start();
    }

    public void announce() { send(obj("ev", "ready", "version", Globals.version, "protocol", PROTOCOL, "fs", root != null)); }

    // ------------------------------------------------------------ io helpers
    void send(Map<String, Object> m) { synchronized (sink) { sink.send(Json.write(m)); } }

    static Map<String, Object> obj(Object... kv) {
        Map<String, Object> m = new LinkedHashMap<>();
        for (int i = 0; i + 1 < kv.length; i += 2) m.put((String) kv[i], kv[i + 1]);
        return m;
    }

    void flushOutput() { System.out.flush(); System.err.flush(); out.flush(); err.flush(); }

    final class EventStream extends OutputStream {
        final String stream;
        final ByteArrayOutputStream buf = new ByteArrayOutputStream();
        EventStream(String s) { stream = s; }
        @Override public synchronized void write(int b) { buf.write(b); if (buf.size() > 4096) flush(); }
        @Override public synchronized void write(byte[] b, int off, int len) { buf.write(b, off, len); if (buf.size() > 4096) flush(); }
        @Override public synchronized void flush() {
            if (buf.size() == 0) return;
            String s = new String(buf.toByteArray(), UTF8);
            buf.reset();
            send(obj("ev", "out", "stream", stream, "text", s));
        }
    }

    /** System.in replacement: asks the front end for input when MIPS reads and nothing is buffered. */
    final class InputFeed extends InputStream {
        final Mailbox<byte[]> q = new Mailbox<>();
        byte[] cur = null; int pos = 0;
        volatile boolean waiting = false;
        void feed(String s) { q.put(s.getBytes(UTF8)); wake.put(Boolean.TRUE); }
        void clear() { q.clear(); cur = null; pos = 0; waiting = false; }
        /** Before MARS reads: if nothing is buffered anywhere, ask the front end and suspend the instruction. */
        void ensureReadable() {
            if (SystemIO.inputReady() || (cur != null && pos < cur.length) || q.size() > 0) return;
            fill();   // sends input_request once, then throws IO.Suspend
        }
        private boolean fill() {
            while (cur == null || pos >= cur.length) {
                byte[] next = q.poll();
                if (next == null) {
                    if (waiting) throw new IO.Suspend("input", true);
                    flushOutput();
                    int v0 = RegisterFile.getValue(2);
                    String kind;
                    switch (v0) {
                        case 5: kind = "int"; break;
                        case 6: kind = "float"; break;
                        case 7: kind = "double"; break;
                        case 8: kind = "string"; break;
                        case 12: kind = "char"; break;
                        default: kind = "data";
                    }
                    waiting = true;
                    send(obj("ev", "input_request", "kind", kind, "syscall", v0));
                    throw new IO.Suspend("input", true);     // the run loop waits; the syscall re-executes
                }
                waiting = false;
                cur = next; pos = 0;
            }
            return true;
        }
        @Override public synchronized int read() { if (!fill()) return -1; return cur[pos++] & 0xff; }
        @Override public synchronized int read(byte[] b, int off, int len) {
            if (len == 0) return 0;
            if (!fill()) return -1;
            int n = Math.min(len, cur.length - pos);
            System.arraycopy(cur, pos, b, off, n);
            pos += n;
            return n;
        }
        @Override public int available() { return cur == null ? 0 : cur.length - pos; }
    }

    final class EngineHost implements Host {
        public String dialog(String kind, String message, int type) {
            if (pendingDialog != null) {
                Object[] r;
                while ((r = dialogReplies.poll()) != null) {
                    if (r[0] == null || pendingDialog.equals(r[0])) { pendingDialog = null; return (String) r[1]; }
                }
                throw new IO.Suspend("dialog", true);
            }
            flushOutput();
            String token = "d" + (++dialogSeq) + "-" + System.currentTimeMillis();
            pendingDialog = token;
            dialogReplies.clear();
            send(obj("ev", "dialog", "token", token, "kind", kind, "message", message, "type", type));
            throw new IO.Suspend("dialog", true);      // re-executes with the answer once it arrives
        }
        public void tone(int pitch, int durationMs, int instrument, int volume) {
            send(obj("ev", "tone", "pitch", pitch, "duration", durationMs, "instrument", instrument, "volume", volume));
        }
    }

    final class MmioObserver implements Observer {
        @Override public void update(Observable o, Object arg) {
            if (!(arg instanceof MemoryAccessNotice)) return;
            MemoryAccessNotice n = (MemoryAccessNotice) arg;
            if (!n.accessIsFromMIPS()) return;
            int a = n.getAddress();
            try {
                if (n.getAccessType() == AccessNotice.READ && a == RDR) {
                    Globals.memory.setRawWord(RCR, Globals.memory.getWordNoNotify(RCR) & ~1);
                } else if (n.getAccessType() == AccessNotice.WRITE && a == TDR) {
                    send(obj("ev", "mmio_out", "char", n.getValue() & 0xff));
                    int tc = Globals.memory.getWordNoNotify(TCR);
                    Globals.memory.setRawWord(TCR, tc | 1);
                    if ((tc & 2) != 0) Simulator.externalInterruptingDevice = Exceptions.EXTERNAL_INTERRUPT_DISPLAY;
                }
            } catch (AddressErrorException ignored) { }
        }
    }


    // ------------------------------------------------------------ dispatch
    /** Handle one JSON command line. Long-running commands reply asynchronously. */
    public void handle(String line) {
        line = line.trim();
        if (line.isEmpty()) return;
        Object id = null;
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> req = (Map<String, Object>) Json.parse(line);
            id = req.get("id");
            final Object rid = id;
            String cmd = String.valueOf(req.get("cmd"));
            if (cmd.equals("step")) {               // runs on the simulator thread so syscall input can arrive
                requireRunnable();
                busy = true;
                submit(() -> { Map<String, Object> res = safe(this::doStep); busy = false; reply(rid, res); });
                return;
            }
            reply(id, dispatch(cmd, req));
        } catch (Throwable t) {
            send(obj("id", id, "ok", false, "error", message(t)));
        }
    }

    interface Action { Map<String, Object> run() throws Exception; }

    private Map<String, Object> safe(Action a) {
        try { return a.run(); }
        catch (Throwable t) { return obj("ok", false, "error", message(t)); }
    }

    private void reply(Object id, Map<String, Object> res) {
        flushOutput();
        res.put("id", id);
        res.putIfAbsent("ok", true);
        send(res);
    }

    static String message(Throwable t) {
        String m = t.getMessage();
        return m == null ? t.toString() : m;
    }

    private Map<String, Object> dispatch(String cmd, Map<String, Object> r) throws Exception {
        switch (cmd) {
            case "hello":    return obj("version", Globals.version, "protocol", PROTOCOL, "fs", root != null,
                                        "state", stateMap(), "assembled", assembled, "speed", speed,
                                        "dialog", pendingDialog, "waiting_input", input.waiting);
            case "assemble": return assemble(r);
            case "reset":    return reset();
            case "backstep": return backstep();
            case "run":      return run(r);
            case "pause":    return pause(false);
            case "stop":     return pause(true);
            case "speed":    speed = toInt(r.get("value")); return obj("speed", speed);
            case "state":    return obj("state", stateMap());
            case "program":  return assembled ? programInfo() : obj("assembled", false);
            case "memory":   return memory(r);
            case "setreg":   return setreg(r);
            case "setmem":   return setmem(r);
            case "input":    input.feed(String.valueOf(r.get("text"))); return obj();
            case "key":      return key(r);
            case "dialog_reply": dialogReplies.put(new Object[] { r.get("token"), r.get("value") }); wake.put(Boolean.TRUE); return obj();
            case "configs":  return configs();
            case "isa":      return isa();
            case "fs_list":  return fsList(r);
            case "fs_read":  return fsRead(r);
            case "fs_write": return fsWrite(r);
            case "fs_delete": return fsDelete(r);
            case "fs_rename": return fsRename(r);
            case "fs_mkdir": return fsMkdir(r);
            case "ping":     return obj("pong", true);
            default: throw new IllegalArgumentException("unknown command: " + cmd);
        }
    }

    // ------------------------------------------------------------ assemble
    @SuppressWarnings("unchecked")
    private Map<String, Object> assemble(Map<String, Object> r) throws Exception {
        haltRunner();
        files = new ArrayList<>();
        for (Object o : (List<Object>) r.get("files")) files.add(resolve(String.valueOf(o)).getPath());
        if (files.isEmpty()) throw new IllegalArgumentException("no files to assemble");
        mainFile = r.get("main") == null ? files.get(0) : resolve(String.valueOf(r.get("main"))).getPath();
        Map<String, Object> s = (Map<String, Object>) r.getOrDefault("settings", new HashMap<>());
        pseudo = bool(s, "pseudo", true);
        warningsAreErrors = bool(s, "warnings_are_errors", false);
        startAtMain = bool(s, "start_at_main", false);
        Settings st = Globals.getSettings();
        st.setBooleanSettingNonPersistent(Settings.DELAYED_BRANCHING_ENABLED, bool(s, "delayed_branching", false));
        st.setBooleanSettingNonPersistent(Settings.SELF_MODIFYING_CODE_ENABLED, bool(s, "self_modifying", false));
        st.setBooleanSettingNonPersistent(Settings.BARE_MACHINE_ENABLED, bool(s, "bare_machine", false));
        st.setBooleanSettingNonPersistent(Settings.EXTENDED_ASSEMBLER_ENABLED, pseudo);
        Object eh = s.get("exception_handler");
        exceptionHandler = (eh == null || String.valueOf(eh).trim().isEmpty()) ? null : resolve(String.valueOf(eh)).getPath();
        programArgs = s.get("program_args") == null ? "" : String.valueOf(s.get("program_args"));
        String cfg = s.get("memory_config") == null ? "Default" : String.valueOf(s.get("memory_config"));
        MemoryConfiguration mc = MemoryConfigurations.getConfigurationByName(cfg);
        if (mc != null) MemoryConfigurations.setCurrentConfiguration(mc);
        return doAssemble(true);
    }

    private Map<String, Object> doAssemble(boolean full) throws Exception {
        assembled = false; finished = false; IO.resetExecuted(); lastError = null;
        input.clear();
        resetSystemIOReader();
        Globals.program = new MIPSprogram();
        List<Object> msgs = new ArrayList<>();
        ErrorList warnings;
        try {
            ArrayList progs = Globals.program.prepareFilesForAssembly(files, mainFile, exceptionHandler);
            lastPrograms = progs;
            warnings = Globals.program.assemble(progs, pseudo, warningsAreErrors);
        } catch (ProcessingException pe) {
            addErrors(msgs, pe.errors());
            return obj("success", false, "messages", msgs);
        }
        addErrors(msgs, warnings);
        RegisterFile.resetRegisters();
        Coprocessor1.resetRegisters();
        Coprocessor0.resetRegisters();
        RegisterFile.initializeProgramCounter(startAtMain);
        SystemIO.resetFiles();
        Globals.memory.setRawWord(TCR, 1);
        if (programArgs != null && !programArgs.trim().isEmpty())
            new ProgramArgumentList(programArgs).storeProgramArguments();
        assembled = true;
        IO.resetExecuted();
        Map<String, Object> res = full ? programInfo() : obj();
        res.put("success", true);
        res.put("messages", msgs);
        res.put("state", stateMap());
        return res;
    }

    private Map<String, Object> programInfo() {
        return obj("files", relList(files), "main", rel(mainFile), "text", textSegment(), "labels", labels(), "segments", segments());
    }

    private void resetSystemIOReader() { SystemIO.resetInputReader(); }

    private void addErrors(List<Object> out, ErrorList el) {
        if (el == null) return;
        for (Object o : el.getErrorMessages()) {
            ErrorMessage m = (ErrorMessage) o;
            out.add(obj("file", rel(m.getFilename()), "line", m.getLine(), "col", m.getPosition(),
                        "message", m.getMessage(), "warning", m.isWarning()));
        }
    }

    private List<Object> textSegment() {
        List<Object> out = new ArrayList<>();
        ArrayList ml = Globals.program.getMachineList();
        if (ml == null) return out;
        for (Object o : ml) {
            ProgramStatement ps = (ProgramStatement) o;
            out.add(obj("addr", ps.getAddress(), "code", ps.getBinaryStatement(),
                        "basic", ps.getPrintableBasicAssemblyStatement(),
                        "source", ps.getSource() == null ? "" : ps.getSource(),
                        "line", ps.getSourceLine(),
                        "file", ps.getSourceMIPSprogram() == null ? "" : rel(ps.getSourceMIPSprogram().getFilename())));
        }
        return out;
    }

    private List<Object> labels() {
        List<Object> out = new ArrayList<>();
        addSymbols(out, Globals.symbolTable, "(global)");
        for (Object o : lastPrograms) {
            MIPSprogram p = (MIPSprogram) o;
            addSymbols(out, p.getLocalSymbolTable(), rel(p.getFilename()));
        }
        return out;
    }

    private static void addSymbols(List<Object> out, SymbolTable t, String file) {
        if (t == null) return;
        for (Object o : t.getTextSymbols()) { Symbol s = (Symbol) o; out.add(obj("name", s.getName(), "addr", s.getAddress(), "data", false, "file", file)); }
        for (Object o : t.getDataSymbols()) { Symbol s = (Symbol) o; out.add(obj("name", s.getName(), "addr", s.getAddress(), "data", true, "file", file)); }
    }

    private static Map<String, Object> segments() {
        return obj("text", Memory.textBaseAddress, "data", Memory.dataBaseAddress, "extern", Memory.externBaseAddress,
                   "gp", Memory.globalPointer, "heap", Memory.heapBaseAddress, "sp", Memory.stackPointer,
                   "ktext", Memory.kernelTextBaseAddress, "kdata", Memory.kernelDataBaseAddress,
                   "mmio", Memory.memoryMapBaseAddress);
    }

    private Map<String, Object> reset() throws Exception {
        haltRunner();
        if (files.isEmpty()) throw new IllegalStateException("nothing assembled yet");
        return doAssemble(false);
    }

    // ------------------------------------------------------------ execution
    private void requireRunnable() {
        if (!assembled) throw new IllegalStateException("assemble first");
        if (busy) throw new IllegalStateException("simulator is busy");
    }

    private Map<String, Object> doStep() {
        if (finished) return obj("state", stateMap(), "finished", true);
        lastError = null;
        stopRequested = false;
        input.waiting = false;
        String reason = stepOnce();
        if ("paused".equals(reason)) reason = null;
        Map<String, Object> res = obj("state", stateMap());
        if (reason != null) {
            res.put("finished", true);
            res.put("reason", reason);
            if (lastError != null) res.put("errors", lastError);
        }
        return res;
    }

    private String stepOnce() {
        try {
            while (true) {
                boolean done = Globals.program.simulateStepAtPC(null);
                if (done) { finished = true; return "exit"; }
                if (IO.suspended == null) return null;
                boolean retry = !"sleep".equals(IO.suspended);
                if (!awaitResume()) return "paused";
                if (!retry) return null;            // sleep: the instruction already completed
            }
        } catch (ProcessingException pe) {
            finished = true;
            List<Object> e = new ArrayList<>();
            addErrors(e, pe.errors());
            lastError = e;
            return "error";
        } catch (InterruptedException ie) {
            return "paused";
        }
    }

    private Map<String, Object> backstep() {
        if (busy) throw new IllegalStateException("simulator is busy");
        if (!assembled) throw new IllegalStateException("assemble first");
        BackStepper bs = Globals.program.getBackStepper();
        if (bs == null || bs.empty()) return obj("state", stateMap(), "empty", true);
        bs.backStep();
        finished = false;
        IO.uncount();
        return obj("state", stateMap());
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> run(Map<String, Object> r) {
        requireRunnable();
        if (finished) return obj("started", false, "finished", true);
        List<Object> bp = (List<Object>) r.getOrDefault("breakpoints", new ArrayList<>());
        final int[] bps = new int[bp.size()];
        for (int i = 0; i < bps.length; i++) bps[i] = toInt(bp.get(i));
        Arrays.sort(bps);
        if (r.containsKey("speed")) speed = toInt(r.get("speed"));
        final long maxSteps = r.containsKey("max_steps") ? toLong(r.get("max_steps")) : -1;
        stopRequested = false;
        input.waiting = false;          // re-ask for input if a previous run was paused while waiting
        busy = true;
        running = true;
        lastError = null;
        submit(() -> {
            String reason;
            try { reason = runLoop(bps, maxSteps); }
            catch (Throwable t) { reason = "error"; lastError = Collections.singletonList((Object) obj("message", message(t))); }
            if ("stopped".equals(reason)) finished = true;
            running = false;
            busy = false;
            flushOutput();
            Map<String, Object> ev = obj("ev", "stopped", "reason", reason, "state", stateMap());
            if (lastError != null) ev.put("errors", lastError);
            send(ev);
        });
        return obj("started", true);
    }

    private String runLoop(int[] bps, long maxSteps) throws Exception {
        long steps = 0;
        boolean first = true;
        while (true) {
            if (stopRequested) return stopKind;
            if (speed <= 0) {
                // full speed: let MARS run in large chunks (pause works between chunks and inside them)
                int chunk = CHUNK;
                if (maxSteps > 0) chunk = (int) Math.min(chunk, maxSteps - steps);
                if (chunk <= 0) return "max_steps";
                IO.fold(); long before = IO.executed();
                try {
                    inChunk = true;
                    boolean done = Globals.program.simulateFromPC(bps.length == 0 ? null : bps, chunk, null);
                    inChunk = false;
                    if (done) { finished = true; return "exit"; }
                    if (IO.suspended != null) {
                        if (!awaitResume()) return stopKind;
                        first = false;
                        continue;
                    }
                } catch (ProcessingException pe) {
                    inChunk = false;
                    finished = true;
                    List<Object> e = new ArrayList<>(); addErrors(e, pe.errors()); lastError = e;
                    return "error";
                }
                steps += Math.max(1, IO.executed() - before);
                first = false;
                if (YIELD_MS >= 0) Thread.sleep(YIELD_MS);
                if (bps.length > 0 && Arrays.binarySearch(bps, RegisterFile.getProgramCounter()) >= 0) return "breakpoint";
                continue;
            }
            int pc = RegisterFile.getProgramCounter();
            if (!first && bps.length > 0 && Arrays.binarySearch(bps, pc) >= 0) return "breakpoint";
            first = false;
            if (maxSteps > 0 && steps >= maxSteps) return "max_steps";
            String reason = stepOnce();
            steps++;
            if ("paused".equals(reason)) return stopKind;
            if (reason != null) return reason;
            send(obj("ev", "tick", "state", stateMap()));
            int sp = speed;
            if (sp > 0) Thread.sleep(Math.max(1, 1000 / sp));
        }
    }

    private volatile String stopKind = "paused";

    private Map<String, Object> pause(boolean stop) {
        if (!busy) {
            if (stop && assembled) { finished = true; return obj("running", false, "state", stateMap()); }
            return obj("running", false);
        }
        stopKind = stop ? "stopped" : "paused";
        stopRequested = true;
        if (inChunk) Simulator.getInstance().stopExecution(null);
        wake.put(Boolean.TRUE);
        return obj("running", true);
    }

    private void haltRunner() throws InterruptedException {
        if (busy) {
            pause(false);
            for (int i = 0; i < 200 && busy; i++) Thread.sleep(10);
        }
    }

    private Map<String, Object> stateMap() {
        List<Object> gpr = new ArrayList<>();
        for (Register reg : RegisterFile.getRegisters()) gpr.add(reg.getValueNoNotify());
        List<Object> fpr = new ArrayList<>();
        for (Register reg : Coprocessor1.getRegisters()) fpr.add(reg.getValueNoNotify());
        List<Object> c0 = new ArrayList<>();
        for (Register reg : Coprocessor0.getRegisters())
            c0.add(obj("name", reg.getName(), "num", reg.getNumber(), "value", reg.getValueNoNotify()));
        Register h = RegisterFile.getUserRegister("hi"), l = RegisterFile.getUserRegister("lo");
        BackStepper bs = Globals.program == null ? null : Globals.program.getBackStepper();
        return obj("pc", RegisterFile.getProgramCounter(), "gpr", gpr,
                   "hi", h == null ? 0 : h.getValueNoNotify(), "lo", l == null ? 0 : l.getValueNoNotify(),
                   "fpr", fpr, "flags", Coprocessor1.getConditionFlags(), "cop0", c0,
                   "running", running, "busy", busy, "finished", finished, "assembled", assembled,
                   "can_backstep", bs != null && !bs.empty(), "count", IO.executed(),
                   "waiting_input", input.waiting, "speed", speed);
    }

    private Map<String, Object> memory(Map<String, Object> r) {
        int addr = toInt(r.get("addr")) & ~3;
        int n = Math.min(toInt(r.getOrDefault("words", 64)), 1 << 18);
        List<Object> words = new ArrayList<>(n);
        for (int i = 0; i < n; i++) {
            int a = addr + i * 4;
            Integer v;
            try {
                if (Memory.inTextSegment(a) || Memory.inKernelTextSegment(a)) v = Globals.memory.getRawWordOrNull(a);
                else v = Globals.memory.getWordNoNotify(a);
            } catch (AddressErrorException e) { v = null; }
            words.add(v == null ? 0 : v);
        }
        return obj("addr", addr, "words", words);
    }

    private Map<String, Object> setreg(Map<String, Object> r) {
        if (busy) throw new IllegalStateException("simulator is busy");
        String file = String.valueOf(r.getOrDefault("file", "gpr"));
        int num = toInt(r.getOrDefault("num", 0)), val = toInt(r.get("value"));
        synchronized (Globals.memoryAndRegistersLock) {
            switch (file) {
                case "gpr": if (num == 0) throw new IllegalArgumentException("$zero is read-only"); RegisterFile.updateRegister(num, val); break;
                case "hi": RegisterFile.getUserRegister("hi").setValue(val); break;
                case "lo": RegisterFile.getUserRegister("lo").setValue(val); break;
                case "pc": RegisterFile.setProgramCounter(val); break;
                case "fpr": Coprocessor1.updateRegister(num, val); break;
                case "cop0": Coprocessor0.updateRegister(num, val); break;
                default: throw new IllegalArgumentException("bad register file " + file);
            }
        }
        return obj("state", stateMap());
    }

    private Map<String, Object> setmem(Map<String, Object> r) throws Exception {
        if (busy) throw new IllegalStateException("simulator is busy");
        synchronized (Globals.memoryAndRegistersLock) {
            Globals.memory.setRawWord(toInt(r.get("addr")) & ~3, toInt(r.get("value")));
        }
        return obj();
    }

    private Map<String, Object> key(Map<String, Object> r) throws Exception {
        int ch = toInt(r.get("char")) & 0xff;
        synchronized (Globals.memoryAndRegistersLock) {
            Globals.memory.setRawWord(RDR, ch);
            int rc = Globals.memory.getWordNoNotify(RCR);
            Globals.memory.setRawWord(RCR, rc | 1);
            if ((rc & 2) != 0) Simulator.externalInterruptingDevice = Exceptions.EXTERNAL_INTERRUPT_KEYBOARD;
        }
        return obj();
    }

    private static Map<String, Object> configs() {
        List<Object> out = new ArrayList<>();
        Iterator it = MemoryConfigurations.getConfigurationsIterator();
        while (it.hasNext()) {
            MemoryConfiguration c = (MemoryConfiguration) it.next();
            out.add(obj("id", c.getConfigurationIdentifier(), "name", c.getConfigurationName()));
        }
        return obj("configs", out, "current", MemoryConfigurations.getCurrentConfiguration().getConfigurationIdentifier());
    }

    private static Map<String, Object> isa() {
        List<Object> ins = new ArrayList<>();
        for (Object o : Globals.instructionSet.getInstructionList()) {
            mars.mips.instructions.Instruction i = (mars.mips.instructions.Instruction) o;
            ins.add(obj("name", i.getName(), "format", i.getExampleFormat(), "desc", i.getDescription(),
                        "pseudo", i instanceof mars.mips.instructions.ExtendedInstruction));
        }
        List<Object> dirs = new ArrayList<>();
        for (Object o : Directives.getDirectiveList()) {
            Directives d = (Directives) o;
            dirs.add(obj("name", d.getName(), "desc", d.getDescription()));
        }
        return obj("instructions", ins, "directives", dirs);
    }

    // ------------------------------------------------------------ workspace files
    private static File canonical(File f) {
        try { return f.getCanonicalFile(); } catch (IOException e) { return f.getAbsoluteFile(); }
    }

    /** Resolve a path inside the workspace (relative paths are workspace-relative). */
    private File resolve(String path) {
        if (root == null) return canonical(new File(path));
        File f = new File(path);
        if (!f.isAbsolute()) f = new File(root, path);
        f = canonical(f);
        String rp = root.getPath(), fp = f.getPath();
        if (!fp.equals(rp) && !fp.startsWith(rp + File.separator))
            throw new SecurityException("path outside workspace: " + path);
        return f;
    }

    private String rel(String path) {
        if (path == null || root == null) return path;
        String rp = root.getPath() + File.separator;
        String cp = canonical(new File(path)).getPath();
        return cp.startsWith(rp) ? cp.substring(rp.length()).replace(File.separatorChar, '/') : path;
    }

    private List<Object> relList(List<String> l) {
        List<Object> out = new ArrayList<>();
        for (String s : l) out.add(rel(s));
        return out;
    }

    private void requireFs() { if (root == null) throw new IllegalStateException("no workspace"); }

    private Map<String, Object> fsList(Map<String, Object> r) {
        requireFs();
        File dir = resolve(String.valueOf(r.getOrDefault("path", "")));
        List<Object> out = new ArrayList<>();
        walk(dir, out, 0, new int[] { 0 });
        return obj("entries", out, "root", root.getName());
    }

    private void walk(File dir, List<Object> out, int depth, int[] count) {
        File[] kids = dir.listFiles();
        if (kids == null) return;
        Arrays.sort(kids, (a, b) -> a.isDirectory() != b.isDirectory() ? (a.isDirectory() ? -1 : 1) : a.getName().compareToIgnoreCase(b.getName()));
        for (File k : kids) {
            if (k.getName().startsWith(".") || count[0] > 4000) continue;
            count[0]++;
            out.add(obj("path", rel(k.getPath()), "name", k.getName(), "dir", k.isDirectory(),
                        "size", k.length(), "mtime", k.lastModified(), "depth", depth));
            if (k.isDirectory() && depth < 6) walk(k, out, depth + 1, count);
        }
    }

    private Map<String, Object> fsRead(Map<String, Object> r) throws IOException {
        requireFs();
        File f = resolve(String.valueOf(r.get("path")));
        if (f.length() > 4 << 20) throw new IOException("file too large");
        byte[] data = readAll(f);
        if (Boolean.TRUE.equals(r.get("binary"))) return obj("path", rel(f.getPath()), "b64", Base64.encode(data), "mtime", f.lastModified());
        return obj("path", rel(f.getPath()), "text", new String(data, UTF8), "mtime", f.lastModified());
    }

    private Map<String, Object> fsWrite(Map<String, Object> r) throws IOException {
        requireFs();
        File f = resolve(String.valueOf(r.get("path")));
        File parent = f.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) throw new IOException("cannot create " + parent);
        byte[] data = r.get("b64") != null ? Base64.decode(String.valueOf(r.get("b64"))) : String.valueOf(r.get("text")).getBytes(UTF8);
        try (OutputStream os = new FileOutputStream(f)) { os.write(data); }
        return obj("path", rel(f.getPath()), "mtime", f.lastModified());
    }

    private Map<String, Object> fsDelete(Map<String, Object> r) throws IOException {
        requireFs();
        File f = resolve(String.valueOf(r.get("path")));
        if (f.equals(root)) throw new IOException("refusing to delete the workspace");
        deleteRec(f);
        return obj();
    }

    private static void deleteRec(File f) throws IOException {
        File[] kids = f.listFiles();
        if (kids != null) for (File k : kids) deleteRec(k);
        if (f.exists() && !f.delete()) throw new IOException("cannot delete " + f.getName());
    }

    private Map<String, Object> fsRename(Map<String, Object> r) throws IOException {
        requireFs();
        File a = resolve(String.valueOf(r.get("from"))), b = resolve(String.valueOf(r.get("to")));
        if (b.exists()) throw new IOException(b.getName() + " already exists");
        File parent = b.getParentFile();
        if (parent != null) parent.mkdirs();
        if (!a.renameTo(b)) throw new IOException("rename failed");
        return obj("path", rel(b.getPath()));
    }

    private Map<String, Object> fsMkdir(Map<String, Object> r) throws IOException {
        requireFs();
        File f = resolve(String.valueOf(r.get("path")));
        if (!f.exists() && !f.mkdirs()) throw new IOException("cannot create folder");
        return obj("path", rel(f.getPath()));
    }

    static byte[] readAll(File f) throws IOException {
        try (InputStream in = new FileInputStream(f)) {
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            byte[] b = new byte[8192];
            int n;
            while ((n = in.read(b)) > 0) bo.write(b, 0, n);
            return bo.toByteArray();
        }
    }

    // ------------------------------------------------------------ utils
    private static boolean bool(Map<String, Object> m, String k, boolean d) {
        Object v = m.get(k);
        return v == null ? d : Boolean.TRUE.equals(v);
    }
    static int toInt(Object o) { return (int) toLong(o); }
    static long toLong(Object o) {
        if (o instanceof Number) return ((Number) o).longValue();
        String s = String.valueOf(o).trim();
        if (s.startsWith("0x") || s.startsWith("0X")) return Long.parseLong(s.substring(2), 16);
        return Long.parseLong(s);
    }
}
