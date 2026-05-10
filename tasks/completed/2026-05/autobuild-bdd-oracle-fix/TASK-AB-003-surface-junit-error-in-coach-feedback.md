---
id: TASK-AB-003
title: "Surface junit collection-error message in BDDFailure.reason and Coach feedback"
task_type: feature
parent_review: TASK-REV-8413
feature_id: FEAT-AB-FIX
wave: 1
implementation_mode: task-work
complexity: 4
estimated_minutes: 60
dependencies: []
working_dir: /home/richardwoollcott/Projects/appmilla_github/guardkit
domain_tags:
  - guardkit
  - bdd-oracle
  - feedback
  - observability
status: completed
updated: 2026-05-10T00:00:00Z
completed: 2026-05-10T00:00:00Z
previous_state: in_review
state_transition_reason: "All AC met, tests passing, ready to ship"
---

# TASK-AB-003: Surface junit collection-error message in feedback

## Repository

**Working directory:** this repo (`guardkit`). Parent diagnostic review lives in the sibling
`fleet-gateway` repo at `tasks/backlog/TASK-REV-8413-analyse-autobuild-feat-fg-001-stall.md`.

## Problem

When pytest exits with a collection error (e.g. `ImportError`, `ModuleNotFoundError`,
`SyntaxError`), the bdd_runner constructs:

```
BDDFailure(
    feature_file="",
    scenario_name=<feature path>,
    failing_step="collection failure",
    reason="collection failure",
)
```

The full traceback **is present** in the junit XML
(`.guardkit/bdd/<TASK-ID>_junit.xml`) but the runner does not parse it into `reason`.
The Coach feedback summariser then reduces every BDD failure to the prose:

> *"BDD oracle: 1 scenario(s) failed during pytest-bdd execution. Implementation does
> not satisfy the Gherkin specification."*

This was the second cause of the FEAT-FG-001 stall: the Player saw "Implementation does
not satisfy Gherkin" and tried to fix the implementation, even though the actual error
was `ModuleNotFoundError: No module named 'common'` — a runner-environment problem the
Player had no signal about.

## Scope

Two coordinated edits:

1. **bdd_runner**
   ([`guardkit/orchestrator/quality_gates/bdd_runner.py`](../../../guardkit/orchestrator/quality_gates/bdd_runner.py)):
   when junit XML reports `errors > 0` with no parsable `<failure>` block, parse the first
   `<error>` element's `message` attribute and the inner traceback's last frame, populating
   `BDDFailure.reason` with something like:
   ```
   collection failure: ModuleNotFoundError: No module named 'common'
     at features/.../test_<slug>.py:41 (from common.jarvis_client import ...)
   ```
2. **Feedback summariser**: locate the orchestrator code that builds the Coach-to-Player
   feedback string for `bdd_failure` issues and have it pass `BDDFailure.reason`
   through verbatim instead of substituting the generic *"Implementation does not satisfy
   the Gherkin specification"* prose. The generic prose may stay as a header but must be
   followed by the per-failure `reason` lines.

## Acceptance Criteria

- [x] `BDDFailure.reason` for collection errors includes the junit `<error>` `message` attribute and the *last* traceback frame (file, line, snippet) — not just the literal `"collection failure"`.
- [x] When `<error>` has a python `ImportError` / `ModuleNotFoundError`, `reason` includes the missing module name.
- [x] When `<error>` has any other class (`SyntaxError`, plugin load failure, etc.), `reason` carries the message verbatim — no special-casing required.
- [x] Coach feedback for BDD failures includes the per-failure `reason` strings (one bullet per failure), not only the generic header.
- [x] Existing unit tests for `_extract_failures` / junit parsing continue to pass.
- [x] New unit test: synthetic junit XML with `<error message="collection failure">ImportError ... ModuleNotFoundError: No module named 'common'</error>` produces a `BDDFailure.reason` containing both `"ModuleNotFoundError"` and `"No module named 'common'"`.
- [x] New unit test: feedback summariser given that BDDFailure produces feedback text that *contains* the missing-module string.

## Implementation Summary

**Code changes** (2 files):

- `guardkit/orchestrator/quality_gates/bdd_runner.py` — added `_TRACEBACK_FRAME_RE` and `_extract_error_reason(message, body)` helper. `parse_junit_xml` now branches on `<error>`-only testcases and routes them through `_extract_error_reason` so the resulting `FailureDetail.reason` carries the actual exception class+message and the last traceback frame (file:line + source snippet) instead of the literal `"collection failure"`.
- `guardkit/orchestrator/quality_gates/coach_validator.py` (`_check_bdd_results`) — the `bdd_failure` issue's `description` now embeds per-failure reasons as `- {scenario}: {reason}` bullets under the existing prose header. The Player feedback renderer (`AgentInvoker._format_feedback_for_player`) reads only `description`, so this is the path that propagates the missing-module string to the Player.

**Test changes** (1 file):

- `tests/unit/orchestrator/quality_gates/test_bdd_runner.py` — added `TestCollectionErrorReason` (5 tests) covering the `_extract_error_reason` helper directly and via `parse_junit_xml`, plus a `<failure>`-path regression guard. Added `TestCoachFeedbackEmbedsReason` (1 test) hitting `_check_bdd_results` end-to-end and asserting the description contains the missing-module string.

**Verification**: `pytest tests/unit/orchestrator/quality_gates/test_bdd_runner.py::TestCollectionErrorReason ::TestCoachFeedbackEmbedsReason ::TestParseJunitXml ::TestStepExtraction` → 17 passed.

## Out of Scope

- Re-architecting Coach feedback structure beyond fidelity of the bdd_failure path.
- Translating runner-environment errors into actionable suggestions (the goal is fidelity, not interpretation — let the Player reason from the real error).

## Verification

Inspect a stalled-feature junit XML before and after:
```bash
cat .guardkit/worktrees/FEAT-FG-001/.guardkit/bdd/TASK-FG-002_junit.xml
# verify the same content now flows into Coach feedback verbatim
```
