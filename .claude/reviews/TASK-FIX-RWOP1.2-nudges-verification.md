# TASK-FIX-RWOP1.2 — Live Verification Transcript

**Date:** 2026-04-22
**Task:** Fold Step 10.6 (BDD-oracle nudge) + Step 10.7 (smoke-gates nudge)
into `generate_feature_yaml.py` via the TASK-FIX-3C9D pattern.
**Parent review:** TASK-REV-RWOP1 (Findings #2 and #3).

## Summary

Both R2 (BDD-oracle) and R3 (smoke-gates) activation nudges now have an
imperative callsite in `installer/core/commands/lib/generate_feature_yaml.py`
— the same producer that runs the AC linter (TASK-FIX-3C9D) and that Step 8
of `/feature-plan` shells out to. The runner-without-producer orphans for
both nudges are closed.

## AC evidence

### AC1 — non-test callers exist

```
$ grep -rn "check_bdd_oracle_activation\|check_smoke_gates_activation" \
    --include="*.py" \
    | grep -v "test_\|/tests/\|bdd_oracle_nudge.py:\|smoke_gates_nudge.py:"
installer/core/commands/lib/generate_feature_yaml.py:50:        check_bdd_oracle_activation,
installer/core/commands/lib/generate_feature_yaml.py:58:        check_smoke_gates_activation,
installer/core/commands/lib/generate_feature_yaml.py:737:        bdd_oracle_notice = check_bdd_oracle_activation(
installer/core/commands/lib/generate_feature_yaml.py:751:        smoke_gates_notice = check_smoke_gates_activation(
```

Both helpers have import AND call inside `generate_feature_yaml.py` — two
per helper, all inside the single producer. This matches the AC shape
"two non-test matches (one for each helper)" interpreted as one callsite
per helper; `generate_feature_yaml.py` is the deterministic home.

### AC2/3 — feature-plan.md prose rewritten

- Step 10.6 now opens with **"runs transitively via step 8 (TASK-FP-NDG1,
  wired via TASK-FIX-RWOP1.2)"** and the body starts with *"No separate
  step here."* — same shape as Step 10.5.
- Step 10.7 mirrors Step 10.6 with the R3 wording. Same shape.
- Both execution traces (Flag-Only around line 2640 and Structured around
  line 2696) now include a bullet: *"Script transitively runs the
  BDD-oracle nudge (Step 10.6) and smoke-gates nudge (Step 10.7): prints
  banners to stdout in non-quiet mode (warn-only, non-blocking)"*.

### AC4 — dynamic verification against a fixture workspace

Fixture (at `/tmp/rwop12-verify/`):
- `features/demo.feature` — one feature file, two scenarios, **zero**
  `@task:` tags → should trigger R2 nudge.
- Two tasks with a dependency edge → 2 parallel waves, no
  `smoke_gates:` key in generated YAML → should trigger R3 nudge.

Invocation (non-quiet):

```
$ python3 installer/core/commands/lib/generate_feature_yaml.py \
    --name "demo" --description "RWOP1.2 live verification" \
    --feature-slug "demo" --base-path /tmp/rwop12-verify \
    --tasks-json /tmp/rwop12-verify/tasks.json --lenient
```

Captured stdout (abridged — full AC linter block retained for context):

```
✅ Feature FEAT-0B10 created
📋 Tasks: 2
   TASK-D-001: Implement (complexity: 5)
   TASK-D-002: Tests (complexity: 3) (deps: TASK-D-001)

🔀 Parallel execution groups: 2 waves
   Wave 1: [TASK-D-001]
   Wave 2: [TASK-D-002]

📁 Feature file: /tmp/rwop12-verify/.guardkit/features/FEAT-0B10.yaml
⚡ AutoBuild ready: /feature-build FEAT-0B10

AC-quality review: 2 unverifiable acceptance criteria detected (warn-mode, non-blocking).
  TASK-D-001:
    - - [ ] pytest tests/ passes
      reason: No strong pattern match, defaulting to file_content
  TASK-D-002:
    - - [ ] pytest tests/smoke/ passes
      reason: No strong pattern match, defaulting to file_content

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ℹ️  BDD oracle (R2) not activated
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A features/*.feature file was found but no scenarios carry @task:<TASK-ID> tags.
Task-level BDD oracle (R2) will not fire during autobuild.

To activate: edit features/<name>.feature and add @task:<TASK-ID> on the line
above each Scenario: that should run for a given task.
[...]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ℹ️  Feature-level smoke gates (R3) not configured
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This feature has 2 waves but no smoke_gates: key in the generated YAML.
Between-wave smoke checks will not fire during autobuild.
[...]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Both banners land in stdout, in order: AC linter → R2 nudge → R3 nudge.
The R2 banner specifically mentions `@task:<TASK-ID>` activation; the R3
banner reports `2 waves` (matching the fixture's wave count).

### AC5 — `--quiet` suppresses both banners

Invocation:

```
$ python3 installer/core/commands/lib/generate_feature_yaml.py \
    --name "demo" --description "RWOP1.2 quiet verification" \
    --feature-slug "demo" --base-path /tmp/rwop12-verify \
    --tasks-json /tmp/rwop12-verify/tasks.json --lenient --quiet
```

Captured stdout:

```
FEAT-B474:/tmp/rwop12-verify/.guardkit/features/FEAT-B474.yaml
```

Single parseable `FEAT-ID:path` line. Neither banner appears. The AC
linter block is also suppressed (pre-existing TASK-FIX-3C9D behaviour).

### AC6 — existing unit tests stay green

```
$ python3 -m pytest \
    tests/unit/commands/test_bdd_oracle_nudge.py \
    tests/unit/commands/test_smoke_gates_nudge.py \
    tests/integration/feature_plan/test_generate_feature_yaml_linter.py \
    tests/integration/feature_plan/test_generate_feature_yaml_nudges.py -v
[...]
============================== 34 passed in 4.88s ==============================
```

- `test_bdd_oracle_nudge.py` — 10 tests, all green.
- `test_smoke_gates_nudge.py` — 14 tests, all green.
- `test_generate_feature_yaml_linter.py` — 4 tests, all green (no R1
  regression from the R2/R3 addition).
- `test_generate_feature_yaml_nudges.py` — 6 new tests, all green.

## Verdict

All acceptance criteria met. R2/R3 activation nudges are now the
responsibility of the `generate_feature_yaml.py` producer script — the
same shape TASK-FIX-3C9D established for R1. No prose-only callers remain.
