# LangChain DeepAgents — Base Template

## Project Overview

Adversarial Cooperation template for **binary accept/reject evaluation** against fixed pass/fail criteria.
Uses the Player-Coach multi-agent pattern where a Coach evaluates Player output with a structured verdict
(accept at score 4-5, reject at 1-3).

**Evaluation model**: Binary. The Coach returns `CoachVerdict` with a decision (`accept`/`reject`)
and a score. Works for domains where quality is **objectively verifiable**: schema conformance,
code compilation, test pass/fail, metadata accuracy.

**Language**: Python
**Frameworks**: DeepAgents >=0.4.11, LangChain >=1.2.11, LangChain-Core >=1.2.18, LangGraph >=0.2, LangChain-Community >=0.3
**Architecture**: Adversarial Cooperation (Player-Coach multi-agent orchestration)

## When to Use This Template

Use `langchain-deepagents` when your evaluation criteria are **objectively verifiable**:

- Schema conformance (JSON output matches expected structure)
- Code compilation and test pass/fail
- Metadata accuracy (fields present, types correct, ranges valid)
- Data synthesis with measurable correctness

For **subjective or creative domains** (video planning, design, content creation) where quality
requires weighted multi-criteria scoring, use the
[`langchain-deepagents-weighted-evaluation`](../langchain-deepagents-weighted-evaluation/) extension instead.

## What's Included

| Component | Purpose |
|-----------|---------|
| `lib/domain_validator.py` | Type-aware metadata validation with coercion |
| `lib/json_extractor.py` | 5-strategy cascade JSON extraction from LLM output |
| `lib/factory_guards.py` | Tool allowlisting, input contract enforcement |
| `lib/content_pipeline.py` | Canonical pipeline: normalize -> extract -> validate -> write |
| `lib/checkpoint_hooks.py` | HITL checkpoint library (CLI, webhook, auto-approve) — integration hooks in extension |
| `lib/sprint_contract.py` | Sprint contract negotiation library — integration hooks in extension |
| `lib/observability.py` | Token tracking, stage timing, error context logging |
| `lib/preflight.py` | Pre-flight configuration validation |

## What Requires the Extension

The following are NOT in this base template — use `langchain-deepagents-weighted-evaluation`:

- Weighted multi-criteria scoring (configurable weights per criterion)
- GOAL.md quality contracts with acceptance thresholds
- Adversarial intensity modes (full / light / solo)
- `WeightedVerdict` dataclass (composite score vs binary decision)
- Integration hooks (`hooks/hitl.py`, `hooks/sprint_contract.py`) that wire the base libraries into weighted evaluation

## Quick Start

```bash
pip install .[providers]
pytest tests/ -v
```

`.[providers]` installs every LangChain integration named in code (anthropic, openai, google-genai).
The base `dependencies` also include `langchain-anthropic` so a zero-extras install of the default
provider still works. See `pyproject.toml` `[project.optional-dependencies]` and TASK-REV-LES1 /
LES1 §3 LCOI for why every integration must be declared.

## Detailed Guidance

Rules load automatically when you work on relevant files:

- **Code Style**: `.claude/rules/code-style.md`
- **Testing**: `.claude/rules/testing.md`
- **Patterns**: `.claude/rules/patterns/`
- **Guidance**: `.claude/rules/guidance/`

### Pattern rule conventions

Pattern rule files in `.claude/rules/patterns/` end with `Source: <path>` lines
(e.g. `Source: scaffold/orchestrator_pattern.py.template`). These paths are
**post-render** — they refer to the layout a user sees in their rendered
project, not paths inside this template's source tree. In the template source
tree the referenced files live under `templates/other/...` (e.g.
`templates/other/scaffold/orchestrator_pattern.py.template`); once the template
is applied to a user project, those files appear at the paths cited in the rule
files. Do not "correct" `Source:` paths to match the template tree.

## Cross-Domain Evidence

| Domain | Evaluation Model | Evidence |
|--------|-----------------|----------|
| Training data generation | Schema conformance, metadata accuracy | agentic-dataset-factory: 11 runs, 85% acceptance |
| Code synthesis | Test pass/fail, compilation | GuardKit AutoBuild: 100% task completion |

## Python Pinning

`requires-python = ">=3.11"` (open upper bound) is the portfolio canonical for
this template family. Don't add a closed upper bound (`<3.X`) unless you have a
specifically-documented reason — stale upper bounds become latent stall
trapdoors when a new Python minor ships in a developer's PATH. See
[`docs/guides/portfolio-python-pinning.md`](../../../../../docs/guides/portfolio-python-pinning.md)
for rationale and the calendar-cadence revisit policy.

## See Also

- **Extension template**: [`langchain-deepagents-weighted-evaluation`](../langchain-deepagents-weighted-evaluation/) — weighted multi-criteria evaluation for subjective domains
- **Portfolio Python pinning**: [`docs/guides/portfolio-python-pinning.md`](../../../../../docs/guides/portfolio-python-pinning.md) — `requires-python` standard for the portfolio
