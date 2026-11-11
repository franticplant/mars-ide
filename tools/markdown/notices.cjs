/* Include the exact dependency inventory and upstream license text beside the generated bundle. */
const fs = require("node:fs");
const path = require("node:path");
const lock = JSON.parse(fs.readFileSync("package-lock.json", "utf8"));
const sections = ["MARS IDE Markdown renderer — dependency notices\nSources and resolved integrity hashes: tools/markdown/package-lock.json\n"];
for (const dir of Object.keys(lock.packages).sort()) {
  if (!dir || !fs.existsSync(dir)) continue;
  const pkg = JSON.parse(fs.readFileSync(path.join(dir, "package.json"), "utf8"));
  const text = [`${pkg.name} ${pkg.version}`, `License: ${pkg.license || "see upstream license below"}`, `Source: ${lock.packages[dir].resolved || pkg.homepage || "npm registry"}`];
  for (const name of fs.readdirSync(dir).filter(n => /^(licen[cs]e|notice|copying)(\.|$)/i.test(n))) {
    const file = path.join(dir, name);
    if (fs.statSync(file).isFile()) text.push(`\n${name}\n${fs.readFileSync(file, "utf8")}`);
  }
  sections.push(text.join("\n"));
}
fs.writeFileSync("../../web/vendor/THIRD_PARTY.txt", sections.join("\n\n----------------------------------------\n\n"));
