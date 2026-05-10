# IMPLEMENTATION-GUIDE: FEAT-AB-FIX (guardkit slice)

**Parent review:** [TASK-REV-8413](../../../../../fleet-gateway/tasks/backlog/TASK-REV-8413-analyse-autobuild-feat-fg-001-stall.md) (in fleet-gateway)
**Findings:** [autobuild-FEAT-FG-001-review.md](../../../../../fleet-gateway/docs/history/autobuild-FEAT-FG-001-review.md) (in fleet-gateway)
**Sibling slice:** [`fleet-gateway/tasks/backlog/autobuild-bdd-oracle-fix/`](../../../../../fleet-gateway/tasks/backlog/autobuild-bdd-oracle-fix/)
**Aggregate complexity:** 4.3/10 (medium)
**Tasks (this slice):** 3 of the 5 in the larger feature, all Wave 1
**Estimated duration (this slice):** ~3.5h focused work

---

## §1: What This Slice Owns

The full FEAT-AB-FIX feature is split across two repos:

| Repo | Wave | Tasks | Concern |
|------|-----:|-------|---------|
| **guardkit (here)** | 1 | TASK-AB-001, TASK-AB-003, TASK-AB-004 | Orchestrator + bdd_runner + template conftest |
| fleet-gateway | 1 | TASK-AB-002 | `pytest-bdd` dev dep |
| fleet-gateway | 2 | TASK-AB-005 | Resume FEAT-FG-001 + verify |

This guide walks through the three guardkit tasks. The fleet-gateway tasks have their own
guide in [`../../../../../fleet-gateway/tasks/backlog/autobuild-bdd-oracle-fix/IMPLEMENTATION-GUIDE.md`](../../../../../fleet-gateway/tasks/backlog/autobuild-bdd-oracle-fix/IMPLEMENTATION-GUIDE.md).

---

## §2: Why Each Edit Closes a Real Failure Mode

### TASK-AB-001 — pass `python_executable` to `run_bdd_for_task`

**Symptom in FEAT-FG-001:** the BDD oracle subprocess runs `~/.local/bin/pytest` (system
pytest), whose interpreter has user-installed `pytest_bdd` but not the worktree's
editable-installed `fleet-gateway` distribution. Result: `ModuleNotFoundError: No module
named 'common'` at module import time, surfaced as `step: collection failure`.

**Why a fix in the runner alone isn't enough:** `bdd_runner._invoke_pytest_bdd` already
threads `python_executable` through correctly — the bug is upstream, in whoever calls
`run_bdd_for_task`. They never pass it. Find that caller, resolve
`<worktree>/.venv/bin/python3` (with a sensible fallback chain), pass it through.

### TASK-AB-003 — surface junit error in `BDDFailure.reason` and Coach feedback

**Symptom in FEAT-FG-001:** the Player's Coach feedback for five consecutive turns was:

> *"BDD oracle: 1 scenario(s) failed during pytest-bdd execution. Implementation does not
> satisfy the Gherkin specification."*

— even though the *real* error (visible in `.guardkit/bdd/<task>_junit.xml`) was
`ModuleNotFoundError: No module named 'common'`. The Player had no way to know the failure
was infra-side. It kept refactoring the implementation and producing identical Coach
feedback signatures (`sig=47fb7107`), tripping the feedback-stall guard.

**Two coordinated edits:**

1. `bdd_runner.py` — when junit XML reports `errors > 0` and no parsable `<failure>`
   block exists, parse the first `<error>` element's `message` attribute and the inner
   traceback's last frame into `BDDFailure.reason`. Don't special-case error classes —
   pass through whatever message is there.
2. The orchestrator's feedback summariser — for `bdd_failure` issues, include each
   `BDDFailure.reason` as a bullet under the existing prose header. Generic
   *"Implementation does not satisfy the Gherkin specification"* may stay as a header
   but **must not** replace the per-failure reason.

This is the highest-leverage fix in the set: it makes the system robust against the
*next* class of oracle misconfiguration, not just this one.

### TASK-AB-004 — per-task BDD test modules

**Symptom in FEAT-FG-001:** TASK-FG-002 and TASK-FG-003 ran in parallel against the same
worktree, both writing to a single `features/<slug>/test_<slug>.py`. Each Player rewrote
the file for its own scenarios only, racing the other task. Even after AB-001/002 fix the
import error, FG-003's BDD oracle would collect zero scenarios because the shared file
binds only FG-002 scenarios.

**Edits:**

1. `bdd_runner._invoke_pytest_bdd` — set `GUARDKIT_BDD_TASK_ID=<task_id>` in the pytest
   subprocess `env` argument so the conftest can read it.
2. The guardkit project template at `features/conftest.py` (template `_FeatureFile.collect()`)
   — look up glue candidates in priority order: `test_<slug>__<sanitised_task_id>.py`
   first, fall back to `test_<slug>.py` if the per-task file is missing.
3. The fleet-gateway worktree's existing `features/conftest.py` — apply the same change
   so FEAT-FG-001 resume works without waiting for a template re-deploy.
4. Player guidance — update the rule docs that brief the autobuild Player so it writes
   `test_<slug>__<TASK-ID>.py` rather than overwriting the shared module.

---

## §3: Suggested Work Order

All three are parallel-safe (no file overlap, no logical dependency), but if you want a
suggested order:

1. **AB-001 first** — smallest fix, cleanest test, immediately gets the BDD oracle pointing
   at the worktree venv. Once landed, you can manually verify FEAT-FG-001's BDD oracle
   produces a *useful* failure (no longer "collection failure", but instead the real Python
   `ModuleNotFoundError` if the worktree venv is missing pytest-bdd).
2. **AB-003 next** — no dependency on AB-001 but compounds with it. After both land, any
   future infra issue produces actionable Coach feedback.
3. **AB-004 last** — biggest change, most files touched. Doing it last means you can verify
   the smaller fixes worked end-to-end before adding the new env-var contract.

If running parallel, AB-001 and AB-003 should land in the same PR (or two PRs that target
the same release) because they are both pure-fidelity fixes to the BDD oracle path. AB-004
introduces a new contract (`GUARDKIT_BDD_TASK_ID`) and may want its own PR with documentation.

---

## §4: Cross-Repo Coordination

Once all three guardkit tasks merge:

1. The fleet-gateway slice's TASK-AB-002 (add `pytest-bdd` to dev extras) lands.
2. TASK-AB-005 in fleet-gateway:
   - Renames `test_<slug>.py` → `test_<slug>__TASK_FG_002.py` so per-task glue (AB-004) is honoured.
   - Smokes the BDD oracle locally with `GUARDKIT_BDD_TASK_ID=TASK-FG-002`.
   - Runs `guardkit autobuild feature FEAT-FG-001 --resume`.
   - Confirms TASK-FG-002 / TASK-FG-003 reach `final_decision: approved`.

If TASK-AB-005's resume produces a new failure mode, that is a new review's problem — by
construction, it cannot be the four causes Wave 1 closed.

---

## §5: Out of Scope

- **Re-architecting Coach feedback structure** beyond the bdd_failure path's fidelity.
  AB-003 is a targeted fix, not a redesign.
- **Auto-installing the worktree venv.** AB-001 falls back to a logged warning if no
  venv exists; bootstrapping the venv is `feature-build`'s concern.
- **Migrating other deployed projects' `features/conftest.py` files** (TASK-AB-004 only
  touches this repo's template + the fleet-gateway worktree, on the basis that other
  projects pull the template themselves).
- **Re-implementing FEAT-FG-001 work** — `common/jarvis_client.py` and
  `common/graphiti_client.py` are correct; preserve them.
