---
id: TASK-REV-A5F8
title: Analyse TASK-REV-D0C1 follow-ups — scaffolding model and Exemplar references
status: review_complete
created: 2026-04-11T13:00:00Z
updated: 2026-04-11T14:30:00Z
previous_state: backlog
state_transition_reason: "/task-review completed, awaiting decision"
priority: medium
tags: [review, template, architecture, documentation, guardkit-init, dotnet-railway-fastendpoints]
task_type: review
review_mode: architectural
review_depth: standard
parent_review: TASK-REV-D0C1
complexity: 0
review_results:
  mode: architectural
  depth: standard
  findings_count: 7
  recommendations_count: 7
  decision: implement
  report_path: .claude/reviews/TASK-REV-A5F8-review-report.md
  completed_at: 2026-04-11T14:30:00Z
  revised_at: 2026-04-11T15:15:00Z
  revision_reason: "User revised framing — GuardKit is a Software Factory, scaffolds are build-time patterns for AutoBuild Player, not reference material"
  implementation_feature: template-pattern-layer
  implementation_tasks:
    - TASK-PAT-1A5E
    - TASK-DOC-C3D7
    - TASK-REN-B9F2
    - TASK-FIX-E841
  superseded_tasks:
    - TASK-DRF-F4B8
  unchanged_tasks:
    - TASK-DRF-E7A2
---

# Task: Analyse TASK-REV-D0C1 follow-ups — scaffolding model and Exemplar references

## Description

TASK-REV-D0C1 (register `dotnet-railway-fastendpoints` as a builtin template) has been
reviewed and the core registration decision is settled: the template is accepted as a
first-class GuardKit builtin. The `.claude/` config layer that `guardkit init` actually
installs works correctly, so no rollback is needed and the registration edits made
under TASK-DRF-002 stand.

However, two follow-up tasks were filed during that review and need analysis before
they are worked:

1. **[TASK-DRF-F4B8](../backlog/TASK-DRF-F4B8-clarify-template-scaffolding-vs-config-layer.md)**
   (medium) — Clarify GuardKit's template scaffolding model. The
   `dotnet-railway-fastendpoints` template ships a `templates/` subdirectory with 20
   `.cs.template` files that look like project scaffold source code, but `guardkit init`
   only copies `.claude/`, `.guardkit/`, and an empty `tasks/` directory. Same behavior
   confirmed for `python-library` — init is a pure config-layer installer, not a
   project scaffolder. The task asks for a decision between three options:
   document-only, extend init to process `templates/*.template`, or remove the dead
   `.cs.template` files. The decision affects **all** templates, not just the .NET one.

2. **[TASK-DRF-E7A2](../backlog/TASK-DRF-E7A2-replace-exemplar-references-in-agent-docs.md)**
   (low, cosmetic) — Replace literal `Exemplar.*` namespace references with
   `{{Namespace}}` placeholders (or language-neutral descriptions for class names like
   `ExemplarApiFactory`) in the 5 affected agent markdown guidance files under
   `installer/core/templates/dotnet-railway-fastendpoints/agents/`. Not a blocker;
   purely user-facing polish for the template's agent docs.

The goal of this review is to recommend a direction for each follow-up so they can be
worked (or consciously deferred) rather than sitting in backlog indefinitely.

## Review Scope

### 0. Historical analysis — why does `init` only copy `.claude/`? (DO THIS FIRST)

**Important context from the task author**: There is a vague recollection of a
deliberate decision somewhere in the project's history to change `guardkit init` so
that it does NOT copy all files from a template — only the `.claude/` config layer.
The task author felt uneasy about it at the time and now suspects it may have been
the wrong call. Before any recommendation is made on F4B8, the history must be
analysed so the reviewer understands *why* the current behavior exists and whether
the original rationale still holds.

- [ ] `git log` and `git blame` on `guardkit/cli/init.py` — find the commit(s) that
      narrowed what `init` copies. Identify author, date, commit message, and any
      linked task ID in the message.
- [ ] Search `tasks/completed/` for any review or implementation task touching
      `init.py`, template copying, `templates/` subdirectory handling, or the
      config-layer-vs-scaffold distinction. Look especially for:
      - `TASK-REV-INIT-*` (there's already a completed
        `TASK-REV-INIT-review-guardkit-init-after-rules-structure.md`)
      - Any task whose title mentions "init", "template copy", "scaffold",
        "rules structure", "progressive disclosure"
      - Tasks referencing `templates/` subdirectory behavior
- [ ] Read the review reports in `.claude/reviews/` for any matching review tasks —
      they contain the rationale that task frontmatter usually doesn't.
- [ ] Check Graphiti for captured decisions on this topic — search nodes/facts in
      `guardkit__project_decisions`, `guardkit__project_architecture`, and
      `architecture_decisions` for queries like "guardkit init template copy",
      "config layer scaffold", ".claude rules structure init".
- [ ] Reconstruct a timeline: what was init's original behavior → what changed →
      when → why → has anything changed since that would invalidate the original
      rationale?
- [ ] Explicitly answer: was the change to restrict init to `.claude/` a deliberate
      architectural decision (and if so, what was the justification) or an
      accidental regression that nobody caught? This answer drives the F4B8
      recommendation — if it was deliberate with sound rationale, option 1
      (document) is right; if the rationale is now obsolete or it was accidental,
      option 2 (restore full copy) may be warranted.

**Do not proceed to section 1 until this historical analysis is complete and
documented in the review report.** The F4B8 recommendation depends on knowing
whether we are defending an intentional design or correcting a regression.

### 1. Scaffolding model decision (TASK-DRF-F4B8)

- [ ] Confirm current behavior of `guardkit init` against `installer/core/templates/`
      — exactly which directories/files does it copy, and does anything consume the
      `templates/` subdirectory convention at all?
- [ ] Check whether any other GuardKit builtin template (`react-typescript`,
      `fastapi-python`, `python-library`, `langchain-deepagents*`, etc.) ships a
      `templates/` subdirectory with scaffold files, and whether they share the same
      "dead subdirectory" problem.
- [ ] Evaluate the three options in TASK-DRF-F4B8 against GuardKit's positioning as
      a "lightweight, pragmatic task workflow system with built-in quality gates"
      (not a project scaffolder):
      - **Option 1 (document-only)**: cheapest, preserves current architecture, but
        leaves dead `.cs.template` files in the repo.
      - **Option 2 (extend init)**: broadest scope, pushes GuardKit into project-
        scaffolder territory and likely deserves its own feature plan rather than a
        single task. Evaluate whether this is in-scope for GuardKit at all.
      - **Option 3 (remove dead files)**: keeps GuardKit's scope narrow, removes
        user confusion, but discards potentially valuable reference code.
- [ ] Decide whether the `.cs.template` files under dotnet-railway-fastendpoints (and
      any equivalent in other templates) should be moved elsewhere (e.g., a
      `reference/` or `examples/` directory) rather than deleted outright, so the
      reference value is preserved without implying they are scaffold inputs.
- [ ] Recommend one option and scope the follow-up work (documentation changes,
      file moves/deletions, or a new feature plan if option 2 is chosen).

### 2. Exemplar reference cleanup (TASK-DRF-E7A2)

- [ ] Run `grep -rn 'Exemplar' installer/core/templates/dotnet-railway-fastendpoints/agents/`
      to confirm the exact set of occurrences (the filed task lists 5 files but notes
      the list is non-exhaustive).
- [ ] Categorize each occurrence: namespace reference (replace with
      `{{Namespace}}.*`) vs. class name like `ExemplarApiFactory` (generalize or
      rename to a neutral example).
- [ ] Decide whether this task is worth doing on its own or should be folded into a
      broader template polish pass — it's cosmetic and low priority.
- [ ] Confirm the task's "out of scope" note holds: the `.cs.template` files under
      `templates/` also contain `Exemplar` references, but those are reference code
      not consumed by init, so they stay out of scope for E7A2. This depends on
      which option the F4B8 review picks — if option 3 (remove) is chosen, the
      `.cs.template` Exemplar references disappear automatically.

### 3. Cross-cutting concerns

- [ ] Identify any ordering constraints between the two follow-ups. E7A2 on the
      agent markdown files can proceed independently of F4B8, but if F4B8 chooses
      option 3 (remove `.cs.template` files), the scope of E7A2 shrinks because the
      "out of scope" Exemplar references in scaffold files vanish.
- [ ] Check whether either follow-up should be promoted, deferred, or merged.
- [ ] Note any additional follow-ups surfaced by this analysis that were not
      captured at review time.

## Decision Points

0. **Historical rationale**: Was restricting `guardkit init` to copying only
   `.claude/` a deliberate architectural decision, and if so, does the original
   rationale still apply? This is the gating question — answer it before F4B8.
1. **F4B8 direction**: Which of the three options (document-only, extend init,
   remove dead files) should GuardKit commit to? This is a project-wide
   architectural call, not a template-local fix. If the historical analysis
   reveals the narrowing was accidental or its rationale is now obsolete, a
   fourth option — *restore* full-template copying — enters play.
2. **F4B8 scope**: If option 2 is picked, this should probably become a
   `/feature-plan` rather than a single task — confirm or route accordingly.
3. **E7A2 priority**: Keep as standalone low-priority task, fold into a broader
   template polish pass, or defer indefinitely?
4. **Ordering**: Should E7A2 wait for F4B8's decision to avoid rework on the
   scaffold-file Exemplar references, or proceed independently on the agent
   markdown files only?
5. **Reference code preservation**: If F4B8 chooses to remove the `.cs.template`
   files, should they be preserved as reference material elsewhere (a
   `reference/` directory, a separate repo, archived in Graphiti) rather than
   deleted outright?

## Acceptance Criteria

- [ ] Historical analysis complete: the commit(s) that restricted `init` behavior
      are identified, the original rationale is recovered (or confirmed missing),
      and a clear yes/no answer is given on whether that rationale still holds.
- [ ] Clear recommendation on TASK-DRF-F4B8 — one of the three options (or a
      documented fourth, including *restore* if the history analysis indicates
      the narrowing was wrong), with rationale tied to GuardKit's scope and
      positioning.
- [ ] Clear recommendation on TASK-DRF-E7A2 — proceed, fold into broader pass, or
      defer, with rationale.
- [ ] Dependency/ordering call between the two follow-ups documented.
- [ ] Any newly-discovered follow-ups filed as separate tasks with
      `parent_review: TASK-REV-A5F8`.
- [ ] Review report written to `.claude/reviews/TASK-REV-A5F8-review-report.md` via
      `/task-review`.

## Side Note (Not in Scope)

During TASK-REV-D0C1, it was observed that
`installer/core/commands/lib/template_validate_cli.py` is broken with
`ModuleNotFoundError: No module named 'global'`, so the reviewer could not run
`/template-validate` via the CLI path and substituted manual structural verification.
This was **not filed as a task** because it's unclear whether the CLI is still intended
to work or whether the slash-command subagent route has superseded it. This review
should NOT attempt to fix that CLI, but if the reviewer has a clear view on whether
the CLI path is alive or dead, flagging it for a separate task-create is welcome.

## References

- Parent review: `tasks/in_progress/TASK-REV-D0C1-register-dotnet-railway-fastendpoints-template.md`
- Parent review report: `.claude/reviews/TASK-REV-D0C1-review-report.md`
- Follow-up 1: `tasks/backlog/TASK-DRF-F4B8-clarify-template-scaffolding-vs-config-layer.md`
- Follow-up 2: `tasks/backlog/TASK-DRF-E7A2-replace-exemplar-references-in-agent-docs.md`
- Registered template: `installer/core/templates/dotnet-railway-fastendpoints/`
- Installer CLI: `guardkit/cli/init.py`
- Broken validator (side note): `installer/core/commands/lib/template_validate_cli.py`
