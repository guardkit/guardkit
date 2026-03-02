# Feature: AutoBuild Instrumentation and Context Reduction

## Problem

AutoBuild performance on local inference (GB10 / vLLM / Qwen3-Coder-Next) is heavily affected by prefill latency from large always-on context bundles. Without structured observability, we cannot measure where time and tokens are spent, compare prompt strategies, or tune concurrency.

## Solution

1. **Structured instrumentation** — Event emission layer capturing LLM calls, tool executions, Graphiti queries, task lifecycle, and wave management with structured JSON events.

2. **Role-specific digests** — Minimal system prompts (~300-600 tokens) for Player, Coach, Resolver, and Router roles replacing the full rules bundle.

3. **Prompt profile tagging** — A/B comparison between `digest_only`, `digest+graphiti`, and `digest+rules_bundle` profiles.

4. **Adaptive concurrency** — Wave worker count adjustment based on rate limits and p95 latency trends.

## Architecture

Protocol-based EventEmitter injected into existing AutoBuild components. CompositeBackend fans out to JSONL (always-on) and optional NATS. Non-blocking async emission.

## Tasks (9 total, 4 waves)

| Wave | Task | Description | Complexity |
|------|------|-------------|-----------|
| 1 | TASK-INST-001 | Event schema Pydantic models | 4 |
| 2 | TASK-INST-002 | EventEmitter protocol and backends | 5 |
| 2 | TASK-INST-003 | Secret redaction pipeline | 4 |
| 2 | TASK-INST-007 | Role-specific digest system | 5 |
| 3 | TASK-INST-004 | Instrument orchestrator (lifecycle events) | 5 |
| 3 | TASK-INST-005 | Instrument agent invoker (LLM + tool events) | 6 |
| 3 | TASK-INST-006 | Instrument Graphiti loader | 3 |
| 3 | TASK-INST-008 | Adaptive concurrency controller | 5 |
| 4 | TASK-INST-009 | Integration tests | 4 |

**Aggregate Complexity**: 8/10
**Testing**: Full TDD
**BDD Scenarios**: 35 (from feature spec)

## References

- Review: TASK-REV-2FE2
- Feature Spec: `features/autobuild-instrumentation/autobuild-instrumentation.feature`
- Feature Input: `docs/reviews/instrumentation/autobuild-instrumentation-feature-input.md`
- Review Report: `.claude/reviews/TASK-REV-2FE2-review-report.md`
