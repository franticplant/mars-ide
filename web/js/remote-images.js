/* Network-only helper: an opaque-origin sandbox, no IDE storage, cookies or engine access. */
(function () {
  "use strict";
  window.addEventListener("message", async e => {
    if (e.source !== parent || e.data?.type !== "image" || !Number.isInteger(e.data.id)) return;
    const { id, url } = e.data;
    try {
      const target = new URL(url);
      if (target.protocol !== "https:" || target.username || target.password) throw new Error("HTTPS images only");
      const response = await fetch(target.href, { credentials: "omit", referrerPolicy: "no-referrer", redirect: "error", signal: AbortSignal.timeout(8000) });
      if (!response.ok || +(response.headers.get("content-length") || 0) > 5000000) throw new Error("Image unavailable or too large");
      const reader = response.body.getReader(), chunks = []; let size = 0;
      try {
        while (true) {
          const { done, value } = await reader.read(); if (done) break;
          size += value.length;
          if (size > 5000000) { await reader.cancel(); throw new Error("Image too large"); }
          chunks.push(value);
        }
      } finally { reader.releaseLock(); }
      const bytes = new Uint8Array(size); let at = 0;
      for (const chunk of chunks) { bytes.set(chunk, at); at += chunk.length; }
      parent.postMessage({ type: "image", id, bytes: bytes.buffer }, "*", [bytes.buffer]);
    } catch (_) { parent.postMessage({ type: "image", id, error: true }, "*"); }
  });
  parent.postMessage({ type: "ready" }, "*");
})();
