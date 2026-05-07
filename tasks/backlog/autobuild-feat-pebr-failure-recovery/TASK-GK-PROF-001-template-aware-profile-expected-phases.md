---
id: TASK-GK-PROF-001
title: Quality-gate profile must derive expected phases from template's installed agent set
status: backlog
created: 2026-05-07 00:00:00+00:00
updated: 2026-05-07 00:00:00+00:00
priority: medium
priority_band: P2
task_type: refactor
parent_review: TASK-REV-PEBR-001
parent_review_repo: forge
review_report: ../../../forge/docs/reviews/FEAT-PEBR-failed-run-1-analysis.md
implementation_mode: task-work
wave: 1
complexity: 5
estimated_minutes: 90
dependencies: []
tags:
  - autobuild
  - quality-gates
  - profiles
  - template-portability
  - P2
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Quality-gate profile must derive expected phases from template's installed agent set

## Description

The `refactor` (and probably other) quality-gate profile names a
hard-coded specialist agent for phase 3:
`python-api-specialist`
([coach_turn_1.json:24](../../../forge/.guardkit/worktrees/FEAT-PEBR/.guardkit/autobuild/TASK-FRR-PEB-001/coach_turn_1.json#L24)).
That agent is not present in the
`langchain-deepagents-orchestrator` template's installed guidance set
(see `forge/.claude/rules/guidance/`, which has langchain, langgraph,
deepagents, pytest specialists only). The advisory therefore fires on
*every* turn for *every* Python task built from this template,
regardless of what the Player does.

In the FEAT-PEBR run this produced a benign-but-noisy warning that
combined with the basename-scanner bug (TASK-GK-AC-001) to obscure
the real failure cause. After GK-AC is fixed the advisory is still
worth fixing in its own right — it pollutes operator dashboards
across the entire project's autobuild runs.

## Acceptance Criteria

- [ ] AC-1: The phase-3 specialist name is no longer a hard-coded
  literal in the quality-gate profile config. Instead, the profile
  consults the target template's installed `.claude/rules/guidance/`
  registry to discover available specialists.
- [ ] AC-2: When the target template ships a Python-API-shaped
  specialist (e.g. `python-api-specialist`,
  `langchain-tool-decorator-specialist`, etc.), the profile names
  whichever is most appropriate for the task tags. (For
  langchain-deepagents-orchestrator, that's likely
  `langchain-tool-decorator-specialist` for tool-related tasks and
  `pytest-agent-testing-specialist` for test-heavy tasks.)
- [ ] AC-3: When the target template has no Python-API specialist at
  all, the advisory either downgrades to "no phase-3 specialist
  available for this template" (informational) or is suppressed
  entirely.
- [ ] AC-4: Existing templates that *do* ship `python-api-specialist`
  (if any) continue to work — provide a fallback chain:
  template-discovered → profile-default → `python-api-specialist`.
- [ ] AC-5: With this fix applied to the forge repo's installed
  GuardKit, replaying the FEAT-PEBR turn-1 evaluation produces no
  `agent_invocations_advisory` issue (or a different, accurate one
  matching the langchain template's specialist set).
- [ ] AC-6: All modified files pass project-configured lint/format
  checks with zero errors.

## Test requirements

- Unit test: profile resolution with a synthetic
  `.claude/rules/guidance/` containing only langchain specialists →
  advisory either suppressed or names a langchain specialist.
- Unit test: profile resolution with a guidance dir containing
  `python-api-specialist` → advisory unchanged (back-compat).
- Unit test: profile resolution with no guidance dir → fallback chain
  fires.

## Implementation notes

### Files to Modify

- Search the codebase for the literal `python-api-specialist`
  (likely in `guardkit/installer/core/templates/default/settings.json`,
  in agent-invocations-validation logic in coach_validator.py, or in
  a per-task-type profile YAML somewhere under
  `guardkit/orchestrator/quality_gates/`).
- Add a small registry-discovery helper that reads the target
  workspace's `.claude/rules/guidance/*.md` files and returns the
  specialist names present.
- Wire the profile to call the helper at evaluation time, with the
  fallback chain.

### Recommended approach

```python
def _discover_template_specialists(workspace_root: Path) -> Set[str]:
    guidance_dir = workspace_root / ".claude" / "rules" / "guidance"
    if not guidance_dir.is_dir():
        return set()
    return {
        p.stem
        for p in guidance_dir.glob("*.md")
        if p.stem != "README"
    }

def _resolve_phase_3_specialist(
    task_tags: List[str],
    workspace_root: Path,
    profile_default: Optional[str] = None,
) -> Optional[str]:
    available = _discover_template_specialists(workspace_root)
    # Match by tag affinity (TBD: tag→specialist mapping)
    if "tool-decorator" in task_tags and "langchain-tool-decorator-specialist" in available:
        return "langchain-tool-decorator-specialist"
    # ... other tag mappings ...
    if profile_default in available:
        return profile_default
    if "python-api-specialist" in available:
        return "python-api-specialist"  # Legacy fallback
    return None  # → suppress advisory
```

### Scope discipline

The tag→specialist mapping logic could grow large. Keep this task
focused on the **mechanism** (registry discovery + fallback chain).
Building out a comprehensive tag→specialist taxonomy is a follow-up
task in its own right.

## Coach validation commands

```bash
PYTHONPATH=. python -m pytest tests/quality_gates/test_profile_resolution.py -x -v
PYTHONPATH=. python -m pytest tests/quality_gates/test_coach_validator.py -x -v -k specialist
ruff check guardkit/orchestrator/quality_gates/
```

## Out of scope

- Building a comprehensive tag→specialist taxonomy.
- Removing the agent-invocations advisory entirely.
- Per-template default profile overrides (a future feature).
