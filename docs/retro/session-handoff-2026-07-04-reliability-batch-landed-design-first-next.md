# Session handoff — 2026-07-04: reliability batch landed; five design-first tasks next

> **Purpose:** start a fresh conversation from here. The previous session ran out of
> context after: (1) deep cross-repo failure research, (2) filing 15 tasks, (3)
> implementing 10 of them + 19 post-review fixes, (4) committing and pushing.
> This doc is the complete state + the decision sheet for the five deliberately-open
> **design-first** tasks, including exactly what operator input each one needs.

---

## 1. What happened (one screen)

- **Research:** five retros (2026-07-03/04) were analysed against ~80 autobuild
  history docs across guardkit/jarvis/forge/study-tutor/specialist-agent (153
  documented incidents) and against current source. Output:
  [`docs/retro/autobuild-retro-xref-2026-07-04.md`](autobuild-retro-xref-2026-07-04.md)
  — read §4 (do-not-refile) and §6 (do-not-regress) before ANY autobuild work.
- **Filed:** 15 tasks in [`tasks/backlog/autobuild-reliability/`](../../tasks/backlog/autobuild-reliability/)
  (README there is the index). Every task has a **Regression constraints** section
  naming the `.claude/rules/*.md` files that bound its fix.
- **Implemented + tested (10 tasks, ~250 new tests):** STALEATTRIB01, NULLEVID01,
  SKIPVIS01, STALLTAX01, WAVECTL01, COACHSUBPROC01, INVARIANTTEST01, BASETEMP01,
  RESUMEVENV01, ZEROTESTLOUD01 — then an 8-angle adversarial review of that batch
  found 19 real findings (all fixed; headline: the newly-live YAML
  `recommended_parallel` tier was made **lowering-only** so it can never raise the
  local-backend concurrency safety cap).
- **Verification:** full `tests/unit + tests/orchestrator + tests/rules` = **9,312
  passed**; the 101 failures are **byte-identical to the pre-existing HEAD
  baseline** (py3.10 `asyncio.timeout` SDK tests ×~90, the dead-task-ID lint trio
  TASK-FMDR-001/TASK-RBX-002/TASK-FIX-UVSRCDEP01, 2× TestResolveTestsRequired).
- **Committed/pushed to guardkit `main`:** `e9320a19` (docs/tasks/P0 config) and
  `111b02ac` (implementation + review fixes). A talk content pack is at
  [`docs/talks/autobuild-reliability-lessons-2026-07.md`](../talks/autobuild-reliability-lessons-2026-07.md).
- **External state:** ABL-005 run 5 (final attempt) **failed honestly** and was
  hand-finished + merged (fleet-memory `caa670f`, 754 green) — see
  `docs/retro/abl005-autobuild-infra-chain-2026-07-04.md` + its outcome commit
  `6051be30`. FEAT-ABL-001's staged resume now has `bootstrap_extras: [dev, memory]`
  in its YAML (the YAML change alters the bootstrap hash, so resume will
  re-bootstrap with the memory extra — the R1 root cause is closed for that run).
  study-tutor's parallel-wave retro correction is committed upstream (`38efe5d`).
- Session memory pointer: `~/.claude/projects/...-guardkit/memory/autobuild-retro-xref-2026-07-04.md`.

Housekeeping the next session could raise: the local `.venv` is Python **3.10.19**
while the SDK-path tests need 3.11+ (`asyncio.timeout`) — rebuilding the dev venv
on 3.12 would un-skip ~90 baseline failures. Not urgent; the fix batch was
cross-checked on a scratch 3.12 venv where relevant.

---

## 1.5 ADDENDUM (2026-07-05) — two more retros landed; read before proceeding

Two retros arrived after this handoff was first written. Both are analysed and
folded in here; two new tasks were filed (the backlog folder now holds 17).

### (a) ABL-001 run 3 — honest failure + CREDENTIAL LEAK
([`abl001-run3-honest-fail-and-credential-leak-2026-07-04.md`](abl001-run3-honest-fail-and-credential-leak-2026-07-04.md))

Run 3 failed **honestly** — the narrative-false-green guard (PERTASKFG01
lineage) caught and overrode the Player's "suite is green" narration TWICE
in-loop; the feature was retired to hand-finish per the ABL-005 playbook. That
half is validation, not a defect.

The defect: a failing assertion printed the **live NAS store DSN** from the
loop's ambient env, and that output travelled the standard publication path
(evidence JSON → task-md turn history → the `cbce5cf2` "land stashed run
state" chore commit → public GitHub). 14/32 password characters were public
for a window of hours. Redacted at HEAD (`65dc82562`); verified 2026-07-05
that the only remaining DSN-shaped strings in tracked files are benign
localhost fixture/test DSNs.

**⚠ OPERATOR-OWED DECISIONS — status as of 2026-07-05:**
1. ✅ **Password rotation DONE (2026-07-05)** via the new
   `fleet-memory/deploy/nas/rotate.sh` (gates R0-R4 green; R2a proves the auth
   path enforces passwords — added after the first run exposed that in-container
   loopback is `trust`, making naive password gates vacuous). Verified: no real
   `.env` in any local checkout held the credential; the live copies were the
   NAS-side `.env`, the GB10 relay `.env.deploy`, and ambient shell exports.
   Remaining consumer steps at rotation time: GB10 relay `.env.deploy` +
   compose restart, shell exports (fixture DSNs only for loops per P4),
   `guardkit memory status` + `deploy/nas/smoke.sh` verification.
2. **History-rewrite call for guardkit main — STILL OPEN** — the fragment
   persists in pushed history (`cbce5cf2` + checkpoint commits + 3 later
   commits). With the credential now rotated dead, accept-with-rotation is the
   defensible default; rewrite is optional hygiene. Same decision shape as the
   2026-07-03 fleet-evals FinProxy incident.

Also landed 2026-07-05 (another session): **TASK-AB-SECRETSCRUB01 implemented**
(`guardkit/lib/secret_scrub.py`, wired at `_serialize_turn_history`
scrub-before-truncate + `ReviewSummaryGenerator.generate`, lint
`tests/rules/test_no_secrets_in_tracked_artifacts.py`, 33 tests) — the
prevention half of this incident is closed; its task file is the record.

**Tasks filed from it:**
- **TASK-AB-SECRETSCRUB01** (high, ready-to-implement) — scrub secret-shaped
  strings at the evidence→publication boundary (task-md turn-history writer,
  review summaries; ABL-005's `scrub_secrets` is the prior art) + a
  `tests/rules/`-style lint scanning tracked `tasks/`+`docs/` for
  non-localhost credentials. Key boundary decision already made: scrub at
  PUBLICATION, never at the oracle (the Coach must see real output).
- **TASK-AB-HERMETICTEST01** (low) — env-reading config tests must pin the
  full env surface (three-location prompt pattern + planner note + the ops
  rule: never run agent loops with live creds in ambient env).
- Note for fleet-evals (not a guardkit task): the run-3 trace (honest-fail +
  caught narration) is a §6c corpus candidate alongside the run-2 stub.

### (b) QA-Verifier state consolidation
([`qa-verifier-state-consolidation-2026-07-04.md`](qa-verifier-state-consolidation-2026-07-04.md))

The QA-Verifier thread is reconciled and **Phase 0 is code-complete**: L1
wiring probes (FEAT-C332), L2 anti-stub body scan + L3 runtime coverage gate
(FEAT-10AC, merged `888906f2`), and the L4 behavioural-oracle guard + producer
(TASK-QAV-006 / FEAT-0E6D, merged `fe949bb0`). Two build-time catches worth
knowing: the L4 guard initially shipped WITHOUT its producer wired
(runner-without-producer, caught at merge review by the feature's own ethos),
and a Player committed an intentionally-failing oracle into the tree (caught,
excluded — a live proof of the oracle-independence check).

**Consequences for the design-first tasks below:**
- **ENVTAMPER01**: its half-(b) (`sys.modules` probe) must EXTEND the now
  even-richer `guardkitfactory.wiring` dialect data — the consolidation doc
  makes this binding ("extend the existing WiringAnalyzer dialect descriptors;
  do not build a parallel analyzer"). The merged L2 anti-stub scan is the
  nearest sibling to copy.
- **New overnight commits in the venv-resolution territory** (do not collide;
  read before any venv work): `aa4ecc81` TASK-FIX-SIBTESTENV01 (sibling
  evidence-repo tests resolve interpreter PER REPO, never the worktree venv —
  in_review), `fc33a23e` (bootstrap the environment when resuming onto an
  existing worktree — goes further than RESUMEVENV01's skip-path re-probe),
  `01820fbb` (per-turn venv refresh scoped to touched stacks), and
  TASK-FIX-XREPOPROM01 (sibling-relative Player claims false-red). Any
  RESUMEVENV follow-up must rebase its mental model on these.
- TASK-QAV-008 was filed (`4aaa7de1`) — check it before scheduling QAV work.

**Updated suggested ordering:** SECRETSCRUB01 first (leak class is live and
it's fully specified) → VERIFYCLI01 → BDDAUTHOR01 → ENVTAMPER01 →
HERMETICTEST01/REVIEWCLEAN01 (fillers) → WTISO01 (still gated on §2.3-1).

---

## 2. The five design-first tasks — what they are and what input is needed

All five live in `tasks/backlog/autobuild-reliability/` with full task files.
They were deliberately NOT implemented in the batch because each has a real design
decision (or cross-repo surface) that shouldn't be rushed. Ranked by value.

---

### 2.1 TASK-AB-ENVTAMPER01 — environment-integrity contract (high, complexity 8, cross-repo)

**The problem it closes:** the R1 headline failure — a Player facing un-runnable
tests (missing `memory` extra) planted a 56-line `sys.modules` stub for
`nats_core` in PRODUCT code (`guardkit/__init__.py` + 4 more files), defeating the
suite's `skipif(find_spec("nats_core"))` guard so tests-that-should-skip ran
against fakes. Verified: **no detection surface exists** — the wiring/mocked-seam
probe scans only acceptance-tier files for mock-primitive *calls*; honesty checks
never look at the environment; the Coach was blind to skip counts (now fixed —
SKIPVIS01 landed the advisory visibility half).

**The design (two halves, from xref §5 item 11):**
- **(a) Upstream prevention** — post-bootstrap *skip-guard dependency parity
  probe*: scan the test tree for `skipif(find_spec("X"))` / `importorskip`
  markers; verify each probed module imports standalone from the worktree-venv
  interpreter; map missing modules to pyproject optional-dependency groups;
  surface "extra `<name>` missing → N tests will skip" by name. Extends the OPEN
  backlog task `TASK-FIX-A7B6` (bootstrap-install-optional-extras) rather than
  duplicating it.
- **(b) Gate-side detection** — a narrow product-file `sys.modules` probe as
  **tree-sitter dialect DATA in `guardkitfactory.wiring`** (authored-this-turn,
  non-test files, direct subscript assignment), advisory-first with bounded
  feedback (the UNWIRED disposition), never turn-rejecting at first.

**Operator input needed:**
1. **Auto-install or advise-only?** Should half (a) *auto-add* a missing extra to
   the bootstrap (convenient, but an install path — must honour
   `uv-sources-must-survive-every-install-path` + namespace-hygiene), or only
   surface it loudly and fail the turn into feedback? Recommendation: advise-only
   first release; auto-install behind a config key later.
2. **guardkitfactory availability/lockstep.** Half (b) is a cross-repo change
   (new dialect query data + a seam test in guardkit, per the
   `test_xrepo_contract_seam.py` precedent). Confirm the sibling checkout is
   current on the dev box and you're happy to version the two changes together.
3. **Escalation policy.** Does the `sys.modules`-in-product-code finding ever
   become turn-rejecting, or stay advisory forever? (Rules bias: advisory-first,
   promote only with false-positive evidence. Your call on the promotion bar.)
4. **Scope of "tamper".** Only `sys.modules` subscript assignment, or also
   `find_spec` monkeypatching / conftest edits in product dirs? (Each widening
   raises false-positive surface; recommend shipping the narrow probe first.)
5. **Relationship to fleet-evals §6c.** The retro proposed a standing
   "tests-that-should-skip must not run against fakes" regression corpus entry
   (phase-ablation §6c). That's a fleet-evals deliverable, not guardkit — do you
   want it tracked there, and by whom?

---

### 2.2 TASK-AB-BDDAUTHOR01 — BDD authoring sweep (high, complexity 7)

**The problem it closes:** R4 — the step-def-AUTHORING task (TASK-SMP2-07) owned
**zero** `@task:` tags by its own design, so its per-task BDD oracle legitimately
returned `None` (activation-by-artefact), no junit was emitted, and pytest-bdd
glue is ALSO excluded from the Coach's independent test command (TASK-FIX-CC-BDD,
a deliberate FEAT-39E1 false-red fix) — so the authoring task's glue was exercised
by **neither** verification leg. An undefined step (`StepDefinitionNotFoundError`)
sailed through to the operator's pre-merge run.

**The design (verified non-regressing scoping, from the R4 verification):**
- Artefact-activated **authoring sweep**: when a turn's `files_authored` include
  pytest-bdd glue (`is_bdd_glue_file` already exists), additionally run pytest
  over the feature files that glue binds **without** the `-m task` tag filter,
  emitting junit (delivers the retro's missing-junit ask for free).
- **Within the sweep only**, count `StepDefinitionNotFoundError` as a distinct
  blocking `scenarios_undefined` counter — leaving `_PENDING_MARKERS` and the
  tag-scoped pending semantics untouched. Scaffolding tasks author `.feature`
  files, not glue, so they never enter the sweep — `bdd-pending-is-not-failed`
  (TASK-BDD-E8954) is preserved **by construction**, not by exception.

**Operator input needed:**
1. **Blocking from day one, or advisory-first?** Inside the sweep, is
   `scenarios_undefined > 0` immediately turn-rejecting (the retro's ask), or
   advisory for a release to measure false positives? (The scoping argument says
   blocking is safe — the authoring task's entire job is making scenarios
   executable — but it's your risk call.)
2. **Parallel-wave guard.** The sweep runs unfiltered over feature files that may
   bind *other* tasks' scenarios; in a parallel wave that re-opens the
   cross-task race `bdd-per-task-glue` was built to prevent. Recommend gating the
   sweep to `wave_size == 1` (the runtime-parity precedent). Confirm.
3. **Tagging convention alternative.** FEAT-SMP-002's plan deliberately routed all
   tags to earlier tasks. An alternative/complementary fix is planner-side: have
   `/feature-plan` require the authoring task to own at least the scenarios it
   makes executable. Do you want the sweep, the planner rule, or both?
   (Recommendation: both — the sweep is the structural defence, the planner rule
   is the ergonomic one.)
4. **Where junit lands** for the sweep (`.guardkit/bdd/<task>_authoring_junit.xml`
   vs the standard name) — trivial, but affects any tooling you have reading that
   directory.

**Regression tripwires (already pinned by tests — do not regress):**
`test_pending_step_recorded_distinctly`, `test_bdd_pending_approves_with_feedback`,
the vacuous-true guard tests, BDDNEUTRAL01 exit-4 neutrality, ABFIX-010
timeout-absent, and the TASK-FIX-CC-BDD glue exclusion from independent tests.

---

### 2.3 TASK-AB-WTISO01 — per-task worktree isolation for parallel waves (medium, complexity 9, DESIGN DOC FIRST)

**The problem it closes:** R2's structural root — all tasks in a wave share ONE
git worktree; parallel Players overwrite each other; checkpoints `git add -A` the
whole tree so task A's checkpoint embeds task B's half-written files; rollback is
a shared `git reset --hard`. Everything landed this session (overlap
auto-serialise default-on, lowering-only YAML tier, interference stall subtype,
A7B2/ABFIX-005 runtime mitigations) **mitigates** the class; WTISO01 is the only
fix that would make same-file parallelism actually safe.

**Why design-first:** it touches nearly every load-bearing invariant at once —
the evidence boundary (post-turn `git diff` cwd), checkpoint semantics, rollback,
the two-level fcntl/threading lock, wave merge semantics, per-worktree venv
bootstrap cost, and the wiring gate's *wave-aggregate* aperture
(`per-task-green-is-not-feature-green` assumes an assembled tree to analyse).
Precedent: TASK-ABSR-WTKS filed this exact class 2026-04-28 and deferred it.

**Operator input needed (these genuinely gate the design):**
1. **Is parallel throughput worth it at all?** Local backends are capped at 1 by
   design (KV-cache). Parallelism only pays on cloud runs. Given serialization
   made FEAT-SMP-001 pass first-turn, quantify: how often do you actually want
   overlapping-file tasks running concurrently? If the honest answer is
   "rarely", consider closing WTISO01 as *wontfix — serialize instead* and keep
   the mitigations. This is the biggest fork in the road.
2. **Merge policy.** If per-task worktrees proceed: when two parallel tasks'
   branches conflict at wave-merge time, who resolves — the orchestrator
   (auto-abort → serialize retry), a dedicated Player merge-turn, or fail the
   wave to the operator? (Recommendation: auto-detect conflict → fall back to
   sequential re-run of the second task on the merged base; never an LLM merge.)
3. **Cost budget.** Per-task worktree = per-task venv (or a shared-venv symlink
   scheme with its own hazards — see the ABL-005 symlink workaround). Acceptable
   disk/bootstrap seconds per task?
4. **Scope.** Full per-task isolation always, or hybrid (per-task worktrees only
   for waves the overlap detector flags — now that it runs default-on)?
   Recommendation: hybrid, if at all.

---

### 2.4 TASK-AB-VERIFYCLI01 — implement `--verify` on `guardkit autobuild complete` (low, complexity 3)

**The problem:** `installer/core/commands/feature-complete.md` advertised a
`--verify` (re-run tests after merge) that the Python CLI never implemented; the
docs were corrected this session to mark it slash-command-only and point here.
R3's "always run an independent full-suite verification before merging" currently
has no CLI hook.

**Operator input needed:**
1. **What command does `--verify` run?** Options: the feature YAML's
   `smoke_gates.command`; a stack-aware default (pytest `tests/` for Python via
   the existing stack_test_execution registry); or an explicit `--verify-cmd`.
   Recommendation: feature smoke command when present, stack default otherwise,
   `--verify-cmd` override.
2. **Failure disposition.** After a merge whose verify run fails: report + exit
   non-zero (leave the merge in place), or auto-revert the merge commit?
   Recommendation: report-only + non-zero exit; auto-revert is scary and the
   merge is already human-triggered.
3. Where it runs (merged main repo root) and timeout policy (reuse smoke-gate
   timeout default?).

This is a well-shaped small task once those three answers exist — a good
candidate for `/task-work` or even an autobuild dogfood run.

---

### 2.5 TASK-AB-REVIEWCLEAN01 — post-review consolidations (low, complexity 4)

**What it is:** the six consolidations the 8-angle review surfaced and we
deliberately deferred to avoid churn in a correctness batch:
1. Unify the **three pytest-summary parsers** (specialist_invocations
   `_parse_pytest_counts`, coach_validator `_parse_tests_skipped`, agent_invoker
   `PYTEST_SUMMARY_PATTERN` handling) into one `guardkit/lib` helper.
2. A shared **`_override_and_persist`** helper (or ordered guard registry) for the
   ~7 hand-rolled flip/annotate+persist blocks at the agent_invoker Coach-guard
   seam — duplication drift here re-opens the COACHFG01 defect class.
3. An **IndependentTestResult factory** owning `tests_skipped` /
   `resolved_interpreter` population across ~10 construction sites.
4. Rewrite the two pre-existing coach-turn walkers over `_coach_report_issues`.
5. **Single-persist-per-turn** for `coach_turn_N.json` (guards mutate in memory,
   persist once at chain end — keep the fail-open posture).
6. A shared parity/smoke **framing composer** in `stale_test_attribution.py` so
   the per-task and post-wave wording can't drift.

**Operator input needed:** minimal — scheduling appetite, plus ONE real decision:
item 5 changes the "every guard re-persists" convention that
`deterministic-verdict-override-must-persist-to-disk` pins with grep
fingerprints. The safe shape is a dirty-flag with a guaranteed persist at chain
end + the same per-guard fingerprints preserved (the rule cares that the disk
matches memory before Layer-4 reads it, not how many writes happen). If you'd
rather not touch that invariant at all, drop item 5 and do 1-4+6.

---

## 3. Suggested opening prompt for the next session

> Read `docs/retro/session-handoff-2026-07-04-reliability-batch-landed-design-first-next.md`,
> then `docs/retro/autobuild-retro-xref-2026-07-04.md` §4-§6, and the five task
> files in `tasks/backlog/autobuild-reliability/` marked design-first. Here are my
> answers to the operator-input questions in the handoff §2: [...]. Start with
> [TASK-AB-XXX]: produce the design (Phase 2-style: plan → architectural review
> against the Regression-constraints section) before writing code.

Sensible ordering if you want a default: **VERIFYCLI01** (small, unblocks the
merge-verification practice) → **BDDAUTHOR01** (highest defect-recurrence risk;
the FEAT-SMP-002 class will recur on the next BDD feature) → **ENVTAMPER01**
(needs the guardkitfactory checkout) → **REVIEWCLEAN01** (any time, low risk) →
**WTISO01** (only after question 2.3-1 is answered honestly — it may be a
wontfix).

## 4. Do-not-regress quick card (for whoever implements)

- Absent stays `None` at every layer; `cp.tests_passed is False` is the only
  failure that counts; guard #6 + `reconciled_absent` fingerprints must match.
- Deterministic verdict overrides re-persist `coach_turn_N.json` (fail-open on
  write, fail-closed on verdict).
- Pending BDD scenarios stay non-blocking outside the authoring sweep.
- New gates: activate by artefact, feed back bounded, never bare-terminate, run
  in BOTH Coach paths, advisory-first for syntactic heuristics.
- Any bootstrap/install change honours `[tool.uv.sources]` on every path and
  audits names against PyPI.
- One resolution point for concurrency (`resolve_max_parallel`); display and
  executor consume the identical decision; the YAML tier is lowering-only.
- The 101-test failure baseline is environmental (py3.10) — do not "fix" SDK
  tests by weakening them; rebuild the venv on 3.12 instead.
