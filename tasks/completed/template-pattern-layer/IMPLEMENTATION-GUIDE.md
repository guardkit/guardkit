# Implementation Guide: Template Pattern Layer

**Feature ID**: FEAT-1A5E
**Parent review**: [TASK-REV-A5F8](../../in_review/TASK-REV-A5F8-analyse-d0c1-followups-scaffolding-and-exemplar.md)

## Overview

Wire the pattern layer (`templates/*.template` files) into the AutoBuild Player so the Build Agent has stack-specific canonical shapes available when implementing feature tasks.

## Wave 1 — Architectural fix

### TASK-PAT-1A5E — Wire template patterns into AutoBuild Player context

**Priority**: High
**Entry point**: `/feature-plan "Wire template scaffold files into AutoBuild Player context as stack-pattern guidance during feature implementation"`

**Why a feature plan, not a single task**: The scope touches Player prompt, worktree setup, instrumentation, token budget, and the `AUTOBUILD_ESSENTIAL_RULES` prune constant. A single `/task-work` run won't cover the design decisions.

**Indicative scope** (from review report Section 1 "Primary recommendation"):

1. **Source-template identification** — Read `.claude/manifest.json` for the template `name`. Fall back to `.guardkit/template.yaml` or stack-heuristic detection from `pyproject.toml` / `package.json` / `.csproj`.
2. **Path resolution** — Locate `installer/core/templates/{name}/templates/` via the same `__file__`-relative resolver used by [guardkit/cli/init.py:460-510](../../../guardkit/cli/init.py#L460) (`apply_template`).
3. **Pattern selection** — v1: copy the whole `templates/` tree into the worktree. v2: task-scoped selection keyed on the task's mentioned layer (endpoint / repository / service / validator / test) so token cost only grows when the Player needs the patterns.
4. **Worktree injection** — Drop selected patterns into `.guardkit/patterns/` (or `.claude/patterns/`) inside the AutoBuild worktree at setup time. The injection must happen in [guardkit/orchestrator/autobuild.py](../../../guardkit/orchestrator/autobuild.py) worktree-setup path, after template copying and before Player invocation.
5. **Player prompt update** — Instruct the Player to consult `.guardkit/patterns/` before synthesizing new code. Likely an addition to `autobuild.md` or a new `player-patterns.md` rule that is added to the `AUTOBUILD_ESSENTIAL_RULES` frozenset.
6. **Rule-prune reconsideration** — [autobuild.py:210-215](../../../guardkit/orchestrator/autobuild.py#L210) currently aggressively prunes all of `.claude/rules/` except 4 essentials. Decide whether to:
   - (a) Keep aggressive prune, rely on `.guardkit/patterns/` as the pattern source, OR
   - (b) Relax prune to also keep `.claude/rules/patterns/` (stack-specific rule files that accompany `.template` files), OR
   - (c) Task-scoped rule selection (same logic as pattern selection above).
7. **Instrumentation** — Use the existing instrumentation pipeline (TASK-INST-*) to track whether pattern files are actually being read by the Player. If they are not being read, the token cost is wasted and the design needs revisiting.

**Acceptance criteria stub** (flesh out in the feature plan):

- [ ] Player invocations in dotnet-railway-fastendpoints-initialized projects receive relevant `.template` files in context
- [ ] Player invocations in fastapi-python-initialized projects receive relevant `.template` files in context
- [ ] Token budget impact measured and within an acceptable range (design goal: comparable to current pruned ~17 KB rules baseline, not the full 63 KB)
- [ ] Instrumentation confirms Player actually reads the injected patterns
- [ ] No regression in existing AutoBuild runs (worktree setup still idempotent, prune logic still works)

**Do NOT begin implementation until `/feature-plan` has run and a design checkpoint has been approved.**

## Wave 2 — Documentation and cleanup (after Wave 1 design-approved)

### TASK-DOC-C3D7 — Document the two-layer template model

**Priority**: Medium
**Depends on**: TASK-PAT-1A5E (design-approved state)

**Scope**: Update docs to describe the two-layer template model, reframed as:

- **Config layer** — consumed by `guardkit init`. Installs `.claude/`, `agents/`, `manifest.json`, `settings.json`, `CLAUDE.md`, `README.md`.
- **Pattern layer** — consumed by **AutoBuild Player** during feature implementation (via the wiring delivered by TASK-PAT-1A5E). Provides stack-specific canonical shapes the Player reads before synthesizing new code.

**Deliverables**:

- [ ] New section in [installer/core/templates/README.md](../../../installer/core/templates/README.md) (create the file if it does not exist)
- [ ] New guide at `docs/guides/template-layers-guide.md` (or update an existing template philosophy doc)
- [ ] `templates/README.md` stub added to all 10 builtin templates (one-paragraph explanation + pointer to TASK-PAT-1A5E's wiring)
- [ ] `/template-create` post-generation output updated to mention the two-layer model

**Why this is on hold**: If we ship documentation describing a pattern layer that is still not wired into the Player, we bake in a lie. Hold until TASK-PAT-1A5E's design checkpoint is approved so the docs describe real wiring.

### TASK-REN-B9F2 — Rename `templates/` → `patterns/` (deferred)

**Priority**: Low (deferred)
**Depends on**: TASK-PAT-1A5E (landed, not just design-approved)

**Scope**: Rename the `templates/` subdirectory convention to `patterns/` to make its purpose unambiguous post-wiring.

**Coordinated edits required**:

- All 10 builtin templates' `templates/` directories
- [installer/core/lib/template_generator/template_generator.py](../../../installer/core/lib/template_generator/template_generator.py) and `path_resolver.py`
- Agent `-ext.md` files that reference `templates/...` paths (at minimum 16 references in the dotnet template alone)
- Any new code from TASK-PAT-1A5E that resolves `templates/` paths
- Docs from TASK-DOC-C3D7 (if already written)

**Why deferred**: Pure renaming work with no functional change. Cheap to skip indefinitely if the `templates/README.md` stubs from C3D7 prove sufficient to disambiguate the name. Reconsider after TASK-PAT-1A5E lands and the new consumer is real.

## Ordering summary

```
TASK-PAT-1A5E (scope via /feature-plan → design-approved)
    │
    ├─→ TASK-DOC-C3D7 (start after design-approved)
    │
    └─→ TASK-REN-B9F2 (start after landed; may be skipped)
```

E7A2 is fully independent of this feature; see [TASK-DRF-E7A2-replace-exemplar-references-in-agent-docs.md](../TASK-DRF-E7A2-replace-exemplar-references-in-agent-docs.md).
