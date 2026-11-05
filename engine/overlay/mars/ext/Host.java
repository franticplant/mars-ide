package mars.ext;
/**
 * Services the headless engine needs from its front end (web UI, Android, TUI):
 * dialogs for syscalls 50-59 and MIDI tones for syscalls 31/33.
 */
public interface Host {
   /** Show a dialog. kind: "confirm" | "int" | "float" | "double" | "string" | "message".
    *  Blocks until the user answers. Returns null if cancelled. For "confirm" return "0" yes, "1" no, "2" cancel. */
   String dialog(String kind, String message, int messageType);
   /** Play a MIDI-style tone (fire and forget). */
   void tone(int pitch, int durationMs, int instrument, int volume);

   /** The host used when no front end registered one: answers from the console (System.in/out). */
   Host CONSOLE = new Host() {
      public String dialog(String kind, String message, int messageType) {
         mars.util.SystemIO.printString(message + (kind.equals("message") ? "\n" : " "));
         if (kind.equals("message")) return "";
         System.out.flush();
         if (kind.equals("confirm")) {
            mars.util.SystemIO.printString("[y/n/c] ");
            String s = mars.util.SystemIO.readString(0, 16).trim().toLowerCase();
            return s.startsWith("y") ? "0" : s.startsWith("n") ? "1" : "2";
         }
         return mars.util.SystemIO.readString(0, 1024).replaceAll("[\r\n]+$", "");
      }
      public void tone(int pitch, int durationMs, int instrument, int volume) { }
   };

   final class Registry {
      private static volatile Host host = CONSOLE;
      public static Host get() { return host; }
      public static void set(Host h) { host = h == null ? CONSOLE : h; }
   }
}
