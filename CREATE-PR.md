# CREATE-PR Prompt (Codex / Claude)

Use this file as a copy-paste prompt in Codex or Claude.

## Prompt

```text
Prepare and push the current changes on main.

Steps:
1. Ensure branch is main.
2. Run make check and stop if it fails.
3. Stage all changes (tracked + untracked), excluding .env and other ignored files.
4. Commit with this message: "<REPLACE_WITH_COMMIT_MESSAGE>".
5. Push to origin main.
6. Print the exact commands executed and a short summary of files committed.

Constraints:
- Do not create another branch.
- Do not rewrite history.
- Do not use destructive git commands.
```

## One-Line Command (manual fallback)

```bash
git checkout main && make check && git add -A && git commit -m "<REPLACE_WITH_COMMIT_MESSAGE>" && git push origin main
```
