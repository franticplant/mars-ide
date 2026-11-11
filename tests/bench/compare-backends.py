"""Small repeatable JS vs WasmGC comparison. Run in a non-root Node+Python container.

  python3 tests/bench/compare-backends.py [trials=3]
Reports Node-process timing/RSS, not a claim about browser RAM or every MIPS workload.
"""
import gzip, json, os, pathlib, statistics, subprocess, sys, tempfile

root = pathlib.Path(__file__).resolve().parents[2]
trials = int(sys.argv[1]) if len(sys.argv) > 1 else 3
engines = {
    "js": root / "engine/teavm/target/teavm/mars-engine.js",
    "wasm": root / "build/wasm-trial/teavm/mars-engine.wasm",
}
sizes = {}
for name, engine in engines.items():
    files = [engine]
    if name == "wasm": files.append(engine.with_name("mars-engine.wasm-runtime.js"))
    sizes[name] = {"raw_bytes": sum(p.stat().st_size for p in files), "gzip_bytes": sum(len(gzip.compress(p.read_bytes())) for p in files)}
sizes["markdown_renderer"] = {"raw_bytes": (root / "web/vendor/markdown.js").stat().st_size,
                              "gzip_bytes": len(gzip.compress((root / "web/vendor/markdown.js").read_bytes()))}
results = {}
sources = [{"path": p.name, "text": p.read_text()} for p in sorted((root / "tests/conformance/progs").glob("*.asm")) if not p.name.startswith("zz_")]
with tempfile.TemporaryDirectory() as tmp:
    for program in ["arith", "bigloop", "floatfmt", "calls"]:
        job = pathlib.Path(tmp) / "job.json"
        job.write_text(json.dumps({"main": program + ".asm", "files": sources, "measure": True}))
        samples = {name: [] for name in engines}
        reference = None
        for trial in range(trials):
            for name, engine in engines.items():
                run = subprocess.run(["node", "--expose-gc", str(root / "tests/conformance/teavm-run.js"), str(engine), str(job)], text=True, capture_output=True, timeout=60, check=True)
                data = json.loads(run.stdout.strip().splitlines()[-1])
                if "crash" in data or "assemble_error" in data: raise RuntimeError(f"{name}: {data}")
                sample = data.pop("measure")
                if reference is None: reference = data
                elif data != reference: raise RuntimeError(f"{program}: JS/Wasm results differ")
                samples[name].append(sample)
        results[program] = {
            name: {"startup_ms": statistics.median(s["startupMs"] for s in rows),
                   "assemble_ms": statistics.median(s["assembleMs"] for s in rows),
                   "run_ms": statistics.median(s["runMs"] for s in rows),
                   "node_process_rss_bytes": statistics.median(s["memory"]["rss"] for s in rows)}
            for name, rows in samples.items()
        }
report = {"node": subprocess.check_output(["node", "--version"], text=True).strip(), "trials": trials,
          "container_uid": os.getuid(), "sizes": sizes, "programs": results,
          "note": "Separate Node processes; timings include engine work but not process launch. RSS includes Node/V8 and is not browser RAM. Matching output/state checked on every sample."}
(root / "build/backend-comparison.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2), flush=True)
