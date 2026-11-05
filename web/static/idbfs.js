/* Workspace file system in IndexedDB for the static build (same semantics as the engine's fs_* commands). */
(function (global) {
  "use strict";
  const DB = "mars-ide", STORE = "files";
  let dbp = null;
  function db() {
    if (!dbp) dbp = new Promise((res, rej) => {
      const r = indexedDB.open(DB, 1);
      r.onupgradeneeded = () => r.result.createObjectStore(STORE, { keyPath: "path" });
      r.onsuccess = () => res(r.result);
      r.onerror = () => rej(r.error);
    });
    return dbp;
  }
  async function tx(mode, fn) {
    const d = await db();
    return new Promise((res, rej) => {
      const t = d.transaction(STORE, mode), st = t.objectStore(STORE);
      let out;
      Promise.resolve(fn(st)).then(v => { out = v; });
      t.oncomplete = () => res(out);
      t.onerror = () => rej(t.error);
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

  const FS = {
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
      return binary ? { path, b64: toB64(it.data), mtime: it.mtime } : { path, text: dec.decode(it.data), mtime: it.mtime };
    },
    async bytes(path) { const it = await tx("readonly", st => req(st.get(norm(path)))); return it && !it.dir ? it.data : null; },
    async write(path, text, b64) {
      path = check(norm(path));
      if (!path) throw new Error("empty file name");
      const data = b64 != null ? fromB64(b64) : enc.encode(text == null ? "" : String(text));
      const mtime = Date.now();
      await tx("readwrite", st => req(st.put({ path, data, mtime })));
      return { path, mtime };
    },
    async mkdir(path) {
      path = check(norm(path));
      await tx("readwrite", st => req(st.put({ path, dir: true, data: new Uint8Array(0), mtime: Date.now() })));
      return { path };
    },
    async remove(path) {
      path = check(norm(path));
      const items = await all();
      await tx("readwrite", st => Promise.all(items.filter(it => it.path === path || it.path.startsWith(path + "/")).map(it => req(st.delete(it.path)))));
      return {};
    },
    async rename(from, to) {
      from = check(norm(from)); to = check(norm(to));
      const items = await all();
      // the target may also exist only implicitly, as the parent folder of other files
      if (items.some(it => it.path === to || it.path.startsWith(to + "/"))) throw new Error(to.split("/").pop() + " already exists");
      const moving = items.filter(it => it.path === from || it.path.startsWith(from + "/"));
      if (!moving.length) throw new Error("No such file: " + from);
      await tx("readwrite", st => Promise.all(moving.flatMap(it => [req(st.delete(it.path)), req(st.put(Object.assign({}, it, { path: to + it.path.slice(from.length) })))])));
      return { path: to };
    },
    async files() { return (await all()).filter(it => !it.dir); },
    async seed(list) {
      const items = await all();
      if (items.length) return false;
      for (const f of list) await FS.write(f.path, f.text);
      return true;
    },
    toB64,
  };
  global.MarsIDBFS = FS;
})(window);
