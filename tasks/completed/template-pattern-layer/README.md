# Feature: Template Pattern Layer for AutoBuild

**Feature ID**: FEAT-1A5E
**Status**: Closed (superseded) — 2026-04-18
**Superseded by**: FEAT-TPL-PLAYER ([tasks/backlog/template-pattern-player-context/](../../backlog/template-pattern-player-context/), all 7 subtasks `in_review`)
**Parent review**: [TASK-REV-A5F8](../../in_review/TASK-REV-A5F8-analyse-d0c1-followups-scaffolding-and-exemplar.md)
**Review report**: [.claude/reviews/TASK-REV-A5F8-review-report.md](../../../.claude/reviews/TASK-REV-A5F8-review-report.md)
**Created**: 2026-04-11
**Priority**: High (for TASK-PAT-1A5E), Medium/Low for the rest

## Disposition summary

| Original task | Outcome |
|---------------|---------|
| TASK-PAT-1A5E | Closed — implemented under FEAT-TPL-PLAYER (TASK-TPL-001..004) |
| TASK-DOC-C3D7 | Completed by TASK-TPL-007 |
| TASK-REN-B9F2 | Closed (won't do) — Decision D6 in FEAT-TPL-PLAYER |

## Problem

GuardKit is becoming a Software Factory (Ideation → PO → Architect → GuardKit Factory → Build Agent). The AutoBuild Player is the Build Agent that clones repos and implements features autonomously.

Today, the Player enters every feature-implementation turn **with zero stack-specific pattern context**:

- `guardkit init` deliberately excludes scaffold `templates/*.template` files (via `_SKIP_DIRS` in [guardkit/cli/init.py:50-51](../../../guardkit/cli/init.py#L50) — TASK-INST-010, 2026-03-02).
- AutoBuild worktree setup further prunes `.claude/rules/` down to 4 essentials (autobuild, anti-stub, hash-based-ids, testing) to save ~11.5K tokens/turn, via [guardkit/orchestrator/autobuild.py:1172-1215](../../../guardkit/orchestrator/autobuild.py#L1172).
- So the Player has neither the pattern rules (`.claude/rules/patterns/*`) nor the canonical scaffold shapes (`templates/*.template`).

Meanwhile, `/template-create` has been actively producing `.template` scaffold files across **all 10** builtin templates — a pattern library nothing reads. TASK-REV-A5F8's historical analysis traces this to TASK-INST-010's "code scaffold generation is a separate concern" punt, which was never followed through.

This is an **architectural hole in the Software Factory pipeline**, not a documentation gap.

## Solution

Three coordinated tasks:

1. **TASK-PAT-1A5E (HIGH, `needs-feature-plan`)** — Wire template scaffold files into AutoBuild Player context. The architectural fix. Identify source template → resolve `templates/` subdirectory → select task-relevant patterns → inject into worktree at `.guardkit/patterns/` → update Player prompt to consult them → reconsider `AUTOBUILD_ESSENTIAL_RULES` prune list → measure. Scoped via `/feature-plan` because it touches the Player prompt, worktree setup, instrumentation, and token-budget trade-offs.

2. **TASK-DOC-C3D7 (MEDIUM, `depends_on: TASK-PAT-1A5E`)** — Document the two-layer template model (config layer + pattern layer) after PAT-1A5E is design-approved, so docs describe real wiring not future intent.

3. **TASK-REN-B9F2 (LOW, `depends_on: TASK-PAT-1A5E`)** — Optional rename of `templates/` → `patterns/` across all templates, `TemplateGenerator`, `TemplatePathResolver`, and agent `-ext.md` cross-references. Deferred; may be dropped if stub READMEs (from C3D7) prove sufficient.

## Scope note

E7A2 (Exemplar reference cleanup in dotnet agent docs) is **not** part of this feature — it is a standalone cosmetic fix at [tasks/backlog/TASK-DRF-E7A2-replace-exemplar-references-in-agent-docs.md](../TASK-DRF-E7A2-replace-exemplar-references-in-agent-docs.md) and is independent of this architectural work.

## Supersedes

- [TASK-DRF-F4B8](../TASK-DRF-F4B8-clarify-template-scaffolding-vs-config-layer.md) — closed as superseded by this feature. The original F4B8 proposed three options (document / extend init / delete files); TASK-REV-A5F8 rejected all three, identified the Player as the missing consumer, and filed this feature in their place.

## Execution strategy

| Wave | Tasks | Parallelism |
|------|-------|-------------|
| 1 | TASK-PAT-1A5E (scoping via `/feature-plan`) | Single task |
| 2 | TASK-DOC-C3D7, TASK-REN-B9F2 (if pursued) | Parallel, after Wave 1 design-approved |

See [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) for task ordering and entry points.
