package marsx;

import com.sun.net.httpserver.*;

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.*;
import java.util.concurrent.*;

/**
 * Web transport: serves the web UI and bridges it to the engine.
 *   POST /api/cmd     one or more JSON command lines (fire and forget)
 *   GET  /api/events  Server-Sent Events: every reply and event (shared session)
 * Pure JDK (com.sun.net.httpserver) — no dependencies.
 */
public final class WebServer {
    private static final int BACKLOG = 600;

    private final List<BlockingQueue<String>> clients = new CopyOnWriteArrayList<>();
    private final ArrayDeque<String> backlog = new ArrayDeque<>();
    private final String token;
    private final File webRoot;
    private MarsEngine engine;

    WebServer(String token, File webRoot) { this.token = token; this.webRoot = webRoot; }

    void broadcast(String json) {
        if (json.startsWith("{\"ev\":\"out\"") || json.startsWith("{\"ev\":\"mmio_out\"")) {
            synchronized (backlog) {
                backlog.addLast(json);
                while (backlog.size() > BACKLOG) backlog.removeFirst();
            }
        }
        for (BlockingQueue<String> q : clients) q.offer(json);
    }

    public static void main(String[] args) throws Exception {
        String host = "127.0.0.1", tok = null, web = null, root = ".";
        int port = 8080;
        boolean auth = true;
        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--host": host = args[++i]; break;
                case "--port": port = Integer.parseInt(args[++i]); break;
                case "--token": tok = args[++i]; break;
                case "--no-auth": auth = false; break;
                case "--web": web = args[++i]; break;
                case "--root": root = args[++i]; break;
                case "-h": case "--help":
                    System.out.println("usage: WebServer [--host 127.0.0.1] [--port 8080] [--root DIR] [--web DIR] [--token T | --no-auth]");
                    return;
                default: root = args[i];
            }
        }
        if (tok == null && System.getenv("MARS_WEB_TOKEN") != null) tok = System.getenv("MARS_WEB_TOKEN");
        if (auth && (tok == null || tok.isEmpty())) {
            byte[] b = new byte[12];
            new SecureRandom().nextBytes(b);
            StringBuilder sb = new StringBuilder();
            for (byte x : b) sb.append(String.format("%02x", x));
            tok = sb.toString();
        }
        final PrintStream log = new PrintStream(new FileOutputStream(FileDescriptor.out), true, "UTF-8");
        File webRoot = web == null ? null : new File(web).getCanonicalFile();
        WebServer ws = new WebServer(auth ? tok : null, webRoot);
        File ws_root = new File(root).getCanonicalFile();
        ws_root.mkdirs();
        ws.engine = new MarsEngine(ws::broadcast, ws_root);

        HttpServer server = HttpServer.create(new InetSocketAddress(host, port), 64);
        server.setExecutor(Executors.newCachedThreadPool(r -> { Thread t = new Thread(r, "http"); t.setDaemon(true); return t; }));
        server.createContext("/api/events", ws::events);
        server.createContext("/api/cmd", ws::command);
        server.createContext("/", ws::files);
        server.start();
        String shown = host.equals("0.0.0.0") ? "localhost" : host;
        log.println("MARS web UI (engine MARS " + mars.Globals.version + ", workspace " + ws_root + ")");
        log.println("  open: http://" + shown + ":" + port + "/" + (auth ? "?token=" + tok : ""));
        if (!auth) log.println("  WARNING: authentication disabled (--no-auth)");
        Thread.currentThread().join();
    }

    // ------------------------------------------------------------- auth
    private boolean authorized(HttpExchange ex) {
        if (token == null) return true;
        String q = ex.getRequestURI().getRawQuery();
        if (q != null) for (String p : q.split("&")) if (p.equals("token=" + token)) return true;
        List<String> cookies = ex.getRequestHeaders().get("Cookie");
        if (cookies != null) for (String c : cookies) for (String part : c.split(";"))
            if (part.trim().equals("mars_token=" + token)) return true;
        String h = ex.getRequestHeaders().getFirst("X-Mars-Token");
        return token.equals(h);
    }

    private static void send(HttpExchange ex, int code, String type, byte[] body) throws IOException {
        ex.getResponseHeaders().set("Content-Type", type);
        ex.getResponseHeaders().set("X-Content-Type-Options", "nosniff");
        ex.sendResponseHeaders(code, body.length == 0 ? -1 : body.length);
        if (body.length > 0) try (OutputStream os = ex.getResponseBody()) { os.write(body); }
        ex.close();
    }

    // ------------------------------------------------------------- handlers
    private void command(HttpExchange ex) throws IOException {
        if (!authorized(ex)) { send(ex, 401, "text/plain", "unauthorized".getBytes(StandardCharsets.UTF_8)); return; }
        if (!"POST".equals(ex.getRequestMethod())) { send(ex, 405, "text/plain", new byte[0]); return; }
        String body = new String(readAll(ex.getRequestBody()), StandardCharsets.UTF_8);
        for (String line : body.split("\n")) if (!line.trim().isEmpty()) engine.handle(line);
        send(ex, 204, "text/plain", new byte[0]);
    }

    private void events(HttpExchange ex) throws IOException {
        if (!authorized(ex)) { send(ex, 401, "text/plain", "unauthorized".getBytes(StandardCharsets.UTF_8)); return; }
        Headers h = ex.getResponseHeaders();
        h.set("Content-Type", "text/event-stream; charset=utf-8");
        h.set("Cache-Control", "no-cache");
        h.set("X-Accel-Buffering", "no");
        ex.sendResponseHeaders(200, 0);
        BlockingQueue<String> q = new LinkedBlockingQueue<>();
        OutputStream os = ex.getResponseBody();
        try {
            List<String> replay;
            synchronized (backlog) { replay = new ArrayList<>(backlog); clients.add(q); }
            write(os, "{\"ev\":\"replay_begin\"}");
            for (String s : replay) write(os, s);
            write(os, "{\"ev\":\"replay_end\"}");
            os.flush();
            while (true) {
                String s = q.poll(15, TimeUnit.SECONDS);
                if (s == null) { os.write(": ping\n\n".getBytes(StandardCharsets.UTF_8)); os.flush(); continue; }
                write(os, s);
                String more;
                while ((more = q.poll()) != null) write(os, more);
                os.flush();
            }
        } catch (IOException | InterruptedException e) {
            // client went away
        } finally {
            clients.remove(q);
            try { os.close(); } catch (IOException ignored) { }
            ex.close();
        }
    }

    private static void write(OutputStream os, String json) throws IOException {
        os.write(("data: " + json + "\n\n").getBytes(StandardCharsets.UTF_8));
    }

    private static final Map<String, String> TYPES = new HashMap<>();
    static {
        TYPES.put("html", "text/html; charset=utf-8"); TYPES.put("js", "text/javascript; charset=utf-8");
        TYPES.put("css", "text/css; charset=utf-8"); TYPES.put("svg", "image/svg+xml");
        TYPES.put("png", "image/png"); TYPES.put("json", "application/json"); TYPES.put("webmanifest", "application/manifest+json");
        TYPES.put("ico", "image/x-icon"); TYPES.put("woff2", "font/woff2"); TYPES.put("txt", "text/plain; charset=utf-8"); TYPES.put("pdf", "application/pdf");
    }

    private void files(HttpExchange ex) throws IOException {
        String path = ex.getRequestURI().getPath();
        if (path.equals("/")) path = "/index.html";
        if (path.equals("/index.html") || path.equals("/manifest.webmanifest") || path.startsWith("/icon")) {
            // the shell and icons are public so the login hint can render; data needs the token
        } else if (!authorized(ex)) {
            send(ex, 401, "text/plain", "unauthorized".getBytes(StandardCharsets.UTF_8));
            return;
        }
        if (path.equals("/index.html") && token != null) {
            String q = ex.getRequestURI().getRawQuery();
            if (q != null && q.contains("token=" + token)) {
                ex.getResponseHeaders().add("Set-Cookie", "mars_token=" + token + "; Path=/; HttpOnly; SameSite=Strict; Max-Age=31536000");
                ex.getResponseHeaders().set("Location", "/");
                send(ex, 303, "text/plain", new byte[0]);
                return;
            }
        }
        if (path.contains("..")) { send(ex, 400, "text/plain", new byte[0]); return; }
        byte[] data = null;
        if (webRoot != null) {
            File f = new File(webRoot, path.substring(1)).getCanonicalFile();
            if (f.getPath().startsWith(webRoot.getPath()) && f.isFile()) data = readAll(new FileInputStream(f));
        } else {
            InputStream in = WebServer.class.getResourceAsStream("/web" + path);
            if (in != null) data = readAll(in);
        }
        if (data == null) { send(ex, 404, "text/plain", "not found".getBytes(StandardCharsets.UTF_8)); return; }
        String ext = path.substring(path.lastIndexOf('.') + 1);
        ex.getResponseHeaders().set("Cache-Control", "no-cache");
        if (path.equals("/index.html")) {
            ex.getResponseHeaders().set("Content-Security-Policy",
                "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'");
            ex.getResponseHeaders().set("X-Frame-Options", "DENY");
        }
        send(ex, 200, TYPES.getOrDefault(ext, "application/octet-stream"), data);
    }

    static byte[] readAll(InputStream in) throws IOException {
        try (InputStream i = in) {
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            byte[] b = new byte[8192];
            int n;
            while ((n = i.read(b)) > 0) bo.write(b, 0, n);
            return bo.toByteArray();
        }
    }
}
