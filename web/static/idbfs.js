/* Workspace file system in IndexedDB for the static build (same semantics as the engine's fs_* commands). */
(function (global) {
  "use strict";
  const DB = "mars-ide", STORE = "files", HISTORY = "history";
  const WITNESS = "marside.workspace-witness.v1";
  let dbp = null;
  function db() {
    if (!dbp) dbp = new Promise((res, rej) => {
      const r = indexedDB.open(DB, 2);
      r.onupgradeneeded = () => {
        if (!r.result.objectStoreNames.contains(STORE)) r.result.createObjectStore(STORE, { keyPath: "path" });
        if (!r.result.objectStoreNames.contains(HISTORY)) {
          const history = r.result.createObjectStore(HISTORY, { keyPath: "id", autoIncrement: true });
          history.createIndex("path", "path");
          history.createIndex("content", ["path", "checksum"]);
        }
      };
      r.onsuccess = () => {
        r.result.onversionchange = () => { r.result.close(); dbp = null; };
        res(r.result);
      };
      r.onerror = () => rej(r.error);
      r.onblocked = () => rej(new Error("Workspace storage is blocked by another tab. Close older IDE tabs and retry; do not clear site data."));
    });
    return dbp;
  }
  async function tx(mode, fn, history = false) {
    const d = await db();
    return new Promise((res, rej) => {
      const t = d.transaction(history ? [STORE, HISTORY] : [STORE], mode), st = t.objectStore(STORE);
      let out;
      const fail = e => { try { t.abort(); } catch (_) { } rej(e); };
      try { Promise.resolve(fn(st, history ? t.objectStore(HISTORY) : null)).then(v => { out = v; }, fail); } catch (e) { fail(e); }
      t.oncomplete = () => res(out);
      t.onerror = () => rej(t.error);
      t.onabort = () => rej(t.error || new Error("Workspace transaction was aborted; changes were not saved."));
    });
  }
  const req = (r) => new Promise((res, rej) => { r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); });
  const norm = (p) => String(p || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, "").replace(/\/{2,}/g, "/");
  function check(p) {
    if (p.split("/").some(x => x === ".." )) throw new Error("path outside workspace: " + p);
    return p;
  }
  const enc = new TextEncoder(), dec = new TextDecoder();
  const toB64 = (u8) => { let s = ""; for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000)); return btoa(s); };
  const fromB64 = (b) => { const s = atob(b), u8 = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) u8[i] = s.charCodeAt(i); return u8; };

  async function all() { return tx("readonly", st => req(st.getAll())); }
  // A cheap corruption detector, not a cryptographic authenticity claim. Legacy bytes stay untouched.
  function checksum(data) {
    let hash = 2166136261;
    for (const byte of data) hash = Math.imul(hash ^ byte, 16777619);
    return "fnv1a32:" + (hash >>> 0).toString(16).padStart(8, "0");
  }
  function problem(it) {
    if (typeof it.path !== "string" || !it.path || !(it.data instanceof Uint8Array)) return "invalid stored file record";
    if (norm(it.path) !== it.path || it.path.split("/").includes("..")) return "invalid stored workspace path";
    if (it.checksum != null && it.checksum !== checksum(it.data)) return "stored file checksum mismatch";
    return null;
  }
  function checked(it) {
    const error = problem(it);
    if (error) { FS.readonly = `${it.path || "Workspace"}: ${error}. Stored data has not been replaced.`; throw new Error(FS.readonly); }
    return it;
  }
  function writable() { if (FS.readonly) throw new Error("Workspace is protected: " + FS.readonly); }
  const equalBytes = (a, b) => a.length === b.length && a.every((v, i) => v === b[i]);
  async function snapshot(history, path, data, kind, time = Date.now()) {
    const cursor = await req(history.index("path").openCursor(IDBKeyRange.only(path), "prev"));
    const last = cursor?.value;
    const hash = checksum(data);
    if (last && last.checksum === hash) {
      const previous = last.data instanceof Uint8Array ? last : await req(history.get(last.ref));
      if (!previous || previous.path !== path || !(previous.data instanceof Uint8Array) || checksum(previous.data) !== hash) throw new Error("History data is damaged; it was preserved.");
      if (equalBytes(previous.data, data)) return;
    }
    const candidates = await req(history.index("content").getAll(IDBKeyRange.only([path, hash])));
    const shared = candidates.find(it => it.data instanceof Uint8Array && equalBytes(it.data, data));
    await req(history.add(Object.assign({ path, kind, time, checksum: hash }, shared ? { ref: shared.id } : { data })));
  }
  function historyData(it, records) {
    const source = it.data instanceof Uint8Array ? it : records.get(it.ref);
    if (!source || source.path !== it.path || !(source.data instanceof Uint8Array) || checksum(source.data) !== it.checksum)
      throw new Error("History checksum mismatch; original data was preserved.");
    return source.data;
  }
  async function witness() {
    const items = await all();
    try { localStorage.setItem(WITNESS, JSON.stringify({ files: items.filter(it => !it.dir).length, updated: Date.now() })); } catch (_) { }
  }

  const FS = {
    readonly: null,
    async audit() {
      const items = await all(), issues = items.map(it => ({ path: it.path, error: problem(it) })).filter(it => it.error);
      let previous;
      try { previous = JSON.parse(localStorage.getItem(WITNESS) || "null"); } catch (_) { }
      if (!items.length && previous?.files > 0) issues.push({ path: "Workspace", error: "Workspace storage is unexpectedly empty; previous files were recorded in this browser" });
      if (issues.length) FS.readonly = issues.map(it => `${it.path}: ${it.error}`).join("; ");
      return { files: items.filter(it => !it.dir).length, unchecked: items.filter(it => !it.dir && !it.checksum).length,
        initialized: !!previous && typeof previous.files === "number", issues };
    },
    async recovery() {
      const history = await tx("readonly", async (_, store) => req(store.getAll()), true);
      return { format: "mars-ide-recovery-v1", created: new Date().toISOString(), origin: location.origin,
        records: (await all()).map(it => ({ path: it.path, dir: !!it.dir, mtime: it.mtime, checksum: it.checksum,
          b64: it.data instanceof Uint8Array ? toB64(it.data) : null,
          invalidData: it.data instanceof Uint8Array ? undefined : String(it.data), problem: problem(it) })),
        history: history.map(it => ({ id:it.id, path:it.path, kind:it.kind, time:it.time, ref:it.ref, checksum:it.checksum,
          b64:it.data instanceof Uint8Array ? toB64(it.data) : undefined,
          invalidData:it.data !== undefined && !(it.data instanceof Uint8Array) ? String(it.data) : undefined })) };
    },
    async list() {
      const items = await all();
      const dirs = new Set(), files = [];
      for (const it of items) {
        if (it.dir) dirs.add(it.path);
        else files.push(it);
        const parts = it.path.split("/");
        for (let i = 1; i < parts.length; i++) dirs.add(parts.slice(0, i).join("/"));
      }
      const entries = [
        ...[...dirs].map(p => ({ path: p, name: p.split("/").pop(), dir: true, size: 0, mtime: 0, depth: p.split("/").length - 1 })),
        ...files.map(f => ({ path: f.path, name: f.path.split("/").pop(), dir: false, size: f.data.length, mtime: f.mtime, depth: f.path.split("/").length - 1 })),
      ].filter(e => !e.name.startsWith("."));
      // depth-first order, folders first, like the engine's listing
      const kids = new Map();
      for (const e of entries) {
        const parent = e.path.includes("/") ? e.path.slice(0, e.path.lastIndexOf("/")) : "";
        if (!kids.has(parent)) kids.set(parent, []);
        kids.get(parent).push(e);
      }
      const out = [];
      const walk = (p) => {
        const ks = (kids.get(p) || []).sort((a, b) => a.dir !== b.dir ? (a.dir ? -1 : 1) : a.name.localeCompare(b.name, undefined, { sensitivity: "base" }));
        for (const k of ks) { out.push(k); if (k.dir) walk(k.path); }
      };
      walk("");
      return { entries: out, root: "browser" };
    },
    async read(path, binary) {
      path = check(norm(path));
      const it = await tx("readonly", st => req(st.get(path)));
      if (!it || it.dir) throw new Error("No such file: " + path);
      checked(it);
      const version = checksum(it.data);
      return binary ? { path, b64: toB64(it.data), mtime: it.mtime, version } : { path, text: dec.decode(it.data), mtime: it.mtime, version };
    },
    async bytes(path) { const it = await tx("readonly", st => req(st.get(check(norm(path))))); return it && !it.dir ? checked(it).data : null; },
    async write(path, text, b64, expectedVersion) {
      writable();
      path = check(norm(path));
      if (!path) throw new Error("empty file name");
      const data = b64 != null ? fromB64(b64) : enc.encode(text == null ? "" : String(text));
      const mtime = Date.now();
      const version = checksum(data);
      await tx("readwrite", async (st, history) => {
        const previous = await req(st.get(path));
        if (previous?.dir) throw new Error(`${path} is a folder, not a file`);
        const descendant = await req(st.openCursor(IDBKeyRange.bound(path + "/", path + "/\uffff")));
        if (descendant) throw new Error(`${path} is a folder, not a file`);
        const parts = path.split("/");
        for (let i = 1; i < parts.length; i++) {
          const parent = await req(st.get(parts.slice(0, i).join("/")));
          if (parent && !parent.dir) throw new Error(`${parent.path} is a file, not a folder`);
        }
        const current = previous && !previous.dir ? checksum(checked(previous).data) : null;
        if (expectedVersion !== undefined && current !== expectedVersion) {
          const error = new Error(`${path} changed in another tab or by the program. It was not overwritten. Download a recovery copy to preserve both versions.`);
          error.code = "WORKSPACE_CONFLICT"; throw error;
        }
        if (previous && !previous.dir) await snapshot(history, path, previous.data, "saved");
        await snapshot(history, path, data, "saved", mtime);
        await req(st.put({ path, data, mtime, checksum: version }));
      }, true);
      await witness();
      return { path, mtime, version };
    },
    async mkdir(path) {
      writable();
      path = check(norm(path));
      if (!path) throw new Error("empty folder name");
      await tx("readwrite", async st => {
        const parts = path.split("/");
        for (let i = 1; i <= parts.length; i++) {
          const existing = await req(st.get(parts.slice(0, i).join("/")));
          if (existing && !existing.dir) throw new Error(`${existing.path} already exists as a file`);
          if (i === parts.length && existing) return;
        }
        await req(st.add({ path, dir: true, data: new Uint8Array(0), mtime: Date.now() }));
      });
      return { path };
    },
    async remove(path) {
      writable();
      path = check(norm(path));
      await tx("readwrite", async (st, history) => {
        const items = await req(st.getAll());
        for (const it of items.filter(it => it.path === path || it.path.startsWith(path + "/"))) {
          if (!it.dir) await snapshot(history, it.path, checked(it).data, "before delete");
          await req(st.delete(it.path));
        }
      }, true);
      await witness();
      return {};
    },
    async rename(from, to) {
      writable();
      from = check(norm(from)); to = check(norm(to));
      await tx("readwrite", async (st, history) => {
        const items = await req(st.getAll());
        // the target may also exist only implicitly, as the parent folder of other files
        if (items.some(it => it.path === to || it.path.startsWith(to + "/"))) throw new Error(to.split("/").pop() + " already exists");
        const moving = items.filter(it => it.path === from || it.path.startsWith(from + "/"));
        if (!moving.length) throw new Error("No such file: " + from);
        const versions = await req(history.getAll());
        for (const it of moving) { await req(st.delete(it.path)); await req(st.put(Object.assign({}, it, { path: to + it.path.slice(from.length) }))); }
        for (const it of versions.filter(it => it.path === from || it.path.startsWith(from + "/")))
          await req(history.put(Object.assign({}, it, { path: to + it.path.slice(from.length) })));
      }, true);
      return { path: to };
    },
    async files() { return (await all()).filter(it => !it.dir).map(it => Object.assign({}, checked(it), { version: checksum(it.data) })); },
    async checkpoint(path, text) {
      writable(); path = check(norm(path));
      if (!path) throw new Error("empty file name");
      const data = enc.encode(String(text));
      await tx("readwrite", async (_, history) => snapshot(history, path, data, "draft"), true);
    },
    async history(path) {
      path = check(norm(path));
      return tx("readonly", async (_, history) => {
        const list = await req(history.index("path").getAll(IDBKeyRange.only(path)));
        const records = new Map(list.map(it => [it.id, it]));
        return list.reverse().map(it => {
          const data = historyData(it, records);
          return { id: it.id, path: it.path, kind: it.kind, time: it.time, text: dec.decode(data), b64: toB64(data) };
        });
      }, true);
    },
    async allHistory() {
      return tx("readonly", async (_, history) => {
        const list = await req(history.getAll());
        const records = new Map(list.map(it => [it.id, it]));
        return list.map(it => {
          const data = historyData(it, records);
          return { path: it.path, kind: it.kind, time: it.time, b64: toB64(data), checksum: it.checksum };
        });
      }, true);
    },
    async hasHistoryPrefix(prefix) {
      return tx("readonly", async (_, history) => {
        const index = history.index("path");
        return (await req(index.getKey(prefix))) !== undefined ||
          !!(await req(index.openCursor(IDBKeyRange.bound(prefix + "/", prefix + "/\uffff"))));
      }, true);
    },
    async restoreBackupCopy(prefix, files, versions) {
      writable(); prefix = check(norm(prefix));
      if (!prefix || prefix.includes("/")) throw new Error("Invalid backup destination");
      const clean = p => {
        if (typeof p !== "string" || !p || p !== norm(p) || p.split("/").some(x => !x || x === "." || x === ".."))
          throw new Error("Invalid path in backup");
        return p;
      };
      const prepared = files.map(f => {
        const path = clean(f.path);
        if (!(f.data instanceof Uint8Array)) throw new Error("Invalid file in backup");
        return { path: `${prefix}/${path}`, data: f.data, mtime: Date.now(), checksum: checksum(f.data) };
      });
      if (new Set(prepared.map(f => f.path)).size !== prepared.length) throw new Error("Duplicate file path in backup");
      const sortedPaths = prepared.map(f => f.path).sort();
      if (sortedPaths.some((path, i) => i > 0 && path.startsWith(sortedPaths[i - 1] + "/")))
        throw new Error("A backup path is both a file and a folder");
      const old = versions.map(v => {
        const path = clean(v.path), data = fromB64(v.b64);
        if (checksum(data) !== v.checksum || !Number.isFinite(v.time) || typeof v.kind !== "string") throw new Error("Invalid history record in backup");
        return { path: `${prefix}/${path}`, data, time: v.time, kind: v.kind, checksum: v.checksum };
      });
      await tx("readwrite", async (st, history) => {
        const existing = await req(st.getAllKeys());
        if (existing.some(p => p === prefix || String(p).startsWith(prefix + "/"))) throw new Error("Backup destination already exists");
        const index = history.index("path");
        if ((await req(index.getKey(prefix))) !== undefined ||
            (await req(index.openCursor(IDBKeyRange.bound(prefix + "/", prefix + "/\uffff")))))
          throw new Error("Backup destination contains older history");
        for (const f of prepared) await req(st.add(f));
        for (const v of old) await req(history.add(v));
      }, true);
      await witness();
      return { prefix, files: prepared.length, versions: old.length };
    },
    async seed(list) {
      const report = await FS.audit();
      if (report.issues.length) throw new Error(FS.readonly);
      const items = await all();
      if (items.length || report.initialized) { await witness(); return false; }
      writable();
      const records = list.map(f => { const data = enc.encode(f.text); return { path: check(norm(f.path)), data, mtime: Date.now(), checksum: checksum(data) }; });
      await tx("readwrite", st => Promise.all(records.map(it => req(st.put(it)))));
      await witness();
      return true;
    },
    toB64,
    fingerprint: checksum,
    fingerprintB64: b64 => checksum(fromB64(b64)),
  };
  global.MarsIDBFS = FS;
})(window);
