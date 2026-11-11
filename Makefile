# MARS IDE: build, test and spawn. Everything builds in podman containers on this machine:
# build on the laptop, never on the phone. `make` alone lists the targets.
#
# The targets wrap build-all.sh (builds), scripts/spawn.sh (run the IDE in a container) and
# scripts/test-*.sh (tests); see docs/building.md and docs/testing.md.

# Workspace for `make tui` / `make web` (scripts/spawn.sh alone uses the current directory).
MARS_WORKSPACE ?= $(HOME)/mars-workspace
export MARS_WORKSPACE

.PHONY: tui
tui: ## Spawn the terminal IDE in a container on ~/mars-workspace (MARS_WORKSPACE=)
	scripts/spawn.sh tui

.PHONY: web
web: ## Spawn the web IDE on http://127.0.0.1:8080, same workspace (PORT=, BIND=, MARS_WEB_TOKEN=)
	scripts/spawn.sh web

.PHONY: static
static: ## Spawn the static, server-less build on http://127.0.0.1:8081 (PORT=, BIND=)
	scripts/spawn.sh static

.PHONY: engine web-assets
web-assets: ## Bundle the isolated Markdown / Mermaid renderer in a container
	bash scripts/build-web.sh

engine: ## Build the engine, web server and web UI -> build/mars-engine.jar
	./build-all.sh engine

.PHONY: pylib
pylib: ## Install Textual for the TUI -> build/pylib
	./build-all.sh pylib

.PHONY: static-site
static-site: ## Build the static site (engine compiled to JS with TeaVM) -> build/static/
	./build-all.sh static

.PHONY: static-wasm
static-wasm: ## Build the experimental WasmGC site separately -> build/static-wasm/
	STATIC_ENGINE=wasm STATIC_OUT=build/static-wasm ./build-all.sh static

.PHONY: compare-backends
compare-backends: ## Compare JS/WasmGC size, Node timing and RSS (cached engines; TRIALS=3)
	bash scripts/compare-backends.sh

.PHONY: image
image: ## Build the mars-ide images for amd64 + arm64 (ARCHES="amd64") and the phone archive
	./build-all.sh image

.PHONY: static-image
static-image: ## Build the mars-ide-static image from build/static/
	@test -f build/static/index.html || ./build-all.sh static
	podman build -q -f container/static/Containerfile -t mars-ide-static:latest .

.PHONY: test
test: ## Conformance suite: original MARS 4.5 vs desktop engine vs browser engine
	./build-all.sh test

.PHONY: test-tui
test-tui: ## TUI tests (Textual pilot, headless) against the real engine
	scripts/test-tui.sh

.PHONY: test-web
test-web: ## Browser end-to-end tests (Chromium + Playwright), server and static builds
	scripts/test-web.sh

.PHONY: test-all
test-all: test test-tui test-web ## All of the above

.PHONY: refcard
refcard: ## Regenerate mars_tui/refcard.json and web/js/refcard.js from tools/gen_refcard.py
	python3 tools/gen_refcard.py

.PHONY: clean
clean: ## Remove build outputs (build/, engine/teavm/target/); keeps .cache/ and images
	rm -rf build engine/teavm/target

.PHONY: help
help: ## Show this help
	@printf "\nSpecify a command. The choices are:\n\n"
	@grep -hE '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[0;36m%-14s\033[m %s\n", $$1, $$2}'
	@echo ""

.DEFAULT_GOAL := help
