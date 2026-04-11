---
id: TASK-REV-B3F7
title: "Plan: Template Pattern Layer — AutoBuild Player Context"
task_type: review
status: review_complete
priority: high
created: 2026-04-11
parent_spec: docs/features/FEAT-TPL-PLAYER-template-pattern-player-context.md
feature_id: FEAT-TPL-PLAYER
mode: decision
depth: standard
clarification:
  context_a:
    focus: task_decomposition_only
    tradeoff: quality_correctness
    concern: integration_with_autobuild_pipeline
---

# Review: Template Pattern Layer — AutoBuild Player Context

**Spec:** [FEAT-TPL-PLAYER](../../docs/features/FEAT-TPL-PLAYER-template-pattern-player-context.md)

The spec is detailed and its 6 decisions (D1–D6) are accepted. This review validates the spec against the **actual current codebase** (per Context A concern: integration with AutoBuild pipeline) and decomposes implementation into properly-scoped tasks.

---

## Codebase Verification Findings

Three material discrepancies between the spec and the actual codebase:

### F1 — Manifest field is NOT `template`, it is `name` (from raw-copy of template manifest)

**Spec D3 claim:** "`guardkit init <template>` already writes the template name to the manifest" as a `template` field.

**Reality:** [`guardkit/cli/init.py:650-668`](guardkit/cli/init.py#L650-L668) `_copy_manifest()` raw-copies the template's own `manifest.json` (which contains `name: "fastapi-python"`, `schema_version`, `frameworks`, etc.) to `.claude/manifest.json`. There is no separate `template:` field written. The source template name is discoverable as the `name` field inside the copied manifest.

**Additional subtlety:** When a template `extends` another, `_merge_manifests` ([init.py:885](guardkit/cli/init.py#L885)) writes a merged manifest — the `name` field then reflects the most-derived template, which is the correct source of patterns. No change needed there.

**Impact:** The resolver reads `name`, not `template`. Graceful degradation triggers when `.claude/manifest.json` is missing or its `name` doesn't resolve to a template directory.

### F2 — Manifest lives at `.claude/manifest.json`, not `.guardkit/manifest.json`

Spec §6 (data flow) shows `.guardkit/manifest.json`. Actual path is `.claude/manifest.json` per [init.py:667,1011,1130](guardkit/cli/init.py#L667).

### F3 — Player context is built by two collaborating modules, not a single `player_context.py`

Spec §5 (Component Design) names `guardkit/autobuild/player_context.py`. Actual layout:

| Role | Actual file | Notes |
|---|---|---|
| Player context loader | [`guardkit/knowledge/autobuild_context_loader.py`](guardkit/knowledge/autobuild_context_loader.py) — `AutoBuildContextLoader.get_player_context()` | Returns `AutoBuildContextResult` with `prompt_text` |
| Player prompt builder | [`guardkit/orchestrator/agent_invoker.py:1594`](guardkit/orchestrator/agent_invoker.py#L1594) — `_build_player_prompt()` | Consumes context result, formats final Player prompt |
| Task characteristics | [`guardkit/knowledge/task_analyzer.py:88`](guardkit/knowledge/task_analyzer.py#L88) — `TaskCharacteristics` | Exposes `tech_stack: str` — **no `domain_tags` field exists today** |

**Consequence for D5 (domain-tag filtering):** The spec assumes tasks carry domain tags. Today the Player only has `tech_stack` plus the task's file-path hints. The selector must therefore use:
1. `TaskCharacteristics.tech_stack` (primary signal — matches template `language`/`frameworks`)
2. File-path hints from the task's modified-file list (e.g. a task touching `app/api/users.py` matches `templates/api/`)
3. Fallback to alphabetical first-3 if nothing matches (already in spec §7)

This is still convention-based per D5; we simply source the "tag-like" signal from what already exists rather than adding a new `domain_tags` field. **No schema change required.**

### F4 — Template resolver already exists and is reusable

[`_resolve_template_source_dir()`](guardkit/cli/init.py#L485) already handles `installer/core/templates/<name>/` + `~/.guardkit/templates/<name>/` lookup. The new feature should **import and reuse** it rather than duplicate — but since it currently lives under `cli/`, the proper move is to extract it into a neutral module (e.g. `guardkit/templates/resolver.py`) that both `cli/init.py` and the new AutoBuild pattern loader can import. This is a small, zero-risk refactor.

### F5 — `.template` files exist as expected

Confirmed via glob: `installer/core/templates/fastapi-python/templates/` contains `api/`, `core/`, `crud/`, `db/`, `dependencies/`, `models/`, `schemas/`, `testing/`, `config/` subdirs with `.template` files. Matches spec assumption. The dotnet template follows the same convention.

---

## Technical Options Analysis

### Option 1 — Direct integration into `AutoBuildContextLoader` (Recommended)

**Complexity:** 5/10. **Effort:** 4–6 hours.

Add a new `TemplatePatternLoader` module under `guardkit/knowledge/` that:
- Reads `.claude/manifest.json` → extracts `name`
- Resolves template dir via refactored `templates/resolver.py`
- Selects relevant `.template` files using `tech_stack` + file-path hints
- Returns a `TemplatePatternContext` dataclass

`AutoBuildContextLoader.get_player_context()` calls it and appends the formatted pattern block to `AutoBuildContextResult.prompt_text`.

**Pros:**
- Minimal surface change — single call site
- Leverages existing context pipeline (per D4)
- No change to `TaskCharacteristics` schema
- Reuses existing resolver

**Cons:**
- `knowledge/` module gets one more responsibility (acceptable — it already owns context loading)

### Option 2 — New `guardkit/autobuild/` package mirroring the spec

**Complexity:** 6/10. **Effort:** 6–8 hours.

Create `guardkit/autobuild/template_patterns.py` per spec §5 and wire it in from the context loader.

**Pros:** Matches spec literally; clean package boundary.
**Cons:** There is no existing `guardkit/autobuild/` package (all AutoBuild code lives in `orchestrator/` + `knowledge/`). Creating one adds an inconsistent layout for a single-module feature. Rejected — would fragment the codebase.

### Option 3 — Inject via `_build_player_prompt()` in `agent_invoker.py`

**Complexity:** 4/10. **Effort:** 3–4 hours.

Bypass the context loader and inject pattern text directly into the prompt builder.

**Pros:** Simplest diff.
**Cons:** Violates D4 (use existing context pipeline). Template patterns would not flow through `AutoBuildContextResult`, making them invisible to logging/telemetry. Rejected.

---

## ✅ Recommended Approach: Option 1

Adjusted to reflect codebase reality:

1. **Refactor** `_resolve_template_source_dir()` out of `cli/init.py` into a shared `guardkit/templates/resolver.py` (zero-behaviour change).
2. **Create** `guardkit/knowledge/template_pattern_loader.py` — new module with:
   - `load_template_patterns(task_characteristics, manifest_path) -> TemplatePatternContext`
   - Manifest reading with graceful degradation
   - Domain-hint selector (tech_stack + file-path matching against template subdirs)
   - Token budget cap (max 5 files, ~3000 tokens)
3. **Wire** into [`AutoBuildContextLoader.get_player_context()`](guardkit/knowledge/autobuild_context_loader.py) — append pattern block to `prompt_text`.
4. **Log** selected/skipped patterns to existing AutoBuild logger.
5. **Tests** under `tests/unit/test_template_pattern_loader.py` + integration test extending `tests/unit/test_autobuild_thread_loaders.py`.
6. **Docs** — update F4B8a (reframe `templates/` directories as "build-time pattern templates") and AutoBuild guide.

**Risk level:** Low. All integration points exist; only one schema-free extension to `AutoBuildContextResult`.

---

## Task Decomposition

| # | Task | Complexity | task_type | Depends on |
|---|------|-----------|-----------|-----------|
| T1 | Extract template resolver from `cli/init.py` into `guardkit/templates/resolver.py` (shared module, identical behaviour) | 3 | refactor | — |
| T2 | Create `TemplatePatternContext` dataclass + `load_template_patterns()` core module under `guardkit/knowledge/template_pattern_loader.py` | 5 | feature | T1 |
| T3 | Implement domain-hint selector (tech_stack + file-path → template subdir matching, alphabetical fallback, token cap) | 5 | feature | T2 |
| T4 | Wire pattern loader into `AutoBuildContextLoader.get_player_context()` + append block to `prompt_text`; add logging | 4 | feature | T3 |
| T5 | Unit tests: resolver, selector, manifest graceful-degradation, token-cap | 4 | testing | T2, T3 |
| T6 | Integration test: full AutoBuild context loading with fastapi-python fixture; seam test for T4 contract | 5 | testing | T4 |
| T7 | Documentation: update F4B8a docs + AutoBuild guide + CLAUDE.md template section | 3 | documentation | T4 |

**Execution waves:**
- Wave 1: T1 (foundation refactor)
- Wave 2: T2 (loader core) — waits on T1
- Wave 3: T3, T5 (selector + unit tests, parallel) — T5 can TDD T3
- Wave 4: T4 (wiring) — waits on T3
- Wave 5: T6, T7 (integration test + docs, parallel)

**Integration contracts identified:**
- **Contract `TemplatePatternContext`** — Producer: T2; Consumers: T3 (selector populates it), T4 (wiring reads `prompt_block` field). Seam test required on T6.
- **Contract `.claude/manifest.json` name field** — Producer: existing `guardkit init`; Consumer: T2. Format: JSON object with top-level `name: str`. Graceful degradation if absent/unreadable.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Context window overflow from pattern flood | Medium | High | Hard cap at 5 files / ~3000 tokens in T3; log over-budget skips |
| `tech_stack` + file-paths too coarse for selection | Medium | Low | Fall back to alphabetical first-3 (spec §7); revisit with explicit mapping if users complain |
| `.claude/manifest.json` missing `name` for non-template projects | Low | Low | Graceful degradation path validated in T5 unit tests |
| Resolver refactor breaks `cli/init.py` | Low | Medium | T1 is a pure extract-and-import; existing init tests catch regressions |

---

## Acceptance Criteria (Feature-Level)

1. When AutoBuild runs on a project with `.claude/manifest.json` containing a resolvable template `name`, the Player receives relevant `.template` files in its context payload.
2. Pattern selection is filtered by `tech_stack` and task file-path hints, capped at 5 files / ~3000 tokens.
3. Projects with missing/unresolvable manifest `name` run identically to today (no errors, no warnings leaked to Player output).
4. AutoBuild logs list which patterns were loaded, which were skipped, and why.
5. Unit + integration tests cover resolver, selector, graceful degradation, and the wiring contract.
6. Manual validation: at least 2 AutoBuild runs on a templated project demonstrate pattern adherence in Player output (recorded in the feature completion notes).
7. All modified files pass project-configured lint/format checks with zero errors.

---

## Decision Checkpoint

Review complete. The spec is sound; three file-path/field-name adjustments are required (F1–F3 above) but do not change the architecture. Task decomposition produces 7 tasks across 5 waves.

**Options:**
- **[A]ccept** — save findings, defer implementation
- **[R]evise** — request deeper analysis or re-examine decisions
- **[I]mplement** — create feature structure with 7 subtasks and FEAT YAML
- **[C]ancel** — discard
