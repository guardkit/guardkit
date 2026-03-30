# Weighted Evaluation — Adversarial Cooperation Template

## Overview

Extended adversarial cooperation template that adds **weighted multi-criteria evaluation**
to the base Player-Coach pattern. Where the base template uses binary accept/reject verdicts,
this template scores content against weighted criteria and computes a composite score.

**Extends**: `langchain-deepagents`

Inherits from the base template:
- `lib/factory_guards.py` — Tool allowlisting, `assert_tool_inventory()`, `assert_no_system_messages()`
- `lib/json_extractor.py` — Robust JSON extraction from LLM output
- `lib/domain_validator.py` — Type-aware domain validation with range notation
- `lib/preflight.py` — Pre-flight checks for agent configuration
- `lib/observability.py` — Structured logging and tracing

## Template Variables

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `project_name` | string | yes | — | Project identifier (snake_case) |
| `domain_name` | string | yes | — | Domain for GOAL.md generation |
| `adversarial_intensity` | enum | no | `full` | Intensity: `full` \| `light` \| `solo` |
| `roles` | list | no | `[orchestrator, player, coach]` | Role definitions |
| `evaluation_criteria` | list | no | See below | Weighted criteria for Coach |
| `max_retries` | int | no | `3` | Maximum Player revision attempts |
| `acceptance_threshold` | float | no | `0.7` | Minimum weighted score for acceptance |

### Default Evaluation Criteria

```yaml
evaluation_criteria:
  - name: accuracy
    weight: 0.3
    description: "All claims supported by cited sources"
    accept_example: "Every factual statement has a source reference"
    reject_example: "Claims made without evidence or citation"
  - name: completeness
    weight: 0.3
    description: "Content addresses the request fully"
    accept_example: "All aspects of the query are covered"
    reject_example: "Major aspects of the query are missing"
  - name: structure
    weight: 0.2
    description: "Output follows required JSON schema"
    accept_example: "Valid JSON with all required fields"
    reject_example: "Missing fields or invalid JSON"
  - name: quality
    weight: 0.2
    description: "Writing quality and clarity"
    accept_example: "Clear, well-organized content"
    reject_example: "Incoherent or poorly structured text"
```

## Relationship to Anthropic Terminology

| This Template | Anthropic Term | Role |
|---------------|----------------|------|
| Orchestrator | Planner | Coordinates pipeline, owns writes, manages retries |
| Player | Generator | Produces content using domain tools |
| Coach | Evaluator | Evaluates content against weighted criteria, returns structured verdict |

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Orchestrator (Python loop)                │
│                                                               │
│  1. Load domain config (GOAL.md / DOMAIN.md)                 │
│  2. Create Player + Coach agents                              │
│  3. Run evaluation pipeline:                                  │
│     ┌─────────┐    content    ┌─────────┐                    │
│     │ Player  │──────────────▶│  Coach  │                    │
│     │(tools:  │               │(tools:  │                    │
│     │ search) │◀──────────────│ NONE)   │                    │
│     └─────────┘   weighted    └─────────┘                    │
│                   verdict                                     │
│  4. Write output ONLY after weighted score >= threshold       │
│  5. Retry on rejection (feed issues back to Player)          │
└──────────────────────────────────────────────────────────────┘
```

## Adversarial Intensity Modes

| Mode | Player | Coach | Retries | Use Case |
|------|--------|-------|---------|----------|
| `full` | Full tools + memory | Weighted evaluation | 3 | Production quality |
| `light` | Full tools, no memory | Simple pass/fail | 1 | Fast iteration |
| `solo` | Full tools + memory | Disabled (auto-accept) | 0 | Development/debug |

## Directory Structure

```
scaffold/
  orchestrator.py.j2       # Three-role wiring with weighted evaluation
  pipeline.py.j2            # Canonical evaluation pipeline
  goal_schema.py.j2         # Domain configuration schema
prompts/
  coach_template.py         # Coach/Evaluator weighted prompts
  adversarial_base.py       # Shared adversarial prompt patterns
hooks/
  hitl.py                   # Human-in-the-loop checkpoints
  sprint_contract.py        # Sprint negotiation hooks
config/
  adversarial_config.py     # Intensity and threshold settings
tests/
  test_scaffold.py          # Template generation smoke tests
```

## Usage

```bash
# Initialize a new project with weighted evaluation
guardkit init langchain-deepagents-weighted-evaluation

# The template will prompt for:
# - project_name
# - domain_name
# - adversarial_intensity (default: full)
# - evaluation_criteria (default: accuracy, completeness, structure, quality)
```

## Proven Patterns (from 11 production runs)

This template encodes fixes for the following failure categories:

| Fix ID | Category | Pattern Encoded |
|--------|----------|-----------------|
| TRF-003 | Tool leakage | `create_restricted_agent()` — no FilesystemMiddleware |
| TRF-005 | Write bypass | `OrchestratorWriteGate` — only Orchestrator writes |
| TRF-008 | Malformed output | `critical_response_format()` — recency-biased JSON enforcement |
| TRF-014 | Excessive tool calls | `tool_usage()` with explicit call limits |
| TRF-027 | Rubber-stamp Coach | `quality_gates()` with weighted criteria |
| TRF-029 | Format drift | `output_structure()` with negative examples |
| TRF-031 | Recency bias | Critical section placed LAST in prompt |
| TASK-REV-R2A1 | Dual system messages | `assert_no_system_messages()` at every call site |
