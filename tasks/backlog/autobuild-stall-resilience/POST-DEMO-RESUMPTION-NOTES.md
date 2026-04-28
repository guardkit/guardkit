# Post-DDD-Southwest resumption notes — FEAT-ABSR-9C6E

**Created**: 2026-04-28 after WTKS design approval
**Demo deadline**: ~20 days from 2026-04-28 (target ~2026-05-18)
**Pick this back up after**: Demo wraps and you're ready for the post-demo sprint

---

## Snapshot of where we left off

The autobuild-stall-resilience feature has **three open work items** when you return:

| Task | Status | Priority | What's done | What's next |
|------|--------|----------|-------------|-------------|
| [TASK-ABSR-CMPL](TASK-ABSR-CMPL-phase-25-complexity-heuristic.md) | backlog | **HIGH** (escalated by TASK-REV-WORS) | Spec written | `/task-work TASK-ABSR-CMPL` — implement Phase-2.5 effective-complexity heuristic |
| [TASK-ABSR-WTKS](TASK-ABSR-WTKS-worktree-isolation-per-parallel-task.md) | **design_approved** | medium | Design doc + Phase-2.5 review (76/100) + Phase-2.8 human checkpoint approved 2026-04-28 | `/task-work TASK-ABSR-WTKS --implement-only` — begin Phase 1 implementation |
| [TASK-FIX-OCRC](../TASK-FIX-OCRC-orchestrator-cancellation-cleanup.md) | backlog | low (post_demo: true) | Triage complete (TASK-REV-OCRC v1) — real bug confirmed; 12 ACs across 3 defects; complexity 4; ~1-2 days; design-phase caveats embedded | `/task-work TASK-FIX-OCRC --design-only` — produce plan, then implement (independent of CMPL/WTKS) |

**Already shipped (don't repeat)**:
- TASK-ABSR-FLOR — MAXT floor 150 + task_timeout floor 3000s. Validated by jarvis FEAT-J004-702C run-4 (20/20 tasks, 100% success, 0 ceiling hits).
- All R1-R6 fixes from TASK-REV-9D13 v2 (in commit `87c27e60`).
- All FA04-driven Wave 1-2 fixes.

---

## Recommended sequencing when you return

The architect's recommendation (from WTKS Phase-2.8 checkpoint): **CMPL first, then WTKS**. Reason: CMPL reduces ceiling-hit *frequency*, which reduces the cascade's *frequency*, which reduces WTKS's marginal value per unit effort. CMPL is more leveraged.

Suggested order:

1. **TASK-ABSR-CMPL** (~4-8 hours, complexity 5)
   - Phase-2.5 effective-complexity heuristic (AC count + dep count + consumer count signals)
   - Re-run jarvis autobuild after to validate no regression on previously-passing tasks
2. **TASK-ABSR-WTKS Phase 1** (~2 days, Option C — pre-Phase-4 consistency check)
   - Tactical guard. Detects worktree poisoning, doesn't prevent it
   - Validates the consistency-check approach in production before committing to Phase 2
3. **TASK-ABSR-WTKS Phase 2** (~4 days, Option A — per-task subworktrees)
   - Structural fix. Each parallel task gets its own git worktree
   - Eliminates the cascade class
4. **TASK-FIX-OCRC** (~1-2 days, complexity 4, low priority, post_demo: true)
   - Single task covering the three coupled defects from TASK-REV-OCRC triage:
     - Defect 1: atomic `_clean_state` (`feature_orchestrator.py:1628-1631` — `reset_state()` and `save_feature()` are non-atomic)
     - Defect 2: replay-vs-execute event disambiguation (`feature_orchestrator.py:2300-2321` — `WaveCompletedEvent` always emits even when wave is fully short-circuited on resume)
     - Defect 3: orphan `TASK-J004-013` START at `events.jsonl:49` — bundled with explicit downscope clause (AC-010): if Defect 1's fix closes it, regression-test it; otherwise file separately
   - **AC-007 surfaces a small correctness exposure** (worth pinning even though no incident is traced to it): `ConcurrencyController.on_wave_completed` consumes `WaveCompletedEvent`, so Defect 2's replay-vs-execute disambiguation is **NOT purely cosmetic** — replayed waves currently feed zero-latency datapoints into worker-count adaptation. Replacing the spurious emission with a `WaveSkippedEvent` (or adding a `replay` flag) prevents observability/adaptation pipeline pollution
   - Single task chosen over three because all three defects share the `_clean_state` → `_execute_wave_parallel` → wave event emission call sites; bundling avoids duplicate call-site audits
   - **Sequencing interaction with WTKS Phase 2**: per-task subworktree cleanup is sibling to feature-level state cleanup (the `_clean_state` path Defect 1 fixes). If WTKS Phase 2 ships before TASK-FIX-OCRC, the design phase here must reconcile the two cleanup paths. If TASK-FIX-OCRC ships first, WTKS Phase 2's cleanup design should adopt the atomic-save pattern landed here
   - Independent track otherwise; can run alongside CMPL or WTKS Phase 1 without code conflict

---

## WTKS design-approved snapshot (most important to recover)

**Design doc**: `.claude/task-plans/TASK-ABSR-WTKS-implementation-plan.md` (619 lines)

**Recommended option (DIVERGED from task file's starting point)**:
- Phase 1: **Option C** (Pre-Phase-4 consistency check) — tactical guard, ~2 days
- Phase 2: **Slimmed Option A** (Per-task subworktrees) — structural, ~4 days

**Why diverged from task file's "Option E (B+C) starting point"**: Option B rejected because:
- `git stash` / `git reset --hard` are worktree-wide operations, not per-task scopable
- Bash subprocesses (including pytest) always see the underlying filesystem, so a Python-level overlay can't protect Coach
- macOS dev hosts lack overlayfs (Linux-only kernel feature, macFUSE alternatives unmaintained on Apple Silicon)

This rejection is structurally correct; don't second-guess it.

**Phase-2.5 Architectural Review**:
- Score: **76/100** (clears AC-DES-003 ≥60/100 bar)
- Breakdown: SOLID 74, DRY 82, YAGNI 72
- Verdict: APPROVE WITH RECOMMENDATIONS
- M1/M2/M3 medium-issue corrections were applied to the design doc before approval

**Phase-2.8 Human Checkpoint**: APPROVED on 2026-04-28 15:30 UTC (status: design_approved in frontmatter).

**Effort estimate**: 6-8 days total (Phase 1: 2d, Phase 2: 4d, +20% test-mock churn buffer).

**LOC estimate**: ~870 source + ~350 tests = ~1220 lines total.

**Key files Phase 1 will touch**:
- `guardkit/orchestrator/worktree_consistency.py` (NEW)
- `guardkit/orchestrator/autobuild.py` (additive)
- `guardkit/orchestrator/feature_orchestrator.py` (additive)
- ~200 LOC tests

**Key files Phase 2 will touch**:
- `guardkit/orchestrator/worktree/manager.py` — new `create_for_task()` method
- `guardkit/orchestrator/feature_orchestrator.py` — wave setup/teardown
- `guardkit/orchestrator/worktree_checkpoints.py` — lock conditionalisation
- ~350 LOC tests including the regression test pinning the J004-011/J004-012 cascade scenario

---

## Two caveats to address at Phase-2 design checkpoint

These are NOT blockers for Phase 1 (Option C is independent of these). Surface them when planning Phase 2 (Option A):

### Caveat 1 — Verify R3 disk-usage against actual Jarvis worktree size

The architect estimated 4 parallel tasks × 300 MB = 1.2 GB per wave. **Verify the 300 MB number is realistic for Jarvis specifically** before Phase 2 implementation. Jarvis has vendored deps + a Python venv; real-world per-task worktree could be 500 MB-1 GB.

```bash
du -sh /Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/worktrees/FEAT-J004-702C
```

If closer to 1 GB, then 4 × 1 GB = 4 GB per wave on dev hosts. Still fine, but the architect's arithmetic should reflect ground truth, and the docs should warn about disk usage on smaller dev machines.

### Caveat 2 — `.guardkit/autobuild/TASK-XXX/` artifact path placement

The orchestrator currently writes `player_turn_*.json`, `coach_turn_*.json`, `task_work_results.json` etc. to a **shared** path under `.guardkit/autobuild/<TASK>/`. If each task gets its own subworktree under Option A, the artifact dir might end up *inside* the per-task subworktree, breaking the orchestrator's collection logic and the events.jsonl that lives at the feature-level shared path.

**Add this as an explicit Phase-2 AC**: "Per-task subworktrees contain only source/test code; autobuild artifacts continue to live in `.guardkit/autobuild/<TASK>/` at the feature root, written by the orchestrator after Player completion."

This is essentially what R5's call-site audit should cover, but worth calling out specifically because the events.jsonl trace work in TASK-REV-WORS depends on the shared-path assumption.

---

## Open question worth resolving (non-blocker)

**Action B from TASK-REV-WORS** was never run: replay TASK-J004-011 at `git checkout 87c27e60^` to determine whether the +25 turn delta from run-2 to run-3 is GuardKit-internal or external. The run-4 success made it lower-priority, but if you want to fully close the diagnostic loop, this is the cheapest discriminating experiment (~30-60 min).

If external (Anthropic-side variance), then WTKS is correctly solving the *cascade class* but not the underlying turn-count variability. That's fine — the FLOR floors handle the variability, and WTKS handles the cascade — but worth knowing for the post-mortem write-up.

---

## Cross-references

- [TASK-REV-WORS report v2](../../../.claude/reviews/TASK-REV-WORS-report.md) — full diagnostic with C4 + 4 sequence diagrams. Source of truth for the failure mode WTKS prevents.
- [TASK-REV-WORS report v2 §4.3](../../../.claude/reviews/TASK-REV-WORS-report.md#43-the-shared-worktree-poison--file-system-level-view) — the cascade sequence diagram WTKS Phase-2 regression test must replicate-and-prevent.
- [TASK-REV-9D13 report v2](../../../.claude/reviews/TASK-REV-9D13-report.md) — prior diagnostic that drove R1-R6 (now all shipped).
- [Feature README](README.md) — full subtask matrix including completed work.
- [Implementation Guide](IMPLEMENTATION-GUIDE.md) — wave plan and test strategy from the original FA04+9D13 work.

---

## When you actually pick this up

1. **Re-read this doc first** to recover context (5 min).
2. **Re-read the WTKS design doc** at `.claude/task-plans/TASK-ABSR-WTKS-implementation-plan.md` (15-20 min for 619 lines).
3. **Decide order**: CMPL → WTKS, or skip CMPL if no longer relevant after the demo.
4. **Run** `/task-work TASK-ABSR-CMPL` (or `/task-work TASK-ABSR-WTKS --implement-only` if going straight to WTKS Phase 1).
5. **Re-validate with jarvis autobuild** between each major change so you can attribute any new behaviour cleanly.
6. **Update this doc** when work resumes (rename to `RESUMPTION-COMPLETE.md` and link to the resulting completed tasks for future-you's reference).
