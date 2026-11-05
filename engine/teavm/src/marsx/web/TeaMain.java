package marsx.web;

import java.io.File;

import org.teavm.jso.JSBody;
import org.teavm.jso.JSFunctor;
import org.teavm.jso.JSObject;

import marsx.MarsEngine;

/**
 * Browser entry point (TeaVM). Runs inside a Web Worker:
 *   page → worker: postMessage(jsonCommandLine)  → engine
 *   worker → page: postMessage(jsonReplyOrEvent)
 * Files live in TeaVM's in-memory file system under /work; the page keeps the
 * durable copy (IndexedDB) and syncs it in.
 */
public final class TeaMain {
    @JSFunctor
    public interface StringHandler extends JSObject { void handle(String s); }

    @JSBody(params = "f", script = "self.__marsInput = f;")
    private static native void installInput(StringHandler f);

    @JSBody(params = "s", script = "self.postMessage(s);")
    private static native void post(String s);

    /** Commands from the page. The worker sleeps on it — no polling, no idle wake-ups. */
    private static final Inbox INBOX = new Inbox();

    // Java's Float/Double.toString rules (JDK 19+): shortest round-tripping digits (length 1 widened to 2 when
    // closer), plain notation for 1e-3 <= |x| < 1e7, otherwise d.dddE±n. TeaVM's own toString differs.
    private static final String JAVA_FMT =
        "var f = function (x, isFloat) {"
      + " if (x !== x) return 'NaN'; if (x === Infinity) return 'Infinity'; if (x === -Infinity) return '-Infinity';"
      + " if (x === 0) return (1 / x < 0) ? '-0.0' : '0.0';"
      + " var rt = function (s) { var v = parseFloat(s); return isFloat ? Math.fround(v) === x : v === x; };"
      + " var s = null;"
      + " if (isFloat) { for (var p = 1; p <= 9; p++) { var t = x.toExponential(p - 1); if (rt(t)) { s = t; break; } } }"
      + " else s = x.toExponential();"
      + " var m0 = s.split('e')[0].replace('-', '').replace('.', '');"
      // Java widens a 1-digit result to 2 digits when that is closer to the EXACT value (e.g. 4.9E-324).
      // Compare exactly: BigInt against a 25-digit correctly-rounded expansion of x.
      + " var dec = function (str) { var n = str.charAt(0) === '-'; if (n) str = str.substring(1); var q = str.split('e');"
      + "   var m = q[0], dot = m.indexOf('.'), fr = dot < 0 ? '' : m.substring(dot + 1);"
      + "   return { d: BigInt((dot < 0 ? m : m.substring(0, dot)) + fr), e: parseInt(q[1], 10) - fr.length }; };"
      + " var scale = function (v, e) { var r = v.d, k = v.e - e, ten = BigInt(10); while (k-- > 0) r = r * ten; return r; };"
      + " var dist = function (a, b, e) { var r = scale(a, e) - scale(b, e); return r < BigInt(0) ? -r : r; };"
      + " if (s.split('e')[0].replace('-', '').replace('.', '').length === 1) { var s2 = x.toExponential(1);"
      + "   if (rt(s2)) { var X = dec(Math.abs(x).toExponential(24)), A = dec(s), B = dec(s2);"
      + "     var e = Math.min(X.e, A.e, B.e); if (dist(B, X, e) < dist(A, X, e)) s = s2; } }"
      + " var neg = s.charAt(0) === '-'; if (neg) s = s.substring(1);"
      + " var parts = s.split('e'); var exp = parseInt(parts[1], 10);"
      + " var d = parts[0].replace('.', '').replace(/0+$/, ''); if (d === '') d = '0';"
      + " var ax = Math.abs(x), out;"
      + " if (ax >= 1e-3 && ax < 1e7) { var pt = exp + 1;"
      + "   if (pt <= 0) out = '0.' + new Array(1 - pt).join('0') + d;"
      + "   else if (pt >= d.length) out = d + new Array(pt - d.length + 1).join('0') + '.0';"
      + "   else out = d.substring(0, pt) + '.' + d.substring(pt); }"
      + " else out = d.charAt(0) + '.' + (d.length > 1 ? d.substring(1) : '0') + 'E' + exp;"
      + " return (neg ? '-' : '') + out; };";

    @JSBody(params = "v", script = JAVA_FMT + " return f(v, true);")
    private static native String jsFloat(double v);

    @JSBody(params = "v", script = JAVA_FMT + " return f(v, false);")
    private static native String jsDouble(double v);

    static final class Inbox {
        private final java.util.ArrayDeque<String> q = new java.util.ArrayDeque<>();
        synchronized void put(String s) { q.addLast(s); notifyAll(); }
        synchronized String take() throws InterruptedException { while (q.isEmpty()) wait(); return q.pollFirst(); }
    }

    public static void main(String[] args) throws Exception {
        // called from JS on message: never blocks, just queues (green threads switch only at blocking points)
        mars.ext.IO.numberFormat = new mars.ext.IO.NumberFormat() {
            public String floatText(float v) { return jsFloat(v); }
            public String doubleText(double v) { return jsDouble(v); }
        };
        MarsEngine.CHUNK = 50_000;   // short run slices so pause/input messages get through
        MarsEngine.YIELD_MS = 0;
        // JS callbacks can't block, so each message is handed over by a short-lived green thread
        installInput(s -> new Thread(() -> INBOX.put(s)).start());
        File root = new File("/work");
        root.mkdirs();
        MarsEngine engine = new MarsEngine(TeaMain::post, root);
        engine.announce();
        while (true) engine.handle(INBOX.take());
    }
}
