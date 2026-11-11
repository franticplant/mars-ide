/* Optional TeaVM WasmGC backend. Uses the same messages and workspace mirror as JavaScript. */
const early = [];
self.onmessage = e => { if (self.__marsInput) self.__marsInput(e.data); else early.push(e.data); };
importScripts("mars-engine.wasm-runtime.js");
TeaVM.wasmGC.load("mars-engine.wasm").then(engine => {
  const task = engine.exports.main([]);
  if (task?.catch) task.catch(error => { throw error; });
  const wait = setInterval(() => {
    if (!self.__marsInput) return;
    clearInterval(wait);
    for (const message of early.splice(0)) self.__marsInput(message);
  }, 5);
}).catch(error => { setTimeout(() => { throw error; }); });
