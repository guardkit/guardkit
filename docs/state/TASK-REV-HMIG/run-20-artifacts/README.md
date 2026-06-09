# Run-20 autobuild artifacts snapshot — 🎉 SUCCESS REPLICATED + COACHTESTTO VALIDATED

> **Purpose**: snapshot the full FEAT-AOF artifact tree from run 20
> (second attempt — first attempt was a 0s skip per
> [TASK-FIX-FRESHRESET01](../../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-FRESHRESET01-fresh-flag-no-op-on-completed-feature.md)).
> Second consecutive end-to-end success — confirms run 19 was not a
> fluke and TASK-FIX-COACHTESTTO closes the run-19 independent-test
> caveat.
>
> **Source**: live worktree artifacts copied 2026-06-09T14:04Z from
> `.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/`.
> **Run log**:
> [`autobuild-FEAT-AOF-run-20-second-attempt.md`](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-20-second-attempt.md)
> (committed in the same change as this snapshot). The 0s first-attempt
> log at
> [`autobuild-FEAT-AOF-run-20.md`](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-20.md)
> is also committed as historical evidence of the FRESHRESET01 bug.

## 🎉 TL;DR — FEAT-AOF COMPLETED again: 3/3 first-pass approve in 52m 31s

```
═════════════════════════════════════════════════════════════
FEATURE RESULT: SUCCESS
═════════════════════════════════════════════════════════════
Status: COMPLETED
Tasks: 3/3 completed
Duration: 52m 31s
```

| Task | Player | Coach | Decision | ACs | Tests passed |
|---|---|---|---|---|---|
| TASK-FIX-IA03 (Wave 1) | ✓ 41 created, 1 modified | ✓ Turn 1 | **approve** | 5/5 | **14 passed in 3.29s** in `test_doc_level_exclusions.py` |
| TASK-FIX-TP05 (Wave 2) | ✓ 4 created, 3 modified | ✓ Turn 1 | **approve** | 6/6 | **140 passed in 3.62s** in `test_agent_invoker_git_delta.py + test_task_types.py` |
| TASK-FIX-GD02 (Wave 2) | ✓ 4 created, 3 modified | ✓ Turn 1 | **approve** | 7/7 | **140 passed in 3.58s** in same files |

Within ~10s of run 19's 52m 4s wall-time. Reproducibility confirmed.

## TASK-FIX-COACHTESTTO ✅ VALIDATED

The single most important new datapoint vs run 19:

- **Run 19** ([run-19 log:197,540,545](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-19.md#L197)):
  `ERROR: SDK coach test execution timed out after 300s` on all three
  tasks. First-pass approval rested on Player self-reported tests +
  deterministic non-test gates, NOT on the Coach's own test execution.
- **Run 20** ([run-20:202](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-20-second-attempt.md#L202)):
  `Independent tests passed in 3.9s` ← **TASK-FIX-COACHTESTTO bypass-LLM
  path completed cleanly**. Coach saw real independent-test results
  (`tests_run: true, tests_passed: true` with specific commands and
  output summaries — see the three `coach_turn_1.json` files).

The TASK-FIX-COACHTESTTO contract (Coach independent tests bypass LLM
under LangGraph; mark non-completion ABSENT) is now empirically
validated. The "non-completion → ABSENT" fallback path was not needed
this run because the bypass-LLM path completed for all three tasks.
That fallback remains as defence-in-depth; future evidence will show
whether it ever fires.

## The three Coach verdicts in this snapshot

### TASK-FIX-IA03 ([`coach_turn_1.json`](TASK-FIX-IA03/coach_turn_1.json))

```json
{
  "task_id": "TASK-FIX-IA03",
  "turn": 1,
  "decision": "approve",
  "validation_results": {
    "requirements_met": ["AC-001","AC-002","AC-003","AC-004","AC-005"],
    "tests_run": true,
    "tests_passed": true,
    "test_command": "pytest tests/unit/test_doc_level_exclusions.py -v --tb=short",
    "test_output_summary": "14 passed, 2 warnings in 3.29s",
    "code_quality": "High. The logic is cleanly separated into a helper function and a constant list of patterns, making it easy to maintain. The test coverage is comprehensive.",
    "edge_cases_covered": [
      "Artifacts only (no warning)",
      "Mixed user files and artifacts (correct count)",
      "Exceeding limit with artifacts (correct user count in warning)",
      "Unknown constraint levels (no limit applied)",
      "Paths similar to excluded patterns but not actually excluded"
    ]
  },
  "rationale": "All acceptance criteria have been met. ..."
}
```

### TASK-FIX-GD02 ([`coach_turn_1.json`](TASK-FIX-GD02/coach_turn_1.json))

**7/7 ACs verified**, **140 tests passed**, edge cases including the
load-bearing "Baseline files correctly excluded from delta" case that
motivated GD02 in the first place. Rationale acknowledges Player
implemented "across both task-work and direct mode paths" with
observability logging — Coach actually engaged with the implementation
shape, not just the test count.

### TASK-FIX-TP05 ([`coach_turn_1.json`](TASK-FIX-TP05/coach_turn_1.json))

**6/6 ACs verified**, **140 tests passed**, edge cases incl.
"Zero-test anomaly (zero_test_blocking=False)" and "Infrastructure-only
test files (conftest.py)" — both the load-bearing surfaces this task
was meant to address.

## What's resolved (post-run-19 + post-run-20)

| Finding | Status |
|---|---|
| F1 / F4 / F9 / F10 / F11 / F12 / F14 / F17 / F18 / F22 (code-side) | Closed runs 1-12; still silent |
| F20 (gemma4 ctx overflow) | Closed by D-3 (run 19); reconfirmed run 20 |
| F23A (gemma4:31b global OOM) | Closed by D-3 (run 19); reconfirmed run 20 |
| F24 (gemma4 schema-correct emission) | Closed by D-3 (run 19); reconfirmed run 20 |
| Run-13 grammar-no-op finding | Closed by D-3 |
| Run-18 chat-template parser error | Did not recur |
| **Run-19 caveat #1 (Coach independent test 300s timeout)** | **Closed by TASK-FIX-COACHTESTTO (commit `a0de3415`); empirically validated run 20** |
| Run-19 caveat #2 (`criteria_verification` array empty) | Unchanged — grammar leaves it optional; still consistent across runs |

## What's NOT in this snapshot

- The first-attempt run-20 log (the 0s skip) — committed separately
  as
  [`autobuild-FEAT-AOF-run-20.md`](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-20.md)
  for historical evidence of the FRESHRESET01 bug. This snapshot
  references the **second-attempt** run only.
- The full Coach LLM investigation-phase streams for each task — only
  in llama-swap / llama.cpp logs on `promaxgb10-41b1`. The interesting
  GB10 datapoint for future cutover-class features is still the
  **verdict-synthesis-phase token counts**.

## Run progression at a glance

| Phase | Time | Result |
|---|---|---|
| Feature start | 13:11:55 UTC | task budget 4800s × 3 tasks |
| Wave 1 / IA03 Player | → 13:15:55 (~240s) | ✓ 41 created, 1 modified |
| Wave 1 / IA03 specialists | SPECHANG contained | ✓ |
| Wave 1 / IA03 Coach | → 13:23:26 (~7m 30s) | ✓ APPROVE turn 1 |
| Wave 2 / TP05 Player | → 13:38:50 (running parallel with GD02) | ✓ 4 created, 3 modified |
| Wave 2 / TP05 Coach | → 13:49:02 (~10m) | ✓ APPROVE turn 1 |
| Wave 2 / GD02 Player | → 13:42:48 (~10m) | ✓ 4 created, 3 modified |
| Wave 2 / GD02 Coach | → 14:04:28 (~22m) | ✓ APPROVE turn 1 |
| FEATURE | **COMPLETED** | **52m 31s** |

## Substrate posture (unchanged from run 19 + this validates it's the working baseline)

- Harness: LangGraph
- Player: `qwen36-workhorse`
- Coach: `gemma4:31b` + D-3 toolless GBNF-grammar verdict-synthesis
- Coach reasoning: `--reasoning auto`
- Coach independent tests: **bypass-LLM via subprocess** (TASK-FIX-COACHTESTTO,
  commit `a0de3415`) — validated this run
- `task_timeout`: 4800s per-task
- SDK timeout: 3600s
- Graphiti context: disabled this run (`--no-context`)
- Endpoint: `http://promaxgb10-41b1:9000/v1`

## Suggested next steps

1. **TASK-FIX-FRESHRESET01** (filed as `0be5fcff`) — small ~5-10 line
   fix to remove the manual-revert-before-rerun bottleneck. Two runs of
   evidence support landing it.
2. **TASK-HMIG-011 (cutover ceremony)** — flip default harness to
   LangGraph. Two consecutive end-to-end successes is strong evidence
   that this is safe.
3. **Audit-trail update** — mark F20/F23A/F24/COACHTESTTO RESOLVED in
   `feature-run-incidents.md` and `feature-run-analysis.md`; record
   runs 13-20 in `feature-results.json`. Single cleanup commit.

🎉 Reproducible across two runs. Architecture solid. COACHTESTTO closed
the last verification-rigour gap from run 19. Cutover unblocked and
durable.
