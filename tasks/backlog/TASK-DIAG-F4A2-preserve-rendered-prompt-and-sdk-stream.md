---
id: TASK-DIAG-F4A2
title: Preserve rendered Player prompt + SDK message stream under .guardkit/autobuild/<task>/sdk_debug/
status: backlog
created: 2026-04-25T00:00:00Z
updated: 2026-04-25T00:00:00Z
priority: high
task_type: implementation
parent_review: TASK-REV-F4A1
implementation_mode: task-work
complexity: 3
tags: [autobuild, instrumentation, diagnostic, sdk-debug, post-phase2, follow-up, F4A1-followup-1]
related_to:
  - TASK-REV-F4A1
  - TASK-FIX-7A08
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Preserve rendered Player prompt + SDK message stream under sdk_debug/

## Why

TASK-REV-F4A1's Diagram 2 (cross-boundary sequence trace of a Player invocation)
established that **Hops A/B/C are lossless** (filesystem → Python → SDK call) but
**Hops D/E are opaque** — the JSON serialised onto stdin of the bundled Claude
CLI subprocess and the HTTPS payload to the Anthropic API are not preserved
anywhere in current AutoBuild instrumentation. As a consequence, the review
could not directly annotate Hop F (LLM tool-use decision) with wire-level
prompt evidence, and could only *infer* from code inspection that the
TASK-FIX-7A08 mandate text reaches the Player verbatim.

This task closes that opacity. Once preserved-prompt + preserved-stream
artefacts exist for any AutoBuild run, future analyses (revert verifications,
new fix-attempts, regression diagnoses) can verify Hops D–F with quoted
artefacts rather than inferred behaviour. Specifically: a pre-merge
behavioural verification test for any future prompt-class or structural fix
becomes feasible — the test asserts that the recorded SDK stream contains
`Task(subagent_type="test-orchestrator")` invocations after the fix lands.

This is a prerequisite for the broader follow-up (TASK-FEAT for orchestrator-
side specialist invocation, H-G(b)) and for any future `/task-review` pass
that needs to distinguish "prompt didn't reach the LLM" from "prompt reached
the LLM and was ignored".

## Description

Add diagnostic preservation of the rendered Player prompt and the full SDK
message stream, gated behind an environment variable so normal runs pay no
disk cost.

### Scope (in)

1. In `guardkit/orchestrator/agent_invoker.py`:
   - At the call site of `sdk.query(prompt=..., options=...)` (currently
     `agent_invoker.py:~4851`), if `os.environ.get("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG")`
     is truthy:
     - Compute the per-turn debug directory:
       `<worktree>/.guardkit/autobuild/<task_id>/sdk_debug/turn_<n>/`
     - Write `prompt.txt` containing the exact `prompt` string passed to
       `sdk.query(...)`.
     - Write `options.json` containing a JSON-serialisable view of the
       `ClaudeAgentOptions` (allowed_tools, permission_mode, model, system
       prompt if any).
   - As the SDK message stream is consumed (existing
     `TaskWorkStreamParser` loop), also write each event as a JSONL line to
     `<...>/turn_<n>/messages.jsonl` (one line per event). Capture all event
     types — AssistantMessage, ToolUseBlock, ToolResultBlock, ResultMessage,
     SystemMessage, plus any error messages.
   - Make the write idempotent: if `turn_<n>/` already exists from a prior
     interrupted run, overwrite (do not append) to avoid stale-state bugs.

2. The same preservation should apply to **Coach** invocations
   (`AgentInvoker._invoke_coach` and the independent-test SDK path inside
   `coach_validator.py`), under the same env var. Path:
   `<...>/sdk_debug/turn_<n>/coach/{prompt.txt,options.json,messages.jsonl}`.

3. Logging: when preservation is enabled, log a single info-level line per
   turn naming the directory written, so users running with the env var
   can find the artefacts.

### Scope (out)

- No changes to default behaviour. With the env var unset, AutoBuild runs
  produce no `sdk_debug/` directory and have zero new disk cost.
- No PII redaction or compression. The artefacts are local-only and meant
  for diagnostic inspection.
- No change to the existing `task_work_results.json` writer or to checkpoint
  persistence.
- No CI integration in this task. A follow-up task can wire the env var
  into a CI smoke test once the preservation works.

## Acceptance Criteria

- [ ] `GUARDKIT_AUTOBUILD_PRESERVE_DEBUG=1 guardkit autobuild task TASK-XXX`
      on a small canonical task produces:
      - `.guardkit/autobuild/TASK-XXX/sdk_debug/turn_1/prompt.txt`
      - `.guardkit/autobuild/TASK-XXX/sdk_debug/turn_1/options.json`
      - `.guardkit/autobuild/TASK-XXX/sdk_debug/turn_1/messages.jsonl`
      with non-empty content.
- [ ] `prompt.txt` contains the literal `Task(subagent_type=...)` directive
      from `autobuild_execution_protocol.md` (or the post-revert prompt text,
      whichever is current at the time of the test).
- [ ] `messages.jsonl` is one JSON object per line, parseable by a standard
      JSONL reader. Includes at least one `tool_use` event for the Player's
      first tool call.
- [ ] `coach/messages.jsonl` is produced for the Coach turn under the same
      env var.
- [ ] Default-off behaviour: with the env var unset, no `sdk_debug/`
      directory is produced and existing tests continue to pass.
- [ ] New unit test (`tests/orchestrator/test_sdk_debug_preservation.py`)
      asserts:
      - With env var set, the three files are written.
      - With env var unset, no preservation directory exists.
      - The preserved `prompt.txt` is byte-equal to the prompt the SDK
        was invoked with (use a stub SDK that records its inputs).
- [ ] Architectural review (Phase 2.5) ≥60/100; coverage on changed lines ≥80%.
- [ ] No regression in existing `tests/orchestrator/` suite.

## Implementation Notes

- Keep the preservation logic in a small helper module (e.g.
  `guardkit/orchestrator/sdk_debug.py`) so `agent_invoker.py` and
  `coach_validator.py` both consume one API:
  ```python
  from guardkit.orchestrator.sdk_debug import (
      preserve_prompt, preserve_event, preservation_enabled
  )
  if preservation_enabled():
      ctx = preserve_prompt(task_id, turn_n, role="player",
                            prompt=composed, options=opts)
      async for event in stream:
          preserve_event(ctx, event)
          ...  # existing parser logic
  ```
- The helper should never raise into the AutoBuild hot path; preservation
  failures must be logged as warnings and not abort the run.
- `options.json` should round-trip safely — use `dataclasses.asdict` /
  Pydantic `model_dump` where applicable, fall back to `repr()` for
  non-serialisable fields.

## Notes

- This task is the first of three follow-ups recommended by TASK-REV-F4A1.
  Sibling tasks: TASK-FIX-F4A3 (pollution-detector resume hygiene) and a
  pending `/feature-plan` for orchestrator-side specialist invocation
  (H-G(b)).
- Once this lands, re-running the failed jarvis tasks (J002-008/009/013/014)
  with `GUARDKIT_AUTOBUILD_PRESERVE_DEBUG=1` will produce the wire-level
  evidence Diagram 2 was unable to annotate during TASK-REV-F4A1.
