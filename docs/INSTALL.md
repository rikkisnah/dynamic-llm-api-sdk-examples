# Install

For Codex/Claude prompt-based setup on Ubuntu/macOS, use root [INSTALL.md](../INSTALL.md).

## Quick Manual Setup

```bash
cp .env.example .env
make setup
make help
make check
make providers
make run-cli P=openai PROMPT="hello"
```

Fill `.env` with provider keys you plan to use.

## Run

```bash
make run
make run-cli P=openai PROMPT="hello"
```

Optional runtime note:

- UI chat `Web research` uses outbound HTTPS calls to `api.duckduckgo.com` and `en.wikipedia.org`.
