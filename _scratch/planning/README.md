# `_scratch/planning/` — Quarantined `--from-spec` Helpers

## Why this exists

These 7 Python modules + 10 test files implemented the `/feature-plan --from-spec`
execution path: a prose-only CLI flag in `installer/core/commands/feature-plan.md`
that Claude was never actually told to run. At the time of quarantine (2026-04-22)
the entire chain had **zero non-test callers** in the GuardKit codebase.

Removed as part of [TASK-FIX-RWOP1.5](../tasks/completed/2026-04/TASK-FIX-RWOP1.5-feature-plan-from-spec-orphan-disposition.md),
which in turn implemented Finding #8 of
[TASK-REV-RWOP1](../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md)
(the "runner-without-producer" anti-pattern sweep). Decision rationale is in
[`.claude/reviews/TASK-FIX-RWOP1.5-from-spec-decision.md`](../.claude/reviews/TASK-FIX-RWOP1.5-from-spec-decision.md).

## Why repo-root and not `guardkit/_scratch/`

The task originally suggested `guardkit/_scratch/planning/`. That path is inside
the `guardkit` Python package, which
`[tool.hatch.build.targets.wheel] packages = ["guardkit"]` in `pyproject.toml`
ships in the wheel. Keeping dead code out of the distributable is more important
than matching the literal suggestion; repo-root `_scratch/` is obviously
non-package and needs no exclude config.

## Grace window

**Deletion date: 2026-07-21** (90 days from quarantine).

If you are someone who actually uses `/feature-plan --from-spec` in private
scripts or CI, **this is your notice**: the flag, the helpers, and the prose
describing them have all been removed from the live codebase. Raise an issue
or PR before 2026-07-21 to have them wired back in; after that date this
directory is deleted outright with no further consultation.

## What's here

### Module files (`_scratch/planning/`)

| File | LOC | Primary exports |
|------|-----|-----------------|
| `spec_parser.py` | 845 | `parse_research_template`, `TaskDefinition`, `Decision`, `ParsedSpec` |
| `target_mode.py` | 165 | `resolve_target`, `TargetConfig`, `TargetMode` |
| `task_metadata.py` | 394 | `enrich_task`, `render_task_markdown` |
| `adr_generator.py` | 176 | `generate_adrs` |
| `quality_gate_generator.py` | 183 | `generate_quality_gates` |
| `warnings_extractor.py` | 70 | `extract_warnings` |
| `seed_script_generator.py` | 107 | `generate_seed_script` |

Module cross-imports (`adr_generator` → `spec_parser`, `quality_gate_generator`
→ `spec_parser`, `task_metadata` → `spec_parser` + `target_mode`) stayed within
the cluster, so the quarantine is self-contained.

### Test files (`_scratch/planning/tests/`)

- `test_spec_parser.py`
- `test_target_mode.py`
- `test_task_metadata.py`
- `test_adr_generator.py`
- `test_quality_gate_generator.py`
- `test_warnings_extractor.py`
- `test_seed_script_generator.py`
- `test_feature_plan_pipeline.py` (integration — exercised all 7 together)
- `test_planning_module_seams.py` (seam test for the cluster)
- `test_lint_ac_compliance.py` (see note below)

### Note on `test_lint_ac_compliance.py`

This test verified live lint-compliance policy (feature plans include
lint-compliance ACs in implementation tasks) but used the from-spec parser
(`parse_research_template` + `generate_quality_gates`) as its setup scaffolding.
Coming with the rest of the cluster leaves a coverage gap for the live
(non-from-spec) feature-plan flow — the follow-up task to close that gap is
**TASK-FIX-RWOP1.6** (lint-ac coverage against the live
`generate_feature_yaml` producer). Until RWOP1.6 lands, lint-compliance in
live output is unasserted by automated tests.

## How to wire the chain back in (if complaint arrives)

1. `git mv _scratch/planning/*.py guardkit/planning/`
2. `git mv _scratch/planning/tests/*.py tests/<appropriate subdir>/`
3. Restore the `--from-spec` documentation block to
   `installer/core/commands/feature-plan.md` (see commit history for the
   exact content that was removed).
4. Crucially — **add actual wiring**: either a bin-entry + imperative in the
   CRITICAL EXECUTION INSTRUCTIONS section that calls the 8 helpers, or a
   proper `guardkit plan spec` CLI subcommand. The status quo ante (prose-only
   chain with no runner) is what got this code quarantined.
5. Delete this README.

## Contact

Raise an issue on the GuardKit repo referencing `TASK-FIX-RWOP1.5` and
`--from-spec` if you need these helpers back.
