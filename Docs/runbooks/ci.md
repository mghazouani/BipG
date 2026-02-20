# CI & Branch Protection Runbook

## Phase 1 (current)

**Only required status check: `Backend CI / test`.**
Flutter CI is present but **not** a required check in Phase 1 — it runs on `workflow_dispatch` only (see below). It becomes a required check in Phase 2.

---

## Workflows

### `backend.yml` — Backend CI *(Phase 1 — required)*

| Property | Value |
|----------|-------|
| Trigger push | `main` branch, paths `backend-fastapi/**`, `.github/workflows/backend.yml` |
| Trigger PR | any branch, paths `backend-fastapi/**`, `.github/workflows/backend.yml` |
| Runner | `ubuntu-latest` |
| Python | `3.11` (pip cache enabled) |
| Tests | `pytest -v tests/test_health_status.py` (10 tests) |
| Secrets | `WS_SECRET`, `HEALTH_SECRET` — non-sensitive fallback used automatically if repo secrets are absent |

### `flutter.yml` — Flutter CI *(Phase 2 — manual only in Phase 1)*

| Property | Value |
|----------|-------|
| Trigger | `workflow_dispatch` (manual) in Phase 1 |
| Runner | `ubuntu-latest` |
| Flutter | stable `3.x` (cache enabled) |
| Matrix | `liv_driver_app`, `liv_client_app` |
| Steps | `flutter pub get` + `flutter analyze` |

To run Flutter CI manually: **Actions → Flutter CI → Run workflow**.

---

## Branch protection — `main` — step-by-step

> Prerequisite: the repo must exist on GitHub and at least one push must have reached `main`
> so that the `Backend CI / test` check name is available in the search box (step 6).

### Steps

1. Go to your repo on GitHub.
2. Click **Settings** (top nav, repo level — not account settings).
3. Left sidebar → **Code and automation** → **Branches**.
4. Click **Add branch protection rule** (or **Add classic branch protection rule** on older UI).
5. **Branch name pattern** → type `main` → press Enter or click out of the field.
6. Check **Require a pull request before merging** → leave sub-options at default for Phase 1.
7. Check **Require status checks to pass before merging**.
   - A search box appears: type `test` → select **`Backend CI / test`** from the dropdown.
   - ⚠️ The check name only appears after at least one run of `backend.yml` has completed on the repo.
     If it doesn't appear yet: push a small commit to `main` that touches `backend-fastapi/` first,
     wait for the run to complete, then come back here.
8. Check **Do not allow bypassing the above settings**.
9. Under **Rules** → check **Block force pushes** and **Restrict deletions**.
10. Click **Create** (or **Save changes**).

### Optional settings (recommended)

| Setting | Recommendation |
|---------|----------------|
| Require linear history | ✅ cleaner `git log` |
| Dismiss stale pull request approvals when new commits are pushed | ✅ if reviews enabled |
| Require conversation resolution before merging | ✅ |

---

## PR smoke test checklist — validate Phase 1 is active

Run this once after enabling branch protection to confirm everything is wired correctly.

### Step 1 — Create a smoke PR

```bash
git checkout -b ci/smoke-test
# Add a harmless comment to trigger backend CI
echo "# ci smoke" >> backend-fastapi/app/main.py
git add backend-fastapi/app/main.py
git commit -m "ci: smoke test — trigger Backend CI"
git push origin ci/smoke-test
```

Then open a Pull Request from `ci/smoke-test` → `main` on GitHub.

### Step 2 — Verify CI triggers

- [ ] On the PR page, under **Checks**, the job **Backend CI / test** appears within ~30 s.
- [ ] The job runs `pytest tests/test_health_status.py` and shows **10 passed**.
- [ ] Status shows ✅ green.

### Step 3 — Verify merge block on failure (optional but recommended)

Temporarily break a test to confirm the gate works:

```bash
# Break a test (revert after)
sed -i 's/assert r.status_code == 401/assert r.status_code == 999/' \
  backend-fastapi/tests/test_health_status.py
git add backend-fastapi/tests/test_health_status.py
git commit -m "ci: intentional failure — revert after smoke test"
git push origin ci/smoke-test
```

- [ ] CI shows ❌ red on the PR.
- [ ] **Merge** button is greyed out / disabled with message
  *"Required status check 'Backend CI / test' is not passing"*.

Revert the break:

```bash
git revert HEAD --no-edit
git push origin ci/smoke-test
```

- [ ] CI turns ✅ green again.
- [ ] **Merge** button becomes available.

### Step 4 — Merge and close

```bash
# On GitHub UI: Merge pull request (or squash merge)
# Then clean up local branch:
git checkout main
git pull
git branch -d ci/smoke-test
```

- [ ] `main` updated, no direct push was possible.
- [ ] Branch protection confirmed active.

---

## Repo secrets (Settings → Secrets and variables → Actions)

| Secret | Purpose |
|--------|---------|
| `WS_SECRET` | FastAPI WS token signing |
| `HEALTH_SECRET` | FastAPI `/health/status` token |

Both are optional in CI: the workflow uses a non-sensitive fallback automatically when the secret is absent. All tests mock Redis and Odoo — no real service is contacted.

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
