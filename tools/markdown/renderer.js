/* Runs ONLY in an opaque-origin sandbox. Never load this bundle in the IDE document. */
import MarkdownIt from "markdown-it";
import DOMPurify from "dompurify";
import hljs from "highlight.js";
import mermaid from "mermaid";

const root = document.getElementById("content");
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const md = new MarkdownIt({ html: false, linkify: true, typographer: true,
  highlight(code, lang) {
    if (lang === "mermaid") return `<pre class="mermaid">${esc(code)}</pre>`;
    if (code.length < 50000 && hljs.getLanguage(lang)) {
      try { return `<pre><code class="hljs">${hljs.highlight(code, { language: lang, ignoreIllegals: true }).value}</code></pre>`; } catch (_) { }
    }
    return `<pre><code>${esc(code)}</code></pre>`;
  },
});
md.renderer.rules.image = (tokens, i, options, env, self) => {
  const token = tokens[i], url = token.attrGet("src") || "";
  return `<img data-resource="${esc(url)}" alt="${esc(self.renderInlineAsText(token.children, options, env))}"${token.attrGet("title") ? ` title="${esc(token.attrGet("title"))}"` : ""}>`;
};
const heading = md.renderer.rules.heading_open;
md.renderer.rules.heading_open = (tokens, i, options, env, self) => {
  const title = tokens[i + 1].content;
  const base = title.toLowerCase().replace(/[^\p{L}\p{N}_ -]/gu, "").replace(/ /g, "-") || "section";
  const n = env.ids[base] = (env.ids[base] || 0) + 1;
  tokens[i].attrSet("id", "md-" + base + (n > 1 ? "-" + (n - 1) : ""));
  return heading ? heading(tokens, i, options, env, self) : self.renderToken(tokens, i, options);
};
let current = null;
const send = data => parent.postMessage(data, "*");
window.addEventListener("message", async e => {
  if (e.source !== parent || e.data?.type !== "render" || typeof e.data.text !== "string") return;
  const previous = current, job = current = e.data;
  const top = previous?.path === job.path ? scrollY : 0;
  try {
    if (job.text.length > 1000000) throw new Error("Preview limit is 1 MB. The source remains editable.");
    const theme = job.theme, colors = theme.colors;
    for (const [key, value] of Object.entries(colors)) {
      if (/^(surface|panel|raised|text|muted|primary|accent|error|s-(instr|directive|string|label|number|comment))$/.test(key) && /^#[a-f\d]{6}$/i.test(value)) {
        document.documentElement.style.setProperty("--" + key, value);
      }
    }
    document.documentElement.style.colorScheme = theme.dark ? "dark" : "light";
    document.documentElement.style.setProperty("--sans", theme.sans);
    document.documentElement.style.setProperty("--mono", theme.mono);
    document.documentElement.style.setProperty("--code-size", Math.max(11, Math.min(24, theme.codeSize)) + "px");
    const html = md.render(job.text, { ids: Object.create(null) });
    root.innerHTML = DOMPurify.sanitize(html, { USE_PROFILES: { html: true },
      FORBID_TAGS: ["style", "form", "iframe", "object", "embed"], FORBID_ATTR: ["style", "srcset", "name"] });
    // Task lists remain document content, not interactive controls.
    for (const li of root.querySelectorAll("li")) {
      const text = li.firstChild;
      if (text?.nodeType === 3 && /^\[[ xX]\] /.test(text.textContent)) {
        const box = document.createElement("input"); box.type = "checkbox"; box.disabled = true;
        box.checked = text.textContent[1].toLowerCase() === "x";
        text.textContent = text.textContent.slice(4); li.prepend(box);
      }
    }
    // All resource URLs are removed before the browser can fetch them (CSP also blocks them).
    for (const img of root.querySelectorAll("img")) {
      const url = img.dataset.resource || "";
      img.removeAttribute("src"); img.dataset.resource = url;
      const data = job.images?.[url];
      if (typeof data === "string" && /^data:image\/(png|jpeg|gif|webp);base64,/.test(data)) img.src = data;
      else { img.title = "Image not loaded: " + url; send({ type: "image", id: job.id, url }); }
    }
    mermaid.initialize({ startOnLoad: false, securityLevel: "strict", htmlLabels: false, theme: "base",
      themeVariables: { darkMode: theme.dark, background: colors.surface, fontFamily: theme.sans,
        primaryColor: colors.panel, primaryTextColor: colors.text, primaryBorderColor: colors.primary,
        secondaryColor: colors.raised, secondaryTextColor: colors.text, secondaryBorderColor: colors.muted,
        tertiaryColor: colors.surface, tertiaryTextColor: colors.text, tertiaryBorderColor: colors.muted,
        textColor: colors.text, lineColor: colors.muted, mainBkg: colors.panel,
        nodeBorder: colors.primary, clusterBkg: colors.panel, clusterBorder: colors.muted,
        edgeLabelBackground: colors.surface, actorBkg: colors.panel, actorTextColor: colors.text, actorBorder: colors.primary,
        signalColor: colors.text, signalTextColor: colors.text, labelBoxBkgColor: colors.panel, labelTextColor: colors.text,
        noteBkgColor: colors.raised, noteTextColor: colors.text, noteBorderColor: colors.muted,
        errorBkgColor: colors.panel, errorTextColor: colors.error },
      maxTextSize: 50000, maxEdges: 500, suppressErrorRendering: true,
      flowchart: { htmlLabels: false }, secure: ["securityLevel", "startOnLoad", "htmlLabels", "maxTextSize", "maxEdges", "suppressErrorRendering", "flowchart"] });
    let i = 0;
    for (const diagram of root.querySelectorAll("pre.mermaid")) {
      if (++i > 20) { diagram.textContent = "Diagram limit: 20 per preview."; continue; }
      try {
        if (diagram.textContent.length > 50000) throw new Error("Diagram exceeds 50 KB.");
        const { svg } = await mermaid.render("diagram" + i, diagram.textContent);
        if (current !== job) return;
        diagram.innerHTML = DOMPurify.sanitize(svg, { USE_PROFILES: { svg: true, svgFilters: true },
          FORBID_TAGS: ["foreignObject", "a", "image"], FORBID_ATTR: ["href", "xlink:href", "onload"] });
      } catch (err) { diagram.textContent = "Mermaid: " + err.message; }
    }
    if (current === job) { scrollTo(0, top); send({ type: "rendered", id: job.id }); }
  } catch (err) { root.textContent = err.message; send({ type: "rendered", id: job.id }); }
});
document.addEventListener("click", e => {
  const a = e.target.closest("a"); if (!a) return;
  e.preventDefault();
  const url = a.getAttribute("href") || "";
  if (url.startsWith("#")) { document.getElementById("md-" + url.slice(1))?.scrollIntoView(); return; }
  send({ type: "link", id: current?.id, url });
});
document.addEventListener("pointerdown", () => send({ type: "focus", id: current?.id }));
let chord = 0;
document.addEventListener("keydown", e => {
  const mod = e.ctrlKey || e.metaKey, key = e.key.toLowerCase();
  const next = chord > Date.now() && key === "v"; chord = 0;
  if (e.key === "Escape" || e.key === "F10" || next || mod && (["s", "k", "\\"].includes(key) || e.shiftKey && key === "v") || e.altKey && e.shiftKey && ["m", "g"].includes(key)) {
    e.preventDefault(); if (mod && key === "k") chord = Date.now() + 1500;
    send({ type: "key", key: e.key, ctrlKey: e.ctrlKey, metaKey: e.metaKey, altKey: e.altKey, shiftKey: e.shiftKey });
  }
});
send({ type: "ready" });
