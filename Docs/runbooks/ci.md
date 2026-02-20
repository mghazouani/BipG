# CI & Branch Protection Runbook

## Workflows

### `backend.yml` — Backend CI

| Property | Value |
|----------|-------|
| Trigger push | `main` branch, paths `backend-fastapi/**` |
| Trigger PR | any branch, paths `backend-fastapi/**` |
| Runner | `ubuntu-latest` |
| Python | `3.11` (pip cache enabled) |
| Tests | `pytest -v tests/test_health_status.py` (10 tests) |
| Secrets | `WS_SECRET`, `HEALTH_SECRET` — fallback to dummy CI values if not set in repo secrets |

### `flutter.yml` — Flutter CI

| Property | Value |
|----------|-------|
| Trigger push/PR | paths `liv_driver_app/**`, `liv_client_app/**` |
| Runner | `ubuntu-latest` |
| Flutter | stable `3.x` (cache enabled) |
| Matrix | `liv_driver_app`, `liv_client_app` |
| Steps | `flutter pub get` + `flutter analyze` |

---

## Branch protection — `main` (configure in GitHub UI)

Path: **Settings → Branches → Add branch protection rule** → Branch name pattern: `main`

### Required settings (Phase 1)

| Setting | Value |
|---------|-------|
| Require a pull request before merging | ✅ enabled |
| Require status checks to pass before merging | ✅ enabled |
| Status check: **Backend CI / test** | ✅ required |
| Do not allow bypassing the above settings | ✅ enabled |
| Restrict who can push to matching branches (allow direct push) | ✅ disabled (= no direct pushes) |

### Optional settings (recommended)

| Setting | Recommended |
|---------|-------------|
| Require linear history | ✅ (keeps `git log` clean) |
| Dismiss stale pull request approvals when new commits are pushed | ✅ (if code review enabled) |
| Require conversation resolution before merging | ✅ |

---

## Repo secrets (Settings → Secrets and variables → Actions)

| Secret | Purpose | Required? |
|--------|---------|-----------|
| `WS_SECRET` | FastAPI WS token signing (non-empty value required at startup) | Optional — CI uses dummy fallback |
| `HEALTH_SECRET` | FastAPI `/health/status` token | Optional — CI uses dummy fallback |

The dummy fallback values (`ci-dummy-ws-secret`, `ci-dummy-health-secret`) are safe for CI because all tests mock Redis and Odoo — no real services are contacted.

---

## Activating badges in README

Once the repo is on GitHub, uncomment and fill in `ORG/REPO` in `README.md`:

```markdown
![Backend CI](https://github.com/ORG/REPO/actions/workflows/backend.yml/badge.svg)
![Flutter CI](https://github.com/ORG/REPO/actions/workflows/flutter.yml/badge.svg)
```

---

## Validated

| Date | What | Result |
|------|------|--------|
| 2026-02-20 | `pytest tests/test_health_status.py` inside FastAPI container | 10/10 PASS |
| 2026-02-20 | `flutter analyze` liv_driver_app | 0 issues |
| 2026-02-20 | `flutter analyze` liv_client_app | 0 issues |
