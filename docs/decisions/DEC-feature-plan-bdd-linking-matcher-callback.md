# DEC — `/feature-plan` Step 11 BDD linking takes a pluggable `matcher` callback, not a direct subagent invocation

**Status:** ACCEPTED (implemented) · **Date:** 2026-04-22 · **Task:** TASK-FP-LNKB-19AC · **Commit:** `55b940543`

## Context

TASK-FP-LINK delivered the mechanical half of the R2 scenario-linking step: a
`bdd_linker` library (`installer/core/commands/lib/bdd_linker.py`) that parses
`features/*.feature` files, emits a structured `MatchingRequest`, and atomically
rewrites the file with `@task:<TASK-ID>` tags once a mapping is confirmed
(stable JSON contract `MatchingRequest` → `TaskMatch[]`).

TASK-FP-LNKB-19AC ("Wire bdd-linker subagent and BDD scenario linking phase
into `/feature-plan`") had to supply the orchestration half — a new **Step 11**
that runs after task creation, obtains scenario→task matches, presents them for
interactive review, and calls `apply_mapping`. The matching decision itself is
made by the `bdd-linker` subagent (`installer/core/agents/bdd-linker.md`), which
reasons over scenario steps + task title/description/ACs.

The tension: the matching decision needs an LLM, but the Python orchestrator
module cannot depend on Claude Code's `Task` tool — that is a runtime-only API
available only in the markdown-driven command flow, not importable from a Python
library or an integration test.

## Decision

`run_linking_phase` accepts a **`matcher` callback** rather than invoking the
`bdd-linker` subagent directly:

```python
MatcherCallback = Callable[[MatchingRequest], object]

def run_linking_phase(project_root, feature_slug, tasks, matcher, *, ...) -> PhaseResult:
```

The Python module owns everything deterministic — feature-file discovery →
`MatchingRequest` construction → interactive review → threshold application →
summary emission — and delegates *only* the scenario→task matching decision to
the injected callback. In production, the `/feature-plan` markdown wraps the
`Task(bdd-linker, ...)` call in a small callback and passes it to
`run_linking_phase`; in tests, a fixture injects canned `TaskMatch` values.

Matcher responses are parsed by `parse_matcher_response`, which raises
`MatcherResponseError` with a *specific* message on any malformed payload
(invalid JSON, missing required field, empty `task_id`) so the command can offer
a retry instead of silently ending up with zero tags.

## Rationale

- **The module must not know about the `Task` tool.** The callback boundary
  keeps `bdd_linking_phase.py` a pure library: no LLM runtime, no Claude Code
  API surface. The subagent invocation lives in markdown where the `Task` tool
  actually exists.
- **Deterministic orchestration is testable without an LLM.** With the matcher
  injected, the integration tests
  (`tests/integration/feature_plan/test_bdd_linking.py`) exercise the full
  parse → review → `apply_mapping` → summary path against mock matchers — no
  need to stand up an inference runtime for coverage.
- **It matches the existing `/feature-plan` architecture** — mechanical Python
  libraries plus markdown-documented subagent invocations — rather than
  introducing an ad-hoc LLM dependency into a library.
- **Fail loud, not silent.** A half-parsed matcher response would look
  identical to "the agent chose to tag nothing". Surfacing a typed
  `MatcherResponseError` prevents the silently-dormant-R2 failure mode that the
  whole task existed to close: a linking phase that quietly emits zero `@task:`
  tags and leaves the BDD oracle inert.

## Consequences / Implementation

In `installer/core/commands/lib/bdd_linking_phase.py`:

- **`MatcherCallback`** type alias (`:75`) — `Callable[[MatchingRequest], object]`;
  accepts either an already-typed `TaskMatch` list or a JSON string/dict/list
  the parser decodes.
- **`run_linking_phase(...)`** (`:478`) — the deterministic orchestrator:
  `discover_feature_file` → `parse_feature_file` → `build_matching_request` →
  `matcher(request)` → `parse_matcher_response` → `_run_interactive_review`
  (or threshold-only under `--no-questions`) → `apply_mapping`, returning a
  `PhaseResult`.
- **`parse_matcher_response(...)`** (`:144`) and **`MatcherResponseError`**
  (`:134`) — the typed error surface: invalid-JSON (`:182`), missing-required-field
  (`:212`), and empty-`task_id` (`:220`) messages.

The production runtime later moved off in-process invocation to a CLI shim,
`installer/core/commands/lib/feature_plan_bdd_link.py` (`prepare`/`apply`
subcommands, `cmd_prepare` `:287` / `cmd_apply` `:404`), driven from
`installer/core/commands/feature-plan.md` Step 11 as two `Execute:` lines
bracketing one `INVOKE Task(bdd-linker, ...)` — see TASK-FIX-RWOP1.1. The
callback contract in this decision is unchanged by that move: the split exists
precisely so the matcher (the subagent) runs *between* `prepare` and `apply`
without Claude-as-runtime composing a Python callback inline. `run_linking_phase`
remains the in-process reference implementation, and its primitives
(`discover_feature_file`, `parse_matcher_response`) are reused by the shim.

## References

- **Task:** `tasks/completed/TASK-FP-LNKB-19AC/TASK-FP-LNKB-19AC.md`
- **Commit:** `55b940543` — "feat(feature-plan): implement automated BDD
  scenario-to-task linking (Step 11)" (created `bdd_linking_phase.py`;
  completion recorded in `8207179c2`)
- **Follow-on:** TASK-FIX-RWOP1.1 (`docs/state/TASK-FIX-RWOP1.1/implementation_plan.md`)
  — repointed the production path to the `feature-plan-bdd-link` CLI shim while
  preserving the callback contract
- **Subagent:** `installer/core/agents/bdd-linker.md`
- **Mechanical library:** `installer/core/commands/lib/bdd_linker.py` (TASK-FP-LINK)
- **Tests:** `tests/integration/feature_plan/test_bdd_linking.py`,
  `tests/integration/feature_plan/test_bdd_linking_end_to_end.py`
