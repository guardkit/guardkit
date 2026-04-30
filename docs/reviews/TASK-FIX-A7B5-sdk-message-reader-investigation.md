# TASK-FIX-A7B5 — SDK Message Reader Transport Failures: Investigation Deferral Note

**Status**: Partial. AC-004 (log dedup) shipped this task. AC-001/002/003 deferred to follow-up that depends on TASK-REV-COSE.

**Date**: 2026-04-30

**Cross-reference**: §4 of `<sibling>/.claude/reviews/TASK-REV-AB7A-report.md`.

## Origin

The autobuild run for FEAT-70A4 in the sibling `study-tutor` repo emitted

```
Fatal error in message reader: Command failed with exit code 1
```

at every Coach SDK pytest gate (5 occurrences in a 27-minute run). Coach's SDK-first dispatch already catches the underlying `ProcessError` and falls back to direct subprocess execution, so the line is benign — but it dominates run output and, until classified, is indistinguishable from a real transport defect.

## Source: upstream, not guardkit

The literal "Fatal error in message reader" log line lives in the pip-installed `claude_agent_sdk`:

- `claude_agent_sdk/_internal/query.py:308` — `logger.error(f"Fatal error in message reader: {e}")` fires when `transport.read_messages()` raises any exception.
- `claude_agent_sdk/_internal/transport/subprocess_cli.py:673-679` — raises `ProcessError(f"Command failed with exit code {returncode}", exit_code=returncode, stderr="Check stderr output for details")` after `await self._process.wait()` returns non-zero.

Crucially, **stdout JSON drains successfully before the error fires**. The CLI delivers its result, then exits non-zero on `_process.wait()`. The "transport failure" framing in the original task body is misleading — there is no actual transport breakage.

## Coach launch site

- `guardkit/orchestrator/quality_gates/coach_validator.py` — `run_independent_tests()` SDK-first dispatch with structured `ProcessError` handling at the per-message level (introduced by TASK-FIX-7A09) plus an outer fallback that logs and routes to subprocess execution.

## Hypothesis ranking

Two candidate classifications survived triage:

1. **CLI exit-code semantics** (most likely): `claude` CLI exits non-zero after delivering its result, possibly because Coach's `max_turns=1` + single-`Bash`-tool option pattern terminates the agent loop in a way the CLI interprets as non-clean exit. Pattern matches: deterministic firing once per Coach gate, JSON delivered cleanly before the error.
2. **stdin-close race**: SDK closes stdin to CLI before CLI writes its final result/control message, CLI exits non-zero.

**Discriminating evidence required**: the actual CLI stderr. The SDK currently sets `ProcessError.stderr` to the placeholder `"Check stderr output for details"` (`subprocess_cli.py:677`) — real stderr is never captured.

## Why root cause is blocked on TASK-REV-COSE

[TASK-REV-COSE](../../tasks/) covers exactly the opaque-stderr observability gap described above. Without real CLI stderr, the upstream-vs-guardkit blame call cannot be made from log evidence. Filing an upstream bug report against `claude_agent_sdk` with only "exit code 1, no stderr" would be a weak report. The right sequencing is:

1. **TASK-REV-COSE lands real CLI stderr capture** in `coach_validator`'s SDK dispatch.
2. **Follow-up task** (filed alongside this rescope — see [TASK-FIX-A7B7](../../tasks/backlog/) when present) repeats this investigation with real stderr in hand and pins the cause.
3. Either **fix in guardkit's SDK adapter** (if the bug is on guardkit's side of the contract — e.g., `max_turns=1` is misused) or **file upstream** with a strong repro and minimal classification.

## Surprising finding that shaped the rescope

[TASK-FIX-7A09](../../tasks/) (visible in `coach_validator.py` `_run_tests_via_sdk` exception cascade) deliberately restructured the SDK error path so transport-level failures bubble with structured diagnostics rather than being swallowed silently. **The visible "Fatal error in message reader" fallback noise is partly by-design.** AC-004 as originally written ("reduce the log-level of the fallback-path line") would partially undo TASK-FIX-7A09's intent if implemented inside the fallback path itself.

The compromise shipped here: AC-004 is satisfied at the **upstream logger boundary**, not by changing guardkit's fallback handling. The upstream `claude_agent_sdk._internal.query` logger receives a `MessageReaderDedupFilter` that promotes the first occurrence per process to WARNING (still visible) and demotes subsequent occurrences to DEBUG (silenced under default INFO logging). TASK-FIX-7A09's structured-error path inside guardkit is left untouched.

## What this task ships (AC-004)

- `guardkit/orchestrator/sdk_utils.py` — `MessageReaderDedupFilter` class + `install_sdk_message_reader_dedup_filter()` idempotent installer.
- `guardkit/orchestrator/__init__.py` — installs the filter on package import. All three SDK call sites (`coach_validator`, `task_work_interface`, `agent_invoker`) transitively import the orchestrator package, so the filter is active for any guardkit SDK usage.
- `tests/unit/test_sdk_message_reader_dedup.py` — 8 tests covering first-match WARNING, subsequent-match DEBUG, unrelated ERROR pass-through, install idempotency, and end-to-end behaviour through `caplog`.

## What this task defers

- **AC-001** (root cause classification with evidence): blocked on TASK-REV-COSE.
- **AC-002** (minimal reproducer): synthetic shim is feasible now but only reproduces the symptom, not the cause. Real-CLI repro that pins the cause should pair with TASK-REV-COSE landing.
- **AC-003** (disposition: fix in guardkit OR file upstream): cannot be decided without root cause from AC-001.

These are filed under follow-up task TASK-FIX-A7B7 with `depends_on: [TASK-REV-COSE]`.

## Precedent

- Format follows `docs/reviews/TASK-INV-7c71-investigation-report.md`.
- Topic-adjacent: `docs/reviews/autobuild-fixes/db_failed_after_sdk_refactor.md` and `docs/reviews/bdd-acceptance-wired-up/forge-run-3-analysis.md` (the latter at line 155 first surfaced this noise during forge-run-3 analysis; this task is a continuation of the TASK-FIX-7A09 thread).
