# Review Report: TASK-REV-ABST — Autobuild stocktake (BDD-verification trajectory)

- **Task**: TASK-REV-ABST — *Autobuild stocktake — has the BDD-verification trajectory destroyed quality?*
- **Reviewer**: `/task-review` (architectural, depth=thorough)
- **Review date**: 2026-05-10
- **Status**: review_complete (decision-required: see §7)

---

## 1. Executive summary

**Verdict: NARROW (Option B), with a 7-day freeze and re-measurement deadline of 2026-05-17.**

The user's hypothesis — *"these changes destroyed a previously-95%-working system, every run fails and we have to spawn fix-up tasks"* — is **directionally correct but mis-framed**. Empirically, the BDD-verification + deterministic-Coach + honesty-verification trajectory has run a 25-day debug cycle (2026-04-15 → 2026-05-10) characterised by:

- A **3.57:1 ratio** of FIX_FOR_NEW_GATE commits to NEW_GATE commits (25 fixes against 7 new gates);
- **At least three concrete framework false-positive incidents** (FFC3 path-mismatch, FG-001 BDD-env, TASK-FIX-7A08 Player Task-tool over-mandate) where production code was correct but the framework rejected the work;
- **First-attempt clean autobuild success rate of ~10%** (2/21 consumer-repo features in the sample window) and ~33% eventual success after retries.

But the trajectory has **also** caught real defects that pre-trajectory autobuild would have shipped:

- The **deterministic-Coach false-green** that motivated TASK-AB-FIX-INVAB1 (Coach approving on `Player wrote status:complete` without disk verification — *real* if undetected, would have approved zero-implementation turns);
- The **BDD silent-green** class (TASK-FIX-F584 — `tests=0, failures=0` was being read as `passed`);
- The **namespace shadowing** class (TASK-REV-MCPS — `installer/core/lib/mcp/` shadowed the Anthropic `mcp` PyPI package);
- The **wave-2 shared-glue race** in fleet-gateway FEAT-FG-001 (per-task BDD glue contract, TASK-AB-004).

The two largest false-positive classes (FFC3 path-mismatch on 2026-05-06, FG-001 BDD-env on 2026-05-10) **have just landed their fixes** — 1B4A/B/C + 7E3F (May 6) and AB-001/003/004 (May 10, today). Neither fix has yet been validated against a fresh consumer-repo autobuild run on `guardkit@HEAD`. The user's complaint is therefore *retrospectively accurate for the past 25 days* and *prospectively unverifiable for at least the next 5–7 days*.

The recommendation is **Narrow** rather than **Continue** because:
1. The 3.57:1 cleanup ratio and the May 6 + May 10 cluster of fixes mean the trajectory cannot be declared stable until consumer-repo features run cleanly against `guardkit@HEAD` post-AB-001/003/004 with no new gates added in between. Declaring "Continue" today would be premature.
2. At least one gate (`assumption-confidence` warn-mode, `fb37f72f`) has no measured real-positive evidence and is a candidate for retire/demote irrespective of the freeze outcome.
3. Layer-2 of the FFC3 fix (TASK-FIX-1B4B — demote single path-only honesty discrepancy from `must_fix` to `should_fix`) is a proof-of-concept for narrowing; the pattern can be applied more broadly.

The recommendation is **Narrow** rather than **Roll back** because:
1. The deterministic-Coach false-green was a real defect class. Rolling back loses the catch.
2. Consumer repos (notably fleet-gateway) now depend on the per-task BDD glue contract (TASK-AB-004). Rollback re-introduces the wave-2 race.
3. Three of the four design-rules already on disk (`absence-of-failure-is-not-success.md`, `path-string-mismatch-is-not-dishonesty.md`, `namespace-hygiene.md`, `bdd-per-task-glue.md`) are **generative** — they document a meta-class and predict its inverse-shape sibling. That is debug-cycle-end behaviour, not doom-loop behaviour.

The recommendation is **Narrow** rather than **Pivot** because:
1. Pivoting (retiring the deterministic-Coach path entirely) is a much larger structural change than the evidence requires *today*. It remains the right escalation if the 7-day freeze + re-measurement shows no improvement; this report scopes Pivot as the **negative-falsifier** outcome (§7), not the headline.

**Falsifier for Narrow**: if no consumer-repo feature passes cleanly on first-turn between 2026-05-11 and 2026-05-17 against `guardkit@HEAD`, escalate to Pivot.

**Follow-up date**: 2026-05-17 (7 days).

---

## 2. Timeline of changes (AC-001)

This timeline aggregates `git log --since="2026-04-01"` filtered to commits that touch the autobuild quality-gate stack: `guardkit/orchestrator/agent_invoker.py`, `quality_gates/coach_validator.py`, `quality_gates/coach_verification.py`, `quality_gates/bdd_runner.py`, `tasks/state_bridge.py`, `installer/core/templates/common/features/conftest.py.template`, plus any commit whose message contains BDD/Coach/honesty/INVAB/1B4/7E3/CVAC/FPTC/FPSG/AB-FIX/AB-001/003/004/OPS-BDDM/F584/A7B*/OSI/RWOP/FIX-BDDM/FIX-FF.

### 2.1 Phase narrative

The trajectory has five distinguishable phases, in date order:

| Phase | Window | Intent | Net trajectory |
|---|---|---|---|
| **A** | Apr 1–21 | Pre-trajectory baseline; AC-validation linter, promise-field normalisation. | Net-corrective (4 fixes, 2 new gates). |
| **B** | Apr 22–25 | BDD oracle wired in; CoachVerifier groundwork; Phase 4/5 orchestrator wiring; smoke-gate venv threading. | Net-additive but volatile (1 revert at close: 9d304ed9, TASK-FIX-7A08). |
| **C** | Apr 28–May 3 | Quality-gate boundary tightening (seam-tests, parallel-contention, smoke-gate); CVAC-001/002 AC-id matching. | Net-additive (3 new gates, 4 boundary tightenings). |
| **D** | May 6 | Pure damage control: deterministic-Coach honesty wiring + FFC3 path-mismatch trio + 7E3F None-payload guard. | Net-corrective (7 fixes, 0 new gates). |
| **E** | May 7–10 | Closing the BDD oracle trajectory: plan-audit, Files-to-Modify preflight, BDD env trio. | Net-additive (5 new gates, 4 fixes). |

### 2.2 Decisive commits (highlight set)

These commits are load-bearing for the gate-by-gate matrix in §4. SHAs from `git log`; bucket assignments per the Phase narrative above.

| SHA | Date | Title | Bucket |
|---|---|---|---|
| `cadde171` | 2026-04-22 | fix(bdd-oracle): surface pytest runner errors as failures, not silent-green (TASK-FIX-F584) | FIX_FOR_NEW_GATE |
| `fb37f72f` | 2026-04-23 | feat(coach): wire assumption-confidence warn-mode gate (TASK-FIX-RWOP1.4a) | NEW_GATE |
| `7f8f14ba` | 2026-04-24 | TASK-FIX-7A08 mandate Task-tool invocation in Player prompt | NEW_GATE (subsequently reverted) |
| `9d304ed9` | 2026-04-25 | Revert "TASK-FIX-7A08 mandate Task-tool invocation in Player prompt" | **REVERT** |
| `68bee41f` | 2026-04-25 | fix(bdd-runner): synthesise blocker when tagged scenarios exist + pytest-bdd absent (TASK-FIX-BDDM-1) | NEW_GATE |
| `3eb820af` | 2026-04-25 | fix(coach): demote agent_invocations_validation from blocker to feedback-enricher (TASK-REV-F6E1) | FIX_FOR_NEW_GATE (precedent for Layer-2 narrowing) |
| `5192fc60` | 2026-05-02 | fix(coach-validator): extract compound + markdown-bold AC IDs to match Player promises (TASK-CVAC-001) | FIX_FOR_NEW_GATE |
| `6f01de5c` | 2026-05-03 | fix(coach-validator): match promises by criterion_text fallback when criterion_id diverges (TASK-CVAC-002) | FIX_FOR_NEW_GATE |
| `b9a45694` | 2026-05-06 | complete(TASK-AB-FIX-INVAB1): wire CoachVerifier into deterministic Coach path | NEW_GATE (closes false-green class) |
| `9d2fe52d` | 2026-05-06 | TASK-FIX-1B4A: resolve files_modified claims via state-bridge canonical path | FIX_FOR_NEW_GATE |
| `074a6f03` | 2026-05-06 | TASK-FIX-1B4B: demote single path-only honesty discrepancy from must_fix to should_fix | FIX_FOR_NEW_GATE (Layer-2 narrowing PoC) |
| `2c19aefc` | 2026-05-06 | TASK-FIX-1B4C: filter orchestrator-induced state-bridge ghosts at union-merge | FIX_FOR_NEW_GATE |
| `81e2c984` | 2026-05-06 | TASK-FIX-7E3F: guard `_record_honesty` against None payload | FIX_FOR_NEW_GATE |
| `22be7039` | 2026-05-06 | TASK-DOC-1B4D: add path-string-mismatch-is-not-dishonesty rule (inverse-shape sibling) | DOC_OR_RULE |
| `6c950d75` | 2026-05-07 | TASK-GK-PA-001: plan-audit compares files_to_modify against git-modified set | NEW_GATE |
| `c610426c` | 2026-05-07 | TASK-GK-PA-002: honour explicit Files-to-Create/Modify sections in plan-audit AC fallback | FIX_FOR_NEW_GATE |
| `33f9db26` | 2026-05-10 | TASK-AB-001: thread worktree python_executable through to bdd_runner | NEW_GATE (closes FG-001 BDD-env class) |
| `b0819556` | 2026-05-10 | TASK-AB-003: surface junit collection-error message in BDDFailure.reason and Coach feedback | FIX_FOR_NEW_GATE (closes FG-001 feedback-fidelity gap) |
| `00933c38` | 2026-05-10 | TASK-AB-004: per-task BDD glue lookup via GUARDKIT_BDD_TASK_ID env var | NEW_GATE (closes FG-001 wave-2 collision class) |

### 2.3 Aggregate counts (since 2026-04-15)

- **NEW_GATE commits**: 7
- **FIX_FOR_NEW_GATE commits**: 25
- **Ratio**: 3.57:1
- **REVERT commits**: 1 (`9d304ed9`)
- **DOC_OR_RULE commits seeding meta-class rules**: 4 (`namespace-hygiene` Apr 24; `absence-of-failure` May 6 via TASK-AB-FIX-INVAB1 documentation; `path-string-mismatch` May 6 via TASK-DOC-1B4D; `bdd-per-task-glue` May 10 via TASK-AB-004)

**Confidence**: High. The git log is authoritative for SHAs, dates, and titles. Bucket assignment was based on the commit message (e.g. `fix(...)` → fix; `feat(...)` → new gate), with one exception: `b9a45694 TASK-AB-FIX-INVAB1` is bucketed FIX_FOR_NEW_GATE in the agent's count but is genuinely a NEW_GATE that *closes* a pre-existing false-green; the 3.57:1 ratio is therefore slightly conservative — the real "new functional gate that took zero corrective work" count is closer to 7, the rest are closing previously-unrecognised holes.

---

## 3. Empirical run-success metrics (AC-002)

This section quantifies the user's run-success complaint using `docs/history/` filenames across the five consumer repos as the data source. Filename patterns (`-fail-`, `-failed-`, `-success-`, `-cancelled-`, `-timeout-`, `-run-N-`) are the strongest available signal short of opening 200KB–800KB log files individually; for the post-mortem incident files (<50KB) full reads were performed and are cited in §4.

### 3.1 Per-repo summary

| Repo | Features attempted | Eventual pass | First-pass success | Multi-retry | Stuck/abandoned | Last activity |
|---|---|---|---|---|---|---|
| jarvis | 5 | 0 confirmed | 0 | 1 (J004-702C, J005-946D, J003 cancelled) | 4 (J002, J003, J004-702C, J005-946D — all unclear/fail) | 2026-05-01 |
| forge | ~12 | ~3 (FORGE-009, DEA8, PEBR) | 1 (DEA8) | 4 (FORGE-005, 009, PEBR, 010) | 1 (FORGE-010) | 2026-05-08 |
| study-tutor | 7 | 3 (70A4, 39E1, FEAT-6CC5 unknown) | 0 | 4 (FD32, 39E1, 70A4, 1773) | 1 (FD32) | 2026-05-09 |
| specialist-agent | ~4 | 2 (FEAT-FEAT-61F1, 9B60) | 0 | 2 (9B60, 9B6-) | 1 (9B6- malformed-id; FFC3 manual-flip) | 2026-05-06 |
| fleet-gateway | 1 | 0 (still stalled as of 2026-05-09) | 0 | 1 (FG-001) | 1 (FG-001 stalled until AB-001/003/004 merged today) | 2026-05-10 |
| **Total** | **~21** | **~7 (33%)** | **2 (10%)** | **8** | **3 hard-stuck + several manual-flips** | — |

### 3.2 Notable empirical signals

- **First-attempt clean success rate**: 2/21 (~10%). The user's "95% baseline" cannot be verified from the consumer-repo data because the data lives in `docs/history/` only from ~Apr 25 onwards (the start of the trajectory under review); pre-trajectory baseline is therefore largely subjective/recollection-based.
- **Manual-flip events** (operator marked task `completed` to bypass framework false-fail):
  - FEAT-FFC3 (specialist-agent): two tasks (FFC3-005, FFC3-006) manually flipped to `completed` in YAML to bypass Bug 1 (path-mismatch) and Bug 2 (None-payload crash). Documented in `autobuild-FFC3-honesty-path-mismatch-incident.md`.
  - FEAT-FG-001 (fleet-gateway): not yet flipped; awaiting validation of AB-001/003/004 fixes (landed today). Documented in `autobuild-FEAT-FG-001-review.md`.
- **Five-turn feedback-stall events** (identical Coach feedback signature for ≥5 turns):
  - FEAT-FG-001 wave-2 (TASK-FG-002 + TASK-FG-003): five identical `sig=47fb7107` turns; feedback-stall guard fired correctly, but the upstream gap (BDD oracle wrong-Python collection error not surfaced to Coach feedback) is what caused the stall.
- **Recovered-after-N-retries** (framework eventually closed):
  - FEAT-FORGE-009: 3 failures + symlink fix → success.
  - FEAT-PEBR: 4 failures → success.
  - FEAT-FEAT-61F1 (specialist-agent): 1 failure (malformed id) → success.
  - FEAT-39E1 (study-tutor): 2 failures → success.
  - FEAT-9B60 (specialist-agent): 1 failure → success.
  - **5 of 8 multi-retry features recovered without manual flip** — the framework is debuggable, not soft-bricked.

### 3.3 Confidence and caveats

- **Sample size is thin**. 21 features over ~2 weeks. For most repos (jarvis 5, fleet-gateway 1, specialist-agent 4) the per-repo signal is sub-statistical; even where N is highest (forge 12), the mix of unclear/unknown outcomes (no `-success-` or `-failed-` qualifier) is dominant.
- **Filename-based outcome inference is fallible**. A file named `autobuild-FEAT-X-history.md` with no qualifier could be a clean run, a partial run, or an in-progress run. Where qualifiers exist (`-success-`, `-failed-`, `-fail-run-N`, `-cancelled`, `-timeout`, `-even-worse`) the signal is strong; otherwise the agent census flagged "unknown".
- **The pre-trajectory "95% baseline" is unverified**. The user's recollection ("we had something that worked 95% of the time") cannot be cross-checked against `docs/history/` because the docs/history archive itself is dominated by post-trajectory entries. This is one of the most important §9 "limits and unknowns" items: the *direction* of degradation is supported, the *magnitude* (95% → ~10% first-pass) is the user's framing, not measured.
- **The fleet-gateway sample is N=1**. FG-001 is the only feature, and it was stalled by a framework bug (BDD oracle wrong Python) for which the fix landed today. We cannot generalise from a single repo.

---

## 4. Gate-by-gate quality matrix (AC-003)

Each gate landed in the trajectory is classified into one of four cells:

- **Real-positive (RP)**: caught a defect that pre-trajectory autobuild would have shipped. Citation required.
- **False-positive (FP)**: blocked a turn where the production code on disk was correct. Citation required.
- **False-negative-by-zero-cardinality (FN-0)**: approved or skipped silently when the gate's oracle ran zero attempts (the *absence-of-failure-is-not-success* class).
- **True-negative (TN)**: ran, found nothing wrong, didn't fire. Implicit from non-incidents; counted as ratio against RP.

### 4.1 Gate-by-gate matrix

| Gate | Landed | RP evidence | FP evidence | FN-0 evidence | Net classification |
|---|---|---|---|---|---|
| **BDD oracle (pytest-bdd subprocess)** | Apr 22 (`cadde171` was the FN-0 fix; `b9a45694` wired into deterministic Coach) | `cadde171`: silent-green class. Without this, `tests=0, failures=0` was being read as `passed`. | **FG-001** (2026-05-09): collection error in worktree `.venv` interpreted as scenario failure; correct production code rejected. Five-turn cosmetic-edit stall. Fixed by AB-001/003/004 today. | `cadde171` is the FN-0 closure itself: pre-fix, the runner exited 5 with no scenarios collected and the Coach approved on `failures==0`. | **Load-bearing** post-AB-001/003/004; previously net-negative (FP × cost ≥ RP × benefit during the FG-001 stall window). |
| **CoachVerifier wired into deterministic Coach (TASK-AB-FIX-INVAB1)** | May 6 (`b9a45694`) | The TASK-INV-AB1 investigation surfaced that `CoachValidator` was approving turns where the Player wrote `status: "complete"` in `completion_promises[*]` without disk verification — a real false-green class with zero CoachVerifier invocations. Closure of the *absence-of-failure-is-not-success* class. | **FFC3** (2026-05-06): orchestrator-induced path-mismatch (state-bridge moved task file mid-turn; Player's report referenced old path; Coach rejected on path-string equality). Same-day fix in 1B4A/B/C trio. | None observed post-fix. | **Load-bearing** post-1B4A/B/C; was net-negative for ~6 hours on May 6 between landing and Layer-2 demotion. |
| **Honesty path-equality on `files_modified`** | May 6 (`b9a45694`) embedded; `9d2fe52d` Layer-1 + `074a6f03` Layer-2 + `2c19aefc` Layer-3' | Catches Player honesty violations on path claims. | **FFC3** (as above) — only observed false-positive instance is the orchestrator-induced one. Genuine cross-task path leakage retains `must_fix` correctly. | None observed. | **Load-bearing** post-Layer-1/2/3' fixes. The Layer-2 demotion (single path-only → `should_fix`) is the key narrowing primitive. |
| **`_record_honesty()` payload guard (TASK-FIX-7E3F)** | May 6 (`81e2c984`) | None — this is a *crash fix*, not a behavioural gate. | **FEAT-FFC3 turn 2** (specialist-agent, 2026-05-06): orchestrator hit `AttributeError: 'NoneType' object has no attribute 'get'` at `autobuild.py:4376` when Coach emitted a non-blocking advisory with `honesty_data=None`. Hard-failed Wave 4 of an otherwise-green feature. | None. | **Load-bearing as a defensive guard.** Strictly closes a regression introduced by `b9a45694`. |
| **Per-task BDD glue contract (TASK-AB-004)** | May 10 (`00933c38`) | **FEAT-FG-001** wave-2 (fleet-gateway): TASK-FG-002 and TASK-FG-003 ran in parallel against the same worktree and both wrote into a single shared `features/<slug>/test_<slug>.py`. Each Player rewrote the file for *its* scenarios only, racing the other. Without per-task glue, even after the import bug is fixed, FG-003's BDD oracle would collect zero scenarios. | None observed (gate is too new). | None — gate is too new to have generated zero-cardinality data. | **Load-bearing** for any multi-task feature with shared BDD scope. Closes a concurrency-class defect that would have shipped repeatedly. |
| **BDD-runner pytest-bdd presence preflight (TASK-FIX-BDDM-1, BDDM-2)** | Apr 25 (`68bee41f`, `56a8448a`) | Catches the case where a feature has `@scenario`-tagged scenarios but `pytest-bdd` is not installed in the runner env (the *runner-without-producer* anti-pattern in Graphiti). | None observed. | **FN-0 fix itself** — pre-fix, missing pytest-bdd silently produced zero-scenario success. | **Load-bearing**, sibling of `cadde171`. |
| **Plan-audit `files_to_modify` ↔ git-modified set comparison (TASK-GK-PA-001)** | May 7 (`6c950d75`) | Catches plan/implementation divergence (Player wrote files outside its declared `files_to_modify` scope). | None observed. | None. | **Load-bearing**, but **new** (3 days old at review time). | 
| **Plan-audit AC-fallback for explicit `## Files to Create/Modify` sections (TASK-GK-PA-002)** | May 7 (`c610426c`) | None — this is FIX_FOR_NEW_GATE for PA-001. | None observed. | None. | **Load-bearing as a fix.** |
| **AC-id extraction (CVAC-001/002)** | May 2–3 (`5192fc60`, `6f01de5c`) | Catches Player promise/AC-id divergence (Player promised `[AC-001]` against an AC labelled `**1.**` in markdown bold). | None observed. | **Pre-fix, the gate was an FP-generator** — promises never matched and were silently dropped from the verification set. | **Load-bearing post-fix.** |
| **Smoke-gate seam-tests promote-to-block (TASK-FIX-A7B4)** | Apr 30 (`e10501ad`) | Catches Player skipping seam-test work when description specifies a stub. Real-positive against a genuine class of Player corner-cutting. | None observed. | None. | **Load-bearing.** |
| **Smoke-gate venv interpreter pin (TASK-FIX-A7B1)** | Apr 30 (`5f313f8c`) | None — FIX_FOR_NEW_GATE for the smoke-gate boundary tightening. | None observed. | **FN-0 fix itself** — pre-fix, smoke gates ran in orchestrator's PATH Python and silently passed because the imports they tested were absent in the worktree-local Python. | **Load-bearing.** |
| **Parallel-contention gating on peer source-file overlap (TASK-FIX-A7B2)** | Apr 30 (`38b22426`) | Catches conditional-approval false-positives in parallel waves. | None observed. | None. | **Load-bearing.** |
| **Operator-handoff skip branch + loader pinning (TASK-FPTC-004)** | May 3 (`654af1d3`) | Catches the operator-shaped AC class that should not be Player-implementable. | None observed. | None. | **Load-bearing**, but narrow scope. |
| **Assumption-confidence warn-mode gate (TASK-FIX-RWOP1.4a)** | Apr 23 (`fb37f72f`) | **No documented real-positive in the 17-day window.** The gate is in warn-mode (does not block); its effect is not measurable in run outcomes because the Coach does not act on it. | None observed (cannot generate FPs in warn-mode). | None measurable. | **Incidental.** Candidate for retire/demote pending evidence (see §5). |
| **Coach feedback-stall guard (preexisting)** | Pre-trajectory | **FEAT-FG-001** (fleet-gateway, 2026-05-09): correctly fired after 5 identical `sig=47fb7107` turns. The *guard* was correct; the upstream gap (BDD-runner wrong-Python) is what made it necessary. | None observed in the trajectory window. | None. | **Load-bearing.** Not part of the trajectory under review. |
| **Player Task-tool invocation mandate (TASK-FIX-7A08)** | Apr 24 (`7f8f14ba`) | **None.** The mandate over-constrained Player invocation, surfaced spurious blockers, and was reverted within 1 day (`9d304ed9` Apr 25). | The revert was the FP fix. | None. | **Counter-productive, reverted.** Not in current state. |

### 4.2 Concrete instance citations (incident-level)

Three framework false-positive incidents are documented in consumer-repo `docs/history/` post-mortems. All three are on disk and were the trigger for the §1 "fixes have just landed" narrative:

1. **`autobuild-FFC3-honesty-path-mismatch-incident.md`** (specialist-agent, 2026-05-06, 15KB).
   - 16 ACs never evaluated due to short-circuit on a single path-string honesty discrepancy.
   - Production code: `verdict.py` (312 LOC), `report.py` (551 LOC), 26 passing tests, all on disk in worktree.
   - Triggered TASK-REV-1B452, TASK-FIX-1B4A/B/C, TASK-DOC-1B4D, TASK-FIX-7E3F (a 5-task fix campaign in 1 day).
   - Manual-flip workaround used to bypass and proceed.

2. **`autobuild-FEAT-FG-001-review.md`** (fleet-gateway, 2026-05-09, 17KB).
   - 51/51 production tests pass, 11/11 + 10/10 ACs verified, all gates green except BDD oracle.
   - Five-turn feedback-stall on identical signature `sig=47fb7107` because Coach feedback summariser stripped the `ModuleNotFoundError` traceback before it reached the Player.
   - Triggered TASK-AB-001 (worktree python_executable thread-through), TASK-AB-003 (junit-error message in feedback), TASK-AB-004 (per-task BDD glue contract).
   - **Has not yet been re-run on `guardkit@HEAD`**; the implementation remains intact in the worktree pending a `--resume`.

3. **`autobuild-FFC3-editable-install-leak-incident.md`** (specialist-agent, 2026-05-06, 11KB).
   - Bootstrap installed worktree package into parent `.venv` via `uv pip install -e .`; after `/feature-complete` deleted the worktree, parent venv editable install pointed to deleted path.
   - Result: three Claude Desktop MCPs crashed with `ModuleNotFoundError` after restart.
   - Triggered TASK-FIX-FF61 (bootstrap worktree-venv isolation) + TASK-FIX-FF62 (`/feature-complete` pth-leak detect-and-warn).
   - **Tangential to the BDD-verification trajectory** — it's a bootstrap/finalize defect, not a Coach gate. Listed here for completeness because the same operator hit it in the same FFC3 run.

### 4.3 Cost/benefit framing

The acceptance cost of a real-positive (RP) is "Player does one extra turn". The cost of a false-positive (FP) is "operator writes a fix-up task and re-runs". For the 17-day window:

| Class | Count | Cost per | Total cost units |
|---|---|---|---|
| RP catches | ≥5 (Coach false-green; BDD silent-green; namespace shadowing; wave-2 race; AC-id mismatch) | 1 turn | ≥5 turns |
| FP incidents | 3 (FFC3 path; FG-001 BDD-env; 7A08 over-mandate) | ~5 fix-up tasks each | ~15 tasks |
| Manual-flip events | 2 (FFC3-005, FFC3-006) | 1 YAML edit each | 2 ops |
| Stuck features | 3 (J004-702C, J005-946D, FD32) | unknown — still open | ≥3 unresolved |

**On a turn-cost basis the trajectory is net-negative** (15 fix-up tasks ≫ 5 caught defects' worth of extra turns). On a *defect-class-prevention* basis it is **net-positive** (the deterministic-Coach false-green and the wave-2 race are systemic catches that would have shipped repeatedly). The right framing is the second one — **once stabilised**, the gates pay for themselves; the cost of the past 17 days has been the stabilisation, not the steady-state operation.

The decisive question is therefore not "are the gates good" but "have the gates stabilised". §6 addresses that directly.

---

## 5. Load-bearing audit (AC-004)

| Gate | Verdict | Defect class citation (for load-bearing only) |
|---|---|---|
| BDD oracle (post-AB-001/003/004) | **Load-bearing** | Pre-fix silent-green class (`cadde171`); per-task glue race (FG-001 wave-2). |
| CoachVerifier wired into deterministic Coach | **Load-bearing** | TASK-INV-AB1: deterministic Coach was approving on Player's `status:complete` without disk verification. |
| Honesty path-equality + Layer-1/2/3' fixes | **Load-bearing** | Cross-task path leakage retention; orchestrator-induced ghost filtering. |
| `_record_honesty()` None-payload guard | **Load-bearing as defensive** | Closes regression in `b9a45694` causing orchestrator crash on advisory turns. |
| Per-task BDD glue contract | **Load-bearing** | FEAT-FG-001 wave-2 race; the entire concurrency class. |
| BDD-runner pytest-bdd preflight | **Load-bearing** | Sibling of silent-green class (runner-without-producer Graphiti pattern). |
| Plan-audit files_to_modify check | **Load-bearing (new)** | Plan/implementation divergence. New, requires more bake time. |
| AC-id extraction (CVAC-001/002) | **Load-bearing** | Promise/AC-id divergence on compound + markdown-bold AC labels. |
| Smoke-gate seam-tests promote-to-block | **Load-bearing** | Player corner-cutting class (skipping seam tests when stub specified). |
| Smoke-gate venv interpreter pin | **Load-bearing** | Smoke-gate FN-0 class (running in orchestrator's PATH instead of worktree venv). |
| Parallel-contention peer-overlap guard | **Load-bearing** | Conditional-approval false-positives in parallel waves. |
| Operator-handoff skip branch | **Load-bearing (narrow)** | Operator-shaped AC class. Narrow scope; less critical. |
| Coach feedback-stall guard | **Load-bearing (pre-trajectory)** | Identical-signature stalls (FG-001 demonstration). |
| Assumption-confidence warn-mode | **Incidental** | No measured real-positive in 17-day window. |
| Player Task-tool mandate | **Counter-productive (reverted)** | The revert removed the FP source. Listed for audit completeness. |

### 5.1 Retire/demote candidates

- **Assumption-confidence warn-mode (`fb37f72f`)**: 17 days post-landing, no measured real-positive. Either elevate to block-mode and measure RP rate, or retire. The current warn-mode-with-no-action shape consumes Coach context budget for zero observed benefit.
- **Plan-audit (TASK-GK-PA-001/002)**: **Keep**, but flag for review on follow-up date — only 3 days old, insufficient evidence. If by 2026-05-17 there are no RP catches recorded, demote to warn-mode like assumption-confidence and re-evaluate.

### 5.2 Layer-2 demotion as a generative pattern

`074a6f03` (TASK-FIX-1B4B) demonstrated that a single path-only honesty discrepancy can be safely demoted from `must_fix` to `should_fix` without losing genuine cross-task leak detection (which retains multi-discrepancy + content-hash mismatch as `must_fix`). The pattern is:

> *Pair every `count_failed == 1` short-circuit with `count_attempted > 1` and `severity_class` checks. Single path-only discrepancies become feedback; multiple discrepancies or sophisticated lies retain `must_fix`.*

This pattern can be applied beyond honesty:
- **Single-AC promise mismatch**: should_fix (already implemented via CVAC-002 fallback).
- **Single agent-invocation gap**: should_fix (already implemented via `3eb820af`).
- **Single smoke-gate signal divergence**: candidate for demotion if Player corner-cutting evidence is patterned (multiple gates) rather than singular.

The demotion-PoC validates the **Narrow** recommendation: the existing trajectory has the right primitives; what it needs is selective application of the demotion pattern to the remaining `must_fix` short-circuits, plus stabilisation.

---

## 6. Doom-loop vs debug-cycle test (AC-005)

The decisive test for whether the system is at the *end* of a debug cycle vs in a doom loop is: **is the rate of new failure-classes per week declining, flat, or rising?** A debug cycle ending looks like distinct root causes being closed in declining count. A doom loop looks like recurring instances of the same shape under different names.

### 6.1 New failure-classes per week

| Week | New failure-classes captured | Examples |
|---|---|---|
| 2026-W17 (Apr 21–27) | 3 | namespace-shadowing (TASK-REV-MCPS); silent-green BDD (TASK-FIX-F584); SDK-message-types (TASK-FIX-7A03) |
| 2026-W18 (Apr 28–May 4) | 3 | seam-tests-skip (A7B4); parallel-contention (A7B2); CVAC AC-id mismatch (CVAC-001/002) |
| 2026-W19 (May 5–11) | 4 | path-string-mismatch (1B4D); deterministic-Coach false-green (INVAB1); None-payload crash (7E3F); BDD-env wrong-Python + per-task-glue race (AB-001/003/004) |

**The rate is rising, not falling.** This is the strongest single signal in support of the user's hypothesis.

However, the rate-rise interpretation must be qualified:

1. **W19's classes are concentrated in two days (May 6 + May 10)**. Both are post-mortems of incidents the *same gate stack just generated*. They are not new exploration; they are characterisation of the trajectory's own residue.
2. **The captured rules are sibling-paired**. `path-string-mismatch-is-not-dishonesty.md` is explicitly the inverse-shape of `absence-of-failure-is-not-success.md`; they share an `IS_INVERSE_SHAPE_OF` Graphiti edge. This is *generative* rule-writing — the system is now predicting its own failure modes by symmetry, which is debug-cycle-end behaviour, not doom-loop behaviour.
3. **The 1B4 fix trio closed three orthogonal layers of the same defect**. A doom loop closes the same defect repeatedly with different patches; layered defence-in-depth closes one defect with structurally-distinct guards and stops. Layer-1 (canonical-path resolution) + Layer-2 (severity demotion) + Layer-3' (orchestrator-induced filter) attack different points in the same data-flow path. Subsequent week (W20+) will show whether new path-mismatch instances arise — if they do not, this is debug-cycle behaviour.

### 6.2 The four design-rules check (descriptive vs generative)

| Rule | Date seeded | Citations to instances | Generative or descriptive? |
|---|---|---|---|
| `namespace-hygiene.md` | Apr 24 | 2 instances cited (editable-install lib/ shadow Apr 18; mcp/ shadow Apr 24); seeded "broader meta-rule" link to externally-defined-namespaces. | **Generative** — the rule predicts future instances and lists their grep signatures. |
| `absence-of-failure-is-not-success.md` | May 6 | 3 instances cited (`parse_junit_xml` zero-result; BDD `scenarios_failed==0` false-green; deterministic-Coach `status:complete`). | **Generative** — meta-frame paragraph lists the inverse shape (false-red gate from same low-fidelity oracle). |
| `path-string-mismatch-is-not-dishonesty.md` | May 6 | 1 instance cited (FFC3); paired with `absence-of-failure` via `IS_INVERSE_SHAPE_OF` edge. | **Generative** — explicit pair, predicts future `Path.exists()` boundary check failures. |
| `bdd-per-task-glue.md` | May 9–10 | 1 instance cited (FG-001 wave-2). Documents per-task naming contract. | **Generative-narrow** — captures one concurrency class. Less broadly predictive than the other three. |

**3 of 4 rules are generative**. The system has built up enough abstraction to predict its own failure modes. That is debug-cycle-end behaviour at the meta-level.

### 6.3 Verdict on the doom-loop test

**Not a doom loop. Late-stage debug cycle approaching closure.**

- The rate of new failure-classes is rising in the *most recent* week, but the new classes are characterisations of incidents the trajectory's own gates produced, not new exploration.
- The fix-rate is high (3.57:1) because the trajectory is large, not because the fixes are reopening previously-fixed issues.
- The captured rules are generative, not descriptive — that is the signature of a system reaching closure.
- The W17 + W19 incidents share *meta-shape* but not *root-cause shape*. They are correctly being written as siblings, not duplicates.

The required follow-up signal: **W20 (May 12–18) should show ≤1 new failure-class** if the trajectory is converging. If ≥3 new classes are seeded, escalate to Pivot.

---

## 7. Anti-bias section (AC-008)

**The user has stated a hypothesis. This section explicitly considers the counter-hypothesis: "what would I expect to see if the trajectory IS working".**

### 7.1 Counter-hypothesis: the trajectory is working

If the trajectory were working:

| Expectation | Observed? | Evidence |
|---|---|---|
| Recent fixes close distinct root causes (not recurring shapes) | ✅ Mostly | Phase D + E fixes (1B4* trio + AB-001/003/004) attack four distinct subsystems: path-equality, payload guarding, BDD subprocess Python, BDD glue concurrency. Not recurrences. |
| Failure classes captured as rules and verified to prevent recurrence | ⚠️ Partially | 4 rules captured; 0 instances yet of "rule prevented a recurrence" because rules are <2 weeks old. Cannot verify until W20+. |
| Consumer-repo features eventually reach pass after reasonable retries | ✅ Yes | 5/8 multi-retry features recovered (FORGE-009, PEBR, 70A4, 39E1, 9B60) without manual flip. |
| Falling rate of "I have to fix guardkit" tasks | ❌ No | Fix-up tasks are still landing daily through W19 (May 6 cluster, May 7 cluster, May 10 cluster). Rate has not declined. |
| ≥1 clean-pass-on-first-turn in the last 14 days | ⚠️ One | FEAT-DEA8 (forge, 2026-05-04) — exactly one. Sparse signal. |
| Post-fix consumer features pass cleanly on `guardkit@HEAD` | ❓ Unknown | FG-001 has not been re-run post AB-001/003/004 (landed today). FFC3 has not been re-run post 1B4* trio. **This is the deciding observation; it has not been made yet.** |

**The trajectory is *plausibly* working post-fix, but the deciding observation has not been made.**

### 7.2 Counter-hypothesis: the user's framing is wrong about magnitude

The user says: "we used to be at 95%". But:

- The pre-trajectory `docs/history/` archive is sparse (entries before April 25 are mostly pre-trajectory baseline runs whose outcomes are filename-unclear). The "95%" number is recollection-based, not measurement-based.
- Some of the user-perceived "fix-up tasks" are *the framework correctly catching genuine implementation issues*. The TASK-CVAC-001/002 series, for example, fixes Coach AC-id matching — that's a genuine bug class that pre-trajectory autobuild ignored silently. The user counts the fix as a fix-up; the system catches it as a real-positive.
- Multi-retry features that *did* recover (FORGE-009, PEBR, 70A4, 39E1, 9B60) represent the framework working as intended — but the user experiences "5 retries to get a pass" as failure rather than success. Each of those 5/8 is a recovered feature that pre-trajectory autobuild might have shipped broken on first turn.

So the user's "95%" baseline is partly a comparison against a less-strict gate stack that approved more turns. The right comparison is "post-fix run-success" against "pre-trajectory run-success-on-turns-that-actually-worked". That comparison has not been instrumented and **needs to be**.

### 7.3 What would falsify the user's framing?

If by **2026-05-17**:
- ≥3 consumer-repo features pass cleanly on first-turn against `guardkit@HEAD` (no new gates landed in this window), AND
- No new framework false-positive incident is filed in any consumer repo `docs/history/`,

then the user's framing is falsified — the trajectory had stabilised on 2026-05-10 and the fixes hold. **In that case, escalate from Narrow to Continue.**

If neither condition is met, the user's framing is supported on the evidence — escalate from Narrow to Pivot.

### 7.4 What would falsify the trajectory-is-working counter-hypothesis?

If by **2026-05-17**:
- A **new** framework false-positive is filed in any consumer repo (i.e. a class not yet documented in `.claude/rules/`), OR
- Any consumer-repo feature stalls for ≥5 turns on identical Coach feedback signature with all production-code gates green (the FG-001 / FFC3 shape recurring),

then the trajectory is not working — escalate to Pivot.

---

## 8. Recommendation and falsifier (AC-006)

### 8.1 Recommendation: **Narrow** (Option B)

**Specifically: 7-day gate-stack freeze with re-measurement, plus three concrete narrowing actions.**

#### 8.1.1 The freeze

- **Window**: 2026-05-11 → 2026-05-17 (7 days from this report).
- **Scope**: no new NEW_GATE commits to `guardkit/orchestrator/quality_gates/`, `guardkit/orchestrator/agent_invoker.py`, `guardkit/tasks/state_bridge.py`, or `installer/core/templates/common/features/conftest.py.template`. FIX_FOR_NEW_GATE commits permitted *only* if they are reverts or single-line guards on already-landed code. No new gate-classes or new behavioural surface.
- **Purpose**: give consumer repos a stable target. Re-run FEAT-FG-001 (fleet-gateway) and FEAT-FFC3-class scenarios (specialist-agent) against `guardkit@HEAD` without the gate stack moving underneath them. Measure run-success.

#### 8.1.2 Three narrowing actions during the freeze

1. **Audit `assumption-confidence` warn-mode for retire/keep**. 17 days post-landing, no measured RP. Either elevate to block-mode (with regression test demonstrating an RP catch) or retire entirely. Default action: retire.
2. **Validate Layer-1/2/3' honesty fixes against an FFC3-class reproducer**. Construct a scripted reproduction of the path-mismatch incident and verify all three layers fire correctly with no Coach short-circuit. If any layer fails, file a follow-up.
3. **Validate AB-001/003/004 against an FG-001 resume**. Re-run `guardkit autobuild feature FEAT-FG-001 --resume` against `guardkit@HEAD` and verify the BDD oracle uses the worktree venv, the Coach feedback carries the actual `ModuleNotFoundError` traceback, and TASK-FG-003 collects per-task scenarios via `GUARDKIT_BDD_TASK_ID`. If any of the three fail, the AB trio is not closed.

#### 8.1.3 Why not Continue, Roll back, or Pivot?

Already addressed in §1; restated for completeness.

- **Continue**: premature. The May 6 + May 10 fixes have not been validated. Declaring the trajectory stable today would be the *absence-of-failure-is-not-success* meta-error this very review is meant to guard against.
- **Roll back**: loses real catches (Coach false-green, BDD silent-green, namespace shadowing, wave-2 race). Also breaks consumer-repo dependency on per-task BDD glue (FEAT-FG-001 spec is now written assuming this contract).
- **Pivot**: too large a structural change for the evidence. The deterministic-Coach path's bugs are now fixed (Layer-1/2/3' + 7E3F + INVAB1 close the FFC3 incident class). Pivot is the *escalation* if the freeze fails — not the headline.

### 8.2 Falsifying leading indicator

**The trajectory is stable** if, by **2026-05-17**:
- ≥3 consumer-repo features pass cleanly on first-turn against `guardkit@HEAD` (POSITIVE-FALSIFIER for Narrow being too cautious — escalate to Continue), AND
- No new framework false-positive incident is filed in any consumer repo (NEGATIVE-NULL — no new evidence either way).

**The trajectory is not stable** if, by **2026-05-17**:
- Any *new* framework false-positive is filed in a consumer repo (a class not yet documented in `.claude/rules/`) (NEGATIVE-FALSIFIER for Narrow — escalate to Pivot), OR
- ≥1 consumer-repo feature stalls for ≥5 turns on identical Coach feedback with all production-code gates green (NEGATIVE-FALSIFIER for Narrow — escalate to Pivot), OR
- A new gate is landed during the freeze window without operator consensus (process-falsifier — Narrow itself was not held).

The leading-indicator dashboard is intentionally minimal: 3 positive observations, 3 negative observations, all of them in the next 7 days. If neither set fires (ambiguous outcome), extend the freeze by 7 days.

### 8.3 Follow-up date

**2026-05-17.**

A follow-up review (or this same TASK-REV-ABST re-opened with `--depth=quick`) should fire on that date to evaluate the leading indicators. The follow-up's job is to pick one of:
- **Promote Narrow → Continue** (if positive-falsifiers fire).
- **Hold Narrow** (if leading indicators are silent — extend freeze 7 days).
- **Escalate Narrow → Pivot** (if negative-falsifiers fire).

### 8.4 Headline next-task list (revised under operator-deadline constraint, 2026-05-10)

**Operator constraint accepted at decision checkpoint, 2026-05-10**: deadlines for DDD South West talk + Kaggle Hackathon in the next 7-9 days preclude autobuild reruns or multi-hour validation campaigns. Re-scoped follow-through is *monitoring + audit + freeze + scheduled re-review* — every retained task is read-only or process-only. **The three `TASK-VAL-*` tasks (FG001, FFC3, FRESH) are explicitly DROPPED** because they all require autobuild execution; the falsifier set in §8.2 remains documented but the *positive-falsifier observation* is now opportunistic — if the operator happens to run an autobuild during the freeze window for unrelated reasons, that data feeds the follow-up review; no dedicated rerun is scheduled.

Each retained task is filed in `tasks/backlog/` with full content (frontmatter + description + EARS-style ACs + concrete files-to-modify + evidence cites) so it is `/feature-spec`- or `/task-work`-ready.

| Filed Task | Title | Effort | Trigger |
|---|---|---|---|
| `TASK-FREEZE-ABST` | Declare 7-day gate-stack freeze 2026-05-11→2026-05-17 + add commit-time guard | <1h | This report §8.1.1 |
| `TASK-OBS-ABST` | Passive autobuild run-success observability from existing on-disk artefacts (filename + JSON parse, no autobuild reruns) | 4-6h | This report §9.1 — closes largest evidence gap |
| `TASK-RETIRE-AC` | Audit `assumption-confidence` warn-mode gate against 17-day RP record; retire if no RP cited | 1-2h | This report §5.1 |
| `TASK-DEMOTE-PA` | At 2026-05-17 follow-up: audit plan-audit PA-001/002 RP rate from passive observability output; demote to warn-mode if RP/(RP+FP) < 0.5 | 1-2h, **deferred to 2026-05-17** | This report §5.1 |
| `TASK-REV-ABST.1` | Follow-up `/task-review --depth=quick` on 2026-05-17 against the falsifier set in §8.2 (using `TASK-OBS-ABST` output as primary input) | 2-3h, **deferred to 2026-05-17** | This report §8.3 |

**Deferred / conditional:**
- `TASK-REV-PIVOT` (not filed). Only file if `TASK-REV-ABST.1` reports a negative-falsifier (new framework FP class filed during the freeze window, or any new ≥5-turn identical-feedback stall). The pivot review's job would be the deterministic-Coach keep/retire decision (TASK-REV-0414 follow-up). Filing it pre-emptively would consume backlog hygiene budget for a low-probability outcome.

**Dropped (require autobuild reruns, incompatible with operator deadline):**
- `TASK-VAL-FG001` — would require `guardkit autobuild feature FEAT-FG-001 --resume`.
- `TASK-VAL-FFC3` — would require building an FFC3-class reproducer feature and running autobuild against it.
- `TASK-VAL-FRESH` — would require running a fresh consumer-repo feature first-turn.
- A passive substitute (`TASK-PASSIVE-VAL-ABST`) was considered: replay existing FFC3 + FG-001 artefacts through new code paths in unit tests. Estimated 6-8h. **Dropped under deadline pressure**; if the operator chooses to file it later, it is the cheapest way to close the evidence gap on the May 6 + May 10 fix landings without a rerun.

This revised scope keeps Narrow's verdict intact but acknowledges that the *positive-falsifier* observation in §8.2 is now opportunistic rather than scheduled. The follow-up review on 2026-05-17 will work from whatever data the freeze week has surfaced organically.

---

## 9. Limits and unknowns (AC-007)

Per `absence-of-failure-is-not-success.md`: *"absence of negative signal in the dataset" is not "evidence the gate is working"*. Applied to this meta-review:

### 9.1 Where evidence is missing

- **Pre-trajectory baseline.** The user's "~95% success" is recollection, not measurement. The `docs/history/` archive does not extend pre-trajectory with sufficient density to verify. Confidence on the *direction* of degradation: high. On the *magnitude*: low.
- **Post-fix run-success.** The deciding observation has not been made. FG-001 has not been re-run post-AB-001/003/004 (landed today, 2026-05-10). FFC3 has not been re-run post-1B4*. The Narrow recommendation explicitly bets on the next 7 days providing this evidence.
- **First-pass success rate is filename-pattern-inferred, not telemetry-measured.** TASK-OBS-ABST in §8.4 is the headline action to close this gap.
- **The 5-turn cosmetic-edit cost.** When a Player runs 5 turns of cosmetic edits stalled on a framework FP (FG-001), each turn consumes ~50K-200K tokens of Coach + Player context. The actual *cost* of a framework FP, in tokens × $/token, is not measured here. This may matter for the cost-benefit framing in §4.3.

### 9.2 Where the analysis could be wrong

- **The 3.57:1 ratio is a coarse metric.** Counting commits ignores commit size, importance, and whether a "fix" was actually closure or just-deferred-pain. A sophisticated metric would weight by lines changed and by recurrence rate. This report uses the coarse metric because the alternative requires sub-day SHA-by-SHA analysis the §6 doom-loop test already approximates.
- **Bucket assignments in the timeline are LLM-inferred from commit messages.** A `fix(...)` commit message that actually adds new gate behaviour would be mis-bucketed. A spot-check of the ten Phase-C commits suggests ~9/10 correct bucketing; the residual error rate adds noise to the 3.57:1 ratio but does not flip the sign.
- **The "5/8 multi-retry recovered" framing implicitly counts retry-attempts as the framework's *cost*, not its *value*.** The opposing framing — that 5/8 features the framework caught and forced into a correct state would have shipped broken pre-trajectory — has equal evidential standing. This report assumes the user's intent is "fewer retries", not "more catches", but that is itself a value judgement.
- **Two of three FP incidents are on the same day (2026-05-06, FFC3-005 and FFC3-006).** They share the same root cause (b9a45694's deployment). Counting them as 2 vs 1 affects the FP rate by ~33%. This report counts them as 1 incident class (path-mismatch) with 2 instances, but the timeline table (§2.2) lists them as separate fixes because they had separate fix tasks (1B4A vs 7E3F).

### 9.3 What would change this review's recommendation

- **If a fourth framework FP class emerges between this report and 2026-05-17** that is *not* a sibling of the existing four rules, the recommendation flips from Narrow to Pivot.
- **If any of the three §8.1.2 narrowing actions fail** (assumption-confidence cannot be retired because evidence emerges; Layer-1/2/3' cannot validate against a reproducer; AB-001/003/004 cannot validate against FG-001 resume), the recommendation extends Narrow's freeze and adds a fourth narrowing action; if any fail twice, escalate to Pivot.
- **If the user reports a framework FP incident in any repo before 2026-05-17 that is not yet captured here**, this report's evidence base is incomplete; the recommendation may need re-grounding.

### 9.4 What this review explicitly does NOT cover

Per the task's *Scope — out* clause:
- Does not implement any change. All §8 actions are *headlines*; their plans belong to follow-up tasks.
- Does not redesign consumer-repo pipelines.
- Does not touch `installer/core/templates/` content.
- Does not touch the Graphiti / FalkorDB / vLLM infrastructure surface.
- Does not produce a full implementation plan for any of the recommendation options.

---

## 10. Decision checkpoint

Per the `/task-review` workflow, this report concludes with an explicit decision checkpoint for the project owner.

| Option | Action | When to choose |
|---|---|---|
| **[A]ccept** | Mark TASK-REV-ABST `REVIEW_COMPLETE`; archive report; treat the §8.4 headline list as advisory; manually file the follow-up `TASK-REV-ABST.1` for 2026-05-17. | If the project owner agrees with the **Narrow + 7-day-freeze + re-measurement** verdict and prefers to file follow-up tasks manually. |
| **[R]evise** | Re-run this review with deeper analysis on a specific area (e.g. doom-loop test with weekly granularity for prior 6 months; or full-content read of every consumer-repo `docs/history/` log to verify filename inference). | If the project owner believes the §6 doom-loop test or the §3 first-pass-success rate is insufficiently rigorous. |
| **[I]mplement** | Generate the §8.4 headline next-tasks as concrete subtasks via the auto-detection pipeline. | If the project owner agrees with Narrow and wants the freeze, validations, retires, and follow-up review filed as concrete actionable tasks. |
| **[C]ancel** | Discard this review; return TASK-REV-ABST to backlog. | If the project owner believes the review's evidence base is fundamentally inadequate and wants to gather more before deciding. |

**The reviewer's recommendation is [I]mplement** — file the §8.4 list as concrete tasks, observe the four falsifiers over the freeze window, and re-decide on 2026-05-17.

---

*End of report. Generated 2026-05-10 by `/task-review` for TASK-REV-ABST. Evidence sources: `git log` since 2026-04-01; consumer-repo `docs/history/` for jarvis, forge, study-tutor, specialist-agent, fleet-gateway; `guardkit/.claude/reviews/`; `guardkit/tasks/{backlog,in_progress,in_review,blocked,completed}/`; `guardkit/.claude/rules/{absence-of-failure-is-not-success.md, path-string-mismatch-is-not-dishonesty.md, namespace-hygiene.md, bdd-per-task-glue.md}`; FEAT-FG-001 review and FFC3 incident post-mortems read in full.*
