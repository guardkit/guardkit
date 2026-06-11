# TASK-INFRA-CIGREEN — GitHub CI setup (post-merge steps)

> The workflow files (`.github/workflows/tests.yml`) only *run* the suite. To
> make them actually **gate merges**, two things happen on GitHub that can't
> live in the repo: (1) the workflow must be pushed, (2) its checks must be
> marked **required** in branch protection. Steps below. Repo:
> `github.com/guardkit/guardkit`, default branch `main`.

## 0. Prerequisites (token scopes)

| Action | Needs |
|---|---|
| Push `.github/workflows/*.yml` | a token with the **`workflow`** scope (classic PAT) or **Workflows: write** (fine-grained). A push without it fails: *"refusing to allow a Personal Access Token to create or update workflow"*. |
| Set branch protection / required checks | **admin** on the repo — classic PAT `repo` + admin, or fine-grained **Administration: write**. The current `gh` token (RichWoollcott) is fine-grained **without** Administration → `branch protection` API returns 403. Use the **web UI** (no token change) or re-auth with an admin token. |

No repository **secrets** are required: the `graphiti-core` git dependency
(`guardkit/graphiti`) and `guardkitfactory` are both **public**, so the default
`GITHUB_TOKEN` checks them out. (`seam-tests.yml`'s `GUARDKITFACTORY_TOKEN` is an
optional fallback for if guardkitfactory ever goes private.)

## 1. Commit & push the changes

```bash
cd /path/to/guardkit
git add .github/workflows/tests.yml \
        tests/quarantine.txt tests/conftest.py \
        pyproject.toml .gitignore \
        installer/core/lib/external_id_persistence.py \
        guardkit/orchestrator/preflight.py \
        tests/orchestrator/ tests/test_users_endpoint.py \
        docs/state/ tasks/
git commit -m "ci(TASK-INFRA-CIGREEN): gate merges with pytest CI + documented quarantine"
git push origin main      # token needs `workflow` scope (see §0)
```

(For a PR-based flow, push a branch and open a PR — `tests.yml` runs on
`pull_request` too.)

## 2. Confirm the first run is green

```bash
gh run list --workflow=tests.yml --limit 5
gh run watch                       # live-follow the latest run
# or open: https://github.com/guardkit/guardkit/actions/workflows/tests.yml
```

Expect both matrix legs green: **`pytest (py3.11)`** and **`pytest (py3.12)`**,
each ~3 min, logging `[quarantine] skipped 518 pre-existing red test(s)`.

> If a leg is red, it's almost certainly a host-specific test that passed on the
> author's machine but not on `ubuntu-latest` (the quarantine was captured
> locally). Add the failing node id(s) to `tests/quarantine.txt` and push;
> note them on TASK-INFRA-CIGREEN-BURN.

## 3. Make the checks REQUIRED (this is the actual gate)

Required status checks only appear in the picker **after they've run once**, so
do step 2 first.

### Option A — Web UI (no token change needed; recommended)

1. `https://github.com/guardkit/guardkit/settings/branches`
2. **Add branch protection rule** (or edit the rule for `main`).
3. Branch name pattern: `main`.
4. Tick **Require status checks to pass before merging**
   (and optionally **Require branches to be up to date before merging**).
5. In the search box add these contexts:
   - `pytest (py3.11)`
   - `pytest (py3.12)`
   - `Cross-repo harness contract`  ← seam-tests.yml (recommended)
6. **Create / Save**.

### Option B — `gh` CLI (needs an admin-scoped token)

```bash
# Re-auth once with an admin token if needed:
#   gh auth login   (choose a token/scope with Administration: write)

gh api -X PUT repos/guardkit/guardkit/branches/main/protection \
  -H "Accept: application/vnd.github+json" \
  -f 'required_status_checks[strict]=true' \
  -f 'required_status_checks[checks][][context]=pytest (py3.11)' \
  -f 'required_status_checks[checks][][context]=pytest (py3.12)' \
  -f 'required_status_checks[checks][][context]=Cross-repo harness contract' \
  -F 'enforce_admins=false' \
  -F 'required_pull_request_reviews=null' \
  -F 'restrictions=null'
```

(GitHub **Rulesets** — `Settings → Rules → Rulesets` — are the newer equivalent
and work equally well; add the same three checks under "Require status checks".)

## 4. Verify the gate

Open a throwaway PR that breaks a non-quarantined test (e.g. add
`assert False` to any passing test) and confirm the PR shows the failing
required check and **blocks merge**. Revert.

## Notes / follow-ups

- **Speed**: full run is ~2.8 min/leg single-process. If that gets annoying, add
  `pytest-xdist` and `-n auto` to `tests.yml` (noted on TASK-INFRA-CIGREEN-BURN).
- **Burn-down**: as `tests/quarantine.txt` lines are removed (TASK-INFRA-CIGREEN-BURN),
  the gate automatically starts enforcing those tests — no workflow change needed.
- **Existing workflows**: `docs.yml` (Pages) and `seam-tests.yml` (cross-repo
  harness contract) already exist; only `seam-tests.yml` is worth adding as a
  required check alongside the pytest legs.
