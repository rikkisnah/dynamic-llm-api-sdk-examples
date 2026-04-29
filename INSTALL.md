# INSTALL Prompt (Codex / Claude)

Use this file as a copy-paste prompt in Codex or Claude.

## Prompt

```text
Set up this repository so it can run on this machine.

Requirements:
- Support Ubuntu and macOS setup flow.
- Install missing prerequisites: git, make, curl, Python 3.11+ (or current Python 3), and uv.
- Copy .env.example to .env if .env does not exist (the app loads .env from the repo root and from llm_examples/.env, so either location works).
- Run make setup.
- Run make help.
- Run make check.
- Run make providers.
- Run make run-cli P=openai PROMPT="hello" (or any configured provider; valid `P=` values: openai, claude, gemini, deepseek, qwen, zai, oca).
- Start UI once with make run.
- Report what was installed and final status.

Constraints:
- Do not modify application code.
- Do not commit or push anything.
```

## Manual Setup (Ubuntu)

```bash
sudo apt update
sudo apt install -y git make curl build-essential python3 python3-venv python3-pip
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
cp -n .env.example .env
make setup
make help
make check
make providers
make run-cli P=openai PROMPT="hello"
make run
```

## Manual Setup (macOS)

```bash
xcode-select --install || true
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || true
brew install git make python uv
cp -n .env.example .env
make setup
make help
make check
make providers
make run-cli P=openai PROMPT="hello"
make run
```
