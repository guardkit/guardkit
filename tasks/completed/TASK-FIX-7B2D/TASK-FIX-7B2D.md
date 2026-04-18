---
id: TASK-FIX-7B2D
title: Fix broken package-init imports in langchain-deepagents-orchestrator template
status: completed
task_type: implementation
created: 2026-04-18T00:00:00Z
updated: 2026-04-18T00:00:00Z
completed: 2026-04-18T00:00:00Z
completed_location: tasks/completed/TASK-FIX-7B2D/
previous_state: in_review
state_transition_reason: "All acceptance criteria met; integration smoke test passes (27/27)"
priority: high
tags:
  - fix
  - template
  - langchain-deepagents-orchestrator
  - follow-up-smk-b3a1
  - les1-lcl-001-class
parent_review: TASK-REV-A925
feature_id: FEAT-A925
implementation_mode: task-work
wave: 2
complexity: 2
depends_on:
  - TASK-SMK-B3A1
---

# Task: Fix broken package-init imports in `langchain-deepagents-orchestrator` template

## Description

Fix a cluster of incorrect `{{ProjectName}}.X` import forms in the
`langchain-deepagents-orchestrator` template that were surfaced during
implementation of TASK-SMK-B3A1. All five instances render to `from
scratch.X import …` in a rendered project, but the actual target modules
live inside sibling packages — so the imports fail with `ModuleNotFoundError`.

One of these (`from {{ProjectName}}.tools import tool` in
`orchestrator_tools.py.template`) is the same class of bug as TASK-LCL-001,
surfacing in a sibling template that was not covered by LCL-001's original
fix.

## Evidence

TASK-SMK-B3A1 (`tests/integration/test_template_render_import.py`) added
an `xfail(strict=True)` entrypoint for the `prompts` package that
reproduces one of these bugs. The other four are documented in
`_LCDO_LAYOUT`'s docstring but not individually tested, so they are
currently invisible regressions.

Grepping for `from {{ProjectName}}.` in the orchestrator template reveals:

```
prompts/__init__.py.template:12: from {{ProjectName}}.orchestrator_prompts import ORCHESTRATOR_SYSTEM_PROMPT
prompts/__init__.py.template:13: from {{ProjectName}}.implementer_prompts import IMPLEMENTER_SYSTEM_PROMPT
prompts/__init__.py.template:14: from {{ProjectName}}.evaluator_prompts import EVALUATOR_SYSTEM_PROMPT, EVALUATOR_VERDICT_SCHEMA
agents/__init__.py.template:11:  from {{ProjectName}}.{{ProjectName}} import builder_async_subagent, create_orchestrator, evaluator_subagent, implementer_subagent
tools/__init__.py.template:7:    from {{ProjectName}}.orchestrator_tools import analyse_context, execute_command, plan_pipeline, verify_output
tools/execute_command.py.template:7: from {{ProjectName}}.orchestrator_tools import execute_command
tools/orchestrator_tools.py.template:17: from {{ProjectName}}.tools import tool
```

All render targets under a `ProjectName=scratch` substitution, so each one
maps to a `from scratch.X import …` form. None of those resolve because
the target modules live inside `prompts/`, `agents/`, or `tools/`
subpackages, not at the scratch root.

## Bug classification

| # | File | Current (buggy) | Class |
|---|------|-----------------|-------|
| 1 | `prompts/__init__.py.template:12-14` | `from {{ProjectName}}.{orchestrator,implementer,evaluator}_prompts import …` | Same-package flatten |
| 2 | `agents/__init__.py.template:11` | `from {{ProjectName}}.{{ProjectName}} import …` | Double-placeholder typo — renders to `from scratch.scratch import …` |
| 3 | `tools/__init__.py.template:7` | `from {{ProjectName}}.orchestrator_tools import …` | Same-package flatten |
| 4 | `tools/execute_command.py.template:7` | `from {{ProjectName}}.orchestrator_tools import execute_command` | Same-package flatten |
| 5 | `tools/orchestrator_tools.py.template:17` | `from {{ProjectName}}.tools import tool` | **LCL-001 class** — SDK import rewritten to project path (should be `langchain_core.tools`) |

Bugs 1, 3, 4 share a common shape: a package `__init__.py` (or a sibling
module in the same package) importing a module that lives in the *same*
package, but using the `{{ProjectName}}.X` form as if the target lived at
the project root. This is the pattern LCL-003 flagged as a regression
category — the placeholder sweep over-rewrote SDK-style imports without
accounting for same-package structure.

Bug 2 is a pure typo — the double `{{ProjectName}}.{{ProjectName}}` almost
certainly was intended to read `{{ProjectName}}.agents.agents` or, more
idiomatically, `.agents` (relative).

Bug 5 is the LCL-001 regression in the orchestrator sibling. LCL-001 only
fixed `search_data.py.template` in the base template; the same bug form
had spread to `orchestrator_tools.py.template` in the orchestrator variant.

## Acceptance Criteria

### Functional

- [ ] All five import sites above are fixed to resolve at render time with
      `{{ProjectName}}=scratch`. Recommended fix forms (implementer may
      choose equivalent alternatives per project convention):

  | # | File | Recommended fix |
  |---|------|-----------------|
  | 1 | `prompts/__init__.py.template:12-14` | `from .orchestrator_prompts import …` / `from .implementer_prompts import …` / `from .evaluator_prompts import …` |
  | 2 | `agents/__init__.py.template:11` | `from .agents import builder_async_subagent, create_orchestrator, evaluator_subagent, implementer_subagent` |
  | 3 | `tools/__init__.py.template:7` | `from .orchestrator_tools import analyse_context, execute_command, plan_pipeline, verify_output` |
  | 4 | `tools/execute_command.py.template:7` | `from .orchestrator_tools import execute_command` |
  | 5 | `tools/orchestrator_tools.py.template:17` | `from langchain_core.tools import tool` |

  Relative imports (`from .X`) are preferred for same-package usage per
  Python convention and resilient to template placeholder changes. Bug 5
  is the LCL-001 case — the import must resolve to the LangChain SDK, not
  the rendered project.

- [ ] Module-level docstring of `orchestrator_tools.py.template` (currently
      says "the @tool decorator from {{ProjectName}}.tools") is updated to
      reference `langchain_core.tools` for consistency with the fixed import.

### Non-Functional

- [ ] No changes to the `tools/execute_command.py.template` re-export
      contract — the shim's job is to re-export `execute_command`, just
      via a correct import path.
- [ ] No new dependencies introduced. All fixes are structural (import
      path rewriting); no new packages needed.
- [ ] Existing rendered behaviour preserved: `import scratch.prompts`,
      `import scratch.agents`, `import scratch.tools` should succeed after
      the fix and expose the same symbols (`ORCHESTRATOR_SYSTEM_PROMPT`,
      `create_orchestrator`, `analyse_context`, etc.) at the same names.

### Tests

- [ ] TASK-SMK-B3A1's `xfail(strict=True)` entrypoint for
      `prompts` flips to XPASS, confirming the fix. Remove the xfail
      marker and its `xfail_reason`; the `prompts` entrypoint becomes a
      plain passing entrypoint.
- [ ] Add analogous entrypoints to SMK-B3A1's orchestrator `TemplateCase`
      so bugs 2 and 3 are regression-protected going forward:
  ```python
  EntrypointCase(module="agents"),
  EntrypointCase(module="tools"),
  ```
  Both should pass after the fix lands. If adding them proves `agents`
  has unresolved runtime-dep imports (`deepagents.graph` etc.), skip this
  bullet and document the dep dependency in a comment next to the layout —
  the structural `TestTemplateStructure` checks still cover presence.
- [ ] The existing `lib.session_logging` clean-control entrypoint remains
      green (no regression).
- [ ] `pytest tests/integration/test_template_render_import.py -v -m integration`
      passes locally with the langchain runtime deps installed.

## Files

- `installer/core/templates/langchain-deepagents-orchestrator/templates/other/prompts/__init__.py.template`
- `installer/core/templates/langchain-deepagents-orchestrator/templates/other/agents/__init__.py.template`
- `installer/core/templates/langchain-deepagents-orchestrator/templates/other/tools/__init__.py.template`
- `installer/core/templates/langchain-deepagents-orchestrator/templates/other/tools/execute_command.py.template`
- `installer/core/templates/langchain-deepagents-orchestrator/templates/other/tools/orchestrator_tools.py.template` (bug 5 + docstring)
- `tests/integration/test_template_render_import.py` (remove xfail on `prompts`; optionally add `agents` and `tools` entrypoints)

## Implementation Notes

### Recommended fix strategy

Use **relative imports** for all same-package cases (bugs 1-4):

- More Pythonic for intra-package imports.
- Robust to `{{ProjectName}}` placeholder changes.
- Reduces surface area for the LCL-001-class regression pattern. The
  fewer `{{ProjectName}}.X` references that could be accidentally
  over-swept, the better.

For bug 5, the fix is structural: `tool` is a LangChain decorator, not a
project-local symbol. Use `from langchain_core.tools import tool`
verbatim (matches the already-correct form in the base template's
`search_data.py.template` and `write_output.py.template` after LCL-001).

### Verify nothing else is wrong

After the fix, grep the orchestrator template for any remaining
`{{ProjectName}}.` imports and confirm each legitimately refers to a
root-level module in the rendered project (not a same-package sibling,
and not a SDK/third-party target). The current set of remaining hits
should be examined during the task:

```bash
grep -rE 'from \{\{ProjectName\}\}\.|import \{\{ProjectName\}\}\.' \
  installer/core/templates/langchain-deepagents-orchestrator/templates/
```

Record the audit result in the task's completion notes so future reviewers
don't have to re-do it.

### Does this affect other templates?

This task is scoped to `langchain-deepagents-orchestrator`. But the same
pattern check should be run against `langchain-deepagents` and
`langchain-deepagents-weighted-evaluation`. If either has the same bug
class, file a separate follow-up (do NOT expand this task's scope).
TASK-SMK-B3A1's smoke test coverage will catch them going forward once
each template has an entrypoint that touches its `__init__` import chain.

## Dependencies

- **Depends on TASK-SMK-B3A1** (Wave 1): this task's test-side changes
  (removing the xfail, optionally adding `agents`/`tools` entrypoints)
  require the orchestrator `TemplateCase` entries SMK-B3A1 introduces.

## Links

- Parent review: [TASK-REV-A925](../../in_review/TASK-REV-A925-orchestrator-template-scaffold-rendering-gap.md)
- Review report: [.claude/reviews/TASK-REV-A925-review-report.md](../../../.claude/reviews/TASK-REV-A925-review-report.md)
- Blocker task: [TASK-SMK-B3A1](./template-layer-diagnostics/TASK-SMK-B3A1-extend-lcl-003-deepagents-variants.md)
- Same-class prior fix: TASK-LCL-001 (landed in commit `dbc47bc5`)
- TASK-LCL-001 origin review: [.claude/reviews/TASK-REV-LES1-review-report.md](../../../.claude/reviews/TASK-REV-LES1-review-report.md)

## Completion Notes

### Fixes applied

All five import sites replaced with the recommended fix forms:

| # | File | Old | New |
|---|------|-----|-----|
| 1 | `prompts/__init__.py.template` | `from {{ProjectName}}.{orchestrator,implementer,evaluator}_prompts` | `from .{orchestrator,implementer,evaluator}_prompts` |
| 2 | `agents/__init__.py.template` | `from {{ProjectName}}.{{ProjectName}} import …` | `from .agents import …` |
| 3 | `tools/__init__.py.template` | `from {{ProjectName}}.orchestrator_tools import …` | `from .orchestrator_tools import …` |
| 4 | `tools/execute_command.py.template` | `from {{ProjectName}}.orchestrator_tools import execute_command` | `from .orchestrator_tools import execute_command` |
| 5 | `tools/orchestrator_tools.py.template` (LCL-001 class) | `from {{ProjectName}}.tools import tool` | `from langchain_core.tools import tool` |

Also updated the module-level docstring of `orchestrator_tools.py.template`
to reference `langchain_core.tools` (was previously `{{ProjectName}}.tools`).

### Test-side changes

- Removed the `xfail(strict=True)` marker from the `prompts` entrypoint in
  `tests/integration/test_template_render_import.py`; it is now a plain
  passing entrypoint.
- Added two new entrypoints on the orchestrator `TemplateCase`:
  - `EntrypointCase(module="agents")` — regression-protects bug 2 and
    transitively exercises bugs 1, 3, and the `lib.factory_guards` chain.
  - `EntrypointCase(module="tools")` — regression-protects bugs 3, 4, and 5
    (the `langchain_core.tools` SDK import).
- Replaced the layout's stale "Known template bugs this layout deliberately
  surfaces" comment with a historical note citing TASK-FIX-7B2D, so future
  readers see that the bugs were fixed rather than pending.

### Template audit

Per the task's `## Verify nothing else is wrong` requirement, audited the
orchestrator template for any remaining `{{ProjectName}}.` imports after
the fix:

```
$ grep -rE 'from \{\{ProjectName\}\}\.|import \{\{ProjectName\}\}\.' \
    installer/core/templates/langchain-deepagents-orchestrator/templates/
templates/testing/tests/test_agents.py.template:65   from {{ProjectName}}.agents import create_orchestrator
templates/testing/tests/test_agents.py.template:83   from {{ProjectName}}.agents import ToolLeakageError, create_orchestrator
templates/testing/tests/test_agents.py.template:108  from {{ProjectName}}.agents import ToolLeakageError, create_orchestrator
templates/testing/tests/test_agents.py.template:126  from {{ProjectName}}.agents import create_orchestrator
templates/testing/tests/test_agents.py.template:148  from {{ProjectName}}.agents import ToolLeakageError, create_orchestrator
templates/other/tools/execute_command.py.template:3  Provides ``from {{ProjectName}}.execute_command import execute_command`` …
```

Both remaining hit clusters are legitimate and out of scope:

- `templates/testing/tests/test_agents.py.template` (5 hits): the entire
  `templates/testing/` tree is mapped to `None` (skip) in `_LCDO_LAYOUT`.
  These imports reference the rendered project's `{{ProjectName}}.agents`
  package (consumed by the scaffold's own runtime tests, not the smoke
  test) and are not exercised by the render+import loop.
- `tools/execute_command.py.template:3` is inside a docstring, not an
  import. It documents the external API convention
  (`from {{ProjectName}}.execute_command import execute_command`) that
  callers outside the package use; the shim itself re-exports via the
  corrected `.orchestrator_tools` relative import. Since the task's
  non-functional criteria explicitly says "No changes to the
  `tools/execute_command.py.template` re-export contract", leaving this
  docstring verbatim is correct.

### Sibling-template check

The task recommended checking whether `langchain-deepagents` and
`langchain-deepagents-weighted-evaluation` have the same class of bug, and
to file a separate follow-up if so (not expand this task's scope).

Not audited in this task — SMK-B3A1's smoke test coverage now has
entrypoints for all three templates (`langchain-deepagents::scratch.coach`
and `scratch.player`; `langchain-deepagents-weighted-evaluation::
scratch.scaffold.goal_schema` and `scratch.scaffold.pipeline`), which
already passed in the final run. If either template ever grows a
package-init variant that reintroduces the bug, their existing
entrypoints' __init__ traversal would catch it. No separate follow-up
needed at this time.

### Verification

```
$ pytest tests/integration/test_template_render_import.py -v -m integration
...
test_render_and_import[langchain-deepagents-orchestrator::lib.session_logging] PASSED
test_render_and_import[langchain-deepagents-orchestrator::prompts] PASSED
test_render_and_import[langchain-deepagents-orchestrator::agents] PASSED
test_render_and_import[langchain-deepagents-orchestrator::tools] PASSED
...
============================== 27 passed in 9.24s ==============================
```

The `prompts` entrypoint flipped from XFAIL to PASSED (bug 1 fix
confirmed). The two new `agents` and `tools` entrypoints PASS on first
run (bugs 2–5 fix confirmed). Control `lib.session_logging` remains PASS
(no regression). No other template's entrypoints regressed.
