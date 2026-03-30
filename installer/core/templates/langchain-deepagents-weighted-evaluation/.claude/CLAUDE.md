# Adversarial Cooperation with Weighted Evaluation

## Project Overview

Extension of the [`langchain-deepagents`](../../langchain-deepagents/) base template that replaces
binary accept/reject evaluation with **configurable weighted multi-criteria scoring**.

**Evaluation model**: Weighted composite. The Coach evaluates Player output against multiple
criteria, each with a configurable weight. A composite score is computed and compared against
an acceptance threshold. This makes **subjective quality gradable** — the Anthropic insight
applied to creative content, design, and planning domains.

**Extends**: `langchain-deepagents` (inherits all lib modules, factory guards, pipeline)
**Language**: Python
**Frameworks**: DeepAgents >=0.4.11, LangChain >=1.2.11, LangChain-Core >=1.2.18, LangGraph >=0.2, LangChain-Community >=0.3
**Architecture**: Adversarial Cooperation with Weighted Evaluation

## When to Use This Template

Use `langchain-deepagents-weighted-evaluation` when quality requires **subjective judgement
with weighted criteria**:

- Creative content (video planning, article writing, design)
- Multi-dimensional quality (originality + structure + accuracy)
- Configurable acceptance thresholds per domain
- Domains where "good enough" is a spectrum, not a binary

For **objectively verifiable** domains (schema conformance, code compilation, test pass/fail),
use the base [`langchain-deepagents`](../../langchain-deepagents/) template instead — binary
evaluation is simpler and sufficient.

## What This Template Adds

| Feature | Base (`langchain-deepagents`) | This Template |
|---------|-------------------------------|---------------|
| Coach verdict | Binary accept/reject (`CoachVerdict`) | Weighted multi-criteria score (`WeightedVerdict`) |
| Acceptance | Score 4-5 accepts | Composite score >= configurable threshold |
| Criteria | Fixed in DOMAIN.md | Configurable weights per criterion via GOAL.md |
| Intensity | Single mode | full / light / solo modes |
| Quality contract | None | GOAL.md quality contracts |

## GOAL.md Quality Contract Pattern

Each domain defines a `GOAL.md` file specifying weighted evaluation criteria:

```markdown
## Quality Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| hook_strength | 0.30 | Opening hook captures attention |
| originality | 0.25 | Fresh perspective, not derivative |
| structure | 0.25 | Clear narrative arc |
| accuracy | 0.20 | Factual claims are correct |

## Acceptance Threshold

Minimum composite score: 0.70
```

The Coach evaluates each criterion independently and computes a weighted composite score.
This approach was validated by Anthropic's research on adversarial cooperation and Block's
production deployment of multi-agent quality gates.

## Inherited from Base Template

All `lib/` modules from the base template are inherited and available:

- `lib/factory_guards.py` — Tool allowlisting (`assert_tool_inventory`) and input contract enforcement (`assert_no_system_messages`)
- `lib/json_extractor.py` — 5-strategy cascade JSON extraction
- `lib/domain_validator.py` — Type-aware domain validation with coercion
- `lib/content_pipeline.py` — Canonical pipeline: normalize -> extract -> validate -> write
- `lib/checkpoint_hooks.py` — HITL checkpoint library (CLI, webhook, auto-approve)
- `lib/sprint_contract.py` — Sprint contract negotiation library
- `lib/preflight.py` — Pre-flight configuration checks
- `lib/observability.py` — Token tracking, stage timing, structured logging

## This Template Provides

| Component | Purpose |
|-----------|---------|
| `config/adversarial_config.py` | Intensity modes, acceptance thresholds |
| `prompts/coach_template.py` | Weighted evaluation prompt generation |
| `prompts/adversarial_base.py` | Base prompt patterns for adversarial pairs |
| `hooks/hitl.py` | HITL integration hooks — wires base `lib/checkpoint_hooks.py` into weighted evaluation |
| `hooks/sprint_contract.py` | Sprint negotiation hooks — wires base `lib/sprint_contract.py` into weighted evaluation |
| `scaffold/pipeline.py.j2` | Pipeline scaffold with weighted scoring |
| `scaffold/orchestrator.py.j2` | Orchestrator scaffold with intensity modes |
| `scaffold/goal_schema.py.j2` | GOAL.md parser and schema validation |
| `templates/goal.md.j2` | GOAL.md template for new domains |

## Adversarial Intensity Modes

| Mode | Player | Coach | Use Case |
|------|--------|-------|----------|
| `full` | LLM agent with tools | LLM evaluator | Production quality gates |
| `light` | LLM agent with tools | Rule-based evaluator | Fast iteration, CI/CD |
| `solo` | LLM agent with tools | Disabled (auto-accept) | Development, prototyping |

## Cross-Domain Evidence

| Domain | Evaluation Model | Evidence |
|--------|-----------------|----------|
| Video content planning | Hook strength, originality, structure (weighted) | Anthropic research validation |
| Training data generation | Schema conformance (binary, base template) | agentic-dataset-factory: 11 runs |
| Code synthesis | Test pass/fail (binary, base template) | GuardKit AutoBuild: 100% completion |

## Quick Start

```bash
pip install -r requirements.txt
pytest tests/ -v
```

## Templating Conventions

This template chain uses two different templating approaches:

| Convention | Extension | Used By | Purpose |
|------------|-----------|---------|---------|
| Simple substitution | `.py.template` | Base (`langchain-deepagents`) | Leaf files with `{{placeholder}}` variable replacement |
| Jinja2 | `.py.j2` | This extension | Structural scaffolding with loops, conditionals, filters |

**When to use which:**
- **`.template`** (simple substitution) — Use for files that only need variable replacement (e.g., project name, module paths). The base template uses this for all scaffold files.
- **`.j2`** (Jinja2) — Use when scaffold files need loops over criteria, conditionals for intensity modes, or other control flow. This extension uses Jinja2 because weighted evaluation requires iterating over configurable criteria and conditionally including intensity-specific code.

Both conventions are valid within the same `extends` chain. The installer handles each format with its corresponding renderer.

### SKILL.md vs manifest.json

Both templates use `manifest.json` as the **canonical source** for template metadata (name, version, frameworks, dependencies). This is required by the installer.

This extension additionally provides a `SKILL.md` file, which serves a different purpose:
- **`manifest.json`** — Machine-readable metadata: template identity, framework versions, installer configuration
- **`SKILL.md`** — Developer-facing reference: template variables with types/defaults/examples, architecture diagrams, Anthropic terminology mapping, proven failure patterns

The base template does not include a `SKILL.md` because its simpler variable set is fully covered by `manifest.json` and `CLAUDE.md`. Extensions with richer configuration (weighted criteria, intensity modes, threshold tuning) benefit from the additional detail `SKILL.md` provides.

## Detailed Guidance

See `.claude/rules/` for conditional loading rules (when available).
See `SKILL.md` for template variables and configuration options.

## See Also

- **Getting started**: [`docs/GETTING_STARTED.md`](../../langchain-deepagents/docs/GETTING_STARTED.md) in the base template — prerequisites, SDK constraints, tool separation rules, and common pitfalls
- **Base template**: [`langchain-deepagents`](../../langchain-deepagents/) — binary evaluation for verifiable domains
