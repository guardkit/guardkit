# TASK-REV-JMBP — Architectural Review

**Subject**: jarvis FEAT-J002 autobuild failure on MacBook Pro (2026-04-24).
**Mode**: `--mode=architectural --depth=standard`
**Sibling review**: [TASK-REV-E4F5](../../tasks/in_review/TASK-REV-E4F5-analyse-forge-autobuild-failures-gb10.md) (GB10).
**Primary evidence**: [jarvis-FEAT002-run-1.md](bdd-acceptance-wired-up/jarvis-FEAT002-run-1.md) (3326-line DEBUG log),
`.guardkit/worktrees/FEAT-J002/` in jarvis repo, [review-summary.md](../../tasks/in_progress/TASK-REV-JMBP-analyse-jarvis-FEAT-J002-autobuild-failure-on-macbook-pro.md) per-task artefacts,
`guardkit/orchestrator/{agent_invoker.py,autobuild.py,quality_gates/coach_validator.py}`, `installer/core/commands/lib/agent_invocation_validator.py`.
**Preamble artefact**: [TASK-REV-JMBP-graphiti-preamble.md](TASK-REV-JMBP-graphiti-preamble.md).

---

## Executive Summary

The MBP failure is **empirically distinct** from the GB10 failures reviewed in TASK-REV-E4F5.
The Player's Claude Agent SDK invocation ran successfully on every turn; tests executed and passed;
coverage evidence was emitted. The stall is entirely inside the Coach's **agent-invocations** quality
gate, which is now wired via TASK-FIX-RWOP1.3.1 and fires task-blocking when the Player's
producer-side self-validator flags a protocol violation.

**Root cause identified**: the agent-invocations violation is a **true-positive by the gate** with
respect to the Player's own self-reported verdict, but it is an **ambiguous defect in the system**:
the Player in task-work mode is satisfying task acceptance criteria (tests pass, 9 of 9 ACs for
J002-008) without invoking the required sub-agents via the Task tool. The gate correctly detects
this (actual_invocations=1 vs expected=3), but the loop provides *no recovery path*: each retry
re-generates the same protocol-skipping behaviour, producing identical feedback signatures. The
feedback-stall detector fires after 3 turns, summary is rendered with the misattributed default hint,
feature exits FAILED.

**Decision**: **D1 — expand the 7A0x feature scope** with one new subtask,
`TASK-FIX-7A07 — coach_agent_invocations_stall classification & recovery feedback refinement`,
rather than opening a parallel feature. Rationale:
- The Coach-gate stall is structurally a sibling of the summary-hint misattribution defect (7A02
  only handles `player_invocation_stall`; this run proves `coach_agent_invocations_stall` is a
  symmetric gap).
- Remediation is 100% inside the same surfaces 7A0x already touches (`autobuild.py`,
  classifier tables, summary hint renderer, optional Coach feedback template).
- D2 (separate feature) would fragment the stall-resilience taxonomy and inflate coordination cost.
- D3 (defer until 7A0x lands) would leave the active MBP hazard undocumented for at least one more
  sprint, and would duplicate the forensic work if the post-7A0x re-review discovered the same
  evidence.

Bootstrap/Python-3.14 handling is a **separate concern** that TASK-FIX-7A04/7A05 already cover
correctly for the 80% case. One user-side recommendation is added: Python 3.12 via `pyenv` or
`uv python install` is a pragmatic prerequisite on this MBP regardless of whether 7A04 lands.

Partial-success reporting (Workstream F) is genuinely misleading — 14/16 tasks approved in one turn
each, with an 88% first-turn pass rate, but the feature-level verdict is "FAILED". A small change to
the summary renderer to distinguish `mixed_partial_failure` from `all_stalled` is recommended as a
second sibling in 7A07.

---

## Workstream A — Graphiti preamble

See the companion artefact [TASK-REV-JMBP-graphiti-preamble.md](TASK-REV-JMBP-graphiti-preamble.md).

**Headline findings**:
- The wired `validate_agent_invocations` validator (TASK-FIX-RWOP1.3.1) is *in effect* on this run.
  The graph knew it was orphaned, but had no post-wiring episode — **this run is the first
  in-production firing in the observed corpus.**
- Absences (A1–A5 in the preamble) identify 5 decisions that should be seeded on `[A]ccept`, most
  critically: the bimodal `implementation_mode` routing behaviour (direct bypasses gate; task-work
  activates it) and the misattributed fallback hint in `autobuild.py:4552-4555`.

---

## Workstream B — Reproduce the two failure modes

### B.1 — Evidence inventory

From the preserved worktree at `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/worktrees/FEAT-J002/.guardkit/autobuild/`:

| Task | coach_turns saved | task_work_results.json | Outcome |
|---|---|---|---|
| TASK-J002-008 | 1, 5, 6 | ✓ (final, from turn 6) | FAILED — feedback_stall |
| TASK-J002-013 | 2, 3 | ✓ (final, from turn 3) | FAILED — context_pollution |
| TASK-J002-006 | 1 | ✓ | PASSED (direct mode, reference) |
| TASK-J002-016, 018 | 1 | ✓ | PASSED (direct mode) |

Turns 2, 3, 4 for J002-008 were *overwritten* during the multi-turn retry; only turn 1 (the earliest
divergent shape), turn 5 and turn 6 (the final) remain on disk. This is a minor forensic gap;
the surviving turns are sufficient to characterise the defect because the rejection signature is
**stable across turns 5 and 6 to the byte** (identical `rationale`, identical `issues[0].description`,
identical `details`).

### B.2 — Bimodal mode routing is the core differentiator

Every PASSING Wave-2 task ran with `implementation_mode: direct`. Every FAILING Wave-2 task ran
*without* that field (default = task-work mode). This is a 100% correlation across the 12 tasks
whose `task_work_results.json` was preserved.

| Task | Wave | Mode | Phases detected | AV status | `expected_phases` | `actual_invocations` | `relaxed` | AC count |
|---|---|---|---|---|---|---|---|---|
| J002-001 | 1 | direct | phase_3 | *(absent)* | — | — | True | 4 |
| J002-002 | 1 | direct | phase_3 | *(absent)* | — | — | True | 4 |
| J002-003 | 1 | direct | phase_3 | *(absent)* | — | — | True | 4 |
| J002-004 | 1 | direct | phase_3 | *(absent)* | — | — | True | 4 |
| J002-005 | 1 | direct | phase_3 | *(absent)* | — | — | True | 6 |
| J002-007 | 1 | direct | phase_3 | *(absent)* | — | — | True | 5 |
| J002-023 | 1 | direct | phase_3 | *(absent)* | — | — | True | 4 |
| J002-006 | 2 | direct | phase_3 | *(absent)* | — | — | True | 7 |
| J002-016 | 2 | direct | phase_3 | *(absent)* | — | — | True | 5 |
| J002-018 | 2 | direct | phase_3 | *(absent)* | — | — | True | 4 |
| **J002-008** | 2 | **task-work** | phase_3, phase_4 | **violation** | **3** | **1** | — | **9** |
| **J002-013** | 2 | **task-work** | phase_3, phase_4 | **violation** | **3** | **1** | — | **14** |

`expected_phases=3` resolves to the implement-only phase list `['3', '4', '5']`
(`agent_invocation_validator.py:79-85`). `actual_invocations=1` means the stream parser recognised
exactly one phase-completion marker per task. `quality_gates_relaxed=True` on direct-mode tasks
reflects `_invoke_player_direct` (agent_invoker.py:3718) setting looser gate thresholds.

**Observation — AC-count signal**: the only two Wave-2 tasks with >7 ACs (J002-008 at 9 ACs,
J002-013 at 14 ACs) are the ones routed to task-work mode. This is how the plan assigned modes:
high-complexity tasks requested the full three-agent pipeline; low-complexity tasks ran inline
in direct mode. **The routing logic is sensible. The defect is that the task-work-mode path doesn't
actually invoke the three agents.**

### B.3 — J002-008 — feedback-stall exit

**Coach feedback signature** (stable across turns 5 and 6; verbatim from `coach_turn_6.json`):

```
issues[0]: {
  "severity": "must_fix",
  "category": "agent_invocations_violation",
  "description": "task-work results claim phases were completed without matching agent invocations.
                  Missing phases: 4, 5. The Player report cannot be trusted until all required
                  agents are invoked.",
  "details": { "missing_phases": ["4", "5"], "expected_phases": 3, "actual_invocations": 1 }
}
rationale: "Agent-invocations protocol violation: missing phases 4, 5"
```

**Coach turn 1 (divergent — first turn had different signature)**:
Turn 1 rejected on `coverage` (`line_coverage: 44.0`, threshold 80%). Quality gates fired normally.
By turn 5, Player had rewritten to achieve 87.0% coverage with 25 tests passing — but in doing so,
it bypassed sub-agent invocations. From turn 5 onward, the Coach's agent-invocations gate short-
circuits the quality-gates check entirely: `validation_results.quality_gates: null` at turns 5
and 6. The gate consumes the Player's own `agent_invocations_validation` block and blocks approval
before any tests/coverage check runs.

**Player's `task_work_results.json` (turn 6)** shows the **self-contradiction**:
- `completed: true`
- `quality_gates: { tests_passing: true, tests_passed: 25, coverage: 87.0, coverage_met: true, all_passed: true }`
- `summary: "25 tests passed, 87.0% coverage, all quality gates passed"`
- All 9 `completion_promises[].status = "complete"` with detailed, file:line evidence
- `phases.phase_3.completed: true`, `phases.phase_4.completed: false`
  (phase_4 text: "(testing) and Phase 5 (code review) execution with proper output markers. Let me re-execute these ph")
- `agent_invocations_validation.status: "violation"` — *the Player flags itself*

This is a Player that **did the work correctly** (substantively) but **did not follow the sub-agent
invocation protocol**. The producer-side validator (code added by TASK-FIX-RWOP1.3.1) correctly
labels the emitted results as untrustworthy.

**Feedback-stall fire**: `autobuild._is_feedback_stalled` (line 3237) computes md5 over normalised
feedback. Signature `c6bb0e9b` (per the task description citation) is stable across 3 consecutive
turns with `criteria_passed_count = 0` (no AC was verified independently because quality_gates was
null). `threshold = 3`, `counts[0] == 0` — exits via `autobuild.py:3288` → `autobuild.py:1995-2001`.
Final_decision = `unrecoverable_stall`.

### B.4 — J002-013 — context-pollution exit + double-layer failure

Coach rejection signature (turns 2 and 3, identical):

```
issues[0]: { "category": "agent_invocations_violation",
             "details": { "missing_phases": ["3", "5"], "expected_phases": 3, "actual_invocations": 1 } }
```

Note J002-013 has `missing_phases: [3, 5]` — so phase_4 was the one invocation counted. That matches
its `task_work_results.phases.phase_4.completed: true, phase_3.completed: false`. A probable
explanation: in `--mode=tdd`, the Player opened with tests (phase-4-shaped) and never cleanly
re-entered a phase_3 completion marker. The SDK used 50/100 turns.

**Second layer — context-pollution exit path** (`autobuild.py:1957-1988`). `checkpoints.json`:

```
[{turn:1, tests_passed:false, test_count:0}, {turn:2, tests_passed:false, test_count:0},
 {turn:3, tests_passed:false, test_count:0}]
```

`test_count=0` means the Coach's independent-pytest checkpoint never collected a test. But the Player
reports 40 tests passed, 1 failed. The reconciliation: `WorktreeCheckpointManager` runs pytest
independently at turn boundaries against whatever Python is on the worktree's PATH. With bootstrap
at 0/1 and the MBP's `/usr/local/bin/python3 → 3.14.2` not compatible with jarvis's `<3.13,>=3.12`
pin, pytest is likely missing from that interpreter or jarvis is un-installable — pytest exits
non-zero with zero collected. `should_rollback()` fires, `find_last_passing_checkpoint()` returns
None (never any passing checkpoint), exits via `autobuild.py:1982-1988` as `unrecoverable_stall`.

**So J002-013 has two independent task-killing conditions** operating in parallel:
1. Agent-invocations gate rejection (like J002-008) — fires via feedback-stall detector.
2. Context-pollution exit — fires via missing-passing-checkpoint on the independent-pytest path.

The log order is the feedback-stall path fires first (turn 3, checkpoint 3 pattern), which is why
the summary says "3 turns" and the context-pollution path is a latent exit that would have fired
at essentially the same turn if the feedback-stall path had not.

### B.5 — Compare-and-contrast: Wave-2 approved vs failed

| Dimension | Approved (J002-006/009/010/011/014/016/018) | Failed (J002-008, J002-013) |
|---|---|---|
| Mode | direct | (task-work, default) |
| Gate profile | relaxed | strict (feature profile) |
| Agent invocations gate | not evaluated | violation (expected 3, actual 1) |
| Phases detected | phase_3 only | phase_3 + phase_4 (one completed, one not) |
| AC count | 4–7 | 9, 14 |
| Complexity signal | scaffolding, registry, prompt injection | security-critical IO tool (read_file), dispatch/concurrency tool |
| Test count (Player-reported) | 1 per task (light harness) | 25 / 41 |
| Turn count | 1 | 6 / 3 |
| SDK turns used | few | 10 / 50 |
| Exit | approved | unrecoverable_stall |

**Differentiating factors are bimodal by mode, not by incidental complexity.** The AC-count and
complexity signals predict *which* tasks got task-work mode, not the failure itself. Running the
same two tasks with `implementation_mode: direct` in the frontmatter would (based on this
evidence) have produced approval, because the agent-invocations gate would be bypassed.

---

## Workstream C — Root-cause classification

### C.1 — Gate correctness: **True-positive, relative to the Player's own self-report**

The Coach's gate is not an independent checker of whether phase-4/5 agents ran. It consumes
`task_work_results.agent_invocations_validation` from the Player's producer-write
(`agent_invoker._write_task_work_results` → `_compute_agent_invocations_validation`, line 5406),
which calls `validate_agent_invocations(tracker, workflow_mode)` from the installer
`agent_invocation_validator.py` library.

The tracker is populated from `_extract_invocations_from_result_data` (line 5373), which prefers
an explicit `agent_invocations` list if present, otherwise scrapes the parser's `phases` dict
for entries with `completed: True`. The parser itself (`StreamMessageParser`, line 424) captures
phase markers from the SDK stream's tool-use/text output.

**Implication**: the gate fires on **evidence shape**, not on **evidence substance**. If the Player's
stream output contains the text "Phase 3" with a completion marker but not "Phase 4" / "Phase 5"
completion markers (because the Player ran pytest inline rather than delegating to the
`test-orchestrator` sub-agent via the Task tool), the gate concludes the agents weren't invoked.
*And it is correct* — the agents actually weren't invoked. But the gate has no way to distinguish
"agents not invoked because the Player skipped them" from "agents not invoked but the work was done
inline with equivalent quality."

### C.2 — Coach is not the defect; Player's task-work-mode invocation path is

**Fix target**: the Player's task-work delegation (`_invoke_player_task_work`, agent_invoker.py
around line 1410) must either:

- **Option α** — **Force sub-agent invocation in the Player prompt**. Make the system-prompt or
  turn prompt *structurally require* the Player to use the Task tool for Phase 4 (test-orchestrator)
  and Phase 5 (code-reviewer) before emitting `completed: true`. The validator then catches
  non-compliance during the Player's own turn, and the Player self-corrects before reporting out.

- **Option β** — **Accept outcome evidence as a substitute**. Extend
  `_compute_agent_invocations_validation` to treat `quality_gates.tests_passing = true` with
  concrete test counts + coverage as *equivalent to Phase-4 invocation*, and treat the
  completion_promises with per-AC evidence + file paths + line numbers as *equivalent to
  Phase-5 invocation*. The gate becomes an outcome-or-invocation gate, not pure-invocation.
  Risk: weakens the anti-fraud stance that the gate was designed for (per the validator
  docstring: "This prevents false reporting where agents are listed as 'used' when they were
  never called via the Task tool.").

- **Option γ** — **Profile the gate by task_type**. For `task_type: feature`, require all three;
  for lighter types (or specific kinds of features that don't benefit from the specialist split),
  require only phase 3 + one of {4, 5}. Implementation would adjust
  `get_expected_phase_list(workflow_mode, task_type=?)` in the validator library.

**Recommended remediation direction**: **α + feedback refinement**, not β or γ.
- β silently weakens a fraud check the system is evolving toward; adoption should be explicit, not
  a quiet AC relaxation.
- γ adds a configuration surface that needs its own design review and BDD scenarios.
- α is *the designed behaviour*. The Player agent architecture *already* intends to delegate via the
  Task tool (per `.claude/rules/autobuild.md` "Player: Delegates to task-work --implement-only
  (Phases 3-5.5)"). The defect is that the Player isn't actually doing so in task-work mode, and
  the feedback loop isn't giving it a clear instruction to correct.

### C.3 — Why retries don't recover

Even if the gate is correct and Player is the defect, the current feedback text is:

> "task-work results claim phases were completed without matching agent invocations. Missing
> phases: 4, 5. The Player report cannot be trusted until all required agents are invoked."

This is *semantically* correct but *operationally* useless for Player self-correction. The Player
has no primer on what "invoke an agent" means in terms of Task-tool mechanics, nor on which
specific agents to invoke (e.g., "run the `test-orchestrator` agent via a Task tool call with
subagent_type='test-orchestrator'"). Each retry re-runs the whole Player turn from scratch; the
Player re-does its own mix of inline pytest + inline code review, re-writes its own self-violation
verdict, and Coach rejects again with the same feedback signature.

**The recovery path is closed by the interaction of three mechanisms**:
1. Producer-runs-gate folds the self-verdict into the report (correct by design).
2. Coach is a pass-through reader of that verdict (also correct).
3. The feedback-stall detector terminates the loop at threshold 3 identical signatures.

No amount of re-trying the Player will cause it to invoke sub-agents *unless the feedback explicitly
tells it to*. The current feedback does not.

### C.4 — Risk table for any fix against `coach_validator.py` / `agent_invoker.py`

| Change | Blast radius | Risk of regression | Mitigation |
|---|---|---|---|
| Add `[PROTOCOL]` feedback mode in `_compute_agent_invocations_validation` → Coach feedback synthesiser | Feedback text only; gate logic unchanged | Low: Player prompt-side change is isolated | Unit test per new feedback template; BDD scenario covering "retry converges within 2 turns after PROTOCOL feedback" |
| Extend Player system prompt to mandate Task-tool invocation for phases 4+5 | Every task-work-mode run | Medium: could over-invoke for trivial tasks | Gate by task_type profile; add AC to feature-spec for the new prompt fragment; regression-test against FEAT-J002 worktree-replay |
| Relax gate to accept outcome evidence as substitute (option β) | Every task-work-mode run; future anti-fraud posture | High: weakens the explicit guarantee the validator is documented to give | Rejected; do not pursue without an ADR |
| Profile gate by `task_type` (option γ) | Validator library, Player, Coach | Medium: config surface needs spec | Defer as future work unless α+feedback proves insufficient |

**Recommended test matrix**:
- Fixture: replay J002-008 turn-6 `task_work_results.json` against Coach; expect new-format
  PROTOCOL feedback (not the current terse form).
- Fixture: replay the same with Player prompt fragment added; expect `actual_invocations=3,
  status=passed` on the producer-written block.
- Regression: all existing direct-mode Wave-1 tasks in the worktree should still pass (gate is
  not evaluated for direct mode).
- Regression: any feature-type task with complexity ≥ 6 that previously approved in 1 turn
  should continue to approve in 1 turn (no false rejections introduced).

---

## Workstream D — Counterfactual impact of the 7A0x feature

| Task | Would landing this have changed this run's outcome? | Rationale |
|---|---|---|
| **7A01** — Pin SDK + log version | **No** | SDK connectivity was fine on this run; the failure is downstream of the SDK. Version logging would have captured useful forensic data but not changed outcome. |
| **7A02** — `player_invocation_stall` classification | **Partial, misses** | 7A02 classifies stalls where the Player's SDK never produced output. Here the Player produced extensive output (53–92 files per turn, 25–40 tests). 7A02 would not match. **This is the D1 gap**: a new symmetric classification `coach_agent_invocations_stall` is needed. |
| **7A03** — Defensive SDK message handling | **No** | SDK messages landed cleanly (parser found phase markers, per-file changes, test output, etc.). No `NoneType` or malformed message errors in this run's Coach path. |
| **7A04** — Bootstrap hard-fail gate (`bootstrap_failure_mode=block`) | **Possibly critical** | Would have halted the run at bootstrap (0/1 succeeded) before Wave 1 started, emitting "Python 3.14.2 not in <3.13,>=3.12; aborting" as the feature outcome. The feature-level run would have failed earlier and more truthfully. However, this *masks* the Coach-gate defect — the defect would still be latent, waiting for the next compatible-Python MBP run to re-expose it. |
| **7A05** — Wire bootstrap venv into Coach pytest | **Partially relevant** | Would have fixed J002-013's secondary failure (context-pollution from `test_count: 0`) because Coach's independent pytest would run in a correctly-configured venv. But J002-013's *primary* failure (agent-invocations-violation) would still fire, so the task would still fail — just on a different exit path. J002-008 would be unchanged. |
| **7A06** — Runbook + graph seed | **No direct impact on outcome** | Documentation/knowledge. However, had the classifications from 7A06 been seeded, the Graphiti preamble for this review would have had more priors, and the fallback-hint misattribution (Workstream B.4 / autobuild.py:4552-4555) might have been documented as known-bad. |

### D.1 — Decision: D1 (expand scope)

Add **one** new task to the `autobuild-sdk-stall-resilience/` feature folder:

**TASK-FIX-7A07 — coach_agent_invocations_stall classification and recovery feedback refinement**

Scope:
1. Add classifier branch to `autobuild._render_unrecoverable_stall_summary` (line 4538):
   - If `recent_feedback` matches the `agent_invocations_violation` category pattern for ≥ 3 turns,
     emit a new hint:
     > "Coach's agent-invocations gate rejected the Player's task-work results for N consecutive
     > turns (missing phases: X, Y). The Player completed the work inline but did not invoke the
     > required sub-agents via the Task tool. Inspect `task_work_results.json → agent_invocations_validation`.
     > Fix options: (a) ensure Player system prompt mandates Task-tool invocation for Phase 4
     > (test-orchestrator) and Phase 5 (code-reviewer); (b) set `implementation_mode: direct` in
     > the task frontmatter if the task doesn't need the specialist pipeline."
2. Enrich Coach's agent-invocations feedback in `coach_validator.py:658-685` to cite the specific
   sub-agent names Player should invoke (`test-orchestrator`, `code-reviewer`, and the
   stack-specific specialist — detected from the project stack profile) rather than just "phase N".
3. Extend `autobuild._is_feedback_stalled` normalisation so that the md5 signature collapses
   agent-invocations-violation feedback that differs only by `missing_phases` ordering — avoids
   false non-stall if the Player's `phases` dict happens to reorder.
4. Update the Phase-5 Graphiti seeding code to emit a classification entity when this stall type
   is observed.

Explicitly **out of scope** for 7A07 (deferred):
- Changing the Player's system prompt to structurally mandate sub-agent invocation. That is a
  larger change affecting every task-work-mode run and needs its own architectural review plus a
  feature-spec BDD pass. File that as a follow-on: **TASK-FIX-7A08** (proposed), outside this
  review's scope.
- Option β (outcome-evidence substitution in the gate). Rejected above.
- Option γ (task_type profile of expected_phases). Deferred.

### D.2 — Why not D2 (separate feature)

Opening `coach-validation-stall-root-cause` (FEAT-CVSR) as a parallel feature would:
- Split the stall-classification taxonomy across two features, making future retrospective review
  harder. The taxonomy — "what are all the ways autobuild stalls?" — belongs in one place.
- Require its own Graphiti seeding, feature-build pipeline, Coach gates. The surface area isn't
  yet large enough to warrant that overhead.
- Force artificial partitioning decisions (where does 7A02 end and FEAT-CVSR begin?).

The only argument for D2 would be if the Coach-gate root cause leads to broader work than 7A07
encompasses — e.g., redesigning the Player's sub-agent invocation protocol. **That** work would
justify a separate feature (proposed TASK-FIX-7A08 above). But the *classification-and-feedback*
work is cleanly inside the 7A0x scope.

### D.3 — Why not D3 (defer)

D3 accepts one more round of forensic cost on a future reviewer (doing the same trace on a future
MBP run that uncovers the same gap) and leaves the hazard in the field untriaged for at least one
sprint. Also, Graphiti preamble findings A1–A4 — the absence-of-knowledge gaps — persist under D3.
The knowledge-capture investment cost is the same whether we do it now or later, so there's no
savings from deferral.

---

## Workstream E — Python 3.14 / bootstrap interaction

### E.1 — MBP-specific facts

- `/usr/local/bin/python3` resolves to Python 3.14.2 (observed in log lines 70–86).
- jarvis's `pyproject.toml` pins `<3.13,>=3.12`.
- `pip install -e .` fails with an exit code 1 and the clean error "Package 'jarvis' requires a
  different Python".
- The MBP is not PEP 668-marked, so no `--break-system-packages` fallback triggers.
- Orchestrator logs "Environment bootstrap partial: 0/1 succeeded" and proceeds.

### E.2 — Assessment of the three sub-questions from the task spec

1. **Does the user need a Python 3.12 setup independent of 7A04?**
   Yes — pragmatically, yes. Even with 7A04 landed, the run would halt cleanly instead of
   silently limping, which is better but still blocks the user from running FEAT-J002 at all on
   this MBP. Recommend: `uv python install 3.12` or `pyenv install 3.12.6 && pyenv local 3.12.6`
   in the jarvis repo, or set `GUARDKIT_PYTHON=/path/to/python3.12` (assuming guardkit supports
   a Python-override env var — see E.4).

2. **Would 7A04 + 7A05 handle this cleanly?**
   7A04 (hard-fail gate) would halt at the bootstrap step with a correct error. Good outcome.
   7A05 (wire venv into Coach pytest) depends on bootstrap having *succeeded* — if bootstrap fails
   hard via 7A04, 7A05 has nothing to wire. The two tasks are somewhat conditional: 7A04 makes
   7A05 irrelevant *for this specific failure mode*, because 7A04 exits before Coach's pytest runs.

3. **Is there a case for a pre-flight `--doctor` check?**
   Yes, and I would recommend adding a *sub-scope* to 7A04 (not a new task): before running `pip
   install -e .`, the bootstrap code should read `pyproject.toml`'s `requires-python` and compare
   with the active interpreter's version, emitting a clean "Python X.Y.Z does not satisfy
   requires-python=<3.13,>=3.12; install a compatible interpreter with `uv python install 3.12` or
   `pyenv install 3.12`" message *before* invoking pip. This is 10–20 lines in `environment_bootstrap.py`
   and avoids the opaque pip error.

### E.3 — Which 7A0x task should own the pre-flight check?

**Recommend**: fold it into **TASK-FIX-7A04** as an additional AC (rather than a new task). 7A04's
core is "hard-fail the bootstrap step"; adding a "pre-check the interpreter before pip" AC is a
natural extension. Do not create a new task for this.

### E.4 — Scope-creep check

This review is *not* proposing guardkit absorb Python-version-management responsibility. It is
proposing two clean things:
- Hard-fail on bootstrap failure (already 7A04).
- Pre-check `requires-python` vs active interpreter (add to 7A04).

Anything beyond that (auto-installing Python, switching interpreters, spawning a sub-process in a
different venv) is out of scope and should not be absorbed into the 7A0x feature.

---

## Workstream F — Partial-success classification and resume semantics

### F.1 — Feature-level verdict accuracy

The review-summary reports:
- Total tasks: 23; Total turns: 23; First-attempt pass rate: 88%.
- 14 of 16 observed tasks PASSED; 2 FAILED.
- 7 tasks in the plan never ran (009, 010, 011, 014, 015, 017, 019, 020, 021, 022 — not in
  outcomes table but implied by `Total tasks: 23`). They were preempted by Wave 2's failure under
  `stop_on_failure: True`.
- Feature verdict: **FAILED**.

**A reasonable user reading the review-summary would conclude that 88% of work succeeded but the
feature failed.** This is accurate as a partial-success shape but misleading as a binary verdict.
A user triaging this the morning after the run would waste time re-investigating the 14 passing
tasks before realising the two failures are localised.

**Recommendation**: introduce a `mixed_partial_failure` verdict distinct from `all_stalled`. The
renderer (`autobuild.py` — `_render_summary` or equivalent) should:
- Use `mixed_partial_failure` when ≥ 50% first-turn approval rate AND ≥ 1 unrecoverable_stall.
- Use `all_stalled` when 0 first-turn approvals.
- Preserve the FAILED verdict overall but accompany it with "14 of 16 tasks approved; 2 failed with
  unrecoverable_stall; 7 preempted" as the headline.

File this as a second subtask under 7A07 or a separate `TASK-FIX-7A09`. Minor enough to be an AC
on 7A07; consolidating avoids task fragmentation.

### F.2 — Resume semantics

From the log footer: `Next Steps: guardkit autobuild feature FEAT-J002 --resume`. The review-summary
reports 2 failed + 7 preempted tasks.

Expected `--resume` behaviour:
- For the **preempted** tasks (009, 010, 011, 014, 015, 017, 019, 020, 021, 022): straightforward —
  re-run them from scratch in their original wave order.
- For the **failed-stall** tasks (008, 013): not clear whether resume re-runs them (likely to fail
  the same way unless the defect is fixed) or skips them.

**Recommendation**: `--resume` should, on detection of stalled tasks, require an explicit flag:
`--retry-stalled` to re-run the stall-exited tasks, `--skip-stalled` to advance past them. Default
should be to block with a message: "FEAT-J002 has 2 stalled tasks (J002-008, J002-013). Pass
`--retry-stalled` or `--skip-stalled` to proceed." This prevents the foot-gun of "resume re-runs
failures forever".

**Scope note**: this is a resume-semantics change, not a stall-resilience change per se. File as a
separate task; **out of scope for 7A07**. Mark it as a candidate for the same review that might
spawn 7A08 (Player sub-agent invocation protocol rework), because they share the "how should
autobuild behave around multi-layer partial-failures" theme.

### F.3 — Stall-type distinction in the review summary

The review-summary lumps J002-008 (feedback-stall) and J002-013 (context-pollution + feedback-stall)
under the same `unrecoverable_stall` label. They have different root causes; the summary loses
this distinction.

**Recommendation**: in the review-summary renderer, use the classifier output from 7A07 (new branch
in `_render_unrecoverable_stall_summary`) to emit per-task stall sub-type:

```
| TASK-J002-008 | 2 | 6 | FAILED | coach_agent_invocations_stall | … |
| TASK-J002-013 | 2 | 3 | FAILED | coach_agent_invocations_stall + context_pollution_bootstrap | … |
```

This sub-type labelling is a natural third AC for 7A07 and makes the summary immediately useful for
triage.

---

## Decision block

- **Does this review block TASK-COH-RUN1 or any other downstream work?** **No.**
  TASK-COH-RUN1 runs on GB10, not MBP. The MBP-specific bootstrap hazard does not gate it, and
  the agent-invocations-gate defect is latent on GB10 (where the 7A0x scope from TASK-REV-E4F5
  remains unimplemented, so task-work-mode tasks that hit the gate would exhibit the same stall
  there too — but that's a pre-existing condition, not a new block).
- **Does this review supersede or conflict with TASK-REV-E4F5?** **No.** TASK-REV-E4F5's 7A01–7A06
  decisions stand. This review proposes 7A07 as a sibling addition (D1), not a replacement. The
  counterfactual table in Workstream D confirms each existing 7A0x task still has its original
  rationale.
- **Cross-reference with TASK-REV-MCPS**: the re-invocation at log line 22 succeeding (after the
  user had applied the MCPS fixes) is empirical post-flight corroboration that TASK-FIX-MCPS.1 +
  .2 are in effect on MBP. TASK-FIX-MCPS.3 (post-flight Graphiti seeding) can cite this as a
  confirming live run. *Recommendation*: add a one-line note to TASK-FIX-MCPS.3's post-flight
  section linking to this review and log line 22 as the MBP-confirmation datum.

## Acceptance-criteria completion summary

| AC | Status | Artefact |
|---|---|---|
| Workstream A — Graphiti preamble filed | ✓ | [TASK-REV-JMBP-graphiti-preamble.md](TASK-REV-JMBP-graphiti-preamble.md) |
| Workstream B — coach feedback + task_work_results + compare-contrast | ✓ | §B.1–B.5 above |
| Workstream C — root-cause classification with risk table | ✓ | §C.1–C.4 above |
| Workstream D — per-7A0x table + decision D1/D2/D3 | ✓ | §D (decision: **D1**) |
| Workstream E — Python 3.14 remediation recommendation | ✓ | §E (fold pre-check into 7A04) |
| Workstream F — partial-success + resume semantics | ✓ | §F.1–F.3 |
| Main review filed at docs/reviews/TASK-REV-JMBP-jarvis-autobuild-mbp-review.md | ✓ | This file |
| Decision block recorded | ✓ | Above |

## On [A]ccept — Graphiti seeding plan

Three episodes to write (see preamble §"Knowledge-graph remediation recommendations"):
1. Findings → `guardkit__project_decisions`: failure taxonomy with 4 distinguished classes.
2. Outcome → `guardkit__task_outcomes`: per-workstream verdict + D1.
3. Rule → `guardkit__project_decisions`: bimodal `implementation_mode` routing rule.

Plus a one-line citation into the namespace-hygiene.md sibling-rule list (pending stale-reference
check — out of scope for this review).

## On [I]mplement — subtask shape

Per Workstream D: one new subtask added to `tasks/backlog/autobuild-sdk-stall-resilience/`:

- **TASK-FIX-7A07** — coach_agent_invocations_stall classification & feedback refinement.
  Modes: task-work. Wave: 2 (after 7A02 lands; depends on 7A02's classifier framework).
  ACs: (1) new stall classifier branch; (2) enriched Coach feedback with specific sub-agent names;
  (3) per-task stall-subtype in review-summary; (4) feedback-stall md5 normalisation robustness;
  (5) Graphiti seeding for the new classification.

Plus one amendment-AC folded into **TASK-FIX-7A04** (bootstrap hard-fail gate): pre-check
`requires-python` against active interpreter before pip invocation.

Both changes stay inside the existing `autobuild-sdk-stall-resilience/` feature folder; no new
folder is created.

## Notes for the Phase-5 checkpoint

The user-facing decision prompt should present the three standard options plus the explicit
counterfactual: if the user picks [I]mplement, the executor will amend 7A04 (one AC) and create
7A07 (new task) under the same feature folder — **not** spawn a separate feature.
