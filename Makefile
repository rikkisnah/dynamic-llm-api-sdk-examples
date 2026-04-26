UV ?= uv
P ?= openai
M ?=
PROMPT ?= Hello from dynamic-llm-api-sdk-examples
PROMPT_FILE ?=
SYSTEM ?=
MAX_TOKENS ?= 512
HELLO_PROMPT ?= Hello world
V ?= openai
PORT ?= 8501
ARGS ?=

.PHONY: help setup install install-dev ui cli run run-cli run-file run-stream run-json list list-json check-conn check-conn-json providers providers-json example test-llm-all test test-% lint lint-imports type fmt score check all

help:
	@printf "%s\n" \
	"== Setup ==" \
	"make install                        # uv sync (app dependencies)" \
	"make install-dev                    # uv sync with dev dependencies" \
	"make setup                          # alias for install-dev" \
	"" \
	"== UI ==" \
	"make run PORT=8501                  # start Streamlit UI (preferred)" \
	"make ui PORT=8501                   # alias to start Streamlit UI" \
	"" \
	"== CLI ==" \
	"make providers                      # list providers" \
	"make providers-json                 # list providers as JSON" \
	"make list P=openai                  # list models for provider" \
	"make list-json P=openai             # list models as JSON" \
	"make run-cli P=openai PROMPT='hello' # run one-shot prompt" \
	"make run-file P=openai PROMPT_FILE=prompt.txt # run prompt from file" \
	"make run-stream P=openai PROMPT='hello' # run with streaming" \
	"make run-json P=openai PROMPT='hello' # run with JSON output" \
	"make check-conn P=openai            # validate provider credentials" \
	"make check-conn-json P=openai       # credential check as JSON" \
	"make test-llm-all                   # live hello-world test across all providers" \
	"make cli ARGS='--json run --provider openai --prompt hello' # pass raw args" \
	"make example V=openai               # run standalone provider example script" \
	"" \
	"== Quality ==" \
	"make test                           # run full test suite" \
	"make test-providers                 # run a single test file (tests/test_providers.py)" \
	"make lint                           # run ruff lint checks" \
	"make lint-imports                   # run import-layer checks" \
	"make type                           # run strict mypy" \
	"make fmt                            # run formatter" \
	"make score                          # run architecture score gate" \
	"make check                          # lint + lint-imports + type + test + score" \
	"make all                            # setup + check"

setup: install-dev

install: ## uv sync (app deps)
	$(UV) sync

install-dev: ## uv sync with dev deps
	$(UV) sync --group dev

ui: ## start Streamlit UI
	$(UV) run streamlit run llm_examples/ui/app.py --server.port $(PORT)

run: ui ## preferred UI entrypoint

cli: ## generic CLI passthrough: make cli ARGS='providers'
	$(UV) run llm-examples $(ARGS)

run-cli: ## run prompt from inline string (CLI)
	$(UV) run llm-examples run --provider $(P) --prompt "$(PROMPT)" --max-tokens $(MAX_TOKENS) $(if $(M),--model "$(M)") $(if $(SYSTEM),--system "$(SYSTEM)")

run-file: ## run prompt from file path
	$(UV) run llm-examples run --provider $(P) --prompt-file "$(PROMPT_FILE)" --max-tokens $(MAX_TOKENS) $(if $(M),--model "$(M)") $(if $(SYSTEM),--system "$(SYSTEM)")

run-stream: ## run prompt with streaming output
	$(UV) run llm-examples run --provider $(P) --prompt "$(PROMPT)" --stream --max-tokens $(MAX_TOKENS) $(if $(M),--model "$(M)") $(if $(SYSTEM),--system "$(SYSTEM)")

run-json: ## run prompt with JSON output
	$(UV) run llm-examples --json run --provider $(P) --prompt "$(PROMPT)" --max-tokens $(MAX_TOKENS) $(if $(M),--model "$(M)") $(if $(SYSTEM),--system "$(SYSTEM)")

list: ## list models
	$(UV) run llm-examples list-models --provider $(P)

list-json: ## list models with JSON output
	$(UV) run llm-examples --json list-models --provider $(P)

check-conn: ## credential check
	$(UV) run llm-examples check --provider $(P)

check-conn-json: ## credential check with JSON output
	$(UV) run llm-examples --json check --provider $(P)

providers: ## list providers
	$(UV) run llm-examples providers

providers-json: ## list providers with JSON output
	$(UV) run llm-examples --json providers

example: ## run standalone provider example (V=<provider>)
	$(UV) run python examples/$(V)_example.py

test-llm-all: ## live check + hello-world prompt for all providers
	@set -e; \
	for provider in openai claude gemini deepseek qwen zai; do \
		echo "== $$provider =="; \
		$(MAKE) check-conn P=$$provider; \
		$(MAKE) run-json P=$$provider PROMPT="$(HELLO_PROMPT)" MAX_TOKENS=32; \
	done

test: ## run test suite
	$(UV) run pytest

test-%: ## run single test file: make test-providers
	$(UV) run pytest tests/test_$*.py

lint: ## run ruff lint
	$(UV) run ruff check .

lint-imports: ## run import-linter layer checks
	$(UV) run lint-imports

type: ## run strict mypy
	$(UV) run mypy --strict llm_examples/

fmt: ## run formatter
	$(UV) run ruff format .

score: ## run architecture scorecard gate
	$(UV) run python scripts/score_architecture.py --min-score 8

check: lint lint-imports type test score

all: setup check
