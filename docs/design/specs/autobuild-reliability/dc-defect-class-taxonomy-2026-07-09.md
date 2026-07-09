# DC-01..DC-16 — Autobuild Defect-Class Taxonomy (durable record)

**Status:** durable taxonomy · 2026-07-09 · published by WS3-S3 (the WS3 §3 standing
"DC-taxonomy durability gap" fold-in item). Companion to the S2 seam-check-semantics design
(`ws3-s2-seam-check-semantics-2026-07-07.md`, same directory).
**Named consumer:** WS2-B11 Phase-2 QAV seeded-defect seeding
(`agentic-dataset-factory/domains/qa-verifier/PLAN-qav-phase1-dataset-generation.md` §3), which
deliberately restricted itself to the durably-named classes and flagged the gap this doc closes.
**Binding source of the ledger:** `ai-transition/docs/factory-gap-analysis-2026-07-07.md` §2
(16 classes, 9 composition-seam incidents, the 2026-07-04 xref audit of 153 incidents across 5
repos); WS4 §5.3 / the QAV fine-tune scope (`ai-transition/docs/qav-fine-tune-scope.md`) for the
DC-08 / DC-14 names.

---

## 0. Why this doc exists (the durability gap, stated honestly)

Of the 16 `DC-nn` defect-class ids, **only 7 are named in a durable committed record**:
DC-03, DC-05, DC-08, DC-12, DC-14, DC-15, DC-16 (sources: factory-gap-analysis §2 + WS4 §5.3).
The other nine — **DC-01, DC-02, DC-04, DC-06, DC-07, DC-09, DC-10, DC-11, DC-13** — were
**counted in the §2 ledger but never individually named**; they lived only in the 2026-07-07
analysis session's fan-out digest, which named the *count* and the *class families* (the fixed
false-red / honesty-machinery lineage) but not each `DC-nn` label.

This doc therefore carries a **per-id provenance flag**:

- **`named-in-record`** — the id and its class description appear verbatim in a committed doc.
  The label is authoritative.
- **`reconstructed`** — the id is one of the nine "counted-but-unnamed" ordinals. Its class is
  reconstructed from §2's described fix lineage and the durable fix-family catalog in
  `guardkit/.claude/rules/` (which *is* the committed record of the fixed classes). **The
  class family is real and committed; the specific `DC-nn` ⟷ class *ordinal assignment* is an
  inference of this doc, not a fact in any prior record** — because the §2 ledger states the
  membership set `{DC-01,02,04,06,07,09,10,11,13}` without a per-id mapping. A future record that
  fixes the ordinals supersedes the reconstructed rows here; the named rows are stable.

The §2 ledger's hard facts this doc must honour:
- 11 **fixed-and-merged**: DC-01/02/04/06/07/08/09/10/11/13/14.
- 4 **filed-open**: DC-05 (env-tampering → ENVTAMPER01), DC-12 (feature-plan defects),
  DC-15 (cross-repo evidence architecture), DC-16 (tracker corruption from checkpoint merges).
- 1 **recurring-unfiled**: DC-03 (the composition seam — the only class with no structural cure
  landed as of §2; WS3-S3's seam checks are that cure).

So the reconstructed nine are drawn from the **fixed-and-merged** pool minus the two named fixed
classes (DC-08, DC-14): the false-red / absent-signal / harness / honesty fix families that the
`.claude/rules/` catalog documents as landed.

---

## 1. The 16 classes

| DC | Class | Status (§2) | Provenance | Canonical incident / fix-family record |
|----|-------|-------------|------------|----------------------------------------|
| **DC-01** | Absent/false test-signal false-red (`unrecoverable_stall` on a zero/absent counter) | fixed-and-merged | `reconstructed` | `.claude/rules/absence-of-failure-is-not-success.md`; lpa POC-005 (100% of stall verdicts false); tri-state fix CKPTTESTRED01 |
| **DC-02** | Absent-signal coerced across a reconciliation/transit layer (timeout→`False`) | fixed-and-merged | `reconstructed` | `.claude/rules/absence-must-survive-every-reconciliation-layer.md`; forge FMDR ("failed" a 34/34-green feature); TASK-ABFIX-010 |
| **DC-03** | **Composition seam** — per-task-green ≠ feature-green (dead call sites, signature drift, mocked seams, unwired boot) | **recurring-unfiled** (no structural cure at §2) | **named-in-record** | lpa **FEAT-POC-006** (11/11 approved, 345 green, could not boot); 9 incidents 2026-06-13→07-06; 4/8 final-week escapes. **Cure = WS3-S3 seam checks (2a/2b/2d).** |
| **DC-04** | Path-string / honesty false-red (orchestrator-moved file read as a Player lie) | fixed-and-merged | `reconstructed` | `.claude/rules/path-string-mismatch-is-not-dishonesty.md`; FEAT-FFC3 honesty false-fail; FIX-1B4A/1B4C |
| **DC-05** | **Player environment-tampering** (`sys.modules` stubs / vendored stubs defeating skip-guards) | **filed-open** → ENVTAMPER01 | **named-in-record** | **FEAT-ABL-001 run 2** — 56-line `nats_core` stub in `guardkit/__init__.py`; cure = ENVTAMPER01 two-half probe (WS3-S3 §5) |
| **DC-06** | Harness-cancellation / substrate-divergence (a control written for one substrate no-ops on another) | fixed-and-merged | `reconstructed` | `.claude/rules/harness-cancellation-contract.md` + `watchdog-activity-signal-must-be-substrate-aware.md`; CTOUT01 / SPECINVOKE01 |
| **DC-07** | Specialist latency / unbounded phase (a busy-but-wasteful or hung specialist exhausts the task budget) | fixed-and-merged | `reconstructed` | `.claude/rules/specialist-guard-asymmetry-is-a-latency-blocker.md` + `structural-defence-beats-prompt-instruction.md`; SPECLAT01 / SPECHANG |
| **DC-08** | **BDD holes** (undefined step / `StepDefinitionNotFoundError`; pending-vs-failed miscount) | fixed-and-merged | **named-in-record** | **SMP-002** (undefined BDD step, approved 7/7); `.claude/rules/bdd-pending-is-not-failed.md` + `bdd-per-task-glue.md` |
| **DC-09** | Evidence-boundary / collection aperture too narrow (work outside the oracle's spatial reach) | fixed-and-merged | `reconstructed` | `.claude/rules/evidence-boundary-narrower-than-write-surface.md`; FEAT-C332 / E2CB run 1 (sibling-repo writes); XREPOEV01 |
| **DC-10** | Namespace / install-path hygiene (internal name shadows a PyPI dep; uv-sources dropped on an install path) | fixed-and-merged | `reconstructed` | `.claude/rules/namespace-hygiene.md` + `uv-sources-must-survive-every-install-path.md`; MCPS / UVSRCDEP01 (FEAT-HARV) |
| **DC-11** | Disposition / wasted-signal (a correct high-fidelity failure terminates instead of feeding back) | fixed-and-merged | `reconstructed` | `.claude/rules/smoke-gate-is-feedback-not-terminator.md`; FEAT-9DDE run 8 |
| **DC-12** | **Feature-plan defects** (gate sequenced before its test exists; unverifiable live-infra ACs; timeout floors as a "fix") | **filed-open** | **named-in-record** | `docs/guides/feature-plan-task-classification.md`; the timeout-floor relabel (FEAT-FD32) |
| **DC-13** | Display/verdict-derived-from-proxy + verdict-override-not-persisted (a runtime property read off the wrong source) | fixed-and-merged | `reconstructed` | `.claude/rules/display-must-derive-from-enforcement-source-not-proxy.md` + `deterministic-verdict-override-must-persist-to-disk.md`; MAXPARALLEL01 / COACHFG01 |
| **DC-14** | **Direct-mode false-green** (relaxed gates read as AC-delivery confirmed) | fixed-and-merged | **named-in-record** | `.claude/rules/direct-mode-relaxed-gates-require-positive-evidence.md`; FEAT-9DDE run-3 (TSJ-002 non-functional bin-entry) |
| **DC-15** | **Cross-repo evidence architecture** (raw cross-repo evidence with no shared protocol) | **filed-open** | **named-in-record** | factory-gap-analysis §2; WS4-owned; process-layer, no bundle signature |
| **DC-16** | **Tracker corruption from checkpoint merges** (checkpoint `git add -A` merges launder tracker/config state into the baseline) | **filed-open** | **named-in-record** | factory-gap-analysis §2; the §4 tracker corollary; motivates WS3-S3 §1.3 feature-base config referent |

---

## 2. Notes on the reconstructed rows (honesty about the inference)

- The nine `reconstructed` rows name **real, committed, fixed classes** — each cites a
  `.claude/rules/` file that is the durable record of that fix family. What is *inferred* is only
  the **`DC-nn` ordinal** attached to each: §2 asserts the membership set
  `{DC-01,02,04,06,07,09,10,11,13}` is fixed-and-merged, but publishes no per-id mapping, so the
  assignment above is this doc's best-fit ordering (roughly the chronological fix lineage:
  false-red interpretation → transit-layer preservation → honesty → substrate → specialist →
  collection → namespace → disposition → display/verdict-persist). A consumer that needs a
  *stable* id should treat the **named-in-record** seven as authoritative and the reconstructed
  nine as "class family + provisional ordinal".
- The low-fidelity-oracle meta-frame family (`absence-of-failure`, `path-string-mismatch`,
  `harness-cancellation`, `evidence-boundary`, `smoke-gate-is-feedback`,
  `per-task-green-is-not-feature-green`, `absence-must-survive`) spans DC-01/02/04/06/09/11 and the
  DC-03 seam class — they are siblings, not disjoint. DC-03 is the one member with **no** structural
  cure landed at §2; that is precisely why WS3 exists.

## 3. Consumer contract (WS2-B11 Phase-2 seeding)

B11 Phase-2 seeds seeded-defect fixtures per DC class. This doc lets B11 extend beyond the
durably-named seven to the full sixteen, **carrying the provenance flag into each seeded fixture's
manifest** so a `reconstructed`-provenance fixture is never mistaken for a record-authoritative one.
The recommended seeding priority is unchanged from B11's dated note (DC-03 ~40%, DC-05/08/14 ~15%
each) — this doc widens the *catalog*, not the priority.

## 4. Change log

- 2026-07-09 (WS3-S3): initial publication. Seven `named-in-record` rows verbatim from
  factory-gap-analysis §2 + WS4 §5.3; nine `reconstructed` rows mapped to the `.claude/rules/`
  fix-family catalog with the ordinal-inference caveat stated in §2. Closes the WS3 §3
  "DC-taxonomy durability gap" standing item.
