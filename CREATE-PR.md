# Create PR (One-Line)

```bash
BRANCH="feat/llm-sdk-ui-cli" && TITLE="Implement dynamic multi-provider LLM SDK examples" && BODY="Implements docs/PLAN.md with uv-based CLI/UI parity, provider adapters, tests, docs, and score gates." && git checkout -b "$BRANCH" && git add README.md .env.example .gitignore .importlinter .streamlit/config.toml AGENTS.md CLAUDE.md INSTRUCTIONS-build-it.md Makefile docs examples llm_examples pyproject.toml scripts tests uv.lock CREATE-PR.md && git commit -m "$TITLE" && git push -u origin "$BRANCH" && gh pr create --title "$TITLE" --body "$BODY"
```
