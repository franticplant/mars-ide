const fs = require("fs");
globalThis.self = globalThis;
let ready, stopped; const rp = new Promise(r => ready = r); let sres;
const pend = new Map(); let seq = 0;
self.postMessage = s => { const m = JSON.parse(s); if (m.ev === "ready") ready(); else if (m.ev === "stopped") sres(m); else if (pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); } };
const send = (cmd, a = {}) => new Promise(r => { const id = "n" + (++seq); pend.set(id, r); self.__marsInput(JSON.stringify({ id, cmd, ...a })); });
const t0 = Date.now();
require(process.argv[2]).main([]);
(async () => {
  await rp; const startup = (Date.now() - t0) / 1000;
  for (const prog of ["loop.asm", "fib.asm"]) {
    await send("fs_write", { path: prog, text: fs.readFileSync("/bench/" + prog, "utf8") });
    await send("assemble", { files: [prog] });
    const runs = [];
    for (let k = 0; k < 3; k++) {
      await send("reset");
      const done = new Promise(r => sres = r); const t = Date.now();
      await send("run"); const m = await done;
      runs.push([(Date.now() - t) / 1000, m.state.count]);
    }
    const b = runs.reduce((a, r) => r[0] < a[0] ? r : a);
    console.log(`  ${prog.padEnd(9)} startup ${startup.toFixed(2)} s | run ${b[0].toFixed(2).padStart(5)} s for ${String(b[1]).padStart(9)} instr = ${(b[1] / b[0] / 1e6).toFixed(1).padStart(5)} M/s (runs: ${runs.map(r => r[0].toFixed(2)).join(", ")}) | heap ${(process.memoryUsage().heapUsed / 1048576).toFixed(0)} MB, RSS ${(process.memoryUsage().rss / 1048576).toFixed(0)} MB`);
  }
  process.exit(0);
})();
