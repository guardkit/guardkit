---
complexity: 4
consumer_context:
- contract: REDACTION_PIPELINE
  driver: guardkit/orchestrator/instrumentation/redaction.py
  format_note: SecretRedactor (:60), 7 default regex patterns (:37-53) -> '[REDACTED]'
  producer: TASK-INST-003 (completed 2026-03)
created: 2026-07-09
decision_of_record: D-OBS-2 unconditional prerequisite (redaction pass extended to
  message streams)
dependencies: []
feature_id: FEAT-OBSC
id: TASK-OBS-C440
implementation_mode: task-work
priority: high
status: completed
task_type: feature
title: Extend secret redaction to sdk_debug message streams
wave: 3
---

# TASK-OBS-C440: Extend secret redaction to sdk_debug message streams

## Description

D-OBS-2 makes this an **unconditional prerequisite** of the default-on flip
(TASK-OBS-396E): today `sdk_debug` preserves raw rendered prompts and the full SDK
message stream with **zero scrubbing** — `sdk_debug.py` imports no redactor and
writes `prompt.txt` raw (`:262-263`), `options.json` raw (`:265-270`), and
`messages.jsonl` raw including the recursive `.raw` payload walk (`:297-311`,
`:207-231`). `SecretRedactor` currently covers only ToolExecEvent fields
(`agent_invoker.py:4536-4540`). Given the 80-minute FinProxy leak incident and client
data in prompts, default-on capture without stream redaction is prohibited.

Scope note on the existing separate-scope design: `guardkit/lib/secret_scrub.py`
(TASK-AB-SECRETSCRUB01) is a *publication-boundary* scrubber whose docstring states
the Coach must see raw evidence in the gitignored `.guardkit/autobuild/` dirs. That
design holds: the Coach reads `player_turn_N.json` / `task_work_results.json`, **not**
sdk_debug. Redacting sdk_debug streams does not change what any gate sees. Player /
Coach turn-JSON evidence stays out of scope here.

## Changes

1. Apply `SecretRedactor` to every sdk_debug write path:
   - `preserve_prompt` — redact the rendered prompt before `write_text` (`:262-263`)
     and the options snapshot (`:265-270`);
   - `preserve_event` — redact string content in the serialized event line, including
     the recursive raw-payload walk output (`:207-231`, `:297-311`).
2. Redact at serialization time (strings in the JSON line), not by mutating live SDK
   message objects — the stream consumed by the harness must be untouched.
3. Keep the never-raise-into-the-hot-path guarantee (`sdk_debug.py:15-16`): a
   redaction error degrades to **dropping the line with a `[REDACTION-FAILED]`
   marker written in its place** — never writing the raw payload, and never raising.
   (Fail-closed for content, fail-open for control flow.)
4. Pattern set: reuse the existing `SecretRedactor` default patterns; add patterns
   only if the WS4 Appendix A conformance pass (TASK-OBS-396E) surfaces gaps.
   Configurability stays as-is (constructor-injected pattern list).

## Acceptance Criteria

- [ ] AC-1: A run with a planted secret (e.g. `sk-…`, `Bearer …`, `PASSWORD=…`) in
      prompt content and in tool output produces sdk_debug files where every planted
      secret reads `[REDACTED]` — asserted positively per file (prompt.txt,
      messages.jsonl, options.json).
- [ ] AC-2: Non-secret content is byte-identical to the unredacted baseline
      (redaction must not corrupt the trace's training value).
- [ ] AC-3: A forced redaction failure (monkeypatched redactor raising) yields the
      `[REDACTION-FAILED]` placeholder line, no raw payload on disk, and no exception
      reaching the invocation hot path.
- [ ] AC-4: The Coach-facing evidence files (`player_turn_N.json`,
      `task_work_results.json`) are untouched by this task — pinned by a test
      (feature-build-invariants: gates keep seeing raw evidence).
- [ ] AC-5: Redaction happens on every capture write path — the prompt preservation
      (`agent_invoker.py:3966` → `preserve_prompt`), the per-event stream path
      (`agent_invoker.py:4206-4210` → `preserve_event`), and CoachValidator's
      independent-test stream preservation (`coach_validator.py:~4784-4832`) —
      whichever writes, writes redacted. (`sdk_harness.py:154/171` merely stores
      `sdk_debug_dir` and never writes it — the orchestrator owns sdk_debug
      instrumentation; do not "fix" the harness.)

## Test Strategy

Unit tests on the two sdk_debug write paths with planted-secret fixtures; a
round-trip test asserting non-secret byte identity; the failure-path test per AC-3.