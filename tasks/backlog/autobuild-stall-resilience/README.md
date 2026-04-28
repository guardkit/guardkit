# autobuild-stall-resilience (FEAT-ABSR-9C6E)

**Parent reviews**:
- [TASK-REV-FA04](../../../.claude/reviews/TASK-REV-FA04-report.md) — Waves 1-2 (closed langchain trapdoor)
- [TASK-REV-9D13](../../../.claude/reviews/TASK-REV-9D13-report.md) — Waves 3-5 (closes post-Player-specialist-stall)

**Origin incidents**:
- Wave 1-2: Jarvis FEAT-J004-702C / TASK-J004-004 `unrecoverable_stall` (2026-04-27)
- Wave 3-5: Jarvis FEAT-J004-702C / TASK-J004-013 `timeout_budget_exhausted` (2026-04-28, _after_ Wave 1-2 fixes deployed; new failure mode)

**Hash signature of the original failing-feedback loop**: `9c6e2dee` (referenced in feature_id)
**Tight deadline**: DDD South West (~20 days from 2026-04-28). Autobuild builds jarvis/study-tutor/forge for the demo.

## Problem (one-paragraph summary)

`guardkit autobuild feature FEAT-J004-702C` against the Jarvis repo terminated with `UNRECOVERABLE_STALL` after Wave 1 of 7. Three of four Wave-1 tasks ran in `direct` mode and succeeded in 1 turn each; **TASK-J004-004** (`task_type=declarative`, `implementation_mode=task-work`, Pydantic routing-history schema) ran 3 Player+Coach turns producing identical Coach feedback — the same `failure_classification=infrastructure / failure_confidence=ambiguous` signature each turn — and was killed by the feedback-stall detector after 33 minutes. The actual cause was an environment mismatch (`/usr/local/bin/python3` is 3.14 on the user's Mac; Jarvis's `pyproject.toml` declares `requires-python='>=3.12,<3.13'`). Bootstrap silently continued past the mismatch (`bootstrap_failure_mode` defaults to `warn`), Wave 1 ran on a broken environment, and `import jarvis` failed in Coach's independent test verification. The Player had no actionable path because no code change can fix `import jarvis` when there's no editable install. The post-loop hint suggested "Review task_type classification" — the wrong diagnosis entirely.

The same broken bootstrap had been silent for every Mac-side Jarvis run since 3.14 became default; FEAT-J002 succeeded only because **all** its tasks ran in `direct` mode (which bypasses the Coach independent-test gate). FEAT-J004-702C is the **first** Jarvis feature to mix `direct` + `task-work`, and TASK-J004-004 is the **first** task to combine `task_type=declarative` + `implementation_mode=task-work` + a regression test that does `subprocess.run([python, "-c", "import jarvis"])`. That four-way intersection opened the trapdoor.

## Solution Approach (in one paragraph)

Close the incident class with **two complementary safety nets** scoped to GuardKit:

1. **Preflight prevention** (TASK-ABSR-A1B2 + TASK-ABSR-C3D4): smart-default `bootstrap_failure_mode` to `block` when any manifest declares `requires-python`, and replace the misleading stall hint with an environment-aware diagnostic naming the actual interpreter, the manifest constraint, and the `uv`/`pyenv`/`conda` remediation. After this, doomed runs abort at preflight with one minute of wall time, not 33 minutes.

2. **In-loop fallback** (TASK-ABSR-2468): if the user explicitly opts into `bootstrap_failure_mode: warn`, the Coach gains a narrow conditional-approval branch for `infrastructure/ambiguous + all-gates-passed + bootstrap-known-broken` so that Player work that is correct gets approved with an environment flag rather than trapped in a feedback stall.

Plus three quality-of-life improvements: standardise the LangChain DeepAgents template `requires-python` to `>=3.11` (open upper bound, matching forge/study-tutor/agentic-dataset-factory/specialist-agent — Jarvis is the lone outlier today) and document the portfolio pinning guide (TASK-ABSR-E5F6); investigate why Player tests passed when Coach's identical pytest command failed (TASK-ABSR-7890); and stop firing the agent-invocations Phase-3 advisory on declarative tasks where no Phase-3 specialist is meaningful (TASK-ABSR-1357).

## Subtasks

### Waves 1-2 (FA04-driven, all completed 2026-04-27/28)

| Wave | ID | Title | Mode | Complexity | Status |
|---|---|---|---|---|---|
| 1 | TASK-ABSR-A1B2 | Smart-default `bootstrap_failure_mode` to `block` when `requires-python` declared | task-work | 4 | ✓ completed |
| 1 | TASK-ABSR-C3D4 | Add `environment_stall` sub-type with env-aware diagnostic | task-work | 5 | ✓ completed |
| 1 | TASK-ABSR-E5F6 | Standardise DeepAgents template `requires-python` + portfolio guide | direct | 2 | ✓ completed |
| 1 | TASK-ABSR-7890 | Investigate Player↔Coach test divergence (review) | direct | 3 | ✓ completed |
| 2 | TASK-ABSR-2468 | Coach conditional-approval for environment-class infra failures | task-work | 6 | ✓ completed |
| 2 | TASK-ABSR-1357 | Suppress declarative-task Phase-3 advisory | task-work | 3 | ✓ completed |

### Waves 3-5 (9D13-driven, backlog 2026-04-28)

| Wave | ID | Title | Mode | Complexity | Status | Priority |
|---|---|---|---|---|---|---|
| 3 | [TASK-ABSR-CEIL](TASK-ABSR-CEIL-skip-phase4-5-on-sdk-ceiling-hit.md) | Skip Phase 4/5 specialists on Player SDK-ceiling hit | task-work | 3 | backlog | **CRITICAL** |
| 3 | [TASK-ABSR-WALL](TASK-ABSR-WALL-cap-specialist-timeout-at-remaining-wall.md) | Cap specialist `sdk_timeout` at remaining wall budget | task-work | 4 | backlog | **CRITICAL** |
| 3 | [TASK-ABSR-FRSH](TASK-ABSR-FRSH-refresh-remaining-budget-post-player.md) | Refresh `remaining_budget` post-Player before specialist guard | task-work | 3 | backlog | HIGH |
| 3 | [TASK-ABSR-DIAG](TASK-ABSR-DIAG-heartbeat-label-fix.md) | Heartbeat label fix for orchestrator-invoked specialists | task-work | 3 | backlog | MED |
| 4 | [TASK-ABSR-MAXT](TASK-ABSR-MAXT-complexity-scale-sdk-max-turns.md) | Complexity-scale `TASK_WORK_SDK_MAX_TURNS` | task-work | 4 | backlog | MED |
| 4 | [TASK-ABSR-MTBC](TASK-ABSR-MTBC-env-overridable-min-turn-budget.md) | Make `MIN_TURN_BUDGET_SECONDS` env-overridable | direct | 1 | backlog | LOW |
| 5 | [TASK-ABSR-CMPL](TASK-ABSR-CMPL-phase-25-complexity-heuristic.md) | Phase-2.5 effective-complexity heuristic (AC + dep + consumer counts) | task-work | 5 | backlog | MED (post-talk) |

**Separately filed** (review task, not under FEAT-ABSR-9C6E):
- [TASK-REV-COSE](../TASK-REV-COSE-diagnose-coach-sdk-test-execution-opaque-stderr.md) — Diagnose Coach SDK-test-execution opaque-stderr (sidequest, low priority)

## Out-of-scope reminder

Per the TASK-REV-FA04 task brief, no changes to the Jarvis repo are filed here. The recommendation to align Jarvis's `requires-python` to `>=3.11` (matching the rest of the portfolio) has been **verified actionable as of 2026-04-27** — `nats-core` PyPI now declares `>=3.10`, so the original Jarvis tight-pin rationale is obsolete. See [IMPLEMENTATION-GUIDE.md → Out-of-Scope: Jarvis-side pin alignment](IMPLEMENTATION-GUIDE.md#out-of-scope-jarvis-side-pin-alignment-consumer-recommendation--verified-2026-04-27) for the exact diff and verification recipe.

## Waves 3-5 problem (one-paragraph summary)

After Waves 1-2 deployed (Bootstrap-mode `block` smart-default, environment_stall sub-type, Coach conditional-approval), Jarvis FEAT-J004-702C run-2 made it through Waves 1-4 cleanly (12/20 tasks, first-attempt pass rate 77%, quality task-success-rate 92%). Wave 5's single task — **TASK-J004-013** (lifecycle wiring, complexity=6, 9 ACs, 7 dependencies, 3 consumer-context interfaces) — failed with `timeout_budget_exhausted` at turn 1. The Player ran 1158 s and **hit the 100-turn SDK ceiling** (101 turns). The orchestrator then admitted the partial Player output to Phase 4/5 specialist invocation (gate at `autobuild.py:2708` only checks `player_result.success`, not `sdk_ceiling_hit`); the Phase-4 `test-orchestrator` specialist consumed its full 1200 s SDK timeout running on partial code (cap-at-remaining-wall helper exists for the Player path but bypassed for specialists at `autobuild.py:2781,2795`); turn-2 was foreclosed at `MIN_TURN_BUDGET_SECONDS=600 s` with only `21.2 s` remaining. **Two compounding bugs**, **either fix saves the task**.

## Waves 3-5 solution approach (in one paragraph)

**Wave 3 closes the post-Player-specialist-stall class of defect** with three parallel-developable fixes: R1 (TASK-ABSR-CEIL, ~6 lines) adds an `sdk_ceiling_hit` short-circuit before specialist invocation; R2 (TASK-ABSR-WALL, ~10 lines) routes specialist timeouts through a new `_cap_specialist_timeout` helper so a single specialist cannot consume the entire remaining wall; R3 (TASK-ABSR-FRSH, ~5 lines) refreshes `remaining_budget` post-Player so the budget guard sees current state, not stale start-of-turn state. R6.b (TASK-ABSR-DIAG, ~10 lines) fixes the heartbeat label confusion that made TASK-REV-9D13 v1 misdiagnose the J004-013 timing. **Wave 4 reduces ceiling-hit rate** generally: R4 (TASK-ABSR-MAXT) complexity-scales `TASK_WORK_SDK_MAX_TURNS` analogously to how `sdk_timeout` is already complexity-scaled at `agent_invoker.py:3853`; R5 (TASK-ABSR-MTBC) makes `MIN_TURN_BUDGET_SECONDS` env-overridable. **Wave 5** (deferred post-talk preferred): R6.a (TASK-ABSR-CMPL) enhances Phase-2.5 complexity scoring with AC count + dep count + consumer-context count signals so structurally complex tasks like J004-013 are flagged for Phase-2.8 split-or-checkpoint review. Plus separately-filed sidequest TASK-REV-COSE for the Coach SDK-test-execution opaque-stderr issue.

## Quick links

- [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) — wave plan, dependencies, test strategy, replay recipe
- [TASK-REV-FA04 review report](../../../.claude/reviews/TASK-REV-FA04-report.md) — Wave 1-2 diagnostic
- [TASK-REV-9D13 review report v2](../../../.claude/reviews/TASK-REV-9D13-report.md) — Wave 3-5 diagnostic with C4 + 3 sequence diagrams + per-line evidence
