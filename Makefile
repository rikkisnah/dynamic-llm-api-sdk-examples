UV ?= uv
PYTHON ?= python3
P ?= openai
M ?=
PROMPT ?= Hello from dynamic-llm-api-sdk-examples
PROMPT_FILE ?=
SYSTEM ?=
MAX_TOKENS ?= 512
HELLO_PROMPT ?= Reply with exactly: Hello world
HELLO_MAX_TOKENS ?= 64
HELLO_MAX_TOKENS_ZAI ?= 512
OUT ?= txt
V ?= openai
PORT ?= 8501
PORT_SPAN ?= 50
ARGS ?=

.PHONY: help setup install install-dev ui cli run run-cli run-file run-stream run-json list list-json check-conn check-conn-json providers providers-json example test-llm-all test test-% lint lint-imports type fmt score check all

##@ General

help: ## Show this help (auto-generated from inline target annotations)
	@awk 'BEGIN { \
	    FS = ":.*?##"; \
	    printf "\nUsage: make \033[36m<target>\033[0m [VAR=value ...]\n"; \
	  } \
	  /^[a-zA-Z_%][a-zA-Z0-9_%-]*:.*?##/ { \
	    printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2; \
	  } \
	  /^##@/ { \
	    printf "\n\033[1m%s\033[0m\n", substr($$0, 5); \
	  }' \
	  $(MAKEFILE_LIST)
	@printf "\n\033[1mVariables\033[0m\n"
	@printf "  \033[36m%-22s\033[0m %s\n" \
	  "P=<provider>"            "openai|claude|gemini|deepseek|qwen|zai|oca (or set AI_PROVIDER)" \
	  "M=<model>"               "override provider model (overrides env defaults)" \
	  "PROMPT='<text>'"         "inline prompt for run-cli/run-stream/run-json" \
	  "PROMPT_FILE=<path>"      "read prompt from file (use '-' for stdin)" \
	  "SYSTEM='<text>'"         "optional system instruction" \
	  "MAX_TOKENS=<int>"        "max output tokens (default 512)" \
	  "OUT=txt|json"            "output format for run-cli/run-stream/check-conn/list/providers" \
	  "PORT=<int>"              "Streamlit UI port (default 8501)" \
	  "PORT_SPAN=<int>"         "probe window when PORT is busy (default 50)" \
	  "ARGS='<argv>'"           "raw CLI args for 'make cli'" \
	  "V=<provider>"            "provider for 'make example' standalone scripts" \
	  "HELLO_PROMPT='<text>'"   "live test-llm-all prompt override" \
	  "HELLO_MAX_TOKENS=<int>"  "live test-llm-all max-tokens override (default 64)" \
	  "HELLO_MAX_TOKENS_ZAI=<int>" "Z.ai-specific override (default 512, reasoning-heavy)"

##@ Setup

install: ## uv sync (app dependencies)
	$(UV) sync

install-dev: ## uv sync with dev dependencies
	$(UV) sync --group dev

setup: install-dev ## alias for install-dev

##@ UI

ui: ## start Streamlit UI on PORT (auto-picks the next free port up to PORT+PORT_SPAN if busy)
	@selected=`$(PYTHON) scripts/find_free_port.py --start $(PORT) --span $(PORT_SPAN)`; \
	if [ "$$selected" != "$(PORT)" ]; then \
	  echo "Port $(PORT) is busy; starting Streamlit on $$selected instead."; \
	fi; \
	$(UV) run streamlit run llm_examples/ui/app.py --server.port $$selected

run: ui ## preferred UI entrypoint (alias for `make ui`)

##@ CLI

providers: ## list configured providers (set OUT=json for JSON)
	$(UV) run llm-examples $(if $(filter json,$(OUT)),--json) providers

providers-json: ## list configured providers as JSON
	$(UV) run llm-examples --json providers

list: ## list models for a provider: make list P=<provider> [OUT=txt|json]
	$(UV) run llm-examples $(if $(filter json,$(OUT)),--json) list-models --provider $(P)

list-json: ## list models for a provider as JSON: make list-json P=<provider>
	$(UV) run llm-examples --json list-models --provider $(P)

run-cli: ## run a one-shot prompt: make run-cli P=<provider> PROMPT='<text>' [M=<model>] [SYSTEM=...] [OUT=txt|json]
	$(UV) run llm-examples $(if $(filter json,$(OUT)),--json) run --provider $(P) --prompt "$(PROMPT)" --max-tokens $(MAX_TOKENS) $(if $(M),--model "$(M)") $(if $(SYSTEM),--system "$(SYSTEM)")

run-file: ## run a prompt from a file: make run-file P=<provider> PROMPT_FILE=<path> [OUT=txt|json]
	$(UV) run llm-examples $(if $(filter json,$(OUT)),--json) run --provider $(P) --prompt-file "$(PROMPT_FILE)" --max-tokens $(MAX_TOKENS) $(if $(M),--model "$(M)") $(if $(SYSTEM),--system "$(SYSTEM)")

run-stream: ## run with token streaming: make run-stream P=<provider> PROMPT='<text>' [OUT=txt|json]
	$(UV) run llm-examples $(if $(filter json,$(OUT)),--json) run --provider $(P) --prompt "$(PROMPT)" --stream --max-tokens $(MAX_TOKENS) $(if $(M),--model "$(M)") $(if $(SYSTEM),--system "$(SYSTEM)")

run-json: ## run a one-shot prompt and emit JSON: make run-json P=<provider> PROMPT='<text>'
	$(UV) run llm-examples --json run --provider $(P) --prompt "$(PROMPT)" --max-tokens $(MAX_TOKENS) $(if $(M),--model "$(M)") $(if $(SYSTEM),--system "$(SYSTEM)")

check-conn: ## validate provider credentials: make check-conn P=<provider> [OUT=txt|json]
	$(UV) run llm-examples $(if $(filter json,$(OUT)),--json) check --provider $(P)

check-conn-json: ## validate provider credentials as JSON: make check-conn-json P=<provider>
	$(UV) run llm-examples --json check --provider $(P)

cli: ## generic CLI passthrough: make cli ARGS='<argv>'
	$(UV) run llm-examples $(ARGS)

example: ## run standalone provider example: make example V=<provider>
	$(UV) run python examples/$(V)_example.py

##@ Live provider tests (require real API keys)

test-llm-all: ## live credential check + hello prompt for openai|claude|gemini|deepseek|qwen|zai|oca
	@set -e; \
	for provider in openai claude gemini deepseek qwen zai oca; do \
		echo "== $$provider =="; \
		max_tokens="$(HELLO_MAX_TOKENS)"; \
		if [ "$$provider" = "zai" ]; then max_tokens="$(HELLO_MAX_TOKENS_ZAI)"; fi; \
		$(MAKE) check-conn P=$$provider; \
		$(MAKE) run-json P=$$provider PROMPT="$(HELLO_PROMPT)" MAX_TOKENS=$$max_tokens; \
	done

##@ Quality gates

test: ## run full test suite (hermetic; no network)
	$(UV) run pytest

test-%: ## run a single test file: make test-providers (-> tests/test_providers.py)
	$(UV) run pytest tests/test_$*.py

lint: ## run ruff lint checks
	$(UV) run ruff check .

lint-imports: ## run import-linter tier checks
	$(UV) run lint-imports

type: ## run strict mypy
	$(UV) run mypy --strict llm_examples/

fmt: ## run ruff formatter
	$(UV) run ruff format .

score: ## run architecture scorecard gate (min-score 8)
	$(UV) run python scripts/score_architecture.py --min-score 8

check: lint lint-imports type test score ## CI gate: lint + lint-imports + type + test + score

all: setup check ## install dev deps then run the full check gate
