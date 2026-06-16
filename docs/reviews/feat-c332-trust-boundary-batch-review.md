# FEAT-C332 Trust-Boundary Fix Batch — Review

**Status:** REVIEW (captured for action after the next autobuild run)
**Date:** 2026-06-13
**Reviewer session:** Claude Fable 5 (Claude Desktop, ai-transition project)
**Batch reviewed (all `completed`, none yet merged to a shipped baseline at review time):**
TASK-AB-XREPOEV01 · TASK-FIX-WTESCAPE01 · TASK-FIX-SPECVIOL01 · TASK-FIX-COACHNARR01
**Origin:** defects surfaced by the FEAT-C332 (QA-Verifier wiring probes) autobuild runs 1–2 — all caught before merge, none a false-GREEN.
**Companion docs:** `docs/retro/qa-verifier-autobuild-session-handoff.md` · `../ai-transition/docs/fine-tuned-judgment-agents-findings.md`

---

## 1. One-frame summary

All four fixes are the same meta-class: **an oracle whose evidence boundary did
not match the task's real write surface.** FEAT-C332 was the first feature whose
own build *stressed* that boundary (it writes cross-repo into guardkitfactory via
the `.guardkit/worktrees/guardkitfactory` symlink), and the stress exposed four
distinct leaks:

| Fix | Boundary failure | Symptom |
|---|---|---|
| **XREPOEV01** | too **narrow** — legit factory-side writes invisible to worktree git-diff | false-RED ("no implementation provided" over 2,100+ lines of real work) |
| **WTESCAPE01** | too **porous** — Player wrote to absolute host-repo paths the file tools didn't confine | host-repo corruption **and** false-RED (escaped writes read as unstaged → honesty discrepancy) |
| **SPECVIOL01** | **misattributed** — comma-joined `test_file` string audited as one path | `Path.exists()` false → "fabrication" → `partial_honesty_abort`, criteria aborted, budget exhausted |
| **COACHNARR01** | **narrated over** — B-min synthesis paraphrased a deterministic record | invented "files do not exist" for files that exist → unactionable feedback |

The rules tree already names this class
(`absence-of-failure-is-not-success`, `path-string-mismatch-is-not-dishonesty`).

## 2. The load-bearing finding

**The Coach's verdict *direction* was correct in all four cases — every failure
was a false-RED or an honest-but-unactionable rejection, never a false-GREEN.**
SPECVIOL01 states it explicitly: "the verdict direction was right both turns; the
explanation was fabricated." Under genuine stress on novel, cross-repo,
write-surface-stressing work, the honesty oracle stayed **conservative**. What
broke was the scaffolding *around* the verdict — attribution, evidence scope,
narration — not the verdict itself. That is the far less dangerous failure surface,
and it is the asymmetry the whole Player-Coach architecture bets on. It held.

## 3. Per-fix quality read

### XREPOEV01 — standout; most strategically important
- `evidence_repos: [../guardkitfactory]` is the right contract: **explicit
  declaration, never implicit scanning** (AC-003 guards the over-reach).
- **Adversarial review caught a false-GREEN hole *inside the fix*:** the first
  implementation wired `evidence_repos` into AC-verification but not into the
  Coach's own honesty `CoachVerifier` (`_verify_honesty`) → sibling-file lies
  would have been undetectable. Review factored a shared `_evidence_repo_gate`
  across primary + legacy paths and added a seam test. This is the review layer
  doing real work.
- Second-instance discovery is the scary one: **BDDW-002's factory half was
  APPROVED but never committed anywhere** — merged tests passed only while
  uncommitted factory edits sat in the editable-install tree; "one `git clean`
  away from breaking main." Same root cause, now closed.
- Central contract in one module (`evidence_repos.py`), per namespace-hygiene.
  64 new tests, 88% coverage. Sound.

### WTESCAPE01 — most fundamental; falsifies a *claimed invariant*
- `selector.py:363` claimed the backend was path-confined; for **file tools** it
  was not (`build_autobuild_backend` confined the shell cwd, not Write/Edit).
- Fix confines file tools via `PathConfinedBackend` (`Path.resolve()` +
  `is_relative_to`). **Reject, not rebase** — correct, with sharp reasoning
  ("rebasing is the doubly-nested-path NOVMODE failure in reverse").
- **Symlink policy handled exactly right:** explicit narrow allow for the one
  intentional `guardkitfactory` sibling symlink, reject all others, tested both
  ways. Plus explicit `extra_write_roots=`.
- Shook out **two latent gather-path defects** (pre-existing since COACHSYNTH):
  `CompositeBackend.execute` ABC-isinstance gate failing delegating wrappers, and
  `TruncatingBackend` hiding the `timeout` kwarg from signature introspection.
  Both fixed with regression tests. Wrapper is clearly exercising real paths.

### SPECVIOL01 — most instructive; original hypothesis was wrong and forensics caught it
- Original theory (injected `validation=violation` specialist records read as
  Player dishonesty) was **refuted**: the honesty checks never read that field.
- Real cause: claim-audit gate auditing a comma-joined two-path `test_file`
  string as a single path. Fix **partitions claims by provenance** (`test_file` =
  run-claims, comma-split; run-claim on an existing tracked file emits zero
  signal; nonexistent path stays `claim_audit` critical → AC-004 preserved).
- Strength worth naming: a weaker process would have "fixed" the wrong hypothesis,
  the symptom would have vanished (watchdog already bounds the hang), and the real
  comma-split bug would have lurked to fire on any multi-file test claim. The
  provenance partition is the correct, generalising fix.
- Substrate advisory (`_compute_specialist_failure_advisories`) surfaces the
  specialist hang as `should_fix`, never silently dropped (AC-002).

### COACHNARR01 — right call, narrowest scope; guard on a symptom
- Reconciler renders deterministic records **verbatim**
  (`render_deterministic_issues`) and strips unsupported "does not exist" claims
  per-clause (`strip_unsupported_nonexistence_claims`); narrative-only, never
  flips verdict direction; re-persists `coach_turn_N.json`. 13 tests, 93%.
- **The task is admirably honest that it does not fix the cause:** Phase-A
  degrading to B-min 100% of the time (COACHGATHER01) means the synthesis model is
  *always* narrating records it could not inspect. COACHNARR01 guards the symptom;
  the disease is still open.

## 4. The thread that ties it together — and the caution

**Three of the four name COACHGATHER01 as upstream cause or correlate.**
WTESCAPE01 and SPECVIOL01 both fed the *same* run-2 `partial_honesty_abort`
spiral; COACHNARR01 exists *only because* gather degrades to B-min. The picture: a
single substrate weakness (Phase-A never converges on the 26B MoE,
`recursion_limit` of 12) plus an evidence boundary narrower/porous-er than reality,
compounded into one ugly run needing four fixes to unwind.

**Caution (registered honestly):** four targeted guards now sit on top of a
degradation that is still unaddressed. Each is sound, but each adds a special-case
reconciler to `agent_invoker` — the stack is now
`_reconcile_absent_independent_test_signal`, `_apply_spec_gap_absent_guard`,
`_reconcile_coach_narrative_with_records`, the `_evidence_repo_gate`, and the
claim-provenance partition. They all compensate for the same thing: Phase-A not
converging. Fixing gather (COACHGATHER01 Option A) or formally retiring it
(Option B) would remove the *reason* COACHNARR01 must exist and **shrink the
compensation surface rather than grow it.** Priority is currently medium, which is
defensible because `GATHER` is OFF by default (no live false-result risk) — but the
interaction argues for looking sooner than "medium" implies.

## 5. Open threads (parked, not blocking)

- **COACHGATHER01 — the root cause.** Investigate-first step now has **four
  richly-documented run-2 failure cases** as input. Recommend actioning after the
  next autobuild run (operator's stated plan). Decide Option A (make Phase-A
  converge, re-check the 98K-window budget: `recursion_limit × max_tool_result_chars`)
  vs Option B (retire B-full, ship B-min-only, close COACHBFULL promotion track).
- **test-orchestrator hang root cause** (SPECVIOL01 half 2, WTESCAPE01 follow-up):
  bounded by the SPECHANG2 watchdog, unexplained — suspected llama-swap
  model-swap latency under LangGraph. Same contention class as the specialist-agent
  advisory-call problem; the **second GB10 Spark is plausibly the structural fix**
  for both.
- **WTESCAPE01 defence-in-depth follow-ups** (explicitly not done): orchestrator
  host-repo `git status --porcelain` backstop after each Player turn;
  prompt-assembly rewriting of absolute host paths to worktree-relative; SDK-harness
  equivalent confinement (gap is theoretical there, observed on LangGraph only).

## 6. Net

Strong batch. The QA-Verifier deterministic wiring layer (piece #2 of the
fine-tuned-judgment-agents program) is in, and **building it was the most
demanding generalization test the loop has faced** — novel, cross-repo,
write-surface-stressing. The honesty oracle came through it conservative and
trustworthy while the scaffolding around it got hardened. None of the four was a
false-GREEN; all were caught before merge; the adversarial review caught a
false-GREEN hole *inside* a fix. That is the system working.

**For the next findings-doc sync (no action now):**
1. This is the evidence to update the findings-doc framing — QA-Verifier piece #2
   built; the evidence-boundary meta-class now well-characterised with a rules-tree
   home.
2. COACHGATHER01 is the common upstream cause of the compensation stack and
   deserves a hard look sooner than "medium" — its investigate-first step is now
   well-supplied with run-2 evidence.
