---
id: TASK-FIX-E841
title: Repair or deprecate installer/core/commands/lib/template_validate_cli.py
status: completed
created: 2026-04-11T15:15:00Z
updated: 2026-04-11T16:30:00Z
completed: 2026-04-11T16:30:00Z
previous_state: in_review
state_transition_reason: "All acceptance criteria met; Option B (deprecate) implemented and verified"
completed_location: tasks/completed/TASK-FIX-E841/
priority: low
tags: [bug, cli, template-validate, cleanup, technical-debt]
parent_review: TASK-REV-A5F8
implementation_mode: direct
complexity: 2
depends_on: []
resolution: deprecated
---

# Task: Repair or deprecate `template_validate_cli.py`

## Background

Surfaced as a side note in [TASK-REV-D0C1](../in_progress/TASK-REV-D0C1-register-dotnet-railway-fastendpoints-template.md) ("Side Note (Not in Scope)") and confirmed during [TASK-REV-A5F8](../in_review/TASK-REV-A5F8-analyse-d0c1-followups-scaffolding-and-exemplar.md).

The Python CLI at [installer/core/commands/lib/template_validate_cli.py](../../installer/core/commands/lib/template_validate_cli.py) is broken at import time:

```python
# Line 21 — importlib.import_module('global.lib.template_validation')
_validation_module = importlib.import_module('global.lib.template_validation')
```

Two problems:

1. **`global` is a Python keyword**, so an import path starting with `global.` is invalid as a dotted module path. The comment on line 20 acknowledges the intent: "Import using importlib to bypass 'global' keyword issue" — but importlib does not bypass the keyword check; the string is still parsed as a dotted module path.
2. **There is no `installer/core/global/lib/template_validation/` directory**. The real path is `installer/core/lib/template_validation/`. At some point the codebase contained a directory literally named `global/` that has since been renamed or restructured, and this CLI was not updated.

The failure mode is `ModuleNotFoundError: No module named 'global'` when anything tries to run the CLI. It is effectively dead code.

Meanwhile, `/template-validate` works fine as a Claude Code slash command via [installer/core/commands/template-validate.md](../../installer/core/commands/template-validate.md) and its associated subagent. The slash-command route appears to have superseded the Python CLI, but the CLI file was never deleted.

## Description

Decide whether this CLI is still intended to work and either:

**Option A (repair)**: Update the import to target the correct module path (`installer.core.lib.template_validation` or similar, depending on how the package is laid out after the rename). Verify the CLI runs end-to-end against at least one builtin template.

**Option B (deprecate)**: Delete `installer/core/commands/lib/template_validate_cli.py` entirely if the slash-command route is confirmed authoritative. Grep for references first (in case any scripts or docs point at the CLI path) and clean those up too.

This task's acceptance criteria deliberately leave the choice open because the decision depends on whether there is a non-Claude-Code use case for a standalone Python CLI invocation of template-validate (e.g., CI pipelines).

## Acceptance Criteria

- [x] Decide between repair (Option A) or deprecate (Option B) and document the decision in this task file
- [x] If Option B: delete the file, delete any test files that import it, grep the codebase for references to the old path and clean them up, and update any docs that mention the CLI path
- [x] Verify the broken import can no longer be hit — `python -c "from installer.core.commands.lib.template_validate_cli import parse_args"` raises `ModuleNotFoundError: No module named 'installer.core.commands.lib.template_validate_cli'` (predictable "intentionally gone" signal)

## Decision: Option B (Deprecate)

**Rationale**

- The CLI has been broken at import time for an unknown duration with no user impact reports — strong evidence it has no active users.
- The `/template-validate` slash command is the authoritative route and works via the subagent (`installer/core/commands/template-validate.md`) driving the real orchestrator at `installer/core/lib/template_validation/`. No Python CLI entry point is required for this.
- The companion test file (`tests/integration/test_template_validation_cli.py`) was itself dead: it never imported `parse_args`/`print_usage` and patched a non-existent `global.commands.lib.template_validate_cli` module path. Any attempt to collect or run it would have failed — more evidence the CLI has been unused.
- No installer script, CI workflow, Makefile, shell script, or live doc references the CLI path. The only live reference was a "Command Execution" note in `installer/core/commands/template-validate.md` itself, which described the intended CLI/symlink pattern but did not represent the actual execution path.
- No CI pipeline use case was identified that would justify repairing and maintaining a standalone Python CLI in parallel with the slash command.

**Changes made**

1. Deleted `installer/core/commands/lib/template_validate_cli.py` (broken import shim).
2. Deleted `tests/integration/test_template_validation_cli.py` (already broken — undefined symbols and stale `global.*` patch targets).
3. Updated `installer/core/commands/template-validate.md` "Command Execution" section: removed the `python3 ~/.agentecflow/bin/template-validate-cli "$@"` invocation and the CLI-pattern note, replaced with an explicit statement that `/template-validate` is a slash command driven by that file and its subagent, with a reference back to this task.

**Verification**

- `python3 -c "from installer.core.commands.lib.template_validate_cli import parse_args"` → `ModuleNotFoundError: No module named 'installer.core.commands.lib.template_validate_cli'` ✓
- `pytest tests/integration/ --collect-only` → 1199 tests collected, 0 errors (deleted test file no longer affects collection) ✓
- Remaining references to `template_validate_cli` / `template-validate-cli` live only in historical artifacts (`.claude/reviews/*`, `docs/reviews/*`, `docs/archive/*`, `tasks/completed/*`, `.claude/state/backup/*`) and in review reports/task files describing the original bug. These are frozen historical records and are intentionally left untouched.

**Scope notes**

- The `installer/core/commands/lib/` directory still contains several other command-lib modules (e.g., `agent_format_cli.py`, `agent_validate_cli.py`, `agent_enhance_cli.py`, etc.). Whether those still work was explicitly out of scope for this task. If the same "CLI shim next to a markdown slash command" pattern is also dead for them, that warrants a follow-up audit — not filed here, but could be surfaced via `/task-review` of the commands/lib directory.

## References

- Parent review: [TASK-REV-A5F8](../in_review/TASK-REV-A5F8-analyse-d0c1-followups-scaffolding-and-exemplar.md) — Section 1 "On the 'broken template_validate_cli.py' side note"
- Original side note: [TASK-REV-D0C1](../in_progress/TASK-REV-D0C1-register-dotnet-railway-fastendpoints-template.md) "Side Note (Not in Scope)"
- Broken file: [installer/core/commands/lib/template_validate_cli.py](../../installer/core/commands/lib/template_validate_cli.py)
- Likely live alternative: [installer/core/commands/template-validate.md](../../installer/core/commands/template-validate.md) (slash command + subagent)
- Target module (for Option A): [installer/core/lib/template_validation/](../../installer/core/lib/template_validation/)
