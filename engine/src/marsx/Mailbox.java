package marsx;

import java.util.ArrayDeque;

/** Minimal blocking queue on wait/notify — portable to TeaVM's green threads and Android. */
final class Mailbox<T> {
    private final ArrayDeque<T> q = new ArrayDeque<>();

    synchronized void put(T v) { q.addLast(v); notifyAll(); }

    synchronized T poll() { return q.pollFirst(); }

    synchronized T take() throws InterruptedException {
        while (q.isEmpty()) wait();
        return q.pollFirst();
    }

    synchronized void clear() { q.clear(); }

    synchronized int size() { return q.size(); }
}
