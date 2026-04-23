---
task_id: TASK-FIX-RWOP1.4
review_mode: decision
decided_at: 2026-04-22
decided_by: human (vickywoollcott@gmail.com)
parent_review: TASK-REV-RWOP1
feature_id: FEAT-RWOP1
execution_subtasks:
  - TASK-FIX-RWOP1.4a  # Part A — WIRE coach assumption gating (warn-mode)
  - TASK-FIX-RWOP1.4b  # Part B — DELETE feature_spec.py dead surface
---

# TASK-FIX-RWOP1.4 — Decision Record

Parent review: [docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md](../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md) §Per-file findings (feature-spec.md)

This task is `task_type: review`, `review_mode: decision`. The task surfaces two independent concerns in `installer/core/commands/feature-spec.md`; each concern needs a verdict + execution sub-task. The decisions are recorded here; execution is carried by TASK-FIX-RWOP1.4a (Part A) and TASK-FIX-RWOP1.4b (Part B).

## Part A — Phase 5 Coach low-confidence assumption gating

**Decision: WIRE (warn-mode only, not block)**

### Rationale

`installer/core/commands/feature-spec.md:337` states the Coach "is expected to verify all low-confidence assumptions before accepting the specification." Grep of `guardkit/orchestrator/quality_gates/coach_validator.py` for `assumptions.yaml`, `confidence`, `ASSUM-`, and `REVIEW REQUIRED` returns zero matches — the sentence is aspirational prose with no enforcement. Cohort runs that produce `_assumptions.yaml` with `confidence: low` rows have Coach proceed without reading them, and the run looks green despite the ambiguity never being human-resolved.

This is the same failure class as TASK-FIX-3C9D (AC-linter runner without producer): a Coach-visible gate declared in prose, no producer in code. The fix shape is identical — add a validator method that locates the artifact, filters the failure condition, attaches a `task_work_results.json` field, and lets `coach_validator` read it.

**Why warn, not block**: R1 (AC-linter) blocks because a malformed AC silently corrupts BDD scenarios, which corrupts the BDD oracle, which corrupts Player validation — a four-hop cascade with no human-in-the-loop recovery. A `confidence: low` assumption is different: the `REVIEW REQUIRED` flag is already being emitted (per feature-spec.md line 337's preceding sentence), so the human IS in the loop — they can just ignore the flag. The failure mode is "human doesn't notice the flag," which is a salience problem, not a producer problem. Warning in Coach bumps the salience one notch (post-generation, pre-acceptance) without converting a human-attention failure into a build-failure. We can escalate to block in a follow-on task if warn-mode fires frequently and gets ignored — that would be evidence the salience bump isn't enough.

**Why not SOFTEN**: the prose-softening path (rewrite line 337 to drop the Coach claim) would make the doc honest but would leave the `REVIEW REQUIRED` flag as a salience-only signal with no programmatic escalation. Given the cascade risk into BDD scenarios (the flag-bearing assumption becomes a scenario premise, the scenario drives the BDD oracle, the oracle drives Player validation — same four-hop pattern as R1 but initiated by a low-confidence premise rather than a malformed AC), even warn-mode enforcement is worth the ~2h of implementation. SOFTEN rejects that trade.

**Why not ESCALATE**: the wire work is ~2h (match the TASK-FIX-3C9D shape — `_find_assumptions_files`, `_extract_low_confidence_unconfirmed`, attach to results, one E2E test), which doesn't warrant spinning up a sub-feature. ESCALATE is the right call if we want severity levels, opt-in/opt-out config, integration with feature-plan Step 5 human-response loops — none of which warrant doing now.

### Execution

Spawned as TASK-FIX-RWOP1.4a (see [tasks/backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.4a-wire-coach-assumption-gating-warn-mode.md](../../tasks/backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.4a-wire-coach-assumption-gating-warn-mode.md)).

## Part B — FeatureSpecCommand dead-surface disposition

**Decision: DELETE**

### Rationale

`guardkit/commands/feature_spec.py` is orphan-unreachable from production code. Verification greps (run 2026-04-22):

| Check | Result |
|---|---|
| `guardkit/cli/` imports | 0 hits |
| `guardkit/orchestrator/` imports | 0 hits |
| `installer/core/commands/bin-entries.txt` entry | absent |
| `guardkit/commands/__init__.py` re-exports | none (module is just a docstring) |
| Non-test production callers | 0 |
| `tests/unit/commands/test_feature_spec.py` references | 32 |
| `tests/integration/test_feature_spec_e2e.py` references | 12 |

The module exists to back tests that test itself. `/feature-spec` is driven by Claude interpreting `installer/core/commands/feature-spec.md` prose; the Python orchestrator is not in that path.

PROMOTE would add a `guardkit feature spec` subcommand + bin-entry + prose rewrite to include an "Execute: python3 …" imperative. That gives us a deterministic headless/CI path for `/feature-spec`, which is genuinely useful — but nobody has asked for it, and the Claude-runtime interpretation is the intended contract (see feature-spec.md §Workflow: the Propose/Review loop is model-driven by design, not CLI-driven). Building a CLI to rescue orphan code is tail-wagging-dog.

**seed_to_graphiti verification** (the key trap flagged in the parent task):

`guardkit/commands/feature_spec.py:300 async def seed_to_graphiti(...)` seeds per-scenario episodes to group `feature_specs` and per-assumption episodes to group `domain_knowledge`. `guardkit/integrations/graphiti/parsers/feature_spec.py::FeatureSpecParser` is a `BaseParser` subclass matched on filename prefix `feature-spec`, which emits whole-file episodes to group `feature_specs` via the generic `guardkit graphiti parse` CLI (invoked by `guardkit/cli/graphiti.py:50`).

These are NOT functional twins:
- Per-scenario vs whole-file granularity differs.
- Per-assumption seeding (domain_knowledge group) exists in the orchestrator version only.

**But**: the orchestrator version is never invoked. Its `seed_to_graphiti` is called only from `FeatureSpecCommand.execute()` at line 482, and `FeatureSpecCommand.execute()` has no production caller. The per-scenario + per-assumption seeding is dead code, not shadowed-but-live code. DELETE loses a code path that never ran. If a future PROMOTE-equivalent decision ever revives the CLI path, per-scenario seeding can be re-implemented inside the parser or a dedicated seeder at that time — the design space is not foreclosed.

**FEAT-1253.yaml smoke-import**: `.guardkit/quality-gates/FEAT-1253.yaml` has four gates that reference the dead module and must be removed:

```yaml
lint           (line 7)   → ruff check guardkit/commands/feature_spec.py
unit_tests     (line 12)  → pytest tests/unit/commands/test_feature_spec.py
integration_tests (line 17) → pytest tests/integration/test_feature_spec_e2e.py
import_check   (line 22)  → python -c "from guardkit.commands.feature_spec import …"
```

The remaining five gates (`command_definition_size`, `command_frontmatter`, `command_methodology`, `installer_copy`, `documentation_size`) are about the Claude prose + docs and stay.

**Why not PROMOTE**: see above — rescue-by-CLI of orphan code, with no external demand. The live Claude-runtime path is the intended contract.

### Execution

Spawned as TASK-FIX-RWOP1.4b (see [tasks/backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.4b-delete-feature-spec-dead-surface.md](../../tasks/backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.4b-delete-feature-spec-dead-surface.md)).

## Preconditions for execution

The current `main` working tree has uncommitted RWOP1 sweep artifacts (RWOP1.1 BDD linking wiring, RWOP1.2 BDD-oracle+smoke-gates nudges, FEAT-RWOP1 guide, orphan-cleanup subfolder, this decision doc). **Commit the RWOP1 sweep before starting either 1.4a or 1.4b** so that each sub-task has a clean baseline and a contained diff. Both sub-tasks reference this precondition in their frontmatter.

## Post-execution verification (inherited from parent task)

Per TASK-FIX-RWOP1.4 acceptance criterion: rerun the runner-without-producer grep for `feature-spec.md` per the parent review's method; target wiring rate ≥ 50 % for hard-module imperatives (up from 10 %). Record the result in a brief close-out note on this decision doc when both sub-tasks complete.
