// Run the TeaVM-compiled engine in Node: node run.js engine.js prog.asm [input]
const fs = require("fs");
globalThis.self = globalThis;
const out = [];
let done, readyRes;
const ready = new Promise(r => readyRes = r);
const finished = new Promise(r => done = r);
self.postMessage = (s) => {
  const m = JSON.parse(s);
  if (m.ev === "ready") readyRes();
  else if (m.ev === "out") out.push(m.text);
  else if (m.ev === "input_request") self.__marsInput(JSON.stringify({ id: "in", cmd: "input", text: (process.argv[4] || "0") + "\n" }));
  else if (m.ev === "stopped") done(m);
  else if (m.id === "asm" && !m.success) { console.log(JSON.stringify(m.messages)); process.exit(1); }
  else if (m.id === "asm") self.__marsInput(JSON.stringify({ id: "run", cmd: "run" }));
};
const eng = require(process.argv[2]);
eng.main([]);
(async () => {
  await ready;
  self.__marsInput(JSON.stringify({ id: "w", cmd: "fs_write", path: "p.asm", text: fs.readFileSync(process.argv[3], "utf8") }));
  const t = Date.now();
  self.__marsInput(JSON.stringify({ id: "asm", cmd: "assemble", files: ["p.asm"] }));
  const m = await finished;
  const dt = (Date.now() - t) / 1000;
  console.log(JSON.stringify({ reason: m.reason, count: m.state.count, secs: dt, mips: (m.state.count / dt / 1e6).toFixed(2), out: out.join("") }));
  process.exit(0);
})();
