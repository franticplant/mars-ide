package mars.ext;

/**
 * Bit-exact copy of java.util.Random's algorithm (48-bit LCG). MARS's random syscalls (40-44) use it so that
 * seeded sequences are identical on every runtime — browser runtimes ship a different java.util.Random.
 */
public class JRandom {
   private static final long MULT = 0x5DEECE66DL, ADD = 0xBL, MASK = (1L << 48) - 1;
   private static long uniquifier = 8682522807148012L;
   private long seed;

   public JRandom() { this((uniquifier *= 1181783497276652981L) ^ System.nanoTime()); }
   public JRandom(long seed) { setSeed(seed); }

   public synchronized void setSeed(long s) { seed = (s ^ MULT) & MASK; }

   protected int next(int bits) {
      seed = (seed * MULT + ADD) & MASK;
      return (int) (seed >>> (48 - bits));
   }

   public int nextInt() { return next(32); }

   public int nextInt(int bound) {
      if (bound <= 0) throw new IllegalArgumentException("bound must be positive");
      int r = next(31);
      int m = bound - 1;
      if ((bound & m) == 0) return (int) ((bound * (long) r) >> 31);
      for (int u = r; u - (r = u % bound) + m < 0; u = next(31)) { }
      return r;
   }

   public float nextFloat() { return next(24) / ((float) (1 << 24)); }

   public double nextDouble() { return (((long) next(26) << 27) + next(27)) * 0x1.0p-53; }
}
