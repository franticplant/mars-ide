// Drive the TeaVM-compiled engine (browser build) in Node with a job:  node teavm-run.js engine.js job.json
// job: {files:[{path,text}], main, settings, inputs:[...], mode:"run"|"steps", stepBack?:n}
const fs = require("fs");
globalThis.self = globalThis;
const job = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const inputs = (job.inputs || []).slice();
const out = [];
const pending = new Map();
let seq = 0, readyRes, stopped = null, stoppedRes;
const ready = new Promise(r => (readyRes = r));
const send = (cmd, args = {}) => new Promise((res, rej) => {
  const id = "j" + (++seq);
  pending.set(id, { res, rej });
  self.__marsInput(JSON.stringify(Object.assign({ id, cmd }, args)));
});
self.postMessage = (s) => {
  const m = JSON.parse(s);
  if (m.ev === "ready") return readyRes();
  if (m.ev === "out") return out.push(m.text);
  if (m.ev === "input_request") { const v = inputs.length ? inputs.shift() : ""; send("input", { text: v + "\n" }); return; }
  if (m.ev === "dialog") { const v = inputs.length ? inputs.shift() : null; send("dialog_reply", { token: m.token, value: v }); return; }
  if (m.ev === "stopped") { stopped = m; if (stoppedRes) stoppedRes(m); return; }
  if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.ok ? p.res(m) : p.rej(new Error(m.error)); }
};
(async () => {
  const timings = { start: performance.now() };
  if (process.argv[2].endsWith(".wasm")) {
    require(require("path").join(require("path").dirname(process.argv[2]), "mars-engine.wasm-runtime.js"));
    const engine = await TeaVM.wasmGC.load(process.argv[2], { nodejs: true });
    const task = engine.exports.main([]); if (task?.catch) task.catch(e => { throw e; });
  } else require(process.argv[2]).main([]);
  await ready;
  timings.startupMs = performance.now() - timings.start;
  for (const f of job.files) await send("fs_write", { path: f.path, text: f.text });
  timings.assemble = performance.now();
  const asm = await send("assemble", { files: [job.main], main: job.main, settings: job.settings || {} });
  timings.assembleMs = performance.now() - timings.assemble;
  if (!asm.success) { console.log(JSON.stringify({ assemble_error: asm.messages })); process.exit(0); }
  let result;
  if (job.mode === "pausing") {
    const reasons = [];
    for (let i = 0; i < 3; i++) {
      stopped = null;
      const done = new Promise(r => (stoppedRes = r));
      await send("run");
      await new Promise(r => setTimeout(r, 300));
      await send("pause");
      reasons.push((stopped || await done).reason);
    }
    const st = (await send("state")).state;
    console.log(JSON.stringify({ reasons, finished: st.finished, running: st.running, t0_positive: st.gpr[8] > 0 }));
    process.exit(0);
  }
  if (job.mode === "steps") {
    let st = asm.state, n = 0, reason = null, errors = null;
    while (n < 100000) {
      const r = await send("step"); n++; st = r.state;
      if (r.finished) { reason = r.reason; errors = r.errors; break; }
    }
    for (let i = 0; i < (job.stepBack || 0); i++) st = (await send("backstep")).state;
    result = { reason, errors, state: st };
  } else {
    timings.run = performance.now();
    const done = new Promise(r => (stoppedRes = r));
    await send("run");
    const m = stopped || await done;
    timings.runMs = performance.now() - timings.run;
    result = { reason: m.reason, errors: m.errors, state: m.state };
  }
  if (job.measure) { global.gc?.(); result.measure = { startupMs: timings.startupMs, assembleMs: timings.assembleMs, runMs: timings.runMs, memory: process.memoryUsage() }; }
  const st = result.state;
  if (st && st.gpr) {
    const spb = ((st.gpr[29] >>> 0) & ~3) - 512;
    result.mem = {
      data: (await send("memory", { addr: 0x10010000, words: 1024 })).words,
      heap: (await send("memory", { addr: 0x10040000, words: 256 })).words,
      stack: (await send("memory", { addr: spb | 0, words: 256 })).words,
    };
  }
  console.log(JSON.stringify(Object.assign(result, { out: out.join("") })));
  process.exit(0);
})().catch(e => { console.log(JSON.stringify({ crash: String(e) })); process.exit(0); });
