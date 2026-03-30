# Review Report: TASK-REV-4F71

## Executive Summary

**Scope**: Completeness and architectural review of the `langchain-deepagents` (base) and `langchain-deepagents-weighted-evaluation` (extension) template pair, including the `extends` mechanism and cross-template consistency.

**Architecture Score: 82/100**

| Dimension | Score | Notes |
|-----------|-------|-------|
| SOLID Compliance | 8/10 | Clean separation of concerns; SRP well-enforced across roles |
| DRY Adherence | 7/10 | Extension avoids duplicating base; minor overlap in settings.json |
| YAGNI Compliance | 8/10 | Templates encode proven patterns from 11 production runs |
| Composition Design | 9/10 | Extends mechanism is clean file-overlay with manifest merging |
| Completeness | 8/10 | All core features present; minor gaps in docs and integration |
| Consistency | 8/10 | Cross-template alignment is strong; a few inconsistencies noted |

**Summary**: Both templates are substantially complete. All Wave 1-3 tasks, Wave 3.5 SDK alignment fixes, and Wave 4 adversarial scaffold tasks are completed. The `extends` mechanism (TASK-TI-027) is fully implemented with 127 passing tests. The template pair is ready for integration testing against a real project. Eight findings identified, three requiring action.

---

## Review Details

- **Mode**: Architectural Review
- **Depth**: Standard
- **Task**: TASK-REV-4F71
- **Parent Review**: TASK-REV-32D2 (SDK-validated design review, Revision 3)
- **Feature**: FEAT-TI (Template Improvements)

---

## Section 1: Base Template Completeness

### Assessment: STRONG (90%)

All Wave 1-3 components are present and verified:

| Task | Component | Status | Verified |
|------|-----------|--------|----------|
| TI-001 | JsonExtractor (5-strategy cascade) | COMPLETED | lib/json_extractor.py exists, tested |
| TI-002 | Prompt engineering template | COMPLETED | templates/other/prompts/ present |
| TI-003 | Orchestrator-gated writes | COMPLETED | templates/other/scaffold/orchestrator_pattern.py.template |
| TI-004 | Factory guards (tool allowlisting) | COMPLETED | lib/factory_guards.py exists, tested |
| TI-005 | Domain validator (type-aware) | COMPLETED | lib/domain_validator.py exists, tested |
| TI-006 | Observability scaffold | COMPLETED | lib/observability.py exists, tested |
| TI-007 | Model compatibility docs | COMPLETED | docs/reference/model-compatibility.md |
| TI-008 | Pre-flight validation | COMPLETED | lib/preflight.py exists, tested |

**Wave 3.5 SDK alignment fixes** (all COMPLETED):

| Task | Fix | Status |
|------|-----|--------|
| TI-019 | Fix player.py.template (create_agent) | COMPLETED |
| TI-020 | Fix factory_guards.py memory parameter | COMPLETED |
| TI-021 | Fix coach.py.template (create_agent) | COMPLETED |
| TI-022 | Fix agent.py.template entrypoint | COMPLETED |
| TI-023 | Document ainvoke() contract | COMPLETED |
| TI-024 | Populate pattern rules | COMPLETED |

**New Wave 4 libraries added to base** (3 files, all present):

| File | Purpose | Lines | Exports |
|------|---------|-------|---------|
| lib/content_pipeline.py | Canonical pipeline: normalize -> extract -> validate -> write | 359 | ContentPipeline, PipelineResult, StageResult |
| lib/checkpoint_hooks.py | HITL checkpoint hooks (CLI, webhook, auto-approve) | 397 | CheckpointHook, CLICheckpointHook, WebhookCheckpointHook, AutoApproveHook, create_checkpoint_hook |
| lib/sprint_contract.py | Sprint contract negotiation and escalation | 480 | SprintNegotiator, SprintContract, FeasibilityResult, NegotiationResult, EscalationResult |

**lib/__init__.py**: Exports 59 public items, all documented. All 8 modules are properly registered.

**Pattern rules** (5 files, all populated):
- adversarial-cooperation.md
- domain-driven-configuration.md
- factory.md
- memory-injection.md
- tool-delegation.md

**Guidance files** (7 specialist agents): All present and populated.

**CLAUDE.md**: Clearly describes binary evaluation model, when to use base vs extension, 8 included libraries, and cross-domain evidence.

**Standalone operation**: The base template works independently with no references that require the extension. Confirmed standalone.

---

## Section 2: Extension Template Completeness

### Assessment: STRONG (85%)

All Wave 4 tasks (TI-009 through TI-016) are completed and files are present:

| Task | Component | File | Status |
|------|-----------|------|--------|
| TI-009 | Adversarial template scaffold | scaffold/*.j2 | COMPLETED |
| TI-010 | Three-role orchestrator | scaffold/orchestrator.py.j2 | COMPLETED |
| TI-011 | Canonical pipeline | scaffold/pipeline.py.j2 | COMPLETED |
| TI-012 | Domain configuration schema | scaffold/goal_schema.py.j2 | COMPLETED |
| TI-013 | Coach evaluator prompt | prompts/coach_template.py | COMPLETED |
| TI-014 | Configurable adversarial intensity | config/adversarial_config.py | COMPLETED |
| TI-015 | HITL checkpoint hooks | hooks/hitl.py | COMPLETED |
| TI-016 | Sprint contract negotiation | hooks/sprint_contract.py | COMPLETED |
| TI-025 | Register template in installer | init-project.sh | COMPLETED |
| TI-026 | Document template architecture | CLAUDE.md | COMPLETED |
| TI-027 | Installer extends mechanism | guardkit/cli/init.py | COMPLETED |

**manifest.json**: Contains `"extends": "langchain-deepagents"` and `"requires": ["template:langchain-deepagents"]`. Correctly declares additional placeholders (DomainName, AdversarialIntensity, AcceptanceThreshold, MaxRetries).

**CLAUDE.md**: Clearly describes weighted evaluation, when to use, inherited vs added components, feature comparison table, and intensity modes.

**Test coverage**: 4 test files (test_scaffold.py, test_goal_schema.py, test_coach_template.py, test_orchestrator.py) with 172+ tests targeting >=85% coverage.

**WeightedVerdict design**: Uses dataclass (not Pydantic), consistent with the base CoachVerdict pattern. Includes `composite_score`, `criterion_scores`, and `from_json()` classmethod.

**GOAL.md quality contract**: Jinja2 template (goal.md.j2) generates domain-specific GOAL.md files with evaluation criteria, weights, and quality thresholds.

---

## Section 3: Extends Mechanism

### Assessment: STRONG (92%)

TASK-TI-027 is **fully implemented and tested** (127 tests, 65% coverage).

**Design**:
- **File overlay model**: Base template files applied first, extension files overlaid on top. Extension files overwrite base files at the same path.
- **Manifest merging**: `_merge_manifests()` — scalars (extension wins), dicts (shallow merge), lists (concatenate + deduplicate).
- **Chain resolution**: `_resolve_extends_chain()` walks the `extends` field, builds base-first order, with circular reference protection.
- **Overwritable set**: Tracks files from prior templates; extension can overwrite base files, but pre-existing user files are never clobbered.
- **Backward compatibility**: Single-template chains work identically to pre-extends code.
- **CLI flag**: `--base-only` installs only the base template without extension.

**Developer Experience**:
- `guardkit init langchain-deepagents-weighted-evaluation` automatically resolves and installs the base first, then overlays the extension.
- Users don't need to know about the extends chain — it's transparent.

**Pattern rule composition**: Extension files at the same path overwrite base files. Since the extension doesn't include `.claude/rules/patterns/` files, the base's 5 pattern files are inherited unchanged. If the extension later adds pattern files, they would be added alongside (new paths) or replace (same paths) base patterns.

**Risk Assessment**: LOW. The overlay model is simple and predictable. The only risk is if the base template adds a file at a path that conflicts with an extension file — but this is handled by the overwrite mechanism and is a feature, not a bug.

---

## Section 4: Cross-Template Consistency

### Assessment: GOOD (80%)

**Consistent**:
- Both manifest.json files share the same `schema_version`, `language`, and `frameworks` (identical versions).
- Both use the same base placeholders (ProjectName, Namespace, Author); extension adds 4 more.
- Both CLAUDE.md files cross-reference each other with clear "when to use" guidance.
- Installer script lists both with correct descriptions.
- No circular dependencies.

**Inconsistencies** (see Findings F1, F2):

1. **settings.json duplication**: The extension has its own `settings.json` that is nearly identical to the base, with only the addition of a "Hooks" layer. This should inherit from the base and only define the delta.

2. **Pattern count divergence**: Base manifest declares 5 patterns; extension declares 8 (adds "Weighted Evaluation", "HITL Checkpoints", "Sprint Contracts"). However, HITL Checkpoints and Sprint Contracts are implemented in the *base* template's `lib/` (checkpoint_hooks.py, sprint_contract.py), not only in the extension. The extension's `hooks/` directory provides *higher-level integration hooks* that build on the base libraries. This is architecturally correct but the manifest pattern attribution is misleading — it suggests these are extension-only features.

---

## Section 5: Gap Analysis

### Assessment: GOOD (78%)

**Conversation Starter Spec Coverage**:

| Spec Feature (numbered 1-15) | Task | Status | Notes |
|------|------|--------|-------|
| 1. JsonExtractor | TI-001 | COVERED | 5-strategy cascade in base |
| 2. Observability scaffold | TI-006 | COVERED | Token/stage/error logging in base |
| 3. Agent factory + tool allowlisting | TI-004 | COVERED | factory_guards.py in base |
| 4. Model compatibility docs | TI-007 | COVERED | docs/reference/model-compatibility.md |
| 5. Pre-flight validation | TI-008 | COVERED | lib/preflight.py |
| 6. Three-role scaffold | TI-010 | COVERED | scaffold/orchestrator.py.j2 |
| 7. Orchestrator-gated writes | TI-003 | COVERED | orchestrator_pattern.py.template |
| 8. Prompt engineering template | TI-002 + TI-013 | COVERED | Base prompts + weighted coach |
| 9. CoachVerdict schema | TI-012 | COVERED | WeightedVerdict in pipeline.py.j2 |
| 10. GOAL.md quality contract | TI-012 | COVERED | goal_schema.py.j2 + goal.md.j2 |
| 11. Canonical pipeline | TI-011 | COVERED | content_pipeline.py + pipeline.py.j2 |
| 12. Type-aware domain validator | TI-005 | COVERED | domain_validator.py |
| 13. Configurable intensity | TI-014 | COVERED | adversarial_config.py |
| 14. HITL checkpoint hooks | TI-015 | COVERED | hooks/hitl.py + lib/checkpoint_hooks.py |
| 15. Sprint contract negotiation | TI-016 | COVERED | hooks/sprint_contract.py + lib/sprint_contract.py |

**All 15 conversation starter features are covered by completed tasks.**

**Gaps Identified** (see Findings F3-F5):

1. **Missing NATS/messaging integration**: The conversation starter spec mentions checkpoints that "publish to NATS (if configured) or block for console input." The base template's `WebhookCheckpointHook` provides webhook-based integration, but there's no explicit NATS adapter. This is acceptable — the webhook pattern is more general — but should be documented as a design decision.

2. **Missing `first_run.sh` / `FIRST_RUN_CHECKLIST.md`**: The spec includes guided first-run setup scripts and a checklist. Neither template includes these. This is a gap in developer onboarding, though not architecturally critical.

3. **Missing RAG tool template**: The spec includes `rag_retrieval.py` (ChromaDB). The base template has a generic `search_data.py.template` tool, but no ChromaDB-specific RAG implementation. The generic approach is correct for a template — it avoids coupling to a specific vector store — but the spec's ChromaDB reference should be documented as a "possible implementation."

4. **Conversation starter uses Pydantic CoachVerdict; templates use dataclass**: The spec describes `CoachVerdict(BaseModel)` with Pydantic. Both templates use dataclasses instead. This was a deliberate decision documented in TASK-REV-32D2 (dataclass is simpler for internal state; Pydantic reserved for external data). Correctly resolved.

---

## Findings

### F1: settings.json Duplication (LOW)

**Severity**: Low
**Location**: Extension `settings.json` vs base `settings.json`

The extension template includes a full `settings.json` that duplicates nearly all base content, adding only the "Hooks" layer mapping. With the extends mechanism now supporting file overlay, this duplication is unnecessary — the extension should only define what differs from the base.

**Impact**: Maintenance burden. When base naming conventions change, the extension must be updated manually.

**Recommendation**: Remove `settings.json` from the extension template. Either inherit it from the base (current overlay behaviour already does this), or create a minimal override that only adds the "Hooks" layer. The extends manifest merge handles list concatenation for `layers`.

### F2: Pattern Attribution in Manifests (LOW)

**Severity**: Low
**Location**: Extension `manifest.json` patterns array

The extension manifest lists "HITL Checkpoints" and "Sprint Contracts" as extension patterns, but the underlying libraries (`lib/checkpoint_hooks.py`, `lib/sprint_contract.py`) live in the *base* template. The extension provides higher-level integration hooks in `hooks/`, which is architecturally correct.

**Impact**: Could confuse developers about which template provides which capability.

**Recommendation**: Clarify in both CLAUDE.md files: base provides the *library* implementations; extension provides the *integration hooks* that wire them into the weighted evaluation pipeline. Consider adding the patterns to the base manifest as well, since the base now includes these libraries.

### F3: Missing Developer Onboarding Assets (MEDIUM)

**Severity**: Medium
**Location**: Neither template includes first-run setup

The conversation starter spec includes `first_run.sh`, `FIRST_RUN_CHECKLIST.md`, and `SDK_PITFALLS.md`. These onboarding assets would significantly reduce time-to-first-run for new projects using the template.

**Impact**: New users of the template need to discover SDK constraints (ainvoke contract, create_agent vs create_deep_agent) by reading pattern rules, which are comprehensive but not structured as a getting-started guide.

**Recommendation**: Create a `docs/GETTING_STARTED.md` in the base template that condenses the pattern rules into a step-by-step first-run guide. Reference the existing model-compatibility.md and pattern rules. This is a documentation task, not an architectural change.

### F4: Extension Tests Bundled Inside Template (LOW)

**Severity**: Low
**Location**: `langchain-deepagents-weighted-evaluation/tests/`

The extension template bundles 4 test files inside the template directory itself. These tests validate the template's scaffold code (Jinja2 templates, config module). They are *template development tests*, not *user project tests*.

**Impact**: When a user installs the template, these test files would be copied into their project via the extends overlay mechanism, potentially confusing the user's test suite.

**Recommendation**: Verify that the overlay mechanism excludes `tests/` from installation, OR move these tests to the GuardKit repo's `tests/templates/` directory alongside the existing base template tests.

### F5: Conversation Starter File Structure Divergence (INFO)

**Severity**: Informational
**Location**: Conversation starter spec vs actual template structure

The conversation starter spec proposes a detailed file structure with directories like `extraction/`, `validation/`, `orchestrator/`, `config/`, `observability/`, `domain_config/`. The actual templates use a flatter structure: `lib/` for the base (8 modules in one directory), and `config/`, `hooks/`, `prompts/`, `scaffold/` for the extension.

**Impact**: None functionally. The flatter structure is arguably better for template consumption — users don't need to navigate a deep directory tree. The patterns from the spec are fully encoded, just organized differently.

**Assessment**: Correct design decision. The spec was a conversation starter, not a binding contract. The actual structure prioritizes template usability.

### F6: Jinja2 Templates vs .template Files (INFO)

**Severity**: Informational
**Location**: Base uses `.template` extension; extension uses `.j2` extension

The base template uses `.py.template` files with `{{placeholder}}` syntax. The extension uses `.py.j2` files with Jinja2 syntax. Both are valid approaches, but using different templating conventions in the same extends chain could cause confusion.

**Impact**: Low. The extends mechanism treats them as regular files — both get copied. But developers may be confused about which templating engine to use when customizing.

**Recommendation**: Document the distinction in the extension CLAUDE.md: base uses simple placeholder substitution; extension uses Jinja2 for more complex scaffolding (loops, conditionals for criteria/weights). This is already partially documented but could be more explicit.

### F7: Extension SKILL.md Absent from Base (INFO)

**Severity**: Informational
**Location**: Extension has `SKILL.md`; base does not

The extension includes a `SKILL.md` file defining template variables and default evaluation criteria. The base template has no equivalent — its placeholder definitions are only in `manifest.json`.

**Impact**: Inconsistency in how template variables are documented between the two templates.

**Recommendation**: Consider adding a `SKILL.md` to the base template for parity, or document that `manifest.json` is the canonical source for base template configuration and `SKILL.md` is an extension-only pattern for richer variable definitions.

### F8: Base Template lib/ Modules Not Python-Installable (INFO)

**Severity**: Informational
**Location**: `installer/core/templates/langchain-deepagents/lib/`

The base template's `lib/` directory contains 8 Python modules that are designed to be copied into user projects. These are well-structured and tested, but they're template-embedded code, not a pip-installable package.

**Impact**: When upstream fixes are made to these libraries (e.g., a JsonExtractor improvement), existing projects won't receive the update unless they re-run the template.

**Assessment**: This is a known trade-off of the template approach. Templates are point-in-time copies by design. No action needed now, but worth considering a `guardkit update` command in the future to re-apply base template updates to existing projects.

---

## Recommendations

### Keep (Working Well)

1. **Three-role separation** (Orchestrator/Player/Coach) is clean and well-enforced
2. **Extends mechanism** is elegantly simple — file overlay with manifest merging
3. **Pattern rules** are comprehensive and battle-tested (11 production runs)
4. **Base/extension split** is correct — binary vs weighted evaluation is the right dividing line
5. **WeightedVerdict as dataclass** — correct decision over Pydantic for internal state
6. **59-item public API in lib/__init__.py** — well-organized and documented

### Refactor (Minor Improvements)

1. **F1**: Remove duplicated `settings.json` from extension (let base inheritance handle it)
2. **F2**: Align pattern attribution in manifests with actual library locations
3. **F6**: Document templating convention difference (`.template` vs `.j2`)

### Create (New Work)

1. **F3**: Create `docs/GETTING_STARTED.md` for developer onboarding (new task)
2. **F4**: Verify extension `tests/` are excluded from user installation, or relocate them

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Extension tests installed into user projects | Medium | Low | Verify overlay exclusion rules |
| Template drift (base updates don't reach installed projects) | Certain | Low | Document as expected; future `guardkit update` |
| Developer confusion about `.template` vs `.j2` | Low | Low | Document in CLAUDE.md |
| Settings.json divergence over time | Medium | Low | Remove duplicate from extension |

**Overall Risk**: LOW. The architecture is sound, the extends mechanism is well-tested, and all conversation starter features are covered. The findings are housekeeping items, not architectural concerns.

---

## Appendix A: Task Completion Status

### All Waves Complete

| Wave | Tasks | Status |
|------|-------|--------|
| Wave 1 (P0) | TI-001, TI-002, TI-003 | ALL COMPLETED |
| Wave 2 (P1) | TI-004, TI-005, TI-006, TI-007 | ALL COMPLETED |
| Wave 3 (P2) | TI-008 | COMPLETED |
| Wave 3.5 (P0-FIX) | TI-019, TI-020, TI-021, TI-022, TI-023, TI-024 | ALL COMPLETED |
| Wave 4 (P3) | TI-009 through TI-016 | ALL COMPLETED |
| Supporting | TI-025, TI-026, TI-027 | ALL COMPLETED |

**Total**: 24 tasks completed out of 24.

### Appendix B: File Counts

| Template | Python Modules | Pattern Rules | Guidance | Templates | Tests |
|----------|---------------|---------------|----------|-----------|-------|
| Base | 8 (lib/) | 5 | 7 | 12 | 18 files |
| Extension | 5 (config/, prompts/, hooks/) | 0 (inherits base) | 0 | 4 (scaffold/, templates/) | 4 files |

---

*Review completed: 2026-03-30*
*Reviewer: architectural-reviewer*
*Architecture Score: 82/100*
