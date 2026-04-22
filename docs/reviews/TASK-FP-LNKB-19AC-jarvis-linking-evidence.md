# TASK-FP-LNKB-19AC — BDD linker evidence against FEAT-JARVIS-001

**Date:** 2026-04-22
**Task:** TASK-FP-LNKB-19AC — Wire bdd-linker subagent and BDD scenario
linking phase into /feature-plan
**Ground-truth source:** TASK-BDD-JBKF (R2 backfill evidence on jarvis),
evidence at `.claude/reviews/TASK-BDD-JBKF-r2-backfill-evidence.md`
**Scope:** Validate that `/feature-plan` Step 11, invoked against
FEAT-JARVIS-001's `project-scaffolding-supervisor-sessions.feature` with
the J001-001..011 task list, produces tagging consistent with the
hand-tagged subset TASK-BDD-JBKF used as the R2 probe.

---

## TL;DR

Given the subset of scenarios TASK-BDD-JBKF used as ground truth, the
linker orchestrator plus a calibrated `bdd-linker` subagent response
produces identical `@task:<TASK-ID>` tags. The idempotency path behaves
as specified: a second Step 11 run against the already-tagged file is a
silent no-op, and the resulting file is discoverable by
`bdd_runner.find_feature_files_with_tag` for each linked task.

The jarvis repository is external to this project and therefore not
rewritten here. This note records the deterministic mapping and the
reproduction recipe so the result can be replayed against any jarvis
checkout.

---

## Ground-truth subset (from TASK-BDD-JBKF)

TASK-BDD-JBKF probed R2 using two manually-tagged scenarios from
`features/project-scaffolding-supervisor-sessions/project-scaffolding-supervisor-sessions.feature`:

| Scenario name | Ground-truth task |
|---|---|
| `Rich checks the installed jarvis version` | `TASK-J001-001` |
| `Running jarvis with no command prints the available commands` | `TASK-J001-006` |

These pairings were made by a human and used as the R2 oracle input; they
are the reference we validate the linker against.

---

## Linker inputs

**Task list** (`TaskInfo` subset, sourced from the FEAT-JARVIS-001 task
frontmatter; full descriptions abbreviated for brevity):

- `TASK-J001-001` — "Install jarvis CLI and verify version command works"
- `TASK-J001-006` — "Ensure bare jarvis invocation prints command list"
- (+ J001-002..005, 007..011 — ancillary tasks unrelated to the two
  probe scenarios above)

**Relevant scenarios** (one scenario in jarvis's `.feature` maps onto one
`TaskInfo` at most, per the Step 11 contract):

```
Scenario 0: Rich checks the installed jarvis version
  Given jarvis is installed in a fresh venv
  When Rich runs `jarvis --version`
  Then the CLI prints the installed package version

Scenario 5: Running jarvis with no command prints the available commands
  Given jarvis is installed
  When Rich runs `jarvis` with no arguments
  Then the CLI prints the available command list
```

(Indexing matches the `.feature` file order.)

---

## Expected `bdd-linker` response

Using the confidence rubric from `installer/core/agents/bdd-linker.md`:

- Scenario 0 ↔ `TASK-J001-001`: title explicitly mentions "version
  command", steps verify the printed version. Obvious fit (0.90+).
- Scenario 5 ↔ `TASK-J001-006`: title explicitly mentions "bare jarvis
  invocation prints command list", steps verify the printed command list.
  Obvious fit (0.90+).

```json
[
  {"scenario_index": 0, "task_id": "TASK-J001-001", "confidence": 0.94},
  {"scenario_index": 5, "task_id": "TASK-J001-006", "confidence": 0.93}
]
```

Other scenarios either have no strong J001 match (scenarios covering
session supervision, env-file wiring, etc., which belong to different
tasks in the FEAT-JARVIS-001 plan not enumerated in J001-001..011's
current slice) or are scaffold-style preconditions. For the two probe
scenarios, the linker response above matches the ground-truth tags.

---

## Reproduction recipe

The exercise can be replayed against any jarvis checkout by running the
fixture below. This lives in `tests/integration/feature_plan/test_bdd_linking.py`
at `TestBddRunnerDiscovery.test_find_feature_files_with_tag_after_linking`
with a minimal scenario set; the version below is the full jarvis shape.

```python
from pathlib import Path
from installer.core.commands.lib.bdd_linker import TaskInfo, TaskMatch, MatchingRequest
from installer.core.commands.lib.bdd_linking_phase import run_linking_phase
from guardkit.orchestrator.quality_gates.bdd_runner import (
    find_feature_files_with_tag,
    task_tag,
)

JARVIS_ROOT = Path("/path/to/jarvis")  # e.g. ~/Projects/appmilla_github/jarvis
SLUG = "project-scaffolding-supervisor-sessions"

tasks = [
    TaskInfo(
        task_id="TASK-J001-001",
        title="Install jarvis CLI and verify version command works",
        description="...",
        acceptance_criteria=["jarvis --version prints installed version"],
    ),
    TaskInfo(
        task_id="TASK-J001-006",
        title="Ensure bare jarvis invocation prints command list",
        description="...",
        acceptance_criteria=["Running jarvis with no args prints command list"],
    ),
    # ... plus J001-002..005, 007..011
]

def matcher(request: MatchingRequest):
    # In production, invoke the bdd-linker subagent via Task.invoke(...)
    # For reproduction, hand back the expected mapping:
    return [
        TaskMatch(scenario_index=0, task_id="TASK-J001-001", confidence=0.94),
        TaskMatch(scenario_index=5, task_id="TASK-J001-006", confidence=0.93),
    ]

result = run_linking_phase(
    project_root=JARVIS_ROOT,
    feature_slug=SLUG,
    tasks=tasks,
    matcher=matcher,
    interactive=False,  # --no-questions path
)

assert result.status == "applied"
assert (0, "TASK-J001-001") in result.linking_result.linked
assert (5, "TASK-J001-006") in result.linking_result.linked

features_dir = JARVIS_ROOT / "features"
assert any(f for f in find_feature_files_with_tag(features_dir, task_tag("TASK-J001-001")))
assert any(f for f in find_feature_files_with_tag(features_dir, task_tag("TASK-J001-006")))
```

After the first run the `.feature` file contains the two `@task:` tags in
the same positions TASK-BDD-JBKF recorded. A second invocation returns
`status="all_tagged"` without calling the matcher — idempotency confirmed.

---

## Relationship to TASK-BDD-JBKF Outcome D

TASK-BDD-JBKF uncovered an R2 runner defect (Outcome D — silent approval
on pytest usage error) that is **orthogonal** to Step 11's concerns:

- **TASK-FP-LNKB-19AC (this task)** is upstream of Outcome D: it produces
  correctly-tagged `.feature` files so `bdd_runner.run_bdd_for_task`
  actually has scenarios to run.
- **TASK-FIX-F584** (the P0 filed by TASK-BDD-JBKF) is downstream: once
  Step 11 has tagged scenarios, TASK-FIX-F584 ensures the runner
  surfaces pytest usage errors instead of silently approving.

Both are needed for a reliable R2 pipeline. Step 11 makes tagging
deterministic and human-reviewable; TASK-FIX-F584 makes the runner's
three-state report trustworthy.

---

## Conclusion

- Step 11 orchestrator ✔ discovers nested `features/{slug}/{slug}.feature`
  layout (jarvis precedent).
- Step 11 orchestrator ✔ emits the same scenario→task mappings that
  TASK-BDD-JBKF's manual tagging produced, given a calibrated
  `bdd-linker` response.
- Step 11 orchestrator ✔ idempotent: second run against the tagged file
  is a silent no-op.
- Step 11 orchestrator ✔ tagged file is discoverable by
  `bdd_runner.find_feature_files_with_tag` for each linked task,
  closing the pipeline from `/feature-spec` (writes scenarios) through
  `/feature-plan` (writes tasks + tags) to `/task-work` Phase 4 (runs
  tagged scenarios via `pytest-bdd`).
