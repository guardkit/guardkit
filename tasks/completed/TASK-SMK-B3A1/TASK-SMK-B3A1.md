---
id: TASK-SMK-B3A1
title: Extend LCL-003 smoke test to cover langchain-deepagents-orchestrator and -weighted-evaluation
status: completed
task_type: implementation
created: 2026-04-18T00:00:00Z
updated: 2026-04-18T00:00:00Z
completed: 2026-04-18T00:00:00Z
completed_location: tasks/completed/TASK-SMK-B3A1/
previous_state: in_review
state_transition_reason: "All acceptance criteria met, 24 tests pass, 1 xfail documents known orchestrator template bug, negative test green"
organized_files:
  - TASK-SMK-B3A1.md
priority: medium
tags:
  - testing
  - template-validation
  - lcl-003
  - langchain-deepagents-orchestrator
  - langchain-deepagents-weighted-evaluation
  - follow-up-rev-a925
  - follow-up-feat-ltl1
parent_review: TASK-REV-A925
feature_id: FEAT-A925
implementation_mode: task-work
wave: 1
complexity: 5
---

# Task: Extend LCL-003 smoke test to cover `-orchestrator` and `-weighted-evaluation`

## Description

Extend the template-render-and-import smoke test
[tests/integration/test_template_render_import.py](../../../tests/integration/test_template_render_import.py)
to cover the two `langchain-deepagents*` sibling templates that LCL-003
explicitly deferred in its completion notes. Closes the only genuine
LCL-003 scope gap identified by the TASK-REV-A925 review.

This is Recommendation **R3** from
[.claude/reviews/TASK-REV-A925-review-report.md](../../../.claude/reviews/TASK-REV-A925-review-report.md).

## Context

Per [TASK-LCL-003 completion notes](../../completed/TASK-LCL-003/TASK-LCL-003.md#L74):

> **Template coverage**: `langchain-deepagents` (base). The `-orchestrator`
> and `-weighted-evaluation` siblings use different conventions
> (orchestrator uses bare `from prompts import …` imports; weighted-eval
> uses `.j2` not `.template`); adding them is a mechanical extension of
> `TEMPLATES` in the test and is left as a follow-up within FEAT-LTL1.

The TASK-REV-A925 review confirmed this is the only real regression-prevention
gap from the filed BLOCKER. It does not address the Forge-init incident
itself (which is out of scope for this smoke test — see parent review F3),
but it does close the LCL-003 scope debt the filed task complained about.

## Acceptance Criteria

### Functional

- [ ] Add a `TemplateCase` entry to `TEMPLATES` in
      `tests/integration/test_template_render_import.py` for
      `langchain-deepagents-orchestrator`:
  - Declares the orchestrator's entrypoints. Choose library modules with
    module-level import chains that reproduce TASK-LCL-001-class failure
    surfaces. Avoid `agent.py` if it has heavy runtime wiring (config
    loading, live LLM probing) — see LCL-003's rationale for the base
    template (it chose `coach` and `player` over `agent`).
  - Declares runtime deps (subset of `langchain`, `langgraph`, `deepagents`,
    etc.) based on actual imports in the rendered tree.
  - Declares a `layout` mapping `.template` source paths to scratch-project
    destinations. The orchestrator uses *bare* imports like
    `from prompts import …` and `from agents import …` (not
    `from {{ProjectName}}.prompts`). This means the rendered tree must
    place `prompts/`, `agents/`, `tools/` at the **scratch root**, not
    under `scratch/`. Verify by grep'ing `from (?!\.|langchain|langgraph|deepagents)` in the orchestrator's `.template` files and shaping the
    layout so those imports resolve.
  - Full placeholder set from `_DEFAULT_PLACEHOLDERS` (ProjectName,
    Namespace, Author, ...).
- [ ] Add a `TemplateCase` for `langchain-deepagents-weighted-evaluation`:
  - The template uses `.j2` (Jinja) suffix, not `.template`. Extend
    `_render_template` to also pick up `*.j2` via
    `sorted(template_root.rglob("*.j2"))` in addition to `*.template`,
    OR decide `.j2` is out of scope and declare that explicitly in the
    docstring with a follow-up marker (prefer former — the
    render-helper is string-replace, not Jinja, but the file suffix is
    incidental to the placeholder substitution). If `.j2` contains real
    Jinja expressions beyond `{{Key}}`, skip those files via the layout's
    `None` target or add Jinja-safe placeholder handling.
  - Declare entrypoints, runtime deps, placeholders, and layout
    consistent with the variant's actual import conventions.
- [ ] Both new entries pass `pytest tests/integration/test_template_render_import.py`
      locally with their runtime deps installed. If a template has an
      unresolvable upstream regression (TASK-LCL-001-style), mark the
      entrypoint `xfail(strict=True)` with a clear reason pointing at
      the upstream task — same pattern as the base template's
      `scratch.player` entry.
- [ ] `TestTemplateStructure` structural checks run for both new variants
      (parametrised automatically via the `TEMPLATES` list — no test
      changes needed, just the data addition).
- [ ] Negative test (`TestNegative::test_broken_import_fails_loud`) remains
      green — no regression to the harness.

### Non-Functional

- [ ] No change to `guardkit init` behaviour. This test continues to
      bypass `init` via the local `_render_template` shim, per LCL-003's
      documented contract.
- [ ] Skip-on-missing-runtime-deps semantics preserved for both new
      templates.
- [ ] If `_render_template` is extended to handle `.j2`, add a short
      comment clarifying it is placeholder substitution only (no Jinja
      expression evaluation), so reviewers don't assume Jinja2 is in the
      test path.

### Tests

- [ ] `pytest tests/integration/test_template_render_import.py -v` passes
      the three new structural tests (`test_template_source_dir_exists`,
      `test_entrypoints_declared` × 2 new variants).
- [ ] `pytest tests/integration/test_template_render_import.py -v -m integration`
      with the langchain runtime deps installed passes or xfails-strict
      as declared.
- [ ] Negative-test proof still green.

## Files

- `tests/integration/test_template_render_import.py` (modify `TEMPLATES` and
  `_render_template`; add `_LCDO_LAYOUT` and `_LCDWE_LAYOUT` module-level
  constants analogous to `_LCD_LAYOUT`)

## Implementation Notes

### Discovering the layout map

For each variant, the source-of-truth for the layout is the set of
render-time imports in the `.template` / `.j2` files. Workflow:

```bash
# Orchestrator
cd installer/core/templates/langchain-deepagents-orchestrator/templates/

# Which files import project-relative names?
grep -rE '^from [a-z_]+ import|^import [a-z_]+' --include='*.template'

# Which files import via {{ProjectName}} placeholder?
grep -rE 'from \{\{ProjectName\}\}|import \{\{ProjectName\}\}' --include='*.template'

# Which files exist to be rendered?
find . -name '*.template' -o -name '*.j2'
```

From the results, build a layout map modelled on `_LCD_LAYOUT`: each tuple
is `(source_prefix, target_prefix_or_None)` with longest-prefix match.
Root-project files (`pyproject.toml`, `AGENTS.md`, `langgraph.json`) go to
scratch-project root; Python packages go under `scratch/` or at root if
they use bare imports; testing scaffolds use `None` target (skip).

### Handling `.j2` for weighted-eval

The render helper does literal `{{Key}}` substitution, not Jinja. If the
`.j2` files in weighted-eval contain expressions beyond `{{Key}}` (loops,
conditionals, filters), two options:

1. **Preferred**: Skip files with non-trivial Jinja via layout `None`
   target. Keep coverage on the simple substitution subset.
2. **Alternative**: Add minimal Jinja support in `_render_text` via
   `jinja2.Template(src).render(**placeholders)`. Adds a test-only
   dependency on `jinja2` (already transitive via langchain, usually
   available).

Favour (1) to preserve LCL-003's small footprint.

### Entrypoint selection

Same rationale as LCL-003's `_LCD_LAYOUT` — avoid `agent.py`/`main.py`
when it has module-level config loading, domain file parsing, or LLM
probing. Prefer leaf library modules that reproduce the import-chain
failure surface.

## Dependencies

- None at code level (the existing LCL-003 harness is complete and stable).
- Runtime deps for actual import execution: `langchain`, `langgraph`,
  `deepagents`. Tests skip cleanly if missing.

## Links

- Parent review: [TASK-REV-A925](../../in_review/TASK-REV-A925-orchestrator-template-scaffold-rendering-gap.md)
- Review report: [.claude/reviews/TASK-REV-A925-review-report.md](../../../.claude/reviews/TASK-REV-A925-review-report.md) (Recommendation R3, Appendix A)
- Original LCL-003 task: [tasks/completed/TASK-LCL-003/TASK-LCL-003.md](../../completed/TASK-LCL-003/TASK-LCL-003.md)
- LCL-003 completion note deferring this work: line 74-79 of the task file
- Parent feature of LCL-003: FEAT-LTL1 (langchain-template-lessons)
