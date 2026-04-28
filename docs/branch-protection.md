# Branch Protection — Required Status Checks

Configure these settings on GitHub under **Settings → Branches → Branch protection rules** for the `main` branch.

## Required status checks

All four jobs must pass before a PR can be merged:

| Check name | Workflow | What it validates |
|---|---|---|
| `Web — lint / typecheck / test` | `ci.yml` / `web-quality` | ESLint, TypeScript, Vitest |
| `API — ruff / mypy / pytest` | `ci.yml` / `api-quality` | Ruff lint + format, Mypy, Pytest |
| `Build — web` | `ci.yml` / `build (web)` | Next.js production build |
| `Build — api` | `ci.yml` / `build (api)` | Python wheel build |

## Recommended branch protection settings

```
✅ Require a pull request before merging
   ✅ Require approvals: 1
   ✅ Dismiss stale pull request approvals when new commits are pushed
✅ Require status checks to pass before merging
   ✅ Require branches to be up to date before merging
   Status checks (add all four from the table above)
✅ Require conversation resolution before merging
✅ Do not allow bypassing the above settings
```

## How to add the checks

1. Push the `ci.yml` workflow and open at least one PR so the check names appear in GitHub.
2. Navigate to **Settings → Branches → Add branch protection rule**.
3. Set **Branch name pattern** to `main`.
4. Enable **Require status checks** and search for each job name in the table above.
5. Save.

> The exact job names shown in GitHub match the `name:` fields in `ci.yml`.
