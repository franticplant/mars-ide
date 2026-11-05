package marsx;

/** Tiny Base64 codec (portable: no java.util.Base64 needed, so it works under TeaVM/Android too). */
final class Base64 {
    private static final char[] A = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".toCharArray();
    private static final int[] D = new int[128];
    static { java.util.Arrays.fill(D, -1); for (int i = 0; i < A.length; i++) D[A[i]] = i; }

    static String encode(byte[] b) {
        StringBuilder sb = new StringBuilder((b.length + 2) / 3 * 4);
        for (int i = 0; i < b.length; i += 3) {
            int n = (b[i] & 255) << 16 | (i + 1 < b.length ? (b[i + 1] & 255) << 8 : 0) | (i + 2 < b.length ? b[i + 2] & 255 : 0);
            sb.append(A[n >> 18 & 63]).append(A[n >> 12 & 63]);
            sb.append(i + 1 < b.length ? A[n >> 6 & 63] : '=');
            sb.append(i + 2 < b.length ? A[n & 63] : '=');
        }
        return sb.toString();
    }

    static byte[] decode(String s) {
        java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream(s.length() * 3 / 4);
        int buf = 0, bits = 0;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c >= 128 || D[c] < 0) continue;
            buf = buf << 6 | D[c];
            bits += 6;
            if (bits >= 8) { bits -= 8; out.write(buf >> bits & 255); }
        }
        return out.toByteArray();
    }
}
