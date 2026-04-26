# Install

## Prerequisites

- Python 3.11+
- `uv`

## Setup

```bash
cp .env.example .env
make setup
```

Fill `.env` with provider keys you plan to use.

## Smoke Check

```bash
make providers
make check-conn P=openai
```

## Run

```bash
make run
make run-cli P=openai PROMPT="hello"
```
