---
id: TASK-PAT-1A5E
title: Wire template scaffold files into AutoBuild Player context as stack-pattern guidance
status: closed
created: 2026-04-11T15:15:00Z
updated: 2026-04-18T00:00:00Z
priority: high
tags: [autobuild, player, templates, patterns, software-factory, architecture, feature-plan-required, closed, superseded]
parent_review: TASK-REV-A5F8
feature_id: FEAT-1A5E
implementation_mode: task-work
complexity: 8
needs_feature_plan: true
depends_on: []
superseded_by: FEAT-TPL-PLAYER
closed_by: TASK-TPL-004
closed_reason: "Implemented under FEAT-TPL-PLAYER. The /feature-plan flow decomposed this scope into TASK-TPL-001 (extract template resolver), TASK-TPL-002 (template pattern loader + TemplatePatternContext), TASK-TPL-003 (domain-hint selector), TASK-TPL-004 (wire into AutoBuildContextLoader), TASK-TPL-005 (unit tests), TASK-TPL-006 (integration test), and TASK-TPL-007 (documentation). All seven subtasks are in_review under tasks/backlog/template-pattern-player-context/. The Player now receives a TemplatePatternContext block at AutoBuild context-load time with template resolution, domain-hint pattern selection, and graceful degradation. Token budget impact and instrumentation are addressed via TASK-TPL-004 logging and TASK-TPL-007 docs."
---

# Task: Wire template scaffold files into AutoBuild Player context as stack-pattern guidance

> **Closed: superseded by FEAT-TPL-PLAYER.** The architectural fix proposed here was scoped via `/feature-plan` into the seven-task FEAT-TPL-PLAYER feature at [tasks/backlog/template-pattern-player-context/](../template-pattern-player-context/), all subtasks now in_review. See `closed_reason` in frontmatter for the mapping. The original scoping notes below are kept for historical context only.

> ⚠️ ~~**Needs `/feature-plan` before implementation.** This task is scope-sized for a feature, not a single `/task-work` run. The scoping below is indicative; do not begin implementation until `/feature-plan "wire template patterns into AutoBuild Player"` has run and a design checkpoint has been approved.~~ — `/feature-plan` ran, producing FEAT-TPL-PLAYER.

## Background

This task is the primary deliverable of [TASK-REV-A5F8](../../in_review/TASK-REV-A5F8-analyse-d0c1-followups-scaffolding-and-exemplar.md). See the [review report](../../../.claude/reviews/TASK-REV-A5F8-review-report.md), especially Section 1 "Primary recommendation", for full rationale.

**Short version**: GuardKit is a Software Factory. The AutoBuild Player is the Build Agent. Today the Player enters feature implementation with zero stack-specific pattern context because:

1. `guardkit init` deliberately excludes `templates/*.template` files ([guardkit/cli/init.py:50-51](../../../guardkit/cli/init.py#L50), TASK-INST-010, 2026-03-02).
2. AutoBuild worktree setup further prunes `.claude/rules/` down to 4 essentials via `AUTOBUILD_ESSENTIAL_RULES` at [autobuild.py:210-215](../../../guardkit/orchestrator/autobuild.py#L210) and [autobuild.py:1172-1215](../../../guardkit/orchestrator/autobuild.py#L1172).
3. The Player has neither the pattern rules nor the canonical scaffold shapes.

Meanwhile `/template-create` is actively producing `.template` files that nothing reads across all 10 builtin templates. The missing consumer is the Player. TASK-INST-010 parked it as "a separate concern" and never followed through. This task is that follow-through.

## Description

Wire the pattern layer into the AutoBuild Player's context so the Build Agent has stack-specific canonical shapes available when implementing feature tasks.

## Indicative scope (for the feature-plan session to refine)

### 1. Source-template identification

Given a project that has been initialized with `guardkit init {template}`, the AutoBuild orchestrator must determine which template the project came from so it can resolve the pattern library.

**Candidates**:

- Primary: read `.claude/manifest.json` (copied in by `init`) and extract the `name` field
- Fallback: `.guardkit/template.yaml` marker file (if one exists or is introduced by this task)
- Last-resort heuristic: detect stack from `pyproject.toml` / `package.json` / `.csproj` / `Cargo.toml` presence, and map to the best-matching builtin template

### 2. Path resolution

Resolve `installer/core/templates/{name}/templates/` from the installed guardkit package location. Use the same `__file__`-relative resolver that [apply_template() in guardkit/cli/init.py:460-510](../../../guardkit/cli/init.py#L460) already uses. Factor out if needed to avoid duplication.

### 3. Pattern selection

**v1 (simplest)**: Copy the whole `templates/` tree into the worktree. Accept the token cost as a starting point to establish the feature works at all.

**v2 (task-scoped)**: Inspect the task description and plan to identify which layers are relevant (endpoint / repository / service / validator / test / domain / infrastructure) and copy only the matching pattern subdirectories. Token cost scales with task needs rather than flat-rate.

The design pass should pick v1 or v2 based on a measured token-budget analysis.

### 4. Worktree injection

Inject selected patterns into a well-known path inside the worktree — proposed: `.guardkit/patterns/` or `.claude/patterns/` — **not** into the user's working tree. The worktree is ephemeral and per-task; patterns exist only for the duration of the Player turn.

Injection must happen in the AutoBuild worktree-setup path, after template copying and before Player invocation. See [guardkit/orchestrator/autobuild.py](../../../guardkit/orchestrator/autobuild.py) worktree setup.

### 5. Player prompt update

Instruct the Player to consult the pattern library before synthesizing new code. Likely approaches:

- Add an instruction block to `autobuild.md` (which is already in the `AUTOBUILD_ESSENTIAL_RULES` frozenset)
- OR introduce a new `player-patterns.md` rule file and add it to the essentials list
- OR inject a prompt fragment directly into the Player SDK query

Suggested instruction: *"When implementing against the {{stack}} stack, canonical shapes for this project's layers are in `.guardkit/patterns/`. Read the relevant files before writing new code. Your implementation should match the shapes used in these patterns."*

### 6. Rule-prune reconsideration

[autobuild.py:210-215](../../../guardkit/orchestrator/autobuild.py#L210) currently prunes `.claude/rules/` down to 4 files to save ~11.5K tokens/turn. This was sized when patterns did not exist. Once patterns are wired, decide:

- **(a)** Keep aggressive prune, rely on `.guardkit/patterns/` as the sole pattern source
- **(b)** Relax prune to also keep `.claude/rules/patterns/` (stack-specific rule files that accompany `.template` files)
- **(c)** Task-scoped rule selection (same logic as pattern selection in step 3)

Option (c) is the most elegant but highest implementation cost. Design pass should pick.

### 7. Instrumentation

Use the existing instrumentation pipeline (TASK-INST-*) to track whether pattern files are actually being read by the Player during turns. If they are not being read, the token cost is wasted and the design needs revisiting.

Minimum measurement: did the Player issue a Read on any `.guardkit/patterns/` path during the turn?

## Acceptance Criteria (stub)

These must be refined during `/feature-plan`. Indicative only:

- [ ] Source template identification works for all 10 builtin templates
- [ ] Player invocations in a dotnet-railway-fastendpoints-initialized project receive the relevant `.template` files (Railway-Oriented, FastEndpoints, Repository, Testcontainers) in context
- [ ] Player invocations in a fastapi-python-initialized project receive the relevant `.template` files in context
- [ ] Token budget impact measured; design goal is comparable to the current pruned ~17 KB rules baseline
- [ ] Instrumentation confirms the Player actually reads the injected patterns during typical feature tasks
- [ ] No regression in existing AutoBuild runs (worktree setup still idempotent, prune logic still works, existing integration tests pass)
- [ ] New unit tests cover: template name resolution, path resolution, pattern selection logic, worktree injection
- [ ] Integration test: run AutoBuild end-to-end on a toy feature task in at least two different stacks and confirm patterns land in the worktree and are referenced in Player output

## Open questions for `/feature-plan`

1. **Pattern selection**: v1 (copy everything) or v2 (task-scoped)?
2. **Injection path**: `.guardkit/patterns/` or `.claude/patterns/`?
3. **Pattern discovery by Player**: explicit read of directory listing first, or a manifest/index file generated at injection time?
4. **Prune policy**: keep aggressive, relax, or task-scope?
5. **Measurement**: what is "acceptable" token cost? Define the budget.
6. **Dotnet special-case**: the dotnet template's `templates/` subdirectory has paths with spaces and parentheses (e.g. `host / composition root/`, `contracts (anti-corruption layer)/`). Does this need normalization on injection or can the Player handle them as-is?

## References

- Review report: [.claude/reviews/TASK-REV-A5F8-review-report.md](../../../.claude/reviews/TASK-REV-A5F8-review-report.md)
- Historical context: [TASK-INST-010 (design_approved)](../../design_approved/TASK-INST-010-reconcile-init-paths.md) — the reconciliation that introduced `_SKIP_DIRS`
- Installer CLI: [guardkit/cli/init.py](../../../guardkit/cli/init.py)
- AutoBuild orchestrator: [guardkit/orchestrator/autobuild.py](../../../guardkit/orchestrator/autobuild.py)
- Template generator (producer): [installer/core/lib/template_generator/template_generator.py](../../../installer/core/lib/template_generator/template_generator.py)
- Parent feature: [README.md](README.md)
