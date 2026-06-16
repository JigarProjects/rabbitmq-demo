# Contributing

## PR workflow

```bash
# 1. Switch to a new branch from main
git checkout -b fix/my-change

# 2. Make changes, stage, commit
git add -A
git commit -m "type: short description"

# 3. Push branch (not main)
git push origin fix/my-change

# 4. Open PR in browser
#    https://github.com/JigarProjects/rabbitmq-demo/pull/new/fix/my-change
```

## Commit style

Prefix with type: `fix:`, `feat:`, `docs:`, `chore:`, `refactor:`.  
Keep the subject line under 72 chars. No body required for small changes.

## Before pushing

- Run lint/typecheck if applicable
- Verify changes work with a test if one exists

## Rules

- Never push to `main` directly — always use a branch + PR
- Never force-push (`--force` or `-f`)
- Squash commits if the branch has many WIP commits
