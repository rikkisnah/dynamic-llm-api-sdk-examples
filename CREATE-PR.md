# Create PR (One-Line)

```bash
BRANCH="master" && TITLE="Implement dynamic multi-provider LLM SDK examples" && git checkout -B "$BRANCH" && git add README.md .env.example .gitignore .importlinter .streamlit/config.toml AGENTS.md CLAUDE.md INSTRUCTIONS-build-it.md Makefile docs examples llm_examples pyproject.toml scripts tests uv.lock CREATE-PR.md && git commit -m "$TITLE" && git push -u origin "$BRANCH"
```
