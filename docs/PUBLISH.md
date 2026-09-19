# Publish to GitHub

Checklist for the first public (or private) push of Judge Engine.

## Before you push

1. Confirm `.env` is **not** staged (it is gitignored). Never commit real secrets.
2. Confirm `.cursor/` is gitignored (local agent config / usernames).
3. Confirm docs use placeholders (`C:/path/to/...`), not your machine path.
4. Skim [SECURITY.md](../SECURITY.md) and set a strong `BOOTSTRAP_ADMIN_PASSWORD` in your local `.env` after cloning elsewhere.

## First-time publish

From the repo root (PowerShell):

```powershell
# 1. Initialize git (skip if already a repo)
git init -b main

# 2. Review what will be committed
git status
git check-ignore -v .env .cursor .env.example

# 3. Stage and commit
git add -A
git status   # double-check: no .env, no .cursor, no judge_data
git commit -m "chore: initial public release packaging"

# 4. Create the GitHub repo (requires GitHub CLI: https://cli.github.com/)
# Private first (recommended), then flip to public when ready:
gh repo create judge-engine --private --source=. --remote=origin --description "School competitive programming platform (Java judge, contests, scoreboard)"

# 5. Push
git push -u origin main
```

Or create the empty repo on github.com, then:

```powershell
git remote add origin https://github.com/YOUR_ORG/judge-engine.git
git push -u origin main
```

## After first push

1. Replace `YOUR_ORG` / `yourusername` placeholders in [README.md](../README.md) and [CONTRIBUTING.md](../CONTRIBUTING.md) with the real clone URL.
2. On GitHub: **Settings → Code security → Enable private vulnerability reporting** (matches [SECURITY.md](../SECURITY.md)).
3. Optional: **Settings → General → Features** — Issues / Discussions as you prefer.
4. Optional: add a Topics row (`competitive-programming`, `django`, `nextjs`, `education`).
5. When ready for the world: **Settings → Change visibility → Public**.

## What must never be published

| Path | Why |
|------|-----|
| `.env` | Live secrets and local absolute paths |
| `.cursor/` | Local agent/ECC state (may contain other project paths) |
| `judge_data/` | Runtime sandbox scratch |
| `backend/staticfiles/`, `frontend/node_modules/`, `.next/` | Build artifacts |

## Re-publish later

```powershell
git status
git add -A
git commit -m "feat: describe your change"
git push
```
