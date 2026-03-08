---
id: TASK-INST-015
title: Document AutoBuild instrumentation usage guide
task_type: feature
parent_review: TASK-REV-2FE2
feature_id: FEAT-INST
wave: 6
implementation_mode: task-work
complexity: 3
dependencies:
- TASK-INST-013
- TASK-INST-014
- TASK-INST-005b
- TASK-INST-005c
autobuild:
  enabled: false
status: completed
updated: 2026-03-08T00:00:00Z
completed: 2026-03-08T00:00:00Z
completed_location: tasks/completed/2026-03/TASK-INST-015/
---

# Task: Document AutoBuild Instrumentation Usage Guide

## Description

The instrumentation infrastructure is built across TASK-INST-001 through TASK-INST-014, but there is no user-facing documentation explaining how to use it, where events are stored, what data is captured, or how to interpret the output. Create a guide at `docs/guides/autobuild-instrumentation-guide.md` that serves as the single reference for anyone wanting to understand, enable, or analyse AutoBuild instrumentation data.

## Scope

This task ONLY creates:
- `docs/guides/autobuild-instrumentation-guide.md`

It also updates:
- `docs/guides/autobuild-workflow.md` — add a brief section linking to the instrumentation guide
- `docs/guides/local-backend-autobuild-guide.md` — add a brief section linking to the instrumentation guide (particularly relevant for vLLM profiling)
- Root `CLAUDE.md` — add instrumentation guide to the Key References table

It does NOT:
- Modify any Python source code
- Change event schemas or emitter behaviour
- Create analysis scripts or dashboards

## Requirements

### Guide Structure

The guide should follow the existing doc style (see `autobuild-workflow.md`, `local-backend-autobuild-guide.md`) with version header, table of contents, and clear sections.

### Required Sections

#### 1. Overview
- What instrumentation captures and why
- Relationship to the AutoBuild pipeline (Player-Coach loop, waves, tasks)
- Zero-overhead design — always-on JSONL, no runtime cost when not analysed

#### 2. Architecture
- Event emission flow: orchestrators → emitter → backends
- Backend options: JSONLFileBackend (always-on), NATSBackend (optional), CompositeBackend (fan-out)
- Protocol-based injection (NullEmitter for tests, real emitter for production)
- Diagram or description of the data flow from the IMPLEMENTATION-GUIDE.md mermaid diagrams

#### 3. Event Types Reference
- Table of all event types with fields: `llm.call`, `tool.exec`, `task.started`, `task.completed`, `task.failed`, `wave.completed`, `graphiti.query`
- Controlled vocabularies: `AgentRole`, `FailureCategory`, `PromptProfile`, `LLMProvider`
- Example JSON for each event type (realistic, not schema-only)

#### 4. File Locations
- Events: `.guardkit/autobuild/{feature_id}/events.jsonl`
- Digest files: `.guardkit/digests/{role}.md` (player, coach, resolver, router)
- Source modules: `guardkit/orchestrator/instrumentation/`
- Tests: `tests/orchestrator/instrumentation/`

#### 5. How to Use
- **Viewing events**: `cat .guardkit/autobuild/FEAT-XXX/events.jsonl | jq .`
- **Filtering by event type**: `jq 'select(.event_type == "llm.call")' events.jsonl`
- **Token usage summary**: `jq '{input: .input_tokens, output: .output_tokens, latency: .latency_ms}' events.jsonl` (example queries)
- **Comparing prompt profiles**: filtering by `prompt_profile` field for A/B analysis
- **Identifying slow tasks**: sorting by `latency_ms`
- **Failure analysis**: grouping by `failure_category`

#### 6. Prompt Profiles and Digests
- What prompt profiles are: `digest_only`, `digest+graphiti`, `digest+rules_bundle`, `digest+graphiti+rules_bundle`
- Current default: `digest+rules_bundle` (Phase 1 baseline)
- Where digest files live and what they contain
- Token budget: 300-600 target, 700 hard limit
- How to validate digests: `DigestValidator.validate_all()`
- Migration phases (Phase 1-4) from feature input doc

#### 7. Adaptive Concurrency
- How `ConcurrencyController` uses wave events to adjust worker count
- Policy rules: rate limit → reduce 50%, p95 spike → reduce 50%, stable → recover +1
- Relevance to local/vLLM backends where GPU contention is the bottleneck

#### 8. vLLM / Local Backend Specifics
- Provider detection: `local-vllm` detected from base URL
- Prefix cache hit detection via `x-vllm-prefix-cache-hit` response header
- Key metrics to watch: `ttft_ms` (time to first token), `latency_ms`, `input_tokens` (prefill cost)
- Reference to TASK-VPT-001 defaults (max_parallel=1, timeout_multiplier=3.0)
- Cross-reference to `local-backend-autobuild-guide.md`

#### 9. Secret Redaction
- What is redacted automatically (API keys, tokens, passwords, credentials in URLs)
- Applied to `tool.exec` events only (cmd, stdout_tail, stderr_tail)
- How to add custom redaction patterns

#### 10. Troubleshooting
- No events in file → emitter not wired (check TASK-INST-013)
- DigestLoadError → digest files missing (check TASK-INST-014)
- Events file growing large → no auto-rotation, safe to delete between runs
- NATS backend warnings → optional, does not affect JSONL persistence

### Cross-References

Add a brief "Instrumentation" subsection (2-3 lines + link) to:
- `docs/guides/autobuild-workflow.md` — in the "Part 4: Advanced Topics" area
- `docs/guides/local-backend-autobuild-guide.md` — after "Troubleshooting" or "Reference Data"
- Root `CLAUDE.md` — add `| Instrumentation Guide | docs/guides/autobuild-instrumentation-guide.md |` to the Key References table

## Acceptance Criteria

- [x] `docs/guides/autobuild-instrumentation-guide.md` created with all 10 sections
- [x] Version header and table of contents following existing guide style
- [x] All event types documented with realistic JSON examples
- [x] All file locations documented with actual paths
- [x] jq query examples are correct and runnable
- [x] Prompt profile migration phases documented
- [x] vLLM-specific metrics and detection documented
- [x] Cross-reference added to `autobuild-workflow.md`
- [x] Cross-reference added to `local-backend-autobuild-guide.md`
- [x] Cross-reference added to root `CLAUDE.md` Key References table
- [x] No Python source code modified
- [x] Content is accurate against the merged instrumentation code (schemas.py, emitter.py, etc.)

## File Location

New files:
- `docs/guides/autobuild-instrumentation-guide.md`

Changes to:
- `docs/guides/autobuild-workflow.md` (add cross-reference)
- `docs/guides/local-backend-autobuild-guide.md` (add cross-reference)
- `CLAUDE.md` (add to Key References table)

## Test Location

No tests — documentation only task.
