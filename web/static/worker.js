/* Web Worker host for the MARS engine compiled to JavaScript by TeaVM (static build). */
importScripts("mars-engine.js");
const early = [];
self.onmessage = (e) => { if (self.__marsInput) self.__marsInput(e.data); else early.push(e.data); };
self.main([]);
const wait = setInterval(() => {
  if (!self.__marsInput) return;
  clearInterval(wait);
  for (const m of early.splice(0)) self.__marsInput(m);
}, 5);
