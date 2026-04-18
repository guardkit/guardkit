# Feature: LangChain Template Lessons (LES1 back-port)

**Feature ID**: FEAT-LTL1
**Parent Review**: [TASK-REV-LES1](../TASK-REV-LES1-cross-agent-lessons-for-langchain-deepagents-templates.md)
**Review Report**: [.claude/reviews/TASK-REV-LES1-review-report.md](../../../.claude/reviews/TASK-REV-LES1-review-report.md)

## Problem Statement

The three `langchain-deepagents*` templates sit at very different maturity
levels with respect to the LES1 cross-agent lessons distilled from the
specialist-agent MacBook walkthrough (TASK-REV-B8E4). The weighted-evaluation
extension has absorbed the SDK-alignment fixes and post-specialist-agent
hardening; the **base** template has the right pattern rules but ships **two
broken imports** that make it un-runnable out of the box; the
**orchestrator** template has absorbed **none** of the lessons and contains a
latent F2-style tool-leakage bug on its Evaluator SubAgent.

Without this feature, every downstream agent built on our templates
(jarvis, forge, study-tutor, and future agents) will re-hit the same class
of bugs LES1 was written to prevent.

## Solution Approach

A 12-task feature organised into three parallel-safe waves:

- **Wave 1 — Unblock** (3 tasks). Fixes the base template's broken imports,
  introduces a `[providers]` extras pattern, and adds a template-validate
  smoke test that would have caught the import bug in CI.
- **Wave 2 — Orchestrator back-port** (4 tasks). Back-ports the 32D2/4F71/LES1
  lessons that were never applied to the orchestrator template:
  `[providers]` extras, `AGENTS.md.template` with ainvoke contract, env-var
  provider resolution, Evaluator SubAgent tool-inventory assertion.
- **Wave 3 — Shared infrastructure** (5 tasks). Promotes session-logging and
  retry-context helpers into base `lib/` so all three templates can share
  them; adds a long-running-tools pattern rule; closes out the
  medium/low findings from the review.

Waves 2 and 3 can execute in parallel (they touch disjoint file sets).

## Subtasks Summary

| ID | Title | Wave | Mode | Complexity |
|---|---|:-:|:-:|:-:|
| [LCL-001](TASK-LCL-001-fix-broken-imports-base-template.md) | Fix broken `{{ProjectName}}` imports in base coach.py.template and agent.py.template | 1 | direct | 1 |
| [LCL-002](TASK-LCL-002-providers-extras-base-pyproject.md) | Add `[providers]` extras pattern to base pyproject.toml.template | 1 | direct | 2 |
| [LCL-003](TASK-LCL-003-template-validate-render-import-smoke.md) | Template-validate smoke test — render and import each template | 1 | task-work | 4 |
| [LCL-004](TASK-LCL-004-providers-extras-orchestrator.md) | Add pyproject.toml.template with `[providers]` extras to orchestrator | 2 | direct | 2 |
| [LCL-005](TASK-LCL-005-agents-md-orchestrator-ainvoke-contract.md) | AGENTS.md.template with TASK-REV-R2A1 contract for orchestrator | 2 | direct | 2 |
| [LCL-006](TASK-LCL-006-env-var-resolution-orchestrator.md) | `AGENT_MODELS__*` env-var resolution in orchestrator `_create_model` | 2 | task-work | 4 |
| [LCL-007](TASK-LCL-007-evaluator-subagent-tool-inventory-assertion.md) | Evaluator SubAgent post-construction tool-inventory assertion | 2 | task-work | 5 |
| [LCL-008](TASK-LCL-008-extract-session-logging-retry-context-to-base-lib.md) | Extract session_logging + retry_context into base `lib/` | 3 | task-work | 6 |
| [LCL-009](TASK-LCL-009-patterns-long-running-tools-rule.md) | `patterns/long-running-tools.md` rule (base + orch) | 3 | direct | 2 |
| [LCL-010](TASK-LCL-010-patterns-source-path-convention-doc.md) | Clarify `Source:` path convention in base patterns intro | 3 | direct | 1 |
| [LCL-011](TASK-LCL-011-align-weighted-eval-manifest-pattern-attribution.md) | Align weighted-eval manifest pattern attribution | 3 | direct | 1 |
| [LCL-012](TASK-LCL-012-weighted-eval-env-example.md) | Weighted-eval `.env.example.template` with extension vars | 3 | direct | 1 |

**Totals**: 12 tasks · 4 task-work · 8 direct · aggregate complexity 31.

## Findings Coverage

Every finding from [TASK-REV-LES1 review report](../../../.claude/reviews/TASK-REV-LES1-review-report.md)
has a dedicated sub-task, except LOW-3 (missing `-ext.md` siblings in orch
template) which was explicitly recorded as a nit with no action.

| Review finding | Sub-task(s) |
|---|---|
| BLOCKER-1 broken imports | LCL-001 |
| BLOCKER-2 no [providers] extras | LCL-002, LCL-004 |
| HIGH-1 Evaluator F2 risk | LCL-007 |
| HIGH-2 no ainvoke contract / AGENTS.md | LCL-005 |
| HIGH-3 hardcoded anthropic defaults | LCL-006 |
| HIGH-4 no session logs / context manifest | LCL-008 |
| MEDIUM-1 pattern rule path convention | LCL-010 |
| MEDIUM-2 long-running-tool discipline rule | LCL-009 |
| MEDIUM-3 no extension .env.example | LCL-012 |
| MEDIUM-4 requirements.txt vs pyproject inconsistency | LCL-004 (rolled in) |
| LOW-1 pattern attribution in manifest | LCL-011 |
| LOW-2 `AGENT_MODELS__*` naming | LCL-006 (rolled in) |
| LOW-3 missing `-ext.md` siblings | No action (nit) |
| Shared-infra #5 render-import smoke test | LCL-003 |

## Out of Scope

- `nats-asyncio-service` template audit against LES1 §2 / §7. Opened as a
  separate follow-on review task.
- Promoting the orchestrator template to `extends: langchain-deepagents`
  (would eliminate vendoring in LCL-007 and LCL-008). Flagged as
  future-work in LCL-007; larger refactor than this feature's scope.

## Next Steps

See [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) for wave-by-wave
execution plan, dependency ordering, and Conductor workspace assignments.
