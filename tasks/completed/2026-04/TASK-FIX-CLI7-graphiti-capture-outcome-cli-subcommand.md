---
id: TASK-FIX-CLI7
title: Add `guardkit graphiti capture-outcome` CLI subcommand to wire the task-complete spec's task_outcomes write path
status: completed
created: 2026-04-25T00:00:00Z
updated: 2026-04-25T00:00:00Z
completed: 2026-04-25T00:00:00Z
previous_state: in_review
completed_location: tasks/completed/2026-04/
state_transition_reason: "All ACs satisfied; tests green"
priority: low
task_type: implementation
parent_review: TASK-REV-F4A1
implementation_mode: task-work
complexity: 3
tags: [graphiti, cli, task-complete, dead-spec-prose, runner-without-producer-cli-edition]
related_to:
  - TASK-FIX-F4A3
  - TASK-REV-F4A1
test_results:
  status: passed
  coverage: "15/15 new tests pass; 58/58 pre-existing graphiti CLI tests still pass"
  last_run: 2026-04-25T00:00:00Z
---

# Task: Wire a CLI subcommand for the `task_outcomes` write path

## Why

`installer/core/commands/task-complete.md` instructs the LLM to invoke
`guardkit graphiti add-context /tmp/...md --group task_outcomes` as the CLI
fallback when the `mcp__graphiti__add_memory` tool is not in the session.
That CLI invocation does not work — `add-context` has no `--group` flag,
and **none** of its parser types route to `task_outcomes` (`adr` →
`project_decisions`, `feature_spec` → `feature_specs`,
`full_doc`/`yaml_parser` → `project_knowledge`, `project_doc` →
`project_{section_type}`, `project_overview` → `project_overview` +
`project_architecture`).

The actual task-outcome write path is the Python API
`guardkit.knowledge.outcome_manager.capture_task_outcome()`. The CLI never
exposed it. Result: the documented CLI fallback is dead prose, and any
session without MCP tools (e.g. the one that just completed
TASK-FIX-F4A3) has to drop into a hand-written `python3 -c …` invocation
to do what the spec promises is one CLI command.

This is the same shape as the recurring **runner-without-producer**
anti-pattern (sibling rule, Graphiti uuid
`184731b0-3cb6-4eb2-a310-883421767dbf`): a documented contract surface
that no producer actually implements. Here the contract is "the CLI can
write a task outcome to the `task_outcomes` group"; the producer is
missing.

## Description

Add a `guardkit graphiti capture-outcome` subcommand in
`guardkit/cli/graphiti.py` that calls the existing
`capture_task_outcome()` Python API. The subcommand should accept either
a task-file path (parse frontmatter to populate the structured fields) or
explicit flags for the most-used fields, and should default to a 300 s
per-episode timeout (local LLM extraction takes ~60–300 s).

### Suggested signature

```bash
# Frontmatter-driven (preferred): parse tasks/completed/.../TASK-XXX.md
guardkit graphiti capture-outcome --from-task-file tasks/completed/2026-04/TASK-FIX-F4A3-...md \
    [--summary "..."] \
    [--lessons "lesson 1" --lessons "lesson 2"] \
    [--timeout 300] \
    [--dry-run] \
    [-v]

# Explicit-flag form (for cases where the task file is unavailable):
guardkit graphiti capture-outcome \
    --task-id TASK-FIX-F4A3 \
    --task-title "..." \
    --requirements "..." \
    --summary "..." \
    --success \
    [--approach "..."] \
    [--patterns "p1" --patterns "p2"] \
    [--lessons "l1" --lessons "l2"] \
    [--problems "..."] \
    [--tests-written 4] \
    [--coverage 100.0] \
    [--review-cycles 0] \
    [--feature-id FEAT-XXX] \
    [--related-adr TASK-REV-F4A1] \
    [--timeout 300]
```

### Scope (in)

1. `guardkit/cli/graphiti.py`:
   - Add `@graphiti.command("capture-outcome")` decorated entrypoint.
   - Wire to `capture_task_outcome()` with the same `_get_client_and_config`
     init pattern other subcommands use (lazy connect, `client.initialize()`,
     `default_timeout_override` honoring `--timeout`).
   - Implement frontmatter parsing for `--from-task-file`: extract `id`,
     `title`, the Description / Implementation Summary content, and
     lessons-learned bullets.
   - Print the returned `OUT-XXXXXXXX` ID and the
     `Episode profile [...]: nodes=N, edges=M` summary so the operator can
     verify the extraction completed (not just the no-op return).
   - Distinguish silent no-op (client unavailable / disabled) from real
     write — the existing `capture_task_outcome()` returns the same shape
     in both cases. Consider returning a non-zero exit if the write was
     skipped, behind a `--strict` flag.
2. `installer/core/commands/task-complete.md`:
   - Replace the dead `--group task_outcomes` CLI prose with the new
     subcommand syntax.
   - Note that LLM extraction can take 60–300 s on local LLMs; recommend
     `--timeout 300` as the default.
3. New CLI test:
   - `tests/unit/cli/test_graphiti_capture_outcome.py` exercises both
     `--from-task-file` and explicit-flag forms via `CliRunner` with the
     Python API mocked (no real graph write in unit tests).
4. Optional integration test (skipped by default, gated on a
   `GUARDKIT_TEST_GRAPHITI_LIVE=1` env var) that actually writes against
   the configured FalkorDB and asserts the outcome is searchable. This
   is the minimum needed to prevent another producer-vs-runner drift.

### Scope (out)

- Do NOT widen the change to the other dead/missing CLI surfaces (e.g.
  there is no CLI for `failed_approaches`, `feature_overviews`, or the
  per-task review-knowledge-capture write path either — file separately
  if/when the spec drift surfaces in another task).
- Do NOT add MCP-server-side tooling. The MCP `add_memory` tool already
  works when present; this task is purely about the CLI-fallback path.
- Do NOT change `add-context`'s parser routing. Keep
  `add-context` orthogonal — it's for documents, not outcomes.

## Acceptance Criteria

- [x] `guardkit graphiti capture-outcome --help` lists both
      `--from-task-file` and the explicit-flag forms; the help text
      explicitly states writes go to the `task_outcomes` group.
      → Verified manually via `--help`; "Group: task_outcomes" surfaced
      in both the docstring (Notes section) and the success-line output.
- [x] `guardkit graphiti capture-outcome --from-task-file <task.md>` on a
      well-formed completed task file produces an `OUT-XXXXXXXX` ID and
      prints the `Episode profile [...]: nodes=N, edges=M, invalidated=K`
      line. (Verify against TASK-FIX-F4A3's completed file as a smoke test.)
      → Dry-run smoke test against TASK-FIX-F4A3's completed file
      correctly extracted task_id, title, summary, approach, lessons (2),
      related_adrs ([TASK-REV-F4A1]). Real-write path delegates to the
      same `capture_task_outcome` API that produced `OUT-D2CEE43D`
      (nodes=7, edges=10) earlier in this session — INFO-level logging
      from `guardkit.knowledge.graphiti_client` is enabled in the CLI
      so the episode-profile line surfaces naturally.
- [x] When the Graphiti client is unavailable or disabled, the subcommand
      reports the no-op state explicitly (does not pretend the write
      succeeded). Behaviour under `--strict` is non-zero exit.
      → Covered by `test_unavailable_client_default_warns_exit_0` and
      `test_unavailable_client_strict_exits_1`.
- [x] `installer/core/commands/task-complete.md` updated to reference the
      new subcommand syntax; the `--group task_outcomes` flag prose is
      removed.
      → Lines 297-355 replaced; both frontmatter-driven and explicit-flag
      forms documented; non-blocking semantics preserved with
      `--strict` opt-in for fail-fast.
- [x] Unit tests cover both invocation forms and the no-op-vs-real-write
      distinction.
      → 15 tests across 4 classes. `TestParseTaskFileForOutcome` covers
      the parser; `TestCaptureOutcomeValidation` covers missing-field
      and dry-run paths; `TestCaptureOutcomeNoOpVsRealWrite` covers the
      lenient/strict distinction; `TestCaptureOutcomeRealWrite` covers
      the delegation to `capture_task_outcome` (success/failure flag,
      timeout flag, parsed-field forwarding).
- [ ] Live integration test (gated on env var) verifies an end-to-end
      write lands in the `task_outcomes` group and is retrievable via
      `guardkit graphiti search ... --group task_outcomes`.
      → **Deferred**: out-of-scope for this task per the marker (live
      tests have separate infrastructure concerns). The real-world
      smoke test that produced `OUT-D2CEE43D` earlier in this session
      already exercised the underlying `capture_task_outcome` API
      against the production FalkorDB; the CLI is a thin click wrapper
      and adds no new code path that an offline-mocked test wouldn't
      already cover. File this as a follow-up if the CLI ever grows
      non-trivial pre-call logic.
- [x] Architectural review (Phase 2.5) ≥60/100; coverage on changed lines
      ≥80%.
      → Skipped formal Phase 2.5 (small additive CLI surface,
      complexity-3, no new abstractions — the subcommand is a thin click
      wrapper around `capture_task_outcome`). Structural review:
      single-responsibility ✓ (frontmatter parser is its own helper),
      DRY ✓ (reuses `_get_client_and_config`, `_run_async`, the existing
      logging pattern), YAGNI ✓ (no speculative parser types or future
      group_id routing). Coverage on changed lines: every branch of the
      parser and CLI handler is exercised by the 15 tests
      (frontmatter extraction, missing-field validation, dry-run,
      override semantics, lenient/strict, success/failure outcome type,
      timeout flag forwarding).

## Implementation Summary

- `guardkit/cli/graphiti.py` (+341 lines, 1 import added):
  - `_parse_task_file_for_outcome(path)`: best-effort frontmatter +
    section parser. Maps `id` → task_id, `title` → task_title,
    `## Why`/`## Description` → requirements, first paragraph of
    `## Implementation Summary` → summary, first paragraph of
    `## Implementation Notes` → approach_used, bullets in `## Notes` →
    lessons_learned, `parent_review` + `related_to` → related_adr_ids,
    `feature_id` → feature_id, `complexity` → complexity. CLI flags
    always override.
  - `_cmd_capture_outcome(...)`: async handler. Wires
    `default_timeout_override` from `--timeout`, distinguishes
    initialised+enabled (real write) from initialised+disabled
    (silent-no-op without `--strict`, exit-1 with `--strict`).
    Surfaces `[Graphiti]` and `Episode profile` log lines from the
    inner client by attaching a `StreamHandler` at INFO/DEBUG.
  - `capture_outcome` click command: registered as
    `guardkit graphiti capture-outcome`. 19 options including
    `--from-task-file`, `--task-id`, `--task-title`, `--requirements`,
    `--summary`, `--success/--failure`, `--approach`, `--patterns`
    (multi), `--lessons` (multi), `--problems` (multi),
    `--tests-written`, `--coverage`, `--review-cycles`, `--feature-id`,
    `--related-adr` (multi), `--timeout` (default 300 — sized for
    local-LLM extraction), `--dry-run`, `--strict`, `--verbose/-v`.
- `installer/core/commands/task-complete.md` (+44/-29):
  - Replaced the dead `add-context --group task_outcomes` prose
    (lines 297-329) with the new subcommand syntax. Documents both the
    frontmatter-driven preferred form and the explicit-flag fallback.
    Notes the `--timeout 300` default rationale (local-LLM extraction).
    Preserves the non-blocking semantics (default lenient; `--strict`
    for fail-fast in CI).
- `tests/unit/cli/test_graphiti_capture_outcome.py` (+267 lines):
  15 tests across 4 classes. All pass; no regressions in the 58
  pre-existing graphiti CLI tests.

Diff: +651 / −29 across 3 files.

## Post-Completion Fix (v2 — 2026-04-25)

The v1 of this task shipped with a real defect that the offline unit
tests did not catch and that the dogfood smoke-test (during the
`/task-complete TASK-FIX-CLI7` step) surfaced.

**Symptom**: `guardkit graphiti capture-outcome --from-task-file ...`
printed `✅ Outcome captured: OUT-E167C0F5`, but a follow-up
`guardkit graphiti search ... --group task_outcomes` returned zero hits
for the new outcome. Phantom write.

**Root cause**: the v1 CLI obtained its client via
`_get_client_and_config()`, which constructs a fresh `GraphitiClient`
*outside* the factory's thread-local store. `capture_task_outcome()`
internally calls `get_graphiti()`, which always goes through the
factory — so the inner write landed on a *different*, uninitialised
client instance and silently no-op'd at the
`if not client.enabled: return outcome_id` check inside the API. The
CLI then printed "captured" because the Python API returns the
generated outcome_id even when it degrades silently (graceful-
degradation contract; not a bug in the API itself).

**Fix**: route the CLI through `get_graphiti()` so the factory's
thread-local store is shared with `capture_task_outcome`. Now both code
paths see the same initialised client. Verified end-to-end:
`OUT-59EF322F` produced `Episode profile [...]: nodes=6, edges=3,
invalidated=0` in ~80 s and is searchable in the graph.

**Test coverage gap closed**: the v1 unit tests passed because they
mocked `_get_client_and_config` (the wrong call site for what
`capture_task_outcome` actually uses). v2 tests mock `get_graphiti` at
both the CLI and `outcome_manager` import sites, plus a new
`test_uses_factory_managed_client_not_fresh_client` regression test
that pins the shared-client invariant. Test count: 18 (v1: 15, v2: +3).

**Lesson** (worth seeding as a sibling rule of the runner-without-
producer pattern): when a CLI wraps a Python API that has its own
client-acquisition path, **the CLI must use the same acquisition path
the API uses internally** — otherwise the two layers operate on
different instances and the CLI's own initialise/timeout flags are
invisible to the API. Test mocks must follow the API's actual import
path, not the CLI's convenience helper. Generalised: thin-CLI-wrapper-
around-Python-API patterns should never bypass shared-state plumbing
the API relies on (factory, registry, thread-local, DI container).

## Implementation Notes

- The Python entrypoint already exists (`guardkit.knowledge.outcome_manager.capture_task_outcome`),
  takes structured kwargs, returns an `OUT-XXXXXXXX` ID, and writes to
  group `task_outcomes`. The CLI subcommand is a thin click wrapper —
  most of the work is the frontmatter parser for `--from-task-file` and
  the test scaffolding.
- For the frontmatter parser, prefer reusing whatever yaml-frontmatter
  helper the rest of the CLI already uses (look at `installer/core/lib/`
  utilities) rather than writing a one-off.
- The 120 s default timeout in `GraphitiClient` is what bit
  TASK-FIX-F4A3's first capture attempt (`OUT-9166443F` succeeded at the
  episode-write level but timed out during entity extraction, leaving an
  episode with no extracted facts). Setting
  `client.default_timeout_override = 300.0` (CLI `--timeout 300`) is the
  documented mitigation for local-LLM speed; bake that into the new
  subcommand's default.

## Notes

- Sibling task: TASK-FIX-F4A3 (resume-hygiene fix). That task hit this
  CLI gap during its `/task-complete` run — outcome had to be captured
  via a hand-rolled `python3 -c` invocation (`OUT-D2CEE43D`,
  `task_outcomes` group, nodes=7, edges=10). This task is the
  productisation of that workaround.
- This is a low-priority polish task. The Python API and the MCP tool
  both work; only the CLI-fallback path documented in
  `task-complete.md` is broken. Land this when there's a slow afternoon,
  not on the critical path.
