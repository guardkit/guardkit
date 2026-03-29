---
id: TASK-TI-024
title: Populate stub pattern rules from proven code
status: completed
created: 2026-03-29T23:30:00Z
updated: 2026-03-30T01:00:00Z
completed: 2026-03-30T01:05:00Z
completed_location: tasks/completed/TASK-TI-024/
priority: p2
tags: [template, documentation, patterns, developer-experience]
complexity: 4
parent_review: TASK-REV-32D2
feature_id: FEAT-TI
wave: 3.5
implementation_mode: task-work
depends_on: [TASK-TI-019, TASK-TI-021, TASK-TI-022]
test_results:
  status: not_applicable
  coverage: null
  last_run: null
organized_files:
  - TASK-TI-024.md
  - completion-report.md
---

# Task: Populate Stub Pattern Rules from Proven Code

## Description

All 5 pattern rules files in the base `langchain-deepagents` template's `.claude/rules/patterns/` are stubs with boilerplate content. These should be populated with real patterns extracted from the proven template code and the `agentic-dataset-factory` exemplar.

## Scope Boundary — Base Template Only

These pattern rules belong to the **base `langchain-deepagents` template**. They document what's already in the base template — the production-grade adversarial cooperation infrastructure that's currently running a 26-hour production run in `agentic-dataset-factory`.

**DO NOT include** patterns from the future `langchain-deepagents-weighted-evaluation` template:
- No GOAL.md quality contract content
- No Pydantic CoachVerdict with per-criterion scoring
- No configurable adversarial intensity (full/light/solo)
- No sprint contract negotiation
- No HITL checkpoint hooks
- No weighted criteria or scepticism tuning config

Those patterns will have their own rules files in the `langchain-deepagents-weighted-evaluation` template when it's created in Wave 4.

## Template Architecture Context

Two templates exist (or will exist):

| Template | Purpose | Evaluation Model |
|----------|---------|-----------------|
| `langchain-deepagents` (base) | Production-grade adversarial cooperation with binary accept/reject | Fixed criteria — Coach evaluates against clear pass/fail standards |
| `langchain-deepagents-weighted-evaluation` (Wave 4) | Extends base with configurable weighted evaluation | GOAL.md quality contract — decompose subjective quality into weighted, gradable criteria |

The base template works for **verifiable domains** (code generation, data synthesis, schema conformance). The weighted-evaluation extension adds the ability to make **subjective quality gradable** — the Anthropic insight applied to creative content (video planning, design, content creation).

## Files to Populate

| File | What to Document | Source Material |
|------|-----------------|----------------|
| `adversarial-cooperation.md` | Three-role architecture (Orchestrator/Player/Coach), orchestrator-gated writes, binary CoachVerdict dataclass, rejection-revision loop, ainvoke() message contract | `orchestrator_pattern.py.template`, `player.py.template`, `coach.py.template`, TASK-REV-R2A1 |
| `memory-injection.md` | `MemoryMiddleware` + `FilesystemBackend` for AGENTS.md loading, how boundaries are injected into system prompts, why `FilesystemBackend` is for reading only (not adding tools) | `AGENTS.md.template`, proven pattern from `agentic-dataset-factory/agents/player.py` |
| `factory.md` | `create_agent()` vs `create_deep_agent()` decision, why `create_deep_agent()` injects unwanted middleware, `create_restricted_agent()` wrapper, tool allowlisting at factory exit | `agent_factory.py.template`, `factory_guards.py`, SDK source validation from TASK-REV-32D2 |
| `tool-delegation.md` | Tool separation contract (Player: domain tools only, Coach: NO tools), `validate_player_tools()`, `assert_tool_inventory()`, D5 invariant, `assert_no_system_messages()` | `factory_guards.py`, `orchestrator_pattern.py.template` |
| `domain-driven-configuration.md` | DOMAIN.md loading pattern, `_load_domain_prompt()`, how domain context is appended to agent system prompts at runtime | `agent.py.template`, `DOMAIN.md.template` |

## Acceptance Criteria

- [x] All 5 pattern files contain real code examples from the **base** template
- [x] Each includes When-to-use / When-not-to-use guidance
- [x] Each references the relevant TRF fix numbers (domain-driven-configuration has no applicable TRFs)
- [x] `adversarial-cooperation.md` includes the three-role architecture and ainvoke() contract (TASK-REV-R2A1)
- [x] `factory.md` documents `create_agent()` vs `create_deep_agent()` with SDK rationale from TASK-REV-32D2
- [x] NO content from the weighted-evaluation template (GOAL.md, Pydantic CoachVerdict, intensity config, HITL, sprint contracts)

## Effort Estimate

3-4 hours
