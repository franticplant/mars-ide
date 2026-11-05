package marsx;

import java.io.*;

/** stdio transport: one JSON command per line on stdin, replies/events on stdout. Used by the TUI. */
public final class StdioMain {
    public static void main(String[] args) throws Exception {
        final PrintStream proto = new PrintStream(new FileOutputStream(FileDescriptor.out), true, "UTF-8");
        File root = new File(args.length > 0 ? args[0] : ".");
        MarsEngine engine = new MarsEngine(line -> { proto.println(line); proto.flush(); }, root);
        engine.announce();
        BufferedReader in = new BufferedReader(new InputStreamReader(new FileInputStream(FileDescriptor.in), "UTF-8"));
        String line;
        while ((line = in.readLine()) != null) engine.handle(line);
        System.exit(0);
    }
}
