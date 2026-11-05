package mars.ext;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;

/**
 * Portable I/O seams for the headless core (desktop JVM, Android, TeaVM in the browser):
 * console streams the front end can replace, embedded resources, and exit-as-exception.
 */
public final class IO {
   public static volatile InputStream in = System.in;
   public static volatile PrintStream out = System.out;
   public static volatile PrintStream err = System.err;

   private IO() { }

   /** Instructions executed since the last reset: an int tick in the hot loop (cheap in JS), folded into a long. */
   public static int ticks = 0;
   private static long base = 0;
   public static long executed() { return base + ticks; }
   public static void resetExecuted() { base = 0; ticks = 0; }
   public static void fold() { base += ticks; ticks = 0; }
   public static void uncount() { if (ticks > 0) ticks--; else if (base > 0) base--; }
   /** Why the simulator last suspended: "input", "dialog" or "sleep" (null = not suspended). */
   public static volatile String suspended = null;
   /** Float/double → text exactly like Java's Float/Double.toString (browser runtimes format differently). */
   public interface NumberFormat { String floatText(float v); String doubleText(double v); }
   public static NumberFormat numberFormat = null;
   public static String floatText(float v) { NumberFormat f = numberFormat; return f != null ? f.floatText(v) : Float.toString(v); }
   public static String doubleText(double v) { NumberFormat f = numberFormat; return f != null ? f.doubleText(v) : Double.toString(v); }

   /** Workspace directory for MIPS file syscalls (13-16); relative file names resolve against it. */
   public static volatile java.io.File baseDir = null;
   public static java.io.File resolve(String name) {
      java.io.File f = new java.io.File(name);
      return (f.isAbsolute() || baseDir == null) ? f : new java.io.File(baseDir, name);
   }

   /** Called before MARS reads console input: lets the host suspend *before* a reader consumes anything. */
   public static Runnable readGuard = null;
   public static void beforeRead() { Runnable r = readGuard; if (r != null) r.run(); }

   /** Milliseconds to wait after a sleep / synchronous MIDI syscall (honoured by the host's run loop). */
   public static volatile int sleepMs = 0;

   /**
    * Thrown by an instruction that must wait for the outside world. The simulator stops cleanly:
    * retry = true puts the PC back on the instruction (it re-executes once input arrives),
    * retry = false means the instruction completed and the host should just pause (sleep).
    * Instruction execution itself therefore never blocks — essential for browser builds.
    */
   public static final class Suspend extends RuntimeException {
      public final boolean retry;
      public Suspend(String why, boolean retry) { super(why, null, false, false); this.retry = retry; suspended = why; }
   }

   /** MARS called System.exit on internal errors; an embedded engine must never kill its host. */
   public static void exit(int code) {
      throw new IllegalStateException("MARS internal error (exit " + code + ")");
   }

   /** Resources (PseudoOps.txt, *.properties) are compiled in, so no class-path lookup is needed. */
   public static InputStream resource(String name) {
      String text = EmbeddedResources.get(name.startsWith("/") ? name.substring(1) : name);
      return text == null ? null : new ByteArrayInputStream(text.getBytes(StandardCharsets.ISO_8859_1));
   }
}
