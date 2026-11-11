/* Engine client: the same API over HTTP+SSE (browser) or the Android JavaScript bridge (APK). */
(function (global) {
  "use strict";

  class Engine {
    constructor() {
      this.pending = new Map();
      this.listeners = new Set();
      this.prefix = Math.random().toString(36).slice(2, 7) + "-";
      this.seq = 0;
      this.connected = false;
      this.native = !!global.MarsNative;
      this.queue = [];
    }

    on(fn) { this.listeners.add(fn); return () => this.listeners.delete(fn); }
    emit(ev) { for (const fn of this.listeners) { try { fn(ev); } catch (e) { console.error(e); } } }

    /**
     * Static build: the engine runs in a Web Worker (TeaVM-compiled MARS); the durable workspace is IndexedDB.
     * The worker's in-memory file system is kept an exact mirror of IndexedDB:
     *   - on start, every IndexedDB file is pushed to the worker;
     *   - every workspace change (write/delete/rename/mkdir) is applied to IndexedDB, then mirrored to the worker;
     *   - files the MIPS program writes (file syscalls) are pulled back into IndexedDB when a run stops or a
     *     step completes, and the UI is told (ev "fs_changed").
     */
    startLocal() {
      this.local = true;
      const FS = global.MarsIDBFS;
      this.internal = new Map();
      this.mirroredVersions = new Map();
      this.lastPull = 0;
      this.worker = new Worker("engine/worker.js");
      this.worker.onmessage = (e) => {
        let m;
        try { m = JSON.parse(e.data); } catch (err) { return; }
        if (m.ev === "ready") { this.pushAll().then(() => this.setConnected(true)).catch(e => this.storageError(e)); return; }
        if (typeof m.id === "string" && m.id.startsWith("int-")) {
          const p = this.internal.get(m.id);
          if (p) { this.internal.delete(m.id); m.ok ? p.res(m) : p.rej(new Error(m.error)); }
          return;
        }
        if (m.ev === "stopped") this.schedulePull();
        else if (m.state && this.stepIds && this.stepIds.delete(m.id)) this.schedulePull();
        this.receive(m);
      };
      this.worker.onerror = (e) => {
        console.error(e);
        if (global.MARS_BACKEND === "wasm") this.emit({ ev: "backend_error", message: e.message || "Unsupported backend or runtime error" });
        this.emit({ ev: "disconnected" });
      };
      this.ready = FS.seed(global.MARS_EXAMPLES || []).catch(e => { this.storageFailure = e; this.storageError(e); });
      this.stepIds = new Set();
      if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(() => { });
    }

    storageError(error) {
      if (!this.storageReported) { this.storageReported = true; this.emit({ ev: "storage_error", message: error.message || String(error) }); }
    }

    /** request/reply with the worker for the host's own bookkeeping (never shown to the UI) */
    workerCall(cmd, args = {}) {
      const id = "int-" + (++this.seq);
      return new Promise((res, rej) => {
        this.internal.set(id, { res, rej });
        this.worker.postMessage(JSON.stringify(Object.assign({ id, cmd }, args)));
      });
    }

    async pushAll() {
      const FS = global.MarsIDBFS;
      await this.ready;
      if (this.storageFailure) throw this.storageFailure;
      const files = await FS.files();
      await Promise.all(files.map(async f => {
        await this.workerCall("fs_write", { path: f.path, b64: FS.toB64(f.data) });
        this.mirroredVersions.set(f.path, f.version);
      }));
      this.lastPull = Date.now();
    }

    schedulePull() {
      clearTimeout(this.pullTimer);
      this.pullTimer = setTimeout(() => this.pullFromWorker().catch(e => this.storageError(new Error("Program file changes could not be saved to browser storage. Keep this tab open and export a backup. " + e.message))), 150);
    }

    /** Copy files the program created/changed in the worker back into IndexedDB. */
    async pullFromWorker() {
      const FS = global.MarsIDBFS;
      const since = this.lastPull;
      const pulledAt = Date.now();
      const list = await this.workerCall("fs_list");
      const changed = [];
      for (const n of list.entries || []) {
        if (n.dir || (since && n.mtime && n.mtime < since - 1000)) continue;
        const r = await this.workerCall("fs_read", { path: n.path, binary: true });
        const version = FS.fingerprintB64(r.b64), previous = this.mirroredVersions.get(n.path);
        if (version === previous) continue; // An unchanged worker file must not overwrite another tab's edit.
        const mine = await FS.bytes(n.path);
        if (mine && FS.fingerprint(mine) === version) { this.mirroredVersions.set(n.path, version); continue; }
        await FS.write(n.path, null, r.b64, previous ?? null);
        this.mirroredVersions.set(n.path, version);
        changed.push(n.path);
      }
      this.lastPull = pulledAt;
      if (changed.length) this.emit({ ev: "fs_changed", paths: changed });
    }

    async postLocal(line) {
      const FS = global.MarsIDBFS;
      let msg;
      try { msg = JSON.parse(line); } catch (e) { return; }
      const reply = (o) => this.receive(Object.assign({ id: msg.id, ok: true }, o));
      const mirror = (cmd, args) => this.workerCall(cmd, args).catch(e => {
        this.mirrorFailure = e;
        this.storageError(new Error("The browser file was saved, but the simulator mirror failed. Export a backup and reload before assembling. " + e.message));
        throw e;
      });
      try {
        if (msg.cmd === "assemble" && this.mirrorFailure) throw new Error("Simulator files are out of sync. Reload before assembling.");
        switch (msg.cmd) {
          case "fs_list": return reply(await FS.list());
          case "fs_read": return reply(await FS.read(msg.path, msg.binary));
          case "fs_write": {
            const r = await FS.write(msg.path, msg.text, msg.b64, msg.expectedVersion);
            await mirror("fs_write", msg.b64 != null ? { path: r.path, b64: msg.b64 } : { path: r.path, text: msg.text == null ? "" : String(msg.text) });
            this.mirroredVersions.set(r.path, r.version);
            return reply(r);
          }
          case "fs_delete": {
            const r = await FS.remove(msg.path); await mirror("fs_delete", { path: msg.path });
            for (const path of this.mirroredVersions.keys()) if (path === msg.path || path.startsWith(msg.path + "/")) this.mirroredVersions.delete(path);
            return reply(r);
          }
          case "fs_rename": {
            const r = await FS.rename(msg.from, msg.to); await mirror("fs_rename", { from: msg.from, to: msg.to });
            for (const [path, version] of [...this.mirroredVersions]) if (path === msg.from || path.startsWith(msg.from + "/")) {
              this.mirroredVersions.delete(path); this.mirroredVersions.set(msg.to + path.slice(msg.from.length), version);
            }
            return reply(r);
          }
          case "fs_mkdir": { const r = await FS.mkdir(msg.path); await mirror("fs_mkdir", { path: msg.path }); return reply(r); }
          case "step": this.stepIds.add(msg.id); break;
        }
      } catch (e) {
        if (e.code === "WORKSPACE_CONFLICT" || FS.readonly) this.storageError(e);
        if (e.name === "QuotaExceededError" || /quota/i.test(e.message || "")) this.emit({ ev: "history_error", message: "Browser storage is full. The save was not completed; export your work and free space." });
        return this.receive({ id: msg.id, ok: false, error: e.message || String(e) });
      }
      this.worker.postMessage(line);
    }

    start() {
      if (global.MARS_STATIC) { this.startLocal(); return; }
      if (this.native) {
        global.__marsRecv = (json) => this.receive(typeof json === "string" ? JSON.parse(json) : json);
        global.MarsNative.ready();
        this.setConnected(true);
        return;
      }
      const es = new EventSource("api/events");
      this.es = es;
      es.onopen = () => this.setConnected(true);
      es.onerror = () => { if (this.connected) this.setConnected(false); };
      es.onmessage = (m) => { try { this.receive(JSON.parse(m.data)); } catch (e) { console.error(e); } };
    }

    setConnected(v) {
      this.connected = v;
      this.emit({ ev: v ? "connected" : "disconnected" });
      if (v) {
        const q = this.queue; this.queue = [];
        for (const line of q) this.post(line);
      }
    }

    receive(msg) {
      if (msg.ev) { this.emit(msg); return; }
      const p = this.pending.get(msg.id);
      if (!p) return;                       // reply for another tab
      this.pending.delete(msg.id);
      clearTimeout(p.timer);
      if (msg.ok) p.resolve(msg); else p.reject(new Error(msg.error || "engine error"));
    }

    post(line) {
      if (this.local) { this.postLocal(line); return; }
      if (this.native) { global.MarsNative.send(line); return; }
      fetch("api/cmd", { method: "POST", body: line, headers: { "Content-Type": "application/json" }, credentials: "same-origin" })
        .then(r => { if (r.status === 401) this.emit({ ev: "unauthorized" }); })
        .catch(() => this.emit({ ev: "disconnected" }));
    }

    call(cmd, args = {}, timeoutMs = 120000) {
      const id = this.prefix + (++this.seq);
      const line = JSON.stringify(Object.assign({ id, cmd }, args));
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => {
          if (this.pending.delete(id)) reject(new Error(`${cmd}: no answer from engine`));
        }, timeoutMs);
        this.pending.set(id, { resolve, reject, timer });
        if (!this.connected && !this.native) this.queue.push(line); else this.post(line);
      });
    }
  }

  global.MarsEngineClient = Engine;
})(window);
