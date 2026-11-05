package marsx;

import java.util.*;

/** Minimal JSON reader/writer (no dependencies; works on Android and desktop). */
public final class Json {
public static String write(Object o) { StringBuilder sb = new StringBuilder(); w(sb, o); return sb.toString(); }
    @SuppressWarnings("unchecked")
    private static void w(StringBuilder sb, Object o) {
        if (o == null) sb.append("null");
        else if (o instanceof String) str(sb, (String) o);
        else if (o instanceof Number || o instanceof Boolean) sb.append(o);
        else if (o instanceof Map) {
            sb.append('{'); boolean f = true;
            for (Map.Entry<String, Object> e : ((Map<String, Object>) o).entrySet()) {
                if (!f) sb.append(','); f = false; str(sb, e.getKey()); sb.append(':'); w(sb, e.getValue());
            }
            sb.append('}');
        } else if (o instanceof List) {
            sb.append('['); boolean f = true;
            for (Object x : (List<Object>) o) { if (!f) sb.append(','); f = false; w(sb, x); }
            sb.append(']');
        } else str(sb, o.toString());
    }
    private static void str(StringBuilder sb, String s) {
        sb.append('"');
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"': sb.append("\\\""); break;
                case '\\': sb.append("\\\\"); break;
                case '\n': sb.append("\\n"); break;
                case '\r': sb.append("\\r"); break;
                case '\t': sb.append("\\t"); break;
                default:
                    if (c < 0x20) sb.append(String.format("\\u%04x", (int) c)); else sb.append(c);
            }
        }
        sb.append('"');
    }

public static Object parse(String s) { int[] p = {0}; Object v = val(s, p); return v; }
    private static void ws(String s, int[] p) { while (p[0] < s.length() && Character.isWhitespace(s.charAt(p[0]))) p[0]++; }
    private static Object val(String s, int[] p) {
        ws(s, p);
        char c = s.charAt(p[0]);
        if (c == '{') {
            Map<String, Object> m = new LinkedHashMap<>(); p[0]++; ws(s, p);
            if (s.charAt(p[0]) == '}') { p[0]++; return m; }
            while (true) {
                ws(s, p); String k = (String) val(s, p); ws(s, p); p[0]++; // ':'
                m.put(k, val(s, p)); ws(s, p);
                char d = s.charAt(p[0]++); if (d == '}') return m;
            }
        }
        if (c == '[') {
            List<Object> l = new ArrayList<>(); p[0]++; ws(s, p);
            if (s.charAt(p[0]) == ']') { p[0]++; return l; }
            while (true) {
                l.add(val(s, p)); ws(s, p);
                char d = s.charAt(p[0]++); if (d == ']') return l;
            }
        }
        if (c == '"') {
            StringBuilder sb = new StringBuilder(); p[0]++;
            while (true) {
                char d = s.charAt(p[0]++);
                if (d == '"') return sb.toString();
                if (d == '\\') {
                    char e = s.charAt(p[0]++);
                    switch (e) {
                        case 'n': sb.append('\n'); break; case 't': sb.append('\t'); break;
                        case 'r': sb.append('\r'); break; case 'b': sb.append('\b'); break;
                        case 'f': sb.append('\f'); break;
                        case 'u': sb.append((char) Integer.parseInt(s.substring(p[0], p[0] + 4), 16)); p[0] += 4; break;
                        default: sb.append(e);
                    }
                } else sb.append(d);
            }
        }
        if (s.startsWith("true", p[0])) { p[0] += 4; return true; }
        if (s.startsWith("false", p[0])) { p[0] += 5; return false; }
        if (s.startsWith("null", p[0])) { p[0] += 4; return null; }
        int st = p[0];
        while (p[0] < s.length() && "+-0123456789.eE".indexOf(s.charAt(p[0])) >= 0) p[0]++;
        String num = s.substring(st, p[0]);
        if (num.contains(".") || num.contains("e") || num.contains("E")) return Double.parseDouble(num);
        return Long.parseLong(num);
    }
}
