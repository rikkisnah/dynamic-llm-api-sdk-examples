# CREATE-PR Prompt (Codex / Claude)

Use this file as a copy-paste prompt in Codex or Claude.

## Prompt

```text
Prepare and push the current changes on main.

Steps:
1. Ensure branch is main.
2. If behavior changed, sync docs in the same commit: README.md, CLAUDE.md/AGENTS.md, docs/USAGE.md, docs/HOW-IT-WORKS.md, INSTALL.md, CREATE-PR.md, .env.example.
3. Run make check and stop if it fails.
4. If provider or live API behavior changed, also run make test-llm-all (covers all 7 providers including OCA) and stop if it fails.
5. Stage all changes (tracked + untracked), excluding .env and other ignored files.
6. Commit with this message: "<REPLACE_WITH_COMMIT_MESSAGE>".
7. Push to origin main.
8. Print:
   - Exact commands executed
   - Commit hash
   - Files committed

Constraints:
- Do not create another branch.
- Do not rewrite history.
- Do not use destructive git commands.
```

## One-Line Command (manual fallback)

```bash
git checkout main && make check && git add -A && git commit -m "<REPLACE_WITH_COMMIT_MESSAGE>" && git push origin main
```

## One-Line Command (with live provider validation)

```bash
git checkout main && make check && make test-llm-all && git add -A && git commit -m "<REPLACE_WITH_COMMIT_MESSAGE>" && git push origin main
```
