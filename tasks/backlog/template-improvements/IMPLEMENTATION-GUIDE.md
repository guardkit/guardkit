# Implementation Guide: DeepAgents Template Improvements

## Architecture

```
langchain-deepagents/                    # Base template
  lib/
    json_extractor.py                    # TASK-TI-001: Robust 5-strategy extraction
    observability.py                     # TASK-TI-006: Token/stage/error logging
    factory_guards.py                    # TASK-TI-004: Tool allowlist assertions
    domain_validator.py                  # TASK-TI-005: Type-aware validation
    preflight.py                         # TASK-TI-008: --validate script
  prompts/
    templates.py                         # TASK-TI-002: CRITICAL section, tool limits
  docs/
    model-compatibility.md               # TASK-TI-007: Known quirks per model family
  scaffold/
    agent_factory.py.j2                  # Jinja2 template for agent factories

langchain-deepagents-weighted-evaluation/        # Adversarial template (extends base)
  extends: langchain-deepagents
  scaffold/
    orchestrator.py.j2                   # TASK-TI-010: Three-role wiring
    pipeline.py.j2                       # TASK-TI-011: normalize->extract->validate->write
    goal_schema.py.j2                    # TASK-TI-012: GOAL.md parser + evaluation schema
  prompts/
    coach_template.py                    # TASK-TI-013: Weighted criteria, scepticism tuning
    adversarial_base.py                  # Configurable intensity (full/light/solo)
  hooks/
    hitl.py                              # TASK-TI-015: Human-in-the-loop checkpoints
    sprint_contract.py                   # TASK-TI-016: Sprint negotiation pattern
  config/
    adversarial_config.py                # TASK-TI-014: Intensity settings
```

## Execution Strategy

### Wave 1: P0 — Top 3 Improvements (4-5 days)

These 3 tasks can run in parallel as they touch different files.

| Task | Files | Dependencies |
|------|-------|-------------|
| TASK-TI-001 (JsonExtractor) | `lib/json_extractor.py`, tests | None |
| TASK-TI-002 (Prompt template) | `prompts/templates.py`, tests | None |
| TASK-TI-003 (Gated writes) | `scaffold/orchestrator_pattern.py`, tests | None |

**Parallel execution recommended.** No file conflicts between tasks.

### Wave 2: P1 — Factory + Validators (3-4 days)

| Task | Files | Dependencies |
|------|-------|-------------|
| TASK-TI-004 (Factory guards) | `lib/factory_guards.py`, tests | None |
| TASK-TI-005 (Domain validator) | `lib/domain_validator.py`, tests | None |
| TASK-TI-006 (Observability) | `lib/observability.py`, tests | None |
| TASK-TI-007 (Model docs) | `docs/model-compatibility.md` | None |

**Parallel execution recommended.** All independent.

### Wave 3: P2 — Automation (1 day)

| Task | Files | Dependencies |
|------|-------|-------------|
| TASK-TI-008 (Pre-flight) | `lib/preflight.py`, tests | TASK-TI-004 (uses factory guards) |

**Sequential after Wave 2.**

### Wave 4: P3 — Adversarial Template (5-7 days)

| Task | Files | Dependencies |
|------|-------|-------------|
| TASK-TI-009 (Template scaffold) | Template structure, config | Wave 1 + Wave 2 |
| TASK-TI-010 (Three-role) | `scaffold/orchestrator.py.j2` | TASK-TI-009 |
| TASK-TI-011 (Pipeline) | `scaffold/pipeline.py.j2` | TASK-TI-001, TASK-TI-009 |
| TASK-TI-012 (Domain config) | `scaffold/goal_schema.py.j2` | TASK-TI-005, TASK-TI-009 |
| TASK-TI-013 (Coach prompt) | `prompts/coach_template.py` | TASK-TI-002, TASK-TI-009 |
| TASK-TI-014 (Intensity config) | `config/adversarial_config.py` | TASK-TI-009 |
| TASK-TI-015 (HITL hooks) | `hooks/hitl.py` | TASK-TI-010 |
| TASK-TI-016 (Sprint contract) | `hooks/sprint_contract.py` | TASK-TI-010, TASK-TI-015 |

**Sub-waves within Wave 4:**
- 4a: TASK-TI-009 (scaffold — must come first)
- 4b: TASK-TI-010, TI-011, TI-012, TI-013, TI-014 (parallel, all depend on scaffold)
- 4c: TASK-TI-015 (depends on TI-010)
- 4d: TASK-TI-016 (depends on TI-010 + TI-015)

## Key Design Decisions

### JsonExtractor (TI-001)
- Extract from existing `entrypoint/generation_loop.py` — proven code from 11 runs
- 5-strategy cascade: direct parse -> code-fence strip -> brace-match -> JSON repair -> reasoning_content fallback
- Brace matcher MUST be string-aware (TRF-025 lesson)
- JSON repair MUST handle literal newlines (TRF-030 lesson)

### Prompt Template (TI-002)
- `## CRITICAL — Response Format` section MUST be at end of prompt (recency bias)
- MUST use imperative language ("MUST", "NEVER") not polite ("please", "should")
- MUST include concrete JSON example (show-don't-tell)
- Tool usage section MUST specify explicit call limits

### Orchestrator-Gated Writes (TI-003)
- Player tool list: rag_retrieval ONLY (no write, no filesystem)
- Coach tool list: EMPTY (evaluation only, no filesystem)
- Orchestrator calls write_output programmatically post-acceptance
- Retry cap default: 3 per target

### Factory Guards (TI-004)
- `assert set(agent.tools) == expected_tools` at factory exit
- Must bypass `create_deep_agent()` for tool-restricted agents
- Inline warning: "create_deep_agent() unconditionally injects FilesystemMiddleware"

### Adversarial Template (TI-009+)
- Three roles match Anthropic terminology: Planner(=Orchestrator) + Generator(=Player) + Evaluator(=Coach)
- Configurable intensity: full (Coach evaluates every output), light (Coach spot-checks), solo (no Coach)
- GOAL.md schema includes evaluation criteria with weights and scoring rubrics
- Sprint contract: Orchestrator and Player negotiate scope before generation begins

## Testing Strategy

Each task includes:
- Unit tests for the component
- Integration test showing the component in a minimal pipeline
- Regression test derived from the specific TRF fix it prevents

## Documentation Strategy (Decision 4, Option C)

- **Inline**: Critical SDK pitfalls as docstrings and comments where developers hit them
  - Example: `# WARNING: create_deep_agent() injects FilesystemMiddleware — use create_agent() for tool-restricted agents`
- **Reference**: Comprehensive guide at `docs/model-compatibility.md` and template README
