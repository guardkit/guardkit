---
title: "E2E verification: system commands chain after Graphiti population"
priority: P1
complexity: 4
tags: [system-overview, impact-analysis, context-switch, e2e, verification]
feature_id: FEAT-SC-001
implementation_mode: task-work
depends_on: [SPEC-replace-system-plan-stub]
---

# E2E Verification: System Commands Chain After Graphiti Population

## Problem

FEAT-SC-001 delivered three read commands — `/system-overview`, `/impact-analysis`, `/context-switch` — with real implementations (400+, 500+, 350+ lines respectively). However, they have **never been tested against real Graphiti data** because the `/system-plan` write path was a stub. Once the stub replacement task populates Graphiti with GuardKit's architecture, these commands need end-to-end verification.

## Scope

This is a verification task, not an implementation task. The code exists and has unit tests. The goal is to confirm the full chain works: `/system-plan` writes -> Graphiti stores -> read commands retrieve and format correctly.

## Verified in Previous Investigation: NOT Stubs

| Module | Lines | Verdict |
|--------|-------|---------|
| `guardkit/planning/system_overview.py` | ~400 | Real: entity parsing, token budgeting, multi-format display |
| `guardkit/planning/impact_analysis.py` | ~500 | Real: risk scoring, multi-depth, BDD scenarios, implication derivation |
| `guardkit/planning/context_switch.py` | ~350 | Real: YAML config, task discovery, Graphiti queries, display formatting |
| `guardkit/planning/coach_context_builder.py` | built | Real: assembles context for coach injection |
| `guardkit/planning/system_plan.py` | 70 | **STUB** (being replaced by dependency task) |

## What Must Be Verified

### 1. `/system-overview` returns structured output

After Graphiti is populated with GuardKit architecture:

- Default mode returns single-screen output (~40-60 lines) with system name, methodology, component list, ADR titles, concern names
- `--verbose` mode returns expanded content with descriptions
- `--format json` returns valid JSON with `status: "ok"` and populated arrays
- `condense_for_injection()` produces token-budgeted output within 800 tokens
- Entity type inference correctly classifies facts from Graphiti (components vs ADRs vs concerns)

Expected entity counts from `guardkit-system-spec.md`:
- 1 system context
- 9 components (COMP-cli-layer through COMP-template-system)
- 7 cross-cutting concerns (XC-error-handling through XC-httpx-cleanup)
- 8 ADRs (ADR-SP-001 through ADR-SP-008)

### 2. `/impact-analysis` returns meaningful risk assessment

- `guardkit impact-analysis "knowledge layer"` returns affected components with relevance scores
- Quick depth returns components only
- Standard depth returns components + ADRs + implications
- Risk score calculation produces non-trivial values (not all 1/5)
- Task ID enrichment works: `guardkit impact-analysis TASK-SC-005` extracts title/tags for query

### 3. `/context-switch` operates correctly

- `guardkit context-switch guardkit` switches active project in `.guardkit/config.yaml`
- Active task discovery finds tasks in `tasks/in_progress/` and `tasks/backlog/`
- Architecture overview section populated (not empty)
- Display format shows project ID, path, architecture summary, active tasks

### 4. Coach context injection works

- `coach_context_builder.py` successfully assembles architecture context for coach prompts
- Token budget respected (800 tokens for overview, 1200 for impact)
- Complexity gating: low-complexity tasks get zero architecture context, high-complexity get full context

## Files to Verify (read-only review)

- `guardkit/planning/system_overview.py` — Verify against live Graphiti data
- `guardkit/planning/impact_analysis.py` — Verify against live Graphiti data
- `guardkit/planning/context_switch.py` — Verify config management and Graphiti queries
- `guardkit/planning/coach_context_builder.py` — Verify token budgeting and assembly
- `guardkit/cli/system_context.py` — Verify CLI wiring for all three commands

## Files to Create/Modify

- `tests/integration/test_system_commands_e2e.py` — Integration tests that verify the full chain
- Fix any bugs discovered during verification (scope limited to read command modules)

## Acceptance Criteria

- [ ] `/system-overview` returns structured output with >0 components when Graphiti has architecture data
- [ ] `/system-overview --format json` returns valid JSON with `status: "ok"`
- [ ] `/impact-analysis "knowledge layer"` returns non-empty component list with risk score
- [ ] `/impact-analysis` task ID enrichment extracts title from task frontmatter
- [ ] `/context-switch guardkit` updates `.guardkit/config.yaml` and displays orientation
- [ ] `condense_for_injection()` output is within token budget (verify with heuristic)
- [ ] Coach context builder produces non-empty architecture context for complexity >= 7 tasks
- [ ] Integration test file exists with >= 5 test cases covering the chain
- [ ] Any bugs found are fixed and documented in task notes

## Coach Validation Commands

```bash
# Verify integration tests exist
python -c "
from pathlib import Path
test_file = Path('tests/integration/test_system_commands_e2e.py')
assert test_file.exists(), 'Missing integration test file'
content = test_file.read_text()
assert content.count('def test_') >= 5, f'Too few tests: {content.count(\"def test_\")}'
assert 'system_overview' in content, 'Missing system_overview tests'
assert 'impact_analysis' in content, 'Missing impact_analysis tests'
print('Integration test validation OK')
"
```

## Implementation Notes

- This task depends on the stub replacement task completing first (Graphiti must have data)
- Tests should use the already-populated Graphiti instance, not mock data
- If entity type inference patterns don't match what `/system-plan` actually writes, fix the patterns in the read modules
- The key risk is format mismatch: `system_plan.py` writes entities one way, read modules expect them another way. This task catches that.
- `.guardkit/config.yaml` may need a `known_projects` entry for GuardKit — create if missing
