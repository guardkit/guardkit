# Implementation Guide: Init Graphiti Polish

**Feature ID**: FEAT-IGP
**Parent Review**: TASK-REV-A73F

## Wave 1 (All tasks - parallel)

All 3 tasks can be executed in parallel as they modify different parts of the codebase with no file conflicts.

### TASK-IGP-001: Auto-offer system seeding after init
- **Method**: task-work
- **Complexity**: 3 (simple feature addition)
- **Key file**: `guardkit/cli/init.py` (insert after line ~789)
- **Test file**: `tests/cli/test_init.py`
- **Notes**: Import `seed_system_content` from `guardkit.knowledge.system_seeding`. Wrap in try/except for graceful degradation. Honor `--skip-graphiti` and `--no-questions` flags.

### TASK-IGP-002: Document two-phase seeding architecture
- **Method**: direct
- **Complexity**: 2 (documentation only)
- **Key files**: `guardkit/cli/init.py` (console output), `.claude/rules/graphiti-knowledge.md`
- **Notes**: If TASK-IGP-001 lands first, adjust messaging to reflect that system seeding may have already run inline.

### TASK-IGP-003: Encourage --copy-graphiti for multi-project
- **Method**: direct
- **Complexity**: 1 (documentation only)
- **Key files**: `.claude/rules/graphiti-knowledge.md`, `guardkit/cli/init.py` (help text)
- **Notes**: Minimal change. Add a "Multi-Project Setup" section.

## File Conflict Analysis

| File | IGP-001 | IGP-002 | IGP-003 |
|------|---------|---------|---------|
| `guardkit/cli/init.py` | Lines 789-800 (new code) | Lines 801-812 (output text) | Line ~833 (help text) |
| `.claude/rules/graphiti-knowledge.md` | - | New section | New section |
| `tests/cli/test_init.py` | New tests | - | - |

No overlapping line ranges in `init.py`. The two documentation tasks modify different sections of `graphiti-knowledge.md`. Safe to parallelize.

## Quality Gates

- TASK-IGP-001: Standard quality gates (compilation + tests + 80% coverage on new code)
- TASK-IGP-002: Minimal (no code logic changes)
- TASK-IGP-003: Minimal (no code logic changes)

## Post-Implementation

After all tasks complete, re-run the init workflow manually to verify:
1. `guardkit init` offers system seeding after project seeding
2. Console output explains what was seeded
3. `--help` mentions `--copy-graphiti` for shared FalkorDB
