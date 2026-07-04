# ABL-001 run 3: an honest failure, a caught false-green — and a credential leak

**Date:** 2026-07-04 · **Feature:** FEAT-ABL-001 (retrieval arm switch + logging)
**Run:** autobuild run 3 (final attempt per operator policy), `--resume`, gpt-oss-120b Player / gemma4-coach Coach
**Outcome:** FEATURE FAILED after 5 turns / 15m41s — TASK-ABL1-001 passed (retained), TASK-ABL1-002 failed honestly. Autobuild retired for this feature; remainder hand-finished per the ABL-005 playbook.
**Companions:** `abl001-natscore-stub-false-green-2026-07-03.md` (run 2), `abl005-autobuild-infra-chain-2026-07-04.md` (the sibling feature's five-run arc).

## The two failure modes, both real signal

Unlike runs 1–2 (infrastructure), run 3 failed on **substance, honestly graded**:

1. **Turn 1 — env-isolation defect in the Player's test.** The new
   `test_fleet_memory_client` test asserted a monkeypatched
   `postgres_dsn`, but the config loader read the **ambient**
   `FLEET_MEMORY_PG_DSN` from the loop's environment — so the assertion
   failed by printing expected-vs-actual DSNs (33 tests ran, 1 failed).
   The Player then *narrated* the suite as green; the orchestrator's
   evidence guard overrode it:
   `quality_gates claimed all_passed=None/tests_passing=True — overriding
   to NOT passed (narrative false-green)`.
2. **Later turns — collection breakage.** Subsequent Player edits broke
   pytest collection of the same module outright
   (`ERROR collecting tests/unit/knowledge/test_fleet_memory_client…`,
   `tests_run=1 tests_failed=1`), with the false-green narrative caught
   and overridden again. Stall→fail after 5 turns.

Positive note for the loop itself: **the narrative-false-green guard worked**,
twice, in-loop — the class of dishonesty that fs-01 (2026-06-13) let through
is now caught at turn granularity. Run 3 is the first ABL run where every
verdict was backed by an honest test signal end to end.

## The credential leak (severity: real, contained)

The turn-1 assertion failure printed the ambient DSN — the **live NAS
store's** credentials — into pytest output. The leak then travelled:

```
failing assertion output (contains live DSN, truncated by pytest)
  → Coach evidence / turn-tracking JSON (worktree .guardkit/autobuild/)
    → task-md frontmatter turn history (tasks/backlog/…/TASK-ABL1-002-…md)
      → chore commit "land stashed FEAT-ABL-001 run state…"
        → pushed to github.com/guardkit/guardkit — PUBLIC
```

**Exposure:** 14 of the 32 password characters (pytest's diff truncation
cut the rest), one file, public main, window of hours. The store listens
only on the tailnet (`whitestocks…ts.net:5433`), so exploitation requires
tailnet access — mitigating, not excusing.

**Remediation done (2026-07-04):** fragment redacted at HEAD and pushed
(`65dc8256`); fleet-memory and fleet-evals HEADs verified clean; run logs
and worktree evidence files holding the fragment confirmed gitignored.

**Remediation OWED (operator decisions):**
1. **Rotate the fleet_memory Postgres password** — 14/32 chars public means
   treat as compromised. Touches: NAS Postgres, `fleet-memory-relay`
   container env, guardkit/fleet-memory `.env` files, P3/P4 env contracts.
2. **History rewrite decision** for guardkit main (the fragment persists in
   pushed history: `cbce5cf25`, checkpoint commits, and 3 later commits) —
   same call the fleet-evals FinProxy incident forced on 2026-07-03.

## Lessons

1. **Secrets in loop env + failing assertions = leak channel.** Any test
   that compares DSN-bearing config will print credentials on failure.
   Guards, in preference order: don't run agent loops with live credentials
   in ambient env (P4 says fixture DSNs — live creds had no business there);
   scrub DSN-shaped strings in turn-tracking/evidence writers before they
   reach task mds (ABL-005's `scrub_secrets` in fixture/dsn.py is the
   in-repo prior art); make "land stashed run state" chores subject to the
   same secret-scan gate as pre-public scrubs.
2. **Turn-tracking is a publication path.** Task mds carry embedded test
   output into git history by design; anything the suite prints is one
   chore commit from public. Treat evidence-file content as
   publish-equivalent.
3. **The honesty guard earns its keep** — both false-green narrations were
   overridden deterministically. Worth a §6c corpus task of its own: the
   run-3 trace (honest-fail + caught narration) alongside the run-2 stub.
4. **Env isolation belongs in the task spec.** TASK-ABL1-002's spec assumed
   monkeypatched settings; the client reads process env at import/call
   time. The hand-finish must make the arm-switch tests hermetic
   (`monkeypatch.delenv`/`setenv` around the full FLEET_MEMORY_* surface).

## Feature-level verdict

Autobuild for FEAT-ABL-001: 3 runs, retired. Salvage: TASK-ABL1-001
complete and green in the worktree; 002's core arm-switch logic
spec-correct per run-2 forensics (operator commit `9f9d0b75` preserved
it); 003/004 unstarted. Hand-finish proceeds on the ABL-005 pattern:
sequential implementation in the worktree, suite-gated commits, three
arm-state validation (unset/off/fixture) before merge.
