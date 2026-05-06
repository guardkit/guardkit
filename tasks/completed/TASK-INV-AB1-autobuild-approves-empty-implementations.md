---
id: TASK-INV-AB1
title: "Investigate autobuild approving zero-implementation turns (FEAT-6CC5 false-positive approvals)"
status: completed
created: 2026-05-06T00:00:00Z
updated: 2026-05-06T00:00:00Z
completed_at: 2026-05-06T00:00:00Z
previous_state: review_complete
state_transition_reason: "[I]mplement chosen at decision checkpoint; follow-up fix task TASK-AB-FIX-INVAB1 carries the implementation forward"
priority: critical
tags: [autobuild, quality-gate, false-positive-approval, regression, bug-investigation]
task_type: review
review_mode: code-quality
review_depth: standard
complexity: 6
estimated_minutes: 120
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: code-quality
  depth: comprehensive
  score: 48
  findings_count: 7
  recommendations_count: 6
  decision: refactor
  report_path: .claude/reviews/TASK-INV-AB1-review-report.md
  follow_up_task: TASK-AB-FIX-INVAB1
  completed_at: 2026-05-06T00:00:00Z
  revisions:
    - revised_at: 2026-05-06T00:00:00Z
      reason: "First [R]evise: deeper analysis with C4 + sequence diagrams"
      changes: "F6 (LLM Coach hallucinates) retracted — Coach is deterministic Python; the prose is Player-written."
    - revised_at: 2026-05-06T00:00:00Z
      reason: "Second [R]evise: user observed that the original adversarial Player-Coach design appears to have been broken; investigate"
      changes: "Reframed as architectural regression. The codebase contains a complete adversarial honesty verifier (CoachVerifier in coach_verification.py) wired only to the LLM Coach fallback path. The deterministic CoachValidator path (primary since Option D / TASK-REV-0414, 2025-12-30) bypasses CoachVerifier entirely. User intuition correct: adversarial property has been broken since the foundational Option D decision; recent BDD changes were not the cause. Fix narrowed to wire CoachVerifier into CoachValidator + extend CoachVerifier with completion_promises check (~80 lines, restorative not new architecture)."
---

# Task: Investigate autobuild approving zero-implementation turns

## Cross-repo origin

This bug surfaced in the `study-tutor` repo when running
`/feature-build` against FEAT-6CC5. A duplicate of this task lives at
`study-tutor:tasks/backlog/TASK-INV-AB1-autobuild-approves-empty-implementations.md`
and points at the *evidence* (archived player/coach turn JSON). **The fix
lands here in `guardkit`** — the suspect code is the Player→Coach loop in
`guardkit/orchestrator/autobuild.py` and the coach-decision pipeline that
returns `final_decision="approved"`.

## Problem statement

During FEAT-6CC5 (MCP LLM Player and Coach Adapters) in `study-tutor`, the
GuardKit autobuild Player↔Coach loop **approved 5 of 5 tasks
(100% pass rate, coach decision `approved`)** despite the fact that
**3 of those tasks produced zero production-code files**. The merged feature
contained none of the modules that the approved tasks were specified to
create:

- `src/study_tutor/tutoring/adapters/__init__.py`
- `src/study_tutor/tutoring/adapters/session_state.py` (TASK-LCA-003)
- `src/study_tutor/tutoring/adapters/llm_player_adapter.py` (TASK-LCA-001)
- `src/study_tutor/tutoring/adapters/llm_coach_adapter.py` (TASK-LCA-002)

The defect was only caught after the feature was merged to `main` in
`study-tutor`, when `pytest --collect-only` failed with
`ModuleNotFoundError: No module named 'study_tutor.tutoring.adapters'`.

This is a **silent quality-gate failure**: a coach approval is supposed to
guarantee that the acceptance criteria in the task .md were met. In this run
the criteria explicitly required new files (e.g., TASK-LCA-003 lists a
`@dataclass(frozen=True)` at a specific path as the first acceptance
criterion), yet the coach approved despite no files being created.

## Evidence

The most diagnostic artefact is in
`study-tutor:tasks/backlog/mcp-llm-player-coach-adapters/TASK-LCA-003-session-state-dataclass.md`
(also archived in
`study-tutor:.guardkit/archive/FEAT-6CC5/feature_state.yaml`). The
`autobuild_state.turns[*].player_summary` for **every turn** reads:

```
"Implementation via task-work delegation. Files planned: 0, Files actual: 0"
```

At turn 3, the coach decision is `approve` with `feedback: null` —
i.e., a clean approval — even though `Files actual: 0`. No mechanism in the
loop appears to have checked whether the player actually produced any of the
files declared in the task's acceptance criteria.

Turn 2 of the same task contains a long coach-feedback entry about
"source-file contention with peer task(s) in this parallel wave (wave_size=4)"
— a wave-isolation issue that may have suppressed retries or caused the
player to return a "skipped due to contention" report that the coach
mis-classified as success. (Search `guardkit/orchestrator/autobuild.py` for
the comment at ~L1080: *"conditional approval when the contention is real
(not transient infra)"* — that path is a strong candidate for the
false-positive source.)

`study-tutor:.guardkit/archive/FEAT-6CC5/review-summary.md` reports:

| Metric | Value |
|---|---|
| Task success rate | 100% |
| First-turn approvals | 0/5 |
| Multi-turn tasks | 5 |
| Avg SDK turns/invocation | 24.6 |

i.e., every task took multiple coach-feedback rounds before final approval —
the loop *did* produce iterative feedback, but the terminating approval still
fired on a no-implementation state for at least 3 tasks.

## Investigation goals

1. **Root-cause the false-positive approval** in
   `guardkit/orchestrator/autobuild.py`: under what condition did the coach
   (or the orchestrator's approval pipeline) accept a player turn that
   produced zero files when the task spec required new files at specific
   paths? Likely starting points:
   - The conditional-approval path at ~L1080 (wave-contention "real (not
     transient infra)" branch)
   - `final_decision="approved"` propagation through `_run_autobuild_loop`
     (~L2040+) — does it consult any `Files actual` vs acceptance-criteria
     check before terminating?
2. **Identify whether the wave-2 file-contention path is implicated**:
   TASK-LCA-001/002/003/004 ran in the same wave-1 group and the contention
   feedback at turn 2 of TASK-LCA-003 suggests an isolation-snapshot failure
   mode. Determine whether the wave conflict caused an empty player report
   that the coach then rubber-stamped.
3. **Identify any deterministic check that should have blocked approval**:
   in particular, a "Files actual: 0 vs acceptance-criteria expected new
   files at paths X, Y, Z" cross-check before the coach decision is finalised.
4. **Determine blast radius**: scan recent feature archives across consumer
   repos (`study-tutor:.guardkit/archive/`, `forge`, etc.) and prior
   autobuild runs for other completions where `Files actual: 0` appears in
   approved turns.

## Acceptance criteria

- [ ] Written investigation report at
      `.claude/reviews/TASK-INV-AB1-review-report.md` (matching the
      `task_type: review` convention used by TASK-A5D6) covering:
  - Root-cause hypothesis backed by the player/coach turn JSON archived
    in study-tutor *(plus, where recoverable, the per-task
    `coach_turn_*.json` and `player_turn_*.json` blobs from the
    `autobuild/FEAT-6CC5` branch tree — see "Reference data" below)*
  - Specific file:line in `guardkit/orchestrator/autobuild.py` where the
    missing check belongs
  - Whether the wave-isolation contention path is implicated
  - Concrete reproduction steps (minimum failing example, ideally
    runnable from a `tests/integration/` fixture)
  - Affected scope: how many other prior autobuild completions are likely
    false positives
- [ ] A proposed fix to the autobuild loop that would have blocked the
      FEAT-6CC5 approvals — **filed as a separate task** in this repo
      (e.g., TASK-AB-FIX-001 with a concrete patch outline). Do not
      implement the fix under this investigation.
- [ ] A regression check (or written specification for one) that asserts:
      "if a task's acceptance criteria declare new files at specific paths,
      the coach cannot return `decision: approve` while `git diff` shows
      none of those paths created." Test should live under
      `tests/integration/orchestrator/` or equivalent.
- [ ] Decision recorded on whether other recent autobuild-completed
      features in consumer repos (study-tutor's FEAT-1773 / FEAT-FD32
      closeouts; any forge completions) need to be re-audited for the
      same class of false-positive

## Reference data

**Archived FEAT-6CC5 state** (committed in `study-tutor` repo):
- `study-tutor:.guardkit/archive/FEAT-6CC5/feature_state.yaml` — final per-task results
- `study-tutor:.guardkit/archive/FEAT-6CC5/review-summary.md` — pass-rate and turn counts
- `study-tutor:.guardkit/archive/FEAT-6CC5/events.jsonl` — orchestrator event log
- `study-tutor:tasks/backlog/mcp-llm-player-coach-adapters/TASK-LCA-{001,002,003}-*.md` —
  reopened tasks (`status: backlog`); historical `autobuild_state.turns[*]`
  was stripped from these but is preserved in `feature_state.yaml`
- `study-tutor:tasks/completed/TASK-LCA-{004,005}-*.md` — embedded
  `autobuild_state.turns[*]` for the two tasks that *did* produce code

**Deleted autobuild artefacts** — the per-task `player_turn_N.json` /
`coach_turn_N.json` blobs were removed from
`study-tutor:.guardkit/autobuild/TASK-LCA-*/` in
`study-tutor` commit `bb19903`. They are still reachable in git history
via the merge commit `d472565` (`git show d472565:.guardkit/autobuild/...`)
and the deleted branch tip `23b1a5a` (also reachable via `git fsck`).
**Read these for the full coach reasoning that preceded each approval** —
they contain the verbatim `coach_decision` JSON the loop emitted.

**Suspect code in this repo:**
- `guardkit/orchestrator/autobuild.py` — Player↔Coach loop, ~2000+ lines
  - `_run_autobuild_loop` (~L2040): terminating approval check
  - Conditional-approval path (~L1080): wave-contention branch
  - `TurnRecord` dataclass (~L711-737): `decision` literal definition
- `guardkit/orchestrator/autobuild.py:1356`: `status = "in_review" if final_decision == "approved" else "blocked"` — the gate that ultimately let FEAT-6CC5 ship

## Out of scope

- Implementing the missing TASK-LCA-001/002/003 modules in `study-tutor`
  (handled by re-running `/feature-build` against those three tasks;
  restored to that repo's backlog separately)
- Implementing the autobuild-loop fix itself (filed as a follow-up task)
- Re-auditing every prior autobuild completion (this task delivers the
  *decision* on whether that audit is warranted, not the audit itself)

## Notes

This investigation is critical because the fundamental value proposition of
the autobuild Player↔Coach loop is that a coach approval functions as a
quality gate. A 60% false-positive rate within a single feature
(3 of 5 tasks) materially undermines that guarantee. **Until this is
understood and fixed, any new autobuild run completed against any
consumer repo must be treated as suspect** — the merge-time file-existence
check we performed for FEAT-6CC5 in study-tutor should arguably be added
as an interim safety net in the autobuild loop itself.

Related prior investigation: `TASK-A5D6` (SDK timeout passthrough) used the
same `task_type: review` shape and produced
`.claude/reviews/TASK-A5D6-review-report.md` — follow that template.
