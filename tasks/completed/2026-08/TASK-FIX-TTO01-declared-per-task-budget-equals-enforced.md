---
id: TASK-FIX-TTO01
title: The run declares the per-task time budget it actually enforces
status: completed
task_type: bugfix
priority: high
complexity: 4
implementation_mode: direct
created: 2026-08-01
updated: 2026-08-22
completed: 2026-08-01
completed_location: tasks/completed/2026-08/
record_filed: 2026-08-22
record_provenance: reconstructed-after-the-fact
implementing_commit: 4b04eb7c547067eff13e74056473a49669bf13f9
lane_commit: 032818557fddcb8572cf34a77e1abb2d77606fbb
lane_branch: lane/task-timeout-override
tags: [autobuild, timeout, observability, build-monitor, filed-after-the-fact]
related: [TASK-ATR-001]
---

> **THIS RECORD WAS FILED AFTER THE FACT — 2026-08-22, twenty-one days after the
> work shipped.** No task file existed when the code was written. The code went
> in on **2026-08-01** as commit
> [`4b04eb7c`](https://github.com/appmilla/guardkit/commit/4b04eb7c547067eff13e74056473a49669bf13f9)
> (lane squash `03281855`, branch `lane/task-timeout-override`), and four
> comments inside `guardkit/orchestrator/feature_orchestrator.py` attributed
> that code to a task ID — `TASK-FIX-TTO01` — that had never been written down
> anywhere. The continuous-integration lint
> `tests/rules/test_no_dead_task_id_references.py` caught the dangling reference.
>
> Everything below is **reconstructed from the shipped code and its commit
> history**, not from a plan written in advance. The "Acceptance Criteria"
> section is therefore written as *what the shipped change actually does*, and
> is ticked because the code and its tests are on `main` — not because anyone
> ticked them at the time. Nothing here should be read as evidence that this
> work was specified before it was built. It was not.

# The run declares the per-task time budget it actually enforces

## Plain-language summary

GuardKit can build a software feature by itself: it runs a queue of *tasks*, and
each task gets a **time budget** — a wall-clock limit after which the task is
abandoned. A separate program, the *build monitor* (which lives in the `forge`
repository), watches a running build from the outside and decides when a build
has **wedged** — stopped making progress and needs killing. The monitor works out
how long to wait before calling a build wedged by **reading the budget that
GuardKit prints at the start of the run**.

That printed banner was wrong. It printed the *feature-wide default* budget, not
the budget each task was actually being given. So whenever a task carried its own
longer budget, the watcher outside was set to a shorter fuse than the timer
inside — and would call a perfectly healthy build dead.

A second, smaller problem sat next to it. An operator can ask for a *shorter*
budget for one task. GuardKit silently refuses any request below a hard minimum,
raises it back up, and — before this fix — logged that outcome in exactly the same
words it used when it *had* honoured the request. From the operator's chair the
two were indistinguishable.

This task fixed both: the run now declares the budget it will enforce, and a
request that gets overridden says so out loud.

## The find (2026-08-01, live)

During a live `FEAT-WDG1` build a task carried `autobuild: {task_timeout: 120}`
in its frontmatter (a request for a 120-second budget). The build monitor then
reported `window 3120s from per-task-budget-log`, which read as *"the override
never surfaced at all"*.

The run receipts
(`build-FEAT-WDG1-2026080114/15:*/autobuild-stdout.log`) showed neither of the two
hypotheses in the brief was true. The override **did** load, and **did** reach
`asyncio.wait_for`:

```
[TASK-WDG1-001] Per-task task_timeout override active: frontmatter=120s
× multiplier=1.0 = 120s, floored at 3000s → 3000s (feature default was 3000s)
```

`MIN_TURN_BUDGET_SECONDS` (600s) × `max_turns` (5) = 3000s **raised** the 120s
request — and at default settings that floor happens to equal the feature-level
default, so the enforced number was genuinely 3000s and the monitor's 3120s
window was in fact *correct*. The investigation into a non-bug surfaced two real
seams instead.

## Root cause — the two seams

### Seam 1 — floor swallow (the true defect)

Any per-task budget request below `MIN_TURN_BUDGET_SECONDS × max_turns` (3000s at
defaults) is silently raised to that floor, and was reported under the **same**
`INFO` "override active" wording as a request that was genuinely honoured. Because
the floor coincides with the usual feature default, the resulting number is
indistinguishable from "the override never applied" — both downstream (the build
monitor) and to a human reading the log.

### Seam 2 — declaration/enforcement divergence (latent)

The once-per-run banner printed `self.task_timeout`, the **feature-level default**.
A task running on, say, a 7200s override ran on a budget the banner never
mentioned. Because the build monitor derives its wedge window from that banner, an
override *above* the floor would have put the external watcher **inside** GuardKit's
own timeout — i.e. the watcher would kill a build that was still legitimately
running. This had not yet bitten in production; it would have bitten at the next
above-floor override.

## What was changed

All production changes are in `guardkit/orchestrator/feature_orchestrator.py`.

1. **`_resolve_wave_task_timeouts(feature)` — new.** One pass over
   `orchestration.parallel_groups` *before* wave 1, returning
   `task_id -> effective per-task budget in seconds` in dispatch order. Tasks
   whose markdown will not load are simply absent from the map (the dispatch path
   applies its own fallback and logs there); the method never raises.

2. **`_format_task_timeout_banner(effective_timeouts)` — new.** Builds the
   once-per-run banner text. It declares the **largest** effective per-task
   budget, and names the feature default plus the per-task breakdown alongside
   it. Over-declaring only delays a wedge call; under-declaring kills a healthy
   build — so the maximum is the honest direction.

3. **`_emit_wave0_timeout_warnings` now accepts the precomputed map** and reuses
   it, so each task's budget is resolved (and logged) **once** per run instead of
   twice. Omitting the argument preserves the original behaviour.

4. **Floor-swallow warning in `_resolve_task_timeout`.** When the multiplied
   override lands below the min-turn floor, the log line is emitted at `WARNING`
   with a `— NOT honoured verbatim` clause naming the floor's inputs
   (`GUARDKIT_MIN_TURN_BUDGET`, `--max-turns`) and the escape hatch. The
   docstring's incorrect "honoured verbatim" claim was corrected at the same time.

5. **Grammar preservation.** The message text up to `(feature default was Ns)` is
   byte-preserved so the build monitor's `_OVERRIDE_BUDGET_RE` still parses it.
   A comment at the site says so; a test pins it.

The four code comments that name `TASK-FIX-TTO01` — the ones this record exists
to make honest — are at `feature_orchestrator.py` lines ~2288 (the pre-wave-1
resolve), ~4093 (`_resolve_wave_task_timeouts` docstring), ~4129
(`_format_task_timeout_banner` docstring) and ~4313 (the floor-swallow warning).

## Acceptance criteria (as shipped)

- [x] The once-per-run banner declares the **largest effective** per-task budget,
      not the feature-level default.
- [x] When the declared budget differs from the feature default, both numbers plus
      the per-task breakdown appear in the banner.
- [x] Every queued task's effective budget is resolved exactly once per run, before
      wave 1, and the same map feeds the banner and the wave-0 warnings.
- [x] The number the banner declares is the number `asyncio.wait_for` receives
      (pinned by test, both halves asserted against each other).
- [x] A per-task budget request that the min-turn floor raises is logged at
      `WARNING` with an explicit "NOT honoured verbatim" clause naming the floor's
      inputs and the escape hatch.
- [x] The log grammar consumed by the `forge` build monitor
      (`_OVERRIDE_BUDGET_RE`, banner regex) is byte-preserved and pinned by test.
- [x] Timeout **multiplier** semantics are unchanged.
- [x] Resolution never raises on unloadable task markdown.

## Test coverage

`tests/unit/test_feature_orchestrator.py`, class
`TestPerTaskBudgetDeclarationParity` — **+10 tests**, driven from **real task
markdown on disk** rather than dictionary fixtures, including the exact 120s
shape from the live find:

- `test_live_find_override_120_loads_but_floor_swallows_it`
- `test_floor_swallow_warning_still_parses_with_monitor_grammar`
- `test_override_above_floor_keeps_info_and_is_honoured`
- `test_resolve_wave_task_timeouts_reads_real_task_files`
- `test_banner_declares_effective_budget_not_feature_default`
- `test_banner_unchanged_when_no_task_exceeds_the_default`
- `test_banner_falls_back_to_default_when_nothing_resolved`
- `test_wave0_warnings_reuse_the_precomputed_map`
- (plus two wave-dispatch parity cases asserting banner number == `wait_for` number)

**8 of the 10 failed on `main`** before the change. The `forge` build monitor's
banner and override regular expressions are mirrored into the test file so that
GuardKit cannot silently drift out of a grammar another repository parses.

Counts recorded at the time (same command, same virtual environment,
`-p no:randomly --no-cov`):

| Selection | Lane | `main` |
|---|---|---|
| timeout families (8 files) | 268 passed / 5 failed | 258 passed / 5 failed |
| `tests/unit/orchestrator` | 905 passed / 4 failed | 905 passed / 4 failed |

The 5 `test_autobuild_timeout_budget` failures and 4 coach-grammar failures were
pre-existing on `main` and untouched.

## Notes

- **Relationship to `TASK-ATR-001`** (`tasks/completed/2026-04/`): that task
  introduced the per-task `autobuild.task_timeout` override and its resolver.
  This task did not change what gets *enforced* — it made what the run *says*
  match it, and made a silently-overridden request audible.
- **Cross-repository coupling.** GuardKit's log text is a parsed interface for the
  `forge` build monitor. Any future edit to the banner or the override log line
  must keep the grammar up to `(feature default was Ns)` intact; the mirrored
  regular expressions in `tests/unit/test_feature_orchestrator.py` are the
  tripwire.
- **Why this record exists.** The lint
  `tests/rules/test_no_dead_task_id_references.py` requires that any task
  identifier named in orchestrator code resolve to a filed record. Four sites
  named `TASK-FIX-TTO01` and nothing resolved. The work was real; only the
  paperwork was missing, so the paperwork was written — dated honestly, and
  marked as reconstruction.
