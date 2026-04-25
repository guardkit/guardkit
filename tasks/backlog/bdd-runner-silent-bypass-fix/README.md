# Feature: BDD Runner Silent-Bypass Fix + Cross-Repo pytest-bdd Remediation

**Feature ID:** FEAT-BDDM
**Parent review:** [TASK-REV-BDDM](../../in_review/TASK-REV-BDDM-bdd-runner-silently-skips-when-pytest-bdd-missing.md)
**Review report:** [.claude/reviews/TASK-REV-BDDM-review-report.md](../../../.claude/reviews/TASK-REV-BDDM-review-report.md)
**Created:** 2026-04-25

## Problem Statement

When a project authors `.feature` files with `@task:<TASK-ID>` tags but its environment lacks `pytest-bdd`, GuardKit's BDD runner ([bdd_runner.py:466-473](../../../guardkit/orchestrator/quality_gates/bdd_runner.py#L466-L473)) returns `None` and the Coach silently approves on `scenarios_failed == 0`. Empirical evidence: every J002 / J003 task in the **jarvis** project (86 `@task:` tags across 3 feature files) ran AutoBuild with **zero BDD verification**.

This is the same meta-class of defect as TASK-FIX-F584 (pytest runner-error surfacing), but on a different code path that F584's fix did not cover.

## Solution Approach

Two-pronged fix:

1. **GuardKit core fix** (Wave 1, atomic):
   - **R1+R2**: Replace `return None` at `bdd_runner.py:466-473` with a synthetic `BDDResult(scenarios_failed=1)` carrying a `pytest_bdd_not_importable` `FailureDetail`. Promote the log to `WARNING`. Mirrors F584's existing pattern.
   - **R3** (cost-protection invariant): Extend `feature_validator.py` with an env-level preflight that checks for the `pytest-bdd ↔ tagged feature files` gap before any Player turn burns SDK quota.
   - **R5**: Document the pyproject prerequisite in the BDD workflow guide and amend `feature-spec.md` wording.

2. **Cross-repo remediation** (Wave 3): Add `pytest-bdd` to the pyproject of every Python repo that needs it. Audit results (2026-04-25):

   | Repo | pytest-bdd | features | @task tags | Status | Action |
   |------|-----------|----------|------------|--------|--------|
   | agentic-dataset-factory | ✗ | 7 | 0 | advisory | Add (BDD scope authored) |
   | nats-core | ✗ | 6 | 0 | advisory | Add (BDD scope authored) |
   | nats-infrastructure | ✗ | 0 | 0 | proactive | Add (per user request) |
   | specialist-agent | ✗ | 21 | 0 | advisory | Add (BDD scope authored) |
   | forge | ✓ | 7 | 220 | compliant | Skip |
   | jarvis | ✗ | 3 | **86** | **CRITICAL** | Add + re-run FEAT-J002 |
   | guardkit (self) | ✗ | 3 | 0 | dogfood | Add to dev-deps |
   | study-tutor | ✗ | 0 | 0 | proactive | Add (per user request) |

## Wave Plan

```
Wave 1 (GuardKit core fix — parallel, no inter-task conflicts)
  ├── TASK-FIX-BDDM-1: bdd_runner synthetic blocker (R1+R2)
  ├── TASK-FIX-BDDM-2: env-level preflight (R3)
  └── TASK-DOC-BDDM-4: BDD workflow docs (R5)
                          ↓
Wave 2 (depends on Wave 1 merge)
  └── TASK-DOC-BDDM-3: Graphiti episode for "runner without producer" rule (R4)
                          ↓
Wave 3 (depends on Wave 1 GuardKit core fix, parallel across repos)
  ├── TASK-OPS-BDDM-5:  agentic-dataset-factory pyproject
  ├── TASK-OPS-BDDM-6:  nats-core pyproject
  ├── TASK-OPS-BDDM-7:  nats-infrastructure pyproject
  ├── TASK-OPS-BDDM-8:  specialist-agent pyproject
  ├── TASK-OPS-BDDM-9:  jarvis pyproject + FEAT-J002 re-run (CRITICAL)
  ├── TASK-OPS-BDDM-10: guardkit (self) dev-deps for dogfooding
  └── TASK-OPS-BDDM-11: study-tutor pyproject
```

**Wave 1 must ship atomically.** R1 alone (without R3) burns ~3 SDK turns per misconfigured task before TASK-AB-SD01 stall-detection exits. Bundling R1 + R3 keeps cost-efficiency neutral.

**Wave 3 cannot start until Wave 1 GuardKit core fix is merged**, because the cross-repo fixes are designed against the new R1 contract (synthetic blocker on missing pytest-bdd).

## Subtask Summary

| ID | Title | Wave | Mode | Complexity | Effort |
|----|-------|------|------|------------|--------|
| TASK-FIX-BDDM-1 | BDD runner: synthesise blocker on pytest-bdd absence | 1 | task-work | 5 | S (~3h) |
| TASK-FIX-BDDM-2 | Env-level preflight in feature_validator | 1 | task-work | 5 | S (~3h) |
| TASK-DOC-BDDM-4 | Document pytest-bdd prereq in BDD workflow guide | 1 | direct | 2 | XS (~30m) |
| TASK-DOC-BDDM-3 | Graphiti episode for runner-without-producer | 2 | direct | 2 | XS (~30m) |
| TASK-OPS-BDDM-5 | agentic-dataset-factory: add pytest-bdd | 3 | direct | 1 | XS (~10m) |
| TASK-OPS-BDDM-6 | nats-core: add pytest-bdd | 3 | direct | 1 | XS (~10m) |
| TASK-OPS-BDDM-7 | nats-infrastructure: add pytest-bdd | 3 | direct | 1 | XS (~10m) |
| TASK-OPS-BDDM-8 | specialist-agent: add pytest-bdd | 3 | direct | 1 | XS (~10m) |
| TASK-OPS-BDDM-9 | jarvis: add pytest-bdd + re-run FEAT-J002 | 3 | task-work | 4 | M (~2h) |
| TASK-OPS-BDDM-10 | guardkit (self): add pytest-bdd to dev-deps | 3 | direct | 1 | XS (~10m) |
| TASK-OPS-BDDM-11 | study-tutor: add pytest-bdd | 3 | direct | 1 | XS (~10m) |

**Total:** 11 tasks. ~3 waves. Bulk effort in Wave 1.

## Acceptance Criteria for the Feature

- [ ] Wave 1 merged: bdd_runner emits a Coach-blocking synthetic failure when tagged scenarios exist + pytest-bdd is missing.
- [ ] Wave 1 merged: env preflight catches the same gap before any Player turn runs.
- [ ] Wave 1 merged: BDD workflow docs explicitly state the pyproject prerequisite.
- [ ] Wave 2 merged: Graphiti episode created linking this incident to the "runner without producer" rule.
- [ ] Wave 3: every Python repo in scope has `pytest-bdd>=8.1,<9` declared in its pyproject (or has been explicitly excluded via a comment).
- [ ] jarvis FEAT-J002 re-run with BDD verification active produces a non-vacuous `bdd_results` block.

## See Also

- Review report (revision 2): `.claude/reviews/TASK-REV-BDDM-review-report.md`
- Implementation guide: `IMPLEMENTATION-GUIDE.md` in this folder
- Original review task: `tasks/in_review/TASK-REV-BDDM-bdd-runner-silently-skips-when-pytest-bdd-missing.md`
- Sibling rule: `.claude/rules/namespace-hygiene.md`
- Graphiti rule: *"runner without producer anti-pattern"* (uuid `184731b0-3cb6-4eb2-a310-883421767dbf`)
