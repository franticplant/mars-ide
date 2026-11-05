package mars.venus;
import mars.util.Binary;
/** Headless replacement: only the static formatting helpers used by the core. */
public class NumberDisplayBaseChooser {
   public static final int DECIMAL = 10;
   public static final int HEXADECIMAL = 16;
   public static final int ASCII = 0;
   public static String formatUnsignedInteger(int value, int base) {
      return base == HEXADECIMAL ? Binary.intToHexString(value) : Binary.unsignedIntToIntString(value);
   }
   public static String formatNumber(int value, int base) {
      switch (base) {
         case HEXADECIMAL: return Binary.intToHexString(value);
         case ASCII: return Binary.intToAscii(value);
         default: return Integer.toString(value);
      }
   }
   public static String formatNumber(float value, int base) {
      return base == HEXADECIMAL ? Binary.intToHexString(Float.floatToIntBits(value)) : Float.toString(value);
   }
   public static String formatNumber(double value, int base) {
      if (base == HEXADECIMAL) {
         long l = Double.doubleToLongBits(value);
         return Binary.intToHexString(Binary.highOrderLongToInt(l)) + Binary.intToHexString(Binary.lowOrderLongToInt(l)).substring(2);
      }
      return Double.toString(value);
   }
   public static String formatFloatNumber(int value, int base) {
      return base == HEXADECIMAL ? Binary.intToHexString(value) : Float.toString(Float.intBitsToFloat(value));
   }
   public static String formatDoubleNumber(long value, int base) {
      return base == HEXADECIMAL ? Binary.longToHexString(value) : Double.toString(Double.longBitsToDouble(value));
   }
   public static int getBase(boolean setting) { return setting ? HEXADECIMAL : DECIMAL; }
}
