---
id: TASK-FIX-CIGUARD01
title: Restore main to green and add a direct-to-main CI guard (fix dead BDD-wiring import + enforce the Tests gate)
status: backlog
task_type: fix
created: 2026-06-15T00:00:00Z
updated: 2026-06-15T00:00:00Z
priority: high
complexity: 4
related: [TASK-INFRA-CIGREEN, TASK-FIX-BDDFW01, TASK-HMIG-BDDWIRE, TASK-INFRA-CIGREEN-BURN]
implementation_mode: task-work
tags: [ci, tests-gate, branch-protection, direct-to-main, collection-error, enforcement, main-is-red]
---

# Task: Restore main to green and add a direct-to-main CI guard

> [!NOTE] UPDATE 2026-06-15 — Part A (re-green collection) is DONE via TASK-FIX-BDDFW01 (commit `0e4b7912`).
>
> The "preferred" disposition in Part A landed: BDDFW01 corrected the production
> bridge contract and made `map_bdd_run_result` a real public symbol, then
> reconciled `test_coach_validator_bdd_factory_wiring.py` against the real
> `BDDRunResult`/`StackProfile`/`discover(StackProfile, worktree)` contract.
> Status now: **AC-1 ✅** (`pytest tests/ --co` → 16158 collected, 0 errors),
> **AC-2 ✅** (`map_bdd_run_result` exists; the test asserts the real contract),
> **AC-3 ✅** (full Tests command reproduces locally without a collection
> interruption). **Remaining work is Part B only** (the direct-to-main
> enforcing guard — B1 pre-push hook recommended) plus **AC-4/AC-5/AC-6**
> (guard exists + honesty note + a confirmed green `Tests` run on `main`).
> Recommend re-titling to "Add a direct-to-main CI guard" and dropping Part A
> on pickup. (Contract-drift recurrence prevention is a separate task,
> **TASK-INFRA-BDDSEAM01**.)

Follow-up to **TASK-INFRA-CIGREEN** (which created `.github/workflows/tests.yml` to "gate merges"). That task made the suite green and wired a gating job — but the gate is structurally inert on this repo's actual workflow (solo owner, direct-to-main, no branch protection), and a real broken import slipped past it.

## Why this task exists

`main` has been **red on the Tests gate since 2026-06-12** and is still red at HEAD (`3b39764e`). The cause is a two-layer failure:

1. **Technical defect.** `tests/integration/orchestrator/test_coach_validator_bdd_factory_wiring.py` imports a never-shipped symbol `map_bdd_run_result`. This is an import-time `ImportError` that interrupts pytest **collection** for the *whole* `tests/` tree (not just that file), so every CI run since the defect landed exits 2.

2. **Procedural / enforcement hole (the reason it persisted).** The `Tests` workflow is technically sound — it **ran and went RED** on the direct push `740e1585` (both `py3.11` and `py3.12` matrix jobs failed). But nothing acted on the red verdict: `main` has **no branch protection** and **no required status check**, and the owner pushes **directly to main** (a workflow where required-PR-status-checks never even apply). CI is advisory-only. A red `Tests` run does not block a direct push, so the broken commit landed and stuck.

This is the gap TASK-INFRA-CIGREEN's "gate merges" framing missed: a *merge* gate (required check on PRs) does nothing for a *direct-to-main* solo workflow. That workflow needs a guard that does not depend on PR review.

## Root cause

- **Symbol mismatch:** test imports `map_bdd_run_result`; production module `guardkit/orchestrator/quality_gates/coach_validator.py` only defines the private `_map_bdd_run_result_to_bundle` (line 164). No public/free `map_bdd_run_result` exists (`rg 'def map_bdd_run_result' guardkit/` → nothing). Introduced by direct (non-merge) commit `740e1585` ('tidy up', single parent `8b6bfe96`).
- **Why it reds the whole suite:** the bad import runs at collection time. pytest's quarantine here is implemented in `pytest_collection_modifyitems` (`tests/conftest.py:61-85`), a *post*-collection hook — structurally incapable of masking an import-time error. The file is also not in `tests/quarantine.txt` (grep `tests/integration` → 0 matches). The gating command (`.github/workflows/tests.yml:76-81`) has no `--continue-on-collection-errors`, no `--maxfail`, no path/marker filter, no `|| true` / `continue-on-error` / `set +e`. So pytest exits 2 and the step fails — correctly.
- **Why it persisted:** `gh api repos/{owner}/{repo}/branches/main/protection` → HTTP 404 "Branch not protected". No required `Tests` check; direct-to-main push; red verdict unenforced. Gate/conftest/quarantine are unchanged since `740e1585` (`git log 740e1585..HEAD --` over those three paths is empty), so the defect rides unmasked to HEAD.

## Fix

Two parts. Part A re-greens collection (technical); Part B closes the enforcement hole (procedural) without relying on PR review.

### Part A — Fix the broken import (technical)

The test is **dead-on-arrival** against a stale contract: per the TASK-FIX-BDDFW01 audit, this file constructs a real `BDDRunResult`/`StackProfile` and exercises the live factory bridge, which itself targets a stale guardkitfactory contract (wrong `discover` arity, `_detect_stack_profile` returns `str` not `StackProfile`, `_map_bdd_run_result_to_bundle` reads non-existent fields). So the symbol fix is **necessary but not sufficient** for the file to pass meaningfully.

Choose the disposition deliberately (do NOT silently rename to a passing-but-meaningless test):

- **Preferred:** sequence after / fold into **TASK-FIX-BDDFW01**. BDDFW01 corrects the production bridge contract and exports/aligns the mapping helper the test expects; reconcile this test against that corrected `BDDRunResult`/`StackProfile`/`discover(StackProfile, worktree)` contract and the real mapping symbol. This is the only fix that makes the test *both* collect AND verify real behaviour.
- **Acceptable interim (if BDDFW01 is not yet landed and main must be green now):** unblock collection *without* faking green coverage — either (a) `git rm` the dead test and track its reinstatement under BDDFW01, or (b) add the file to `tests/quarantine.txt` **with a referencing comment** AND convert the module-level bad import to a deferred/guarded import (e.g. `pytest.importorskip` / `importorskip`-style guard or a try/except that `pytest.skip`s at runtime) so the import-time error becomes a *skip*, not a collection interruption — the post-collection quarantine hook only works once collection succeeds. Renaming the import to `_map_bdd_run_result_to_bundle` alone is **not acceptable** unless the test still asserts correct behaviour against the real contract (it currently does not — it expects fields the real `BDDRunResult` lacks).

Whichever path: `python -m pytest tests/ -o addopts="" -p no:cacheprovider --co -q` must exit `0` (no collection errors).

### Part B — Make CI enforcing on a direct-to-main solo workflow (procedural)

A required-status-check on PRs is inert here because the owner pushes direct to main. Be honest that a solo direct-to-main workflow needs a guard that does not depend on PR review. Implement at least one enforcing guard (preferably the local pre-push guard, which is the only one that blocks *before* a bad commit reaches main):

- **(B1) Local pre-push guard (recommended primary).** Add a `.git/hooks/pre-push` (or a committed `scripts/pre-push.sh` + a documented `core.hooksPath`/`pre-commit` install step) that runs at minimum a fast collection check (`python -m pytest tests/ -o addopts="" -p no:cacheprovider --co -q`) and aborts the push on non-zero exit. This is the only mechanism that stops a broken direct-to-main push *at the source*, with no PR required. Document the one-time install step in the repo (CONTRIBUTING or `docs/guides/`).
- **(B2) Branch protection / required check (defence-in-depth, document the limitation).** If the owner is willing, enable branch protection on `main` requiring the `Tests` check. Note honestly in the task and docs that with `enforce_admins=false` the owner can still bypass via direct push, and with `enforce_admins=true` direct pushes to main are blocked entirely (forcing a PR flow) — the owner must choose. Record the chosen policy.
- **(B3) Make red CI loud (minimum bar if B1/B2 are declined).** At minimum, wire a notification on `Tests` workflow failure on `main` (push event), so an unenforced red is not also *silent*. This does not prevent the bad commit but ends the advisory-and-invisible state.

Document the chosen enforcement posture next to TASK-INFRA-CIGREEN's notes so the "gate merges" framing is corrected to "gate merges AND direct pushes."

## Acceptance Criteria

- [ ] **AC-1 (technical):** `python -m pytest tests/ -o addopts="" -p no:cacheprovider --co -q` exits `0` with no `error during collection` line. (Currently exits `2` with exactly one ERROR on `test_coach_validator_bdd_factory_wiring.py`.)
- [ ] **AC-2 (technical):** No remaining reference to a non-existent `map_bdd_run_result` symbol — `rg 'map_bdd_run_result' tests/ guardkit/` resolves only to symbols that actually exist (or the file is removed/skipped). If the test is retained, it asserts behaviour against the **real** `BDDRunResult`/`StackProfile`/`discover` contract (reconciled with TASK-FIX-BDDFW01), not the stale field set.
- [ ] **AC-3 (technical):** The full `Tests` workflow command reproduced locally — `python -m pytest tests/ -o addopts="" -p no:cacheprovider --timeout=120 --timeout-method=thread -q -rfE` — completes without a collection interruption (exit `0`, or exit `1` only for genuinely-failing/quarantined tests, never exit `2` from this import).
- [ ] **AC-4 (procedural, enforcing guard exists):** At least one guard from Part B is in place and verifiable. For B1: a committed pre-push script + documented install step, and a demonstration that introducing a collection error makes the guard abort the push (paste the abort output). For B2: `gh api repos/{owner}/{repo}/branches/main/protection` returns 200 with `Tests` in `required_status_checks.contexts`, and the chosen `enforce_admins` value is recorded. For B3 (fallback): a failure-notification step on `main` push is wired and its trigger condition is shown.
- [ ] **AC-5 (procedural, honesty):** The task notes (and a short addendum near TASK-INFRA-CIGREEN) explicitly state that a required-PR-status-check does NOT gate direct-to-main pushes, and record which Part-B guard was adopted and why. No claim that "CI gates main" is left standing unqualified.
- [ ] **AC-6 (verification):** Next `Tests` run on `main` (or a `workflow_dispatch`) concludes `success` on both matrix jobs (`py3.11`, `py3.12`). Confirm via `gh run list --workflow=tests.yml --branch main -L 1`.

## Evidence

- Bad import (live at HEAD `3b39764e`): `tests/integration/orchestrator/test_coach_validator_bdd_factory_wiring.py:28` (`map_bdd_run_result,`), used at lines 68, 87, 110, 127, 152, 171, 362.
- Production symbol that actually exists: `guardkit/orchestrator/quality_gates/coach_validator.py:164` (`def _map_bdd_run_result_to_bundle(`). `rg 'def map_bdd_run_result' guardkit/` → no match.
- Gating command (no bypass): `.github/workflows/tests.yml:76-81` — `python -m pytest tests/ -o addopts="" -p no:cacheprovider --timeout=120 --timeout-method=thread -q -rfE`. `rg 'continue-on-error|continue-on-collection-errors|set \+e|\|\| true|--maxfail' .github/workflows/tests.yml` → no match.
- Triggers: `.github/workflows/tests.yml:24-29` — `push: branches:[main]` + `pull_request: branches:[main]` + `workflow_dispatch`.
- Quarantine is post-collection and cannot mask import errors: `tests/conftest.py:61-85` (`pytest_collection_modifyitems`). File not quarantined: `rg 'tests/integration' tests/quarantine.txt` → 0 matches.
- Empirical: `python -m pytest tests/ -o addopts="" -p no:cacheprovider --co -q` → `16140 tests collected, 1 error`, exit code `2` (sole ERROR is this file).
- No branch protection: `gh api repos/{owner}/{repo}/branches/main/protection` → HTTP 404 "Branch not protected".
- Defect introduced by direct non-merge commit: `git rev-list --parents -n 1 740e1585` → `740e1585 8b6bfe96` (single parent); `git show -s 740e1585` → Richard Woollcott, 'tidy up', 2026-06-13.
- Gate/conftest/quarantine unchanged since the defect: `git log --oneline 740e1585..HEAD -- .github/workflows/tests.yml tests/conftest.py tests/quarantine.txt` → empty. main red on Tests since 2026-06-12 (`015d41a2` failure), last green `ff6f68bb` 2026-06-11.

## Notes

- **gap_class = both.** The adversarial verdict CONFIRMED (refuted=false, high confidence) that the CI config is sound and the run *did* go red; persistence is purely the unenforced-direct-to-main hole. So the fix is genuinely two-part — re-green the import AND add an enforcement guard that doesn't depend on PR review. Do not ship only the import fix and call CI "fixed": the same class of defect will recur on the next direct push.
- **Sequencing with BDDFW01.** Prefer landing **TASK-FIX-BDDFW01** first (it corrects the production bridge contract and the mapping symbol the test needs), then reconcile this test against the corrected contract. The interim collection-unblock options (rm or guarded-import + quarantine) exist only so `main` need not stay red while BDDFW01 is scheduled. Do not rename the import to `_map_bdd_run_result_to_bundle` and leave the test asserting fields the real `BDDRunResult` lacks — that converts a loud false-red into a quiet false-green (see `.claude/rules/absence-of-failure-is-not-success.md`).
- **Stale premise note for HMIG-BDDWIRE.** Out of scope here, but related: TASK-HMIG-BDDWIRE's "nothing consumes guardkitfactory.bdd" premise is factually stale (coach_validator.py imports and calls it) though its intent — the bridge is unreachable on a live run because it raises against a stale contract and is swallowed — still holds. Reconcile under BDDFW01, not this CI task.
- **Coverage realism.** The green sibling `test_bdd_factory_bridge.py` passes only via a local `_FakeBDDRunResult` mirroring the stale shape, so it does NOT protect against this regression class. Whatever replaces/repairs the wiring test should exercise the real contract so the next contract drift reds collection again — but this time against an *enforced* gate.