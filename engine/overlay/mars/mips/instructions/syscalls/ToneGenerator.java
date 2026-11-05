package mars.mips.instructions.syscalls;
/** Headless ToneGenerator: forwards tones to the front end (mars.ext.Host). */
public class ToneGenerator {
   public final static byte DEFAULT_PITCH = 60;
   public final static int DEFAULT_DURATION = 1000;
   public final static byte DEFAULT_INSTRUMENT = 0;
   public final static byte DEFAULT_VOLUME = 100;
   public void generateTone(byte pitch, int duration, byte instrument, byte volume) {
      mars.ext.Host.Registry.get().tone(pitch, duration, instrument, volume);
   }
   public void generateToneSynchronously(byte pitch, int duration, byte instrument, byte volume) {
      generateTone(pitch, duration, instrument, volume);
      mars.ext.IO.sleepMs = Math.max(0, duration);
      throw new mars.ext.IO.Suspend("sleep", false);
   }
}
