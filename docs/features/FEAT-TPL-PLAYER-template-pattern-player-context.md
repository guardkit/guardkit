# Feature Specification: Template Pattern Layer — AutoBuild Player Context

**Date:** 2026-04-11
**Author:** Rich
**Status:** Ready for Implementation
**Research Method:** Claude Desktop (review analysis) → GuardKit `/feature-plan`
**Target Repo:** `guardkit`
**Target Branch:** `feature/template-pattern-player-context`
**Feature ID:** FEAT-TPL-PLAYER *(to be assigned by `/feature-plan`)*

---

## 1. Problem Statement

Every non-trivial GuardKit template ships parameterised `.template` scaffold files that encode stack-specific code patterns (FastAPI routers, NATS handlers, .NET endpoints, React components, test fixtures). These files are produced by `/template-create` but have had no consumer since `agentic_init` was removed in TASK-INST-010 (2026-03-02). The Player in AutoBuild builds features without access to these patterns, relying instead on agent `-ext.md` prose descriptions and cross-references. This means the AI is told *about* the patterns in natural language rather than shown the actual parameterised code — a weaker signal that leads to inconsistent adherence to the template's intended architecture.

## 2. Decision Log

| # | Decision | Rationale | Alternatives Rejected | ADR Status |
|---|----------|-----------|----------------------|------------|
| D1 | Scaffold templates are loaded as Player context at **build time**, not init time | Init is config-layer (workspace setup). Build time is when the Player needs stack patterns to generate code. Separates concerns correctly. | Extend `guardkit init` to scaffold (Yeoman-scope, rejected in TASK-REV-A5F8) |  Accepted |
| D2 | Templates are loaded as **read-only reference context**, not executed as a templating engine | The Player reads the `.template` files to understand the pattern. Placeholder substitution (`{{EntityName}}`, etc.) is the Player's job as part of code generation — it already does this. No Jinja/cookiecutter engine needed. | Build a templating engine (over-engineered, the AI IS the engine) | Accepted |
| D3 | Template resolution uses the **source template name** recorded in `.guardkit/manifest.json` at init time | `guardkit init <template>` already writes the template name to the manifest. At build time, read the manifest → locate the template → load its `templates/` directory. | Detect stack from codebase (unreliable, template name is authoritative) | Accepted |
| D4 | Pattern files are injected into Player context via the **existing context loading pipeline**, not a new mechanism | AutoBuild already loads Graphiti context, task specs, agent docs, and codebase files. Adding template patterns as another context source keeps the architecture consistent. | Seed templates into Graphiti (lossy — Graphiti can't store code reliably, documented Feb/Mar 2026) | Accepted |
| D5 | Only `.template` files from subdirectories **relevant to the current task's domain tags** are loaded | Loading all template files for a 20-file .NET template would flood the context window. Use the task's domain tags and file paths to select relevant subdirectories. | Load all templates (context window waste), load none and rely on agent docs only (status quo, weak signal) | Accepted |
| D6 | The `templates/` directory in each builtin template is **not renamed** | TASK-REV-A5F8 considered renaming to `reference/` or `patterns/`. Now that these files have a proper consumer, `templates/` is accurate — they are template files. The documentation task (F4B8a) should describe them as "build-time pattern templates". | Rename to `reference/` (unnecessary now), rename to `patterns/` (churn for no functional gain) | Accepted |

**Warnings & Constraints:**
- Graphiti cannot store document content reliably (documented fidelity failures, Feb/Mar 2026) — do NOT attempt to seed `.template` files into Graphiti. Load them directly from disk.
- Context window budget: a single `.template` file is typically 50–150 lines. Loading 3–5 relevant files adds ~500 tokens. Loading all 20 dotnet templates would add ~3,000 tokens — too much. Domain-tag filtering (D5) is essential.
- The `manifest.json` must contain the `template` field. Verify this is written by `guardkit init` for all templates. If missing, the feature should gracefully degrade (log a warning, proceed without pattern context).

## 3. Scope

### In Scope

1. **Template pattern resolver** — given a project's `manifest.json`, resolve the source template and locate its `templates/` directory
2. **Domain-tag pattern selector** — given a task's domain tags and file paths, select the relevant `.template` files from the source template
3. **Player context injection** — integrate selected `.template` files into AutoBuild's Player context loading pipeline, clearly labelled as "stack pattern reference"
4. **Manifest validation** — verify the `template` field exists in `manifest.json`; graceful degradation if absent
5. **Documentation** — update AutoBuild docs and template docs to explain the pattern layer's role at build time

### Out of Scope

- **Extending `guardkit init`** — init remains config-layer only (D1)
- **Building a templating/scaffolding engine** — the AI Player is the engine (D2)
- **Renaming `templates/` directories** — not needed now that the consumer exists (D6)
- **Placeholder substitution logic** — the Player already generates code with correct names; showing it the pattern is sufficient
- **Template file CRUD** — `/template-create` already produces these files correctly; no changes to the producer
- **Agent `-ext.md` changes** — the cross-references in agent docs remain valid and complementary; they describe *why* the pattern exists, the `.template` file shows *what* it looks like
- **Coach-side template awareness** — the Coach validates against acceptance criteria, not template adherence. If template conformance matters, it should be an acceptance criterion, not a Coach capability.

## 4. User Stories

**US-1: Player receives stack patterns during feature build**
> As the Player agent during AutoBuild, when I'm implementing a feature in a project initialised from `fastapi-python`, I should receive the relevant `.template` files (e.g., `router.py.template`, `conftest.py.template`) as context so I can generate code that follows the template's established patterns.

**US-2: Pattern context is filtered by relevance**
> As the AutoBuild orchestrator, when loading Player context for a task tagged `endpoints, api`, I should load only the `api/` and `endpoints/` template subdirectories — not `testing/`, `db/`, or `infrastructure/`.

**US-3: Graceful degradation when no template is recorded**
> As a developer using GuardKit on a project that wasn't initialised from a template (or whose manifest is missing), AutoBuild should work exactly as it does today — no errors, no missing context warnings in the Player's output.

**US-4: Template pattern context is clearly labelled**
> As a human reviewing Player output, I should be able to see in the build logs which template patterns were loaded as context, so I can verify the Player had the right reference material.

## 5. Component Design

| Component | File Path | Purpose | New/Modified |
|-----------|-----------|---------|-------------|
| Template pattern resolver | `guardkit/autobuild/template_patterns.py` | Reads `manifest.json` → locates source template → returns path to `templates/` dir | New |
| Domain-tag pattern selector | `guardkit/autobuild/template_patterns.py` | Filters `.template` files by task domain tags and file path hints | New |
| Player context integration | `guardkit/autobuild/player_context.py` (or equivalent) | Adds selected `.template` content to Player's context payload | Modified |
| Manifest reader | `guardkit/config/manifest.py` (or equivalent) | Ensure `template` field is read; add accessor if not present | Modified |
| Tests | `tests/test_template_patterns.py` | Unit tests for resolver, selector, integration | New |

*Note: Exact file paths should be confirmed during `/feature-plan` against the current codebase structure. The above reflects the expected architecture.*

## 6. Data Flow

```
guardkit init fastapi-python
    │
    ▼
.guardkit/manifest.json  ←── records "template": "fastapi-python"
    │
    ... (development happens) ...
    │
/feature-build TASK-XXX
    │
    ▼
AutoBuild Orchestrator
    │
    ├── 1. Read .guardkit/manifest.json → template = "fastapi-python"
    │
    ├── 2. Resolve template path:
    │       ~/.agentecflow/templates/fastapi-python/templates/
    │       (or installer/core/templates/fastapi-python/templates/ in dev)
    │
    ├── 3. Read task domain tags: ["endpoints", "api", "crud"]
    │
    ├── 4. Select matching subdirectories:
    │       templates/api/router.py.template        ✓ matches "api"
    │       templates/crud/crud_base.py.template    ✓ matches "crud"
    │       templates/testing/conftest.py.template   ✗ no match
    │       templates/db/session.py.template         ✗ no match
    │
    ├── 5. Load selected .template file contents
    │
    ├── 6. Inject into Player context as:
    │       "## Stack Pattern Reference (from fastapi-python template)
    │        The following template files show the canonical patterns
    │        for this project's architecture. Use these as reference
    │        when generating code for this task.
    │
    │        ### api/router.py.template
    │        ```python
    │        [file contents]
    │        ```
    │
    │        ### crud/crud_base.py.template
    │        ```python
    │        [file contents]
    │        ```"
    │
    └── 7. Player generates code following the patterns
```

## 7. Domain-Tag to Template Directory Mapping

The selector needs a mapping from task domain tags to template subdirectory names. This mapping varies by template. Two approaches:

**Option A — Convention-based (recommended for v1):** Match domain tags directly against subdirectory names. Tag `api` matches `templates/api/`, tag `testing` matches `templates/testing/`, etc. Simple, works for most templates where subdirectory names are descriptive.

**Option B — Explicit mapping in template manifest:** Each template ships a `templates/mapping.yaml` that maps domain tags to subdirectories. More precise but requires updating all 10+ templates.

**Decision:** Start with Option A. If convention-based matching proves too coarse (loading irrelevant files or missing relevant ones), add Option B as a refinement in a follow-up.

**Fallback:** If no domain tags match any subdirectory, load the first 3 `.template` files alphabetically as a baseline. Better to have some pattern reference than none.

## 8. Implementation Tasks

*These are indicative. `/feature-plan` will decompose into properly-scoped TASK-XXX items.*

| # | Task | Complexity | Dependencies |
|---|------|-----------|-------------|
| T1 | Template pattern resolver — read manifest, locate template, return `templates/` path | Low | None |
| T2 | Domain-tag pattern selector — filter `.template` files by tag matching against subdirectory names | Medium | T1 |
| T3 | Player context injection — integrate selected template content into Player's context payload | Medium | T1, T2 |
| T4 | Logging — log which patterns were loaded, which were skipped, and why | Low | T3 |
| T5 | Tests — unit tests for resolver, selector; integration test for full pipeline | Medium | T1–T4 |
| T6 | Documentation — update template docs (F4B8a reframing), AutoBuild docs, CLAUDE.md positioning | Low | T1–T5 |

## 9. Acceptance Criteria (Feature-Level)

1. When AutoBuild runs `/feature-build` on a project initialised from a template with `.template` files, the Player receives relevant template patterns as context
2. Template pattern selection is filtered by task domain tags — not all templates are loaded
3. Projects without a template reference in `manifest.json` work exactly as they do today (no regression)
4. Build logs show which template patterns were loaded
5. The Player's generated code demonstrably follows template patterns more consistently than without pattern context (validated by manual review of at least 2 AutoBuild runs)

## 10. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Context window overflow from too many template files | Medium | High — degrades Player quality | Domain-tag filtering (D5), max 5 files cap, measure token impact |
| Template subdirectory names don't match domain tags | Medium | Low — falls back to alphabetical selection | Convention-based naming covers most cases; explicit mapping is the fallback |
| `manifest.json` doesn't contain `template` field for older projects | Low | Low — graceful degradation, logs warning | Check field existence; document how to add it manually |
| Player ignores template patterns in context | Low | Medium — no worse than status quo | Frame patterns clearly in context injection prompt; measure adherence |

## 11. Relationship to Other Work

| Work Item | Relationship |
|-----------|-------------|
| TASK-REV-A5F8 (this review) | This feature spec is the architectural response to the review's findings |
| TASK-DRF-F4B8a (documentation) | Still valid — but reframed as "build-time patterns" not "reference material" |
| TASK-DRF-E7A2 (Exemplar cleanup) | Independent, proceed as filed |
| TASK-DRF-F4B8b (rename decision) | Closed — no rename needed now that consumer exists (D6) |
| `guardkit-positioning-2026-q2.md` | This feature supports the repositioning of GuardKit as an AI software factory |
| DDD Southwest talk | Template-driven patterns are one of the five differentiators |
| dev-pipeline Build Agent | When the Build Agent invokes AutoBuild, pattern context flows automatically |

## 12. Graphiti Seeding

```bash
guardkit graphiti add-context docs/features/FEAT-TPL-PLAYER-template-pattern-player-context.md
guardkit graphiti verify --verbose
```

The following ADRs should be created and seeded after `/feature-plan`:

```bash
# After feature-plan creates tasks
guardkit graphiti seed-adrs  # picks up new ADRs from docs/adr/
```
