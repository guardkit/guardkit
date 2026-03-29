---
id: TASK-REV-32D2
title: Review adversarial cooperation template design for DeepAgents SDK
status: completed
created: 2026-03-29T21:00:00Z
updated: 2026-03-29T22:30:00Z
priority: high
tags: [review, adversarial-cooperation, template, deepagents, langchain, architecture-review]
task_type: review
review_mode: architectural
review_depth: deep
complexity: 7
parent_review: TASK-REV-TRF12
feature_id: FEAT-TI
depends_on: []
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  score: 72
  findings_count: 5
  recommendations_count: 10
  decisions_resolved: 7
  decision: refactor
  report_path: .claude/reviews/TASK-REV-32D2-review-report.md
  revision: 3
  revision_note: SDK-validated + cross-referenced with working agentic-dataset-factory production code
  completed_at: 2026-03-29T23:00:00Z
---

# Task: Review Adversarial Cooperation Template Design for LangChain DeepAgents SDK

## Description

Comprehensive design review of the `langchain-deepagents-weighted-evaluation` template before implementation begins (Wave 4, TASK-TI-009 through TASK-TI-016). This review must validate the template architecture, resolve open design decisions, and ensure alignment between the conversation starter spec, the implementation guide, and the current codebase state — all built on the **LangChain DeepAgents SDK**.

The template encodes the adversarial cooperation pattern (Player-Coach / Generator-Evaluator) as a reusable scaffold for the DeepAgents SDK. It extends the existing `langchain-deepagents` base template with adversarial-specific patterns derived from 11 production runs and 31 fixes in the agentic-dataset-factory project.

This template serves three use cases:
1. **Dark Factory / Software Factory** — autonomous code and data generation with quality gates
2. **YouTube Agentic Planner** — adversarial video planning with gradable subjective criteria
3. **General adversarial cooperation** — any domain where Generator + Evaluator improves output quality

## Review Scope

### 1. Architecture Validation

- Validate three-role separation: Orchestrator (plain Python loop) + Player (DeepAgent with domain tools) + Coach (DeepAgent with NO tools)
- Confirm the Orchestrator is NOT a DeepAgent — it's a plain Python coordination loop that invokes Player and Coach as subagents
- Verify tool separation enforcement: Player has domain tools only (NO write/filesystem), Coach has EMPTY tools (evaluation only)
- Validate orchestrator-gated writes pattern: only Orchestrator calls `write_output`, only after Coach acceptance
- Review the `create_agent()` vs `create_deep_agent()` decision — `create_deep_agent()` unconditionally injects `FilesystemMiddleware`, so tool-restricted agents MUST use `create_agent()` or manual LangGraph wiring

### 2. SDK Alignment — LangChain DeepAgents

**CRITICAL: This template MUST be built on the LangChain DeepAgents SDK.**

- Validate use of DeepAgents SDK primitives: `create_deep_agent()`, `create_agent()`, `SubAgentMiddleware`, `FilesystemMiddleware`, `HumanInTheLoopMiddleware`
- Review middleware composition for each role (Player gets domain middleware, Coach gets none, Orchestrator coordinates)
- Validate `memory=["./AGENTS.md"]` pattern for agent boundary injection
- Review `StateBackend` vs `StoreBackend` vs `FilesystemBackend` selection per role
- Assess LangChain middleware customisation patterns per https://blog.langchain.com/how-middleware-lets-you-customize-your-agent-harness/
- Confirm compatibility with LangGraph Studio entrypoint (`agent.py` + `langgraph.json`)

### 3. Conversation Starter Alignment

Review the conversation starter spec against implementation guide for:

- **CoachVerdict schema evolution**: Conversation starter specifies Pydantic `BaseModel` with `Literal["accept", "revise", "reject"]`, per-criterion `criteria_met: dict[str, bool]`, `criteria_scores: dict[str, int]`, and structured `issues: list[Issue]`. Current codebase has simpler `@dataclass`. Determine: should the adversarial template ship the richer Pydantic version while base template keeps the dataclass?
- **GOAL.md vs DOMAIN.md**: Both should exist — DOMAIN.md for domain context injection (existing pattern), GOAL.md for the complete quality contract (evaluation criteria, scoring rubrics, output schema, metadata schema, layer routing). Validate this separation.
- **Configurable adversarial intensity**: full / light / solo modes per the YAML config shape. Validate the generation loop correctly degrades across modes.
- **Sprint contract negotiation**: Orchestrator proposes scope, Coach reviews before generation begins. Validate this maps to DeepAgents SDK primitives.
- **HITL checkpoint hooks**: minimal / standard / full levels. Review NATS transport integration vs console fallback. Consider Ship's Computer / Reachy integration path.

### 4. Cross-Domain Applicability

The template must work for:
- **Code/data generation** (dark factory) — verifiable quality, strict acceptance criteria
- **Creative content planning** (YouTube planner) — subjective quality made gradable via weighted criteria (hook strength, originality, structure, audience alignment, emotional resonance, actionability)
- **General adversarial cooperation** — any domain with a GOAL.md quality contract

Review that the template's abstractions are domain-agnostic while the GOAL.md pattern allows domain-specific customisation.

### 5. Wave 1 Completion Status

Validate that Wave 1 (P0) components are complete and correct:
- `lib/json_extractor.py` — 5-strategy cascade, string-aware brace matching, think tag normalisation
- `templates/other/prompts/templates.py.template` — CRITICAL section, tool usage, quality gates, output structure, assemble_prompt
- `templates/other/scaffold/orchestrator_pattern.py.template` — OrchestratorWriteGate, CoachVerdict, validate_player_tools

### 6. Stub Pattern Rules

The existing rules in `.claude/rules/patterns/` (adversarial-cooperation.md, memory-injection.md, factory.md, tool-delegation.md, domain-driven-configuration.md) are all stubs. Review whether these should be populated from proven code as part of this work.

## Key Design Decisions to Resolve

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| D1 | CoachVerdict: dataclass vs Pydantic | Keep dataclass in base, Pydantic in adversarial | Both — base template simple, adversarial template rich |
| D2 | Agent factory naming | `create_restricted_agent()` vs `create_agent()` | Use SDK naming: `create_agent()` |
| D3 | GOAL.md and DOMAIN.md coexistence | Merge into one / keep separate | Keep separate — different concerns |
| D4 | Orchestrator implementation | DeepAgent vs plain Python loop | Plain Python loop (NOT DeepAgent) |
| D5 | Coach tool invariant | No tools ever / optional tools | No tools ever (D5 invariant from conversation starter) |
| D6 | Multi-model support | Same model both roles / different models | Support different models per role (model_factory.py) |
| D7 | NATS vs console for HITL | NATS required / console fallback | Console default, NATS optional via config |

## Reference Materials

### Primary Sources (In This Repo)

- `tasks/backlog/template-improvements/IMPLEMENTATION-GUIDE.md` — Wave structure, architecture, key design decisions
- `tasks/backlog/template-improvements/README.md` — Feature overview with subtask summary
- `tasks/backlog/template-improvements/TASK-TI-009-adversarial-template-scaffold.md` through `TASK-TI-016-sprint-contract-negotiation.md` — Individual task specifications
- `installer/core/templates/langchain-deepagents/` — Existing base template with Wave 1 code
- `.claude/reviews/TASK-REV-TRF12-review-report.md` — Original review (from agentic-dataset-factory, needs copying)

### Conversation Starters & Planning Documents

- `/Users/richardwoollcott/Projects/YouTube Channel/agent-adversarial-cooperation/langchain-deepagents-weighted-evaluation-conversation-starter.md` — Authoritative spec for the adversarial template (50+ file structure, full component descriptions, constraints from proven code)
- `/Users/richardwoollcott/Projects/YouTube Channel/conversation-starter-adversarial-video-planning-tool.md` — YouTube video planning use case, competitive landscape validation, GOAL.md pattern for creative content, multi-model evaluation rationale

### External References

- **LangChain Blog: How Middleware Lets You Customize Your Agent Harness** — https://blog.langchain.com/how-middleware-lets-you-customize-your-agent-harness/ — Middleware composition patterns for DeepAgents SDK, relevant to role-specific middleware wiring
- **Block AI Research: Adversarial Cooperation in Code Synthesis** (December 2025) — https://block.xyz/documents/adversarial-cooperation-in-code-synthesis.pdf — Original Player-Coach pattern research, effectiveness across code synthesis tasks
- **Anthropic Engineering: Harness Design for Long-Running Application Development** (March 2026) — https://www.anthropic.com/engineering/harness-design-long-running-apps — Generator-Evaluator architecture validation, subjective quality grading framework, evaluator scepticism insight
- **DeepAgents SDK Documentation** — https://docs.langchain.com/oss/python/deepagents/overview
- **DeepAgents GitHub** — https://github.com/langchain-ai/deepagents

### Evidence Base

- 11 production runs, 31 fixes across agentic-dataset-factory
- 84% of fixes (26/31) preventable by better template scaffolding
- 6 root cause categories: validation/schema (29%), prompt engineering (23%), SDK/framework (19%), orchestration (13%), model quirks (10%), test/observability (6%)
- Competitive landscape validated March 2026: adversarial cooperation for creative content planning is genuinely novel (fourth domain after code synthesis, frontend design, training data generation)

## Acceptance Criteria

- [ ] Architecture validated against LangChain DeepAgents SDK primitives
- [ ] All 7 design decisions (D1-D7) resolved with rationale
- [ ] Conversation starter spec reconciled with implementation guide
- [ ] Wave 1 (P0) completion status confirmed
- [ ] Cross-domain applicability validated (dark factory + YouTube planner + general)
- [ ] CoachVerdict evolution path documented (dataclass → Pydantic)
- [ ] Stub pattern rules assessed with population plan
- [ ] Risk assessment for Wave 4 implementation
- [ ] Review report generated in `.claude/reviews/TASK-REV-32D2-review-report.md`

## Suggested Review Approach

```bash
/task-review TASK-REV-32D2 --mode=architectural --depth=deep
```

## Notes

This review gates Wave 4 implementation (TASK-TI-009 through TASK-TI-016). No adversarial template code should be written until this review is complete and design decisions are resolved.
