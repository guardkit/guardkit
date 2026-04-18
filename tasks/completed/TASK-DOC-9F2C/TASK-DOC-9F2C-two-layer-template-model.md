---
id: TASK-DOC-9F2C
title: Document two-layer template model (config + pattern) — user-facing guide
status: completed
task_type: documentation
created: 2026-04-18T00:00:00Z
updated: 2026-04-18T00:00:00Z
completed: 2026-04-18T00:00:00Z
previous_state: in_review
state_transition_reason: "Task completed — R5a user-facing guide delivered, CLAUDE.md link added, all referenced files resolve"
completed_location: tasks/completed/TASK-DOC-9F2C/
organized_files:
  - TASK-DOC-9F2C-two-layer-template-model.md
priority: medium
tags:
  - docs
  - templates
  - pattern-layer
  - config-layer
  - guardkit-init
  - follow-up-rev-a925
parent_review: TASK-REV-A925
feature_id: FEAT-A925
implementation_mode: task-work
wave: 2
complexity: 3
depends_on:
  - TASK-INIT-D4E7
---

# Task: Document two-layer template model — user-facing guide

## Description

Write a short, user-facing documentation guide that explains the two-layer
template model (config layer + pattern layer), what `guardkit init` does
and does not do, and how users should think about the `templates/`
subdirectory inside each template. The absence of this doc is the primary
cause of the Forge-init incident described in TASK-REV-A925.

This is Recommendation **R5a** (the "now" split) from
[.claude/reviews/TASK-REV-A925-review-report.md](../../../.claude/reviews/TASK-REV-A925-review-report.md).
It is a narrow, tactical subset of the previously-filed `TASK-DOC-C3D7`
which is deferred until FEAT-1A5E's Player wire-in lands.

## Context

Per TASK-REV-A925 F5 and R5: users discover the config/pattern split by
failing in a downstream consumer (most recently, the Forge) rather than
through the docs. TASK-DOC-C3D7 in
[tasks/backlog/template-pattern-layer/](../../template-pattern-layer/) is
scoped for the broader architecture doc after FEAT-1A5E lands. That is the
right ordering for the **comprehensive** doc — but it leaves the immediate
user-expectation gap open for weeks or months.

This task is the **minimum viable doc** to close the immediate gap: a
single guide page that says what `init` does, what the pattern layer is,
and what to do when you need scaffold files today.

## Acceptance Criteria

### Functional

- [ ] New file: `docs/guides/template-two-layer-model.md` with these
      sections, in order:
  1. **What `guardkit init` does** — plain list of the four paths it
     copies (`.claude/agents`, `.claude/rules`, `CLAUDE.md` variants,
     `manifest.json`). Literal contract, no aspirational language.
  2. **What `guardkit init` does NOT do** — does not render `.template`
     or `.j2` files under the template's `templates/` directory. Does not
     produce `pyproject.toml`, `AGENTS.md`, `agent.py`, language-specific
     source trees, or any other project-scaffold files. Explicit to
     forestall the same discovery loop that hit the Forge.
  3. **The two-layer template model** — short prose (5-10 sentences)
     explaining the architectural split: config layer (what `init` uses)
     vs pattern layer (`templates/` subdirectory, consumed by AutoBuild
     today and a future `guardkit render` command). Reference
     TASK-INST-010 (2026-03-02) for the original decision and
     TASK-REV-A5F8 (2026-04-11) for the re-affirmation, both by name and
     linked.
  4. **If you need scaffold files today** — three options in order of
     fastest to most architectural:
     - Copy the desired `.template` / `.j2` files from the installed
       template cache at `~/.agentecflow/templates/<template>/templates/`
       and substitute `{{ProjectName}}`, `{{Namespace}}`, etc. by hand.
     - Use `tests/integration/test_template_render_import.py` as a
       reference implementation for string-substitution rendering
       (see `_render_template` and `_resolve_target`).
     - Wait for `guardkit render <template>` (tracked as a design
       spike from TASK-REV-A925 R4; pre-feature-plan at time of writing).
  5. **What the pattern layer is for** — short prose: it is the source
     of canonical scaffold shapes for AutoBuild and automated code
     generation, *not* user-facing scaffolding at init time. Link to
     [FEAT-1A5E README](../../../tasks/backlog/template-pattern-layer/README.md)
     for the architectural roadmap.
- [ ] The guide is linked from at least two entry points:
  - Root `CLAUDE.md` under the "Templates" section (or equivalent) — one
    line: `Template layout explained in [docs/guides/template-two-layer-model.md](docs/guides/template-two-layer-model.md).`
  - `guardkit init --help` output OR init's own summary tip line — the
    tip link produced by TASK-INIT-D4E7 should point at this guide, so
    the link text and path must match what INIT-D4E7 emits
    (`docs/guides/template-two-layer-model.md`).
- [ ] The guide references but does NOT duplicate:
  - TASK-REV-A925 review report (link for architectural reasoning)
  - TASK-REV-A5F8 review report (link for historical context)
  - FEAT-1A5E README (link for the pattern-layer consumer plan)
  - TASK-DOC-C3D7 (note that the comprehensive doc is deferred until
    FEAT-1A5E lands; this guide is the MVP)

### Non-Functional

- [ ] Length: 80-150 lines of markdown. Tight. No aspirational language,
      no speculation about future design.
- [ ] No code in the guide beyond one or two short illustrative fragments
      (e.g. the four copy paths as a code block). The guide describes
      intent and contract, not implementation.
- [ ] Tone matches existing `docs/guides/` files — see
      `docs/guides/system-overview-guide.md` or
      `docs/guides/graphiti-claude-code-integration.md` for established
      voice.

### Tests

- [ ] Documentation link-check (if one exists in the repo) passes.
      Otherwise, manually verify all markdown links resolve.
- [ ] Script that renders docs or builds the site (if applicable)
      succeeds; otherwise, manually preview the markdown.

## Files

- `docs/guides/template-two-layer-model.md` (new)
- `CLAUDE.md` (modify — add the one-line link)
- `guardkit/cli/init.py` (*only if* the tip text doesn't already point at
  this path, which TASK-INIT-D4E7 should have set up correctly)

## Implementation Notes

### Forward-referenced link from TASK-INIT-D4E7

TASK-INIT-D4E7 emits a tip that links to
`docs/guides/template-two-layer-model.md`. If INIT-D4E7 lands first
(Wave 1), the link will be a broken target until this task lands
(Wave 2). That is acceptable and explicit in the INIT-D4E7 task. The two
tasks are sequenced — INIT-D4E7 must NOT block on this doc existing.

### What explicitly NOT to include

- Do not propose changes to `guardkit init`'s behaviour. This doc
  documents the current contract; it does not argue for or against
  reversing it.
- Do not duplicate the full architectural analysis from TASK-REV-A5F8
  or TASK-REV-A925 — link to them. Keep this guide tight.
- Do not describe FEAT-1A5E's internals in detail. That is C3D7's scope,
  deferred. Just name it and link.

### Suggested first draft structure (skeleton)

```markdown
# Template Two-Layer Model

This guide explains how GuardKit templates are structured and what
`guardkit init` does with them.

## What `guardkit init` does

`guardkit init <template>` copies the following from the resolved template:

- `.claude/agents/*.md` → `.claude/agents/`
- `.claude/rules/**/*.md` → `.claude/rules/` (preserves structure)
- `CLAUDE.md` and `.claude/CLAUDE.md` → target root / `.claude/`
- `manifest.json` → `.claude/manifest.json`

Plus: creates `.claude/`, `tasks/`, `.guardkit/` directory scaffolding.
Plus: optional Graphiti project seeding, `.mcp.json` generation.

## What `guardkit init` does NOT do

...

## Why: the two-layer model

...

## If you need scaffold files today

...

## What the pattern layer is for

...

## Further reading

- ...
```

## Dependencies

- **Depends on TASK-INIT-D4E7** (Wave 1): this doc documents the tip link
  that INIT-D4E7 emits. Ordering is: INIT-D4E7 lands first, then this
  doc lands and fills in the target. If this doc lands first by accident,
  nothing breaks — INIT-D4E7 will simply forward-reference the guide that
  already exists.

## Links

- Parent review: [TASK-REV-A925](../../in_review/TASK-REV-A925-orchestrator-template-scaffold-rendering-gap.md)
- Review report: [.claude/reviews/TASK-REV-A925-review-report.md](../../../.claude/reviews/TASK-REV-A925-review-report.md) (Recommendation R5a)
- Sibling task (produces the tip link): [TASK-INIT-D4E7](./TASK-INIT-D4E7-init-pattern-layer-summary.md)
- Deferred comprehensive doc: [TASK-DOC-C3D7](../../template-pattern-layer/TASK-DOC-C3D7-document-two-layer-template-model.md)
- FEAT-1A5E README: [tasks/backlog/template-pattern-layer/README.md](../../template-pattern-layer/README.md)
- Historical context: [TASK-REV-A5F8 review report](../../../.claude/reviews/TASK-REV-A5F8-review-report.md)
- Original architectural decision: TASK-INST-010 (design_approved)
