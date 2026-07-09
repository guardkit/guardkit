# Retro: AutoBuild burned two full runs on a task made un-passable by a pre-existing red baseline (plus four worktree/resume infra gaps)

**Date:** 2026-07-08
**Feature / task:** study-tutor `FEAT-VOICE-003` (Flutter tap-to-talk voice client, 7 tasks `TASK-VC-001..007`) — the blocked task was `TASK-VC-005` (SessionScreen tap-to-talk UX)
**Tool:** `guardkit autobuild feature` (SDK harness, `GUARDKIT_HARNESS=sdk`)
**Severity:** Medium (no bad code shipped — the feature was ultimately built 7/7, all gates green — but **~2.5 h of autobuild wall-clock across two runs was spent on a task that could never pass**, because the worktree's *baseline* test suite was already red and autobuild never checks for that. A human had to diagnose and hand-fix a 2-line stale test before the third run went 7/7 with every task approved in a single turn.)
**Status:** Resolved for this feature (baseline test fixed on study-tutor `main` @ `04226ef`; feature built on `autobuild/FEAT-VOICE-003`, awaiting review/merge). Four guardkit issues below remain open as action items.
**Tags:** autobuild, guardkit, baseline-red, worktree-bootstrap, uv-sources, symlink, task-timeout, refresh, rebase, coach, claim-audit, gitignore, flutter, dart
**Related:** [signature change missed production call sites](./2026-07-04-autobuild-signature-change-missed-production-callsites.md), [Coach missed an undefined BDD step](./2026-07-04-autobuild-coach-missed-undefined-bdd-step.md); study-tutor siblings: [self-defeating boundary tests](../../../study-tutor/docs/retros/2026-07-03-autobuild-self-defeating-boundary-tests.md), [parallel-wave worktree pollution](../../../study-tutor/docs/retros/2026-07-03-autobuild-parallel-wave-worktree-pollution.md).

## Summary

`FEAT-VOICE-003` ran three times before it landed. Waves 1–2 (`TASK-VC-001..004`) passed first-try on run 1. Everything then jammed on `TASK-VC-005` for two full runs:

- **Run 1 (76m):** `TASK-VC-005` hit the per-task wall-clock timeout (3000s) mid-implementation and failed. `stop_on_failure` halted the feature.
- **Run 2 (94m, `--resume` with a raised timeout):** `TASK-VC-005` no longer timed out — it ran all 8 Player↔Coach turns and **still could not get approval**, because the Coach's test gate (`tests_passed`) failed *every turn*.
- **Run 3 (43m, `--resume` after a human fix):** `TASK-VC-005`, `TASK-VC-006`, `TASK-VC-007` **each approved in one turn**; all three between-wave `flutter test` smoke gates passed; feature `completed` 7/7.

The thing that made `TASK-VC-005` un-passable was **not** in `TASK-VC-005`'s scope: the worktree's baseline suite already had one failing test on `main`. `app/test/slice/happy_path_test.dart` asserted `find.text('maths')` after starting a session through the UI, but the app's default subject had been reconciled from `maths` → `english` on 2026-07-07 (ASSUM-001) and that assertion was left stale. `flutter test` was red on `main` before the feature run even began. Every `TASK-VC-005` turn's Coach test gate correctly reported failure; the Player, whose task had nothing to do with the home-screen default subject, could not (and arguably should not) fix it. Once a human changed `'maths'` → `'english'` (2 lines), the whole feature fell out trivially.

Four guardkit behaviours turned "one stale baseline test" into a multi-hour, three-run diagnosis:

1. **No baseline-green check at worktree setup** — autobuild never runs the suite before wave 1, so a pre-existing red baseline is silently attributed to whichever task's Coach first runs the full suite.
2. **The per-task timeout floor is a flat 3000s that ignores the task's own estimate** — `TASK-VC-005`/`006` are estimated at 113/170 min; the 50-min floor guaranteed a timeout on run 1 and masked the real (test) failure as a *time* failure.
3. **`--refresh` rebases onto `origin/<base>`, not local `<base>`** — the baseline fix was committed to *local* `main` (unpushed); `--refresh` rebased the worktree onto a stale `origin/main` and conflicted, then printed a scary "worktree may be in inconsistent state" even though it had restored cleanly.
4. **The Coach's `claim_audit_gitignored` false-positives on negation rules** — `git check-ignore -v --no-index` matches the *negation* pattern `!app/lib/**`; the classifier read that as "silently dropped by `git add -A`" for files that are demonstrably tracked and committed, injecting 3 `should_fix` honesty discrepancies into *every* `TASK-VC-005` turn and dominating the Coach's feedback.

## Timeline / evidence

```
run 1  20:24–21:41  waves 1–2 PASS (VC-001..004). VC-005 → "Task timed out
                     (feature-level timeout) after 3 turn(s). Feature timeout: 3000s."
                     → wave 3 FAILED → stop_on_failure. 4/7.
run 2  (resume, GUARDKIT_AUTOBUILD_TASK_TIMEOUT_FLOOR=12000, --sdk-timeout 2400 --max-turns 8)
                     VC-005 runs 8 turns, no timeout, decision=max_turns_exceeded.
                     Coach every turn: quality gate tests=False (required=True), ALL_PASSED=False.
                     Criteria 0/9 verified (downstream criteria checks skipped once the
                     tests gate fails). 4/7.
run 3  (resume, baseline fix cherry-picked into worktree)
                     VC-005 approved (1 turn) → smoke gate ✓ → VC-006 approved (1 turn)
                     → smoke gate ✓ → VC-007 approved (1 turn) → smoke gate ✓. 7/7, 43m.
```

Ground truth (worktree working tree, run 2 state): `flutter test` → **209 passed, 1 failed** — the single failure was `happy_path_test.dart` `Expected: exactly one matching candidate / Actual: Found 0 widgets with text "maths"`. On `main`: `defaultSubject = 'english'` (`app/lib/ui/home_screen.dart`), test asserts `find.text('maths')` → the suite is red on `main` independent of the feature.

## Root cause — five findings

### 0. (Headline) No baseline-green gate before wave 1

autobuild sets up the worktree and dispatches straight into wave 1. It never asks "is the base suite already green?" So a pre-existing failing test is invisible until some task's Coach happens to run the full suite — and then it presents as *that task's* failure. Here waves 1–2 passed (their Coach test scope didn't surface the slice test), and the red baseline only bit `TASK-VC-005`, whose UI changes pulled the slice test into scope. The signal "this failure predates the task" was available the whole time (one `flutter test` at setup) and was never taken. This is the single highest-leverage gap: a 5-second baseline probe would have converted a 2.5-hour, three-run diagnosis into a wave-0 warning.

### 1. Worktree uv-sources symlink bootstrap follows a stale symlink into autofs (setup-phase crash)

Before any of the above, run 0 died in `_setup_phase` with:

```
FeatureOrchestrationError: Failed to create uv-sources symlink
  /System/Volumes/Data/home/richardwoollcott/Projects/appmilla_github/nats-core
  -> /Users/richardwoollcott/Projects/appmilla_github/nats-core:
  [Errno 45] Operation not supported: '/System/Volumes/Data/home/richardwoollcott'  (TASK-FIX-AB61)
```

study-tutor's `pyproject.toml` has `[tool.uv.sources] nats-core = { path = "../nats-core" }`. `_resolve_uv_sources_symlinks` (`environment_bootstrap.py`) computes the worktree-side link location as `worktree_resolved = (worktree_dir / path_value).resolve()`, i.e. `.guardkit/worktrees/FEAT-VOICE-003/../nats-core` → `.guardkit/worktrees/nats-core`. A **stale symlink already existed there** (left by an earlier environment where `$HOME` was `/home/richardwoollcott`) pointing at `/home/richardwoollcott/...`. `.resolve()` *followed* it → macOS firmlink `/System/Volumes/Data/home/...`, and `_create_worktree_uv_sources_symlinks` then `mkdir(parents=True)`'d that path, which is under the `/home` autofs mount and cannot be created (`Errno 45`). Removing the stale link let the bootstrap recreate it correctly (`nats-core -> /Users/...`). The fragility is guardkit's: `.resolve()` through a *pre-existing, possibly-broken* symlink at the intended link location, with no detect-and-replace of a dangling link.

### 2. Per-task timeout floor is flat 3000s and ignores `estimated_minutes`

`feature_orchestrator.py`:

```python
task_timeout_floor = int(os.environ.get("GUARDKIT_AUTOBUILD_TASK_TIMEOUT_FLOOR", "3000"))
floored_task_timeout = max(task_timeout_floor, task_timeout)
self.task_timeout = int(floored_task_timeout * self.timeout_multiplier)
```

`TASK-VC-005` and `TASK-VC-006` carry `estimated_minutes: 113` and `170` in the feature YAML — both well past the 50-minute floor. Run 1's `TASK-VC-005` timed out at exactly 3000s with 34/160 SDK turns used, no ceiling hit: it was making progress, just budgeted less than half its own estimate. Worse, the timeout **masked the real failure** — run 1 looked like a *time* problem, which is why the first remediation (raise the floor) was reasonable but insufficient; run 2 then revealed the underlying red-baseline test failure. The floor should be derived from (or at least clamped to) the task's `estimated_minutes` / complexity, or emit a wave-0 warning when `estimated_minutes` exceeds the effective per-task timeout.

### 3. `--refresh` rebases onto `origin/<base>`, not local `<base>`; abort-failure message is misleading

The baseline fix was committed to **local** `main` (`04226ef`) and deliberately not pushed. `--refresh` did:

```python
# feature_orchestrator.py _refresh_worktree()
subprocess.run(["git", "rebase", f"origin/{base_branch}"], cwd=worktree_path, check=True, ...)
```

`origin/main` was stale (`e5e108c`; local `main` ahead by the fix), so the rebase brought none of the fix and conflicted. The abort path then printed `⚠ Rebase abort failed -- worktree may be in inconsistent state` — but inspection showed the worktree was **fine** (HEAD back at the last checkpoint, no rebase in progress). The likely trigger wasn't "conflicts" at all: the worktree had one unstaged autobuild artifact (`.guardkit/autobuild/TASK-VC-005/checkpoints.json`), and `git rebase` refuses/aborts on a dirty tree. Workaround: `git -C <worktree> cherry-pick 04226ef` onto the autobuild branch, then plain `--resume`. Three sub-issues: (a) hardcoded `origin/` with no local option; (b) failure message asserts a state it didn't verify; (c) unstaged autobuild-managed artifacts should be stashed/committed before the rebase rather than blowing it up.

### 4. Coach `claim_audit_gitignored` false-positives on negation rules

Every `TASK-VC-005` turn, the Coach emitted (verbatim, `should_fix`):

```
claim_type: claim_audit_gitignored
player_claim: Player claimed file app/lib/ui/session_screen.dart
actual_value: Path is on disk but matched a .gitignore rule (.gitignore:331:!app/lib/**);
              'git add -A' silently skipped it. Fix the ignore rule ... and re-run the turn.
ignore_rule: .gitignore:331:!app/lib/**
```

This is false. `.gitignore` line 18 is `lib/` (which matches `app/lib/`), and lines 330–331 are the intentional re-includes `!app/lib/` / `!app/lib/**`. The file is **not** ignored and **is** committed:

```
$ git -C <worktree> check-ignore -v app/lib/ui/session_screen.dart ; echo $?
1                       # exit 1 = NOT ignored (no output)
$ git -C <worktree> ls-tree -r HEAD --name-only | grep app/lib/ui/session_screen.dart
app/lib/ui/session_screen.dart      # tracked & committed
```

The classifier (`autobuild.py::_git_check_ignore_rec`, `git check-ignore -v --no-index`, and the shared `coach_verification._classify_dropped_path` / `preflight_ignore_gate`) keys off the *matched pattern* while using `--no-index`, which reports the last matching pattern regardless of tracking state — and here that last pattern is a **negation** (`!...`). A negation match means *re-included*, the opposite of dropped. The audit neither honours the exit code nor checks `git ls-files` (is it already tracked?) nor skips `!`-patterns, so it manufactures a discrepancy for tracked files under any `!`-re-included tree. `should_fix` means it's non-blocking, but it led every turn's Coach feedback and plausibly steered the Player into re-churning the same 3–5 `app/lib/**` files each turn (chasing a phantom gitignore problem) instead of the one real red test.

## Impact

No defective code merged — the opposite of the two 2026-07-04 retros. But the failure mode is expensive in a different way: an autonomous run **spent ~2.5 hours and two full feature runs unable to converge**, and the summaries pointed everywhere except the cause (run 1: "timeout"; run 2: "max_turns_exceeded" + honesty discrepancies about gitignore). The real cause was a 2-line stale test in the *baseline*, discoverable in one `flutter test`. Once fixed, `TASK-VC-005/006/007` each passed in a single turn — proof the tasks themselves were never the problem and the Player↔Coach loop works well when the baseline is honest.

## Resolution

- Baseline fix on study-tutor `main` @ `04226ef` (`app/test/slice/happy_path_test.dart`): `find.text('maths')` → `find.text('english')` with a `reason: 'session lists under the default subject (ASSUM-001)'`. Verified green: 125/125 on `main`, 210/210 in the worktree. The ~50 other `'maths'` references pass an *explicit* `subject: 'maths'` and are correct — only the slice test, which starts a session via the UI default, was stale.
- Propagated into the worktree by cherry-pick (`388f893`) after `--refresh` failed; feature completed on `autobuild/FEAT-VOICE-003` (13 commits ahead of `main`, preserved for review). Timeout raised for the successful run via `GUARDKIT_AUTOBUILD_TASK_TIMEOUT_FLOOR=12000 --sdk-timeout 2400 --max-turns 8`.
- The run-0 setup crash was fixed by removing the stale `.guardkit/worktrees/nats-core -> /home/...` symlink and clearing the partial worktree/branch.

## Prevention / action items

- [ ] **(Highest leverage) Add a baseline-green gate at worktree setup.** Run the feature's smoke/test command once before wave 1 and record the result. If the base is already red, surface it as a wave-0 warning ("N pre-existing failures — not attributable to any task") rather than letting it masquerade as the first UI task's failure. Cheap (one test run) and would have collapsed this entire incident.
- [ ] **When a Coach test gate fails, diff against the baseline failures.** A task's test gate should fail the task only for tests that *regressed* relative to the recorded baseline; pre-existing failures should be reported as environmental, not charged to the Player. (Prevents a task being asked to fix tests outside its scope.)
- [ ] **Derive the per-task timeout from the task's own estimate.** Floor at `max(3000, estimated_minutes*60*k)` or similar, and emit a warning when `estimated_minutes` exceeds the effective per-task timeout. A flat 3000s floor guarantees timeouts on the large tasks these features routinely contain — and a timeout masks whatever the real failure is.
- [ ] **`--refresh` should rebase onto the ref the operator actually fixed.** Default to local `<base>` (or make the ref configurable / detect `local ahead of origin`), because operators routinely fix baseline bugs on local `main` without pushing. Minimum: document that `--refresh` targets `origin/<base>`.
- [ ] **`--refresh` must handle a dirty worktree and report state truthfully.** Stash/commit autobuild-managed artifacts (e.g. `.guardkit/autobuild/**/checkpoints.json`) before rebasing; and don't print "worktree may be in inconsistent state" without verifying it — here the restore succeeded and the message was simply wrong.
- [ ] **Fix the `claim_audit_gitignored` negation false-positive.** In the check-ignore classifier (`autobuild.py::_git_check_ignore_rec`, `coach_verification._classify_dropped_path`, `preflight_ignore_gate`): treat a match against a `!`-negation pattern as *not dropped*; and/or short-circuit with `git ls-files --error-unmatch <path>` (a tracked file is never being silently dropped by `git add`), rather than relying on `--no-index` pattern matching alone.
- [ ] **Harden uv-sources symlink bootstrap against stale links.** In `_resolve_uv_sources_symlinks`, avoid `.resolve()`-ing *through* a pre-existing symlink at the intended link location; detect a dangling/wrong link at `<worktree>/<sibling>` and replace it, instead of following it into an un-`mkdir`-able path (`Errno 45` under `/home` autofs on macOS).

## Links

- study-tutor baseline fix: `main` @ `04226ef`. Feature result: `autobuild/FEAT-VOICE-003` (unmerged, 7/7, all smoke gates green).
- guardkit code touched by the action items: `guardkit/orchestrator/environment_bootstrap.py` (`_resolve_uv_sources_symlinks`, `_create_worktree_uv_sources_symlinks`), `guardkit/orchestrator/feature_orchestrator.py` (task-timeout floor ~L770, `_refresh_worktree` ~L1274), `guardkit/orchestrator/autobuild.py` (`_git_check_ignore_rec` ~L5491), `guardkit/orchestrator/preflight_ignore_gate.py`.
- Family of autobuild retros: this one is the "Coach-green loop can't converge because the *baseline* is red, and the infra masks why" case — complementary to the earlier "Coach-green but not mergeable" defects (stale tests, undefined BDD steps, call-site drift).
