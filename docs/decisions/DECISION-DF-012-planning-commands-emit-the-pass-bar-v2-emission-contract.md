# DECISION-DF-012 — Planning commands emit the pass bar: the v2 emission contract (ONE versioned migration, ONE G2b re-freeze)

**Status:** CANDIDATE — drafted 2026-07-08 for Rich's curation (P11 modernization-review follow-up, Fable). **NOT filed in REGISTER.md**; number tentative (behind the DF-010 A2A candidate). Accept/amend/decline at the register. **Two riders (§2.7–§2.8) are proposed as binding conditions of acceptance, not suggestions.**
**Scope:** a **versioned migration** of the pinned FEAT-SPL-007/008 output contracts — additive sidecar artifacts only; the three-file spec output, the feature-YAML schema, and the `feature_loader.py` oracle stay **byte-identical**. Fleet-relevant (WS1 emits, WS2 owns schemas, G2b re-freezes); candidate filed from the guardkit lane because the emitting templates are guardkit's.
**Consumer:** FEAT-SPL-007 `po_feature_spec` + FEAT-SPL-008 `architect_feature_plan` (emitters); Coach task-start precondition (session B2, reader); live-gate runner B3 (reader); `/feature-complete`; G2b FEAT-EVAL-SPEC (emitted bars become gradable eval artifacts); forge Mode P dispatcher (F13 renderable-fields beneficiary).
**Companions:** DF-007 (instances stay repo-owned — emitters write into the *target repo's* qa/), DF-009 (whose §2.4 planning chain these emitters serve), ST-01/ST-12/LPA-04/LPA-09 (the retro recommendations this operationalises), F1–F5 formats `b9f5eff8` (built ON, evolved only via their own dated-note channel — rider §2.7), CONTRACT-feature-spec-plan-outputs.md (the document this migration amends with a dated correction note).
**Reasoning trail:** `docs/reviews/guardkit-modernization-review-2026-07-08.md` §6 (DIM5-F1/F2/F3/F4/F6, all skeptic-verified) + §3 DIM2-F5; `guardkit/qa/formats/pass_bar.py:9-18` (the shipped WS1-CONTRACT docstring naming these tools the writers); `ai-transition/docs/ws2-qa-verifier-and-last-mile-scope-design-2026-07-07.md` §2 (writer matrix; line 346 records the unlanded WS1 delta).

---

## Summary

WS2 shipped the tier-1 QA formats and **named the headless `/feature-spec` + `/feature-plan`
tools as the writers of the F1 pass bar** — in the schema module's own docstring. Nothing emits
one. Until something does, ST-01 ("the pass bar EXISTS before build") is vacuous, the Coach
task-start precondition has nothing to check, and success criteria continue to be defined
after the fact by whatever went green — the fs-01 false-approval class. This record makes the
planning commands producers of the verification data the factory already consumes, as **additive
sidecars** bundled into **one** coordinated re-pin/re-freeze event.

## 1 · Context — why the seam, and why one event

1. **The seam is acknowledged in three shipped places, implemented in zero:**
   `pass_bar.py:9-18` ("The headless /feature-spec + /feature-plan tools are the named WRITERS
   of this block"); `installer/core/templates/common/qa/README.md:19` ("headless /feature-spec +
   /feature-plan **will** emit it" — future tense); WS2 scope-design line 346 (WS1 owes the
   emission before the SPL-007/008 sessions). Both command specs contain zero qa-format
   references (verified by the P11 review).
2. **The incident class is committed:** fs-01 Coach false-approval (2026-06-13,
   FEAT-MEM-04/TASK-RLY-006 — all-green reported while wave-4 wiring broke `test_app_lifespan`;
   corpus `fleet-evals/tasks/abl-fs01-coach-false-approval/`). Pre-committed observable bars
   are ST-01's structural counter; ABL-001's nats_core stub is the env-tamper instance of the
   same class.
3. **Why now:** the 007/008 build sessions have not run. Deciding now means the emitters are
   built once with this in the contract; deciding later means retrofitting a pinned, frozen
   tool and paying the coordination window twice.
4. **Why one event:** the contract is refusal-pinned by content hash. Every separately-landed
   template edit is a separate specialist-tool-down window. This record bundles all five
   emission items into one migration; rider §2.8 extends the batching to any other pending
   byte edits.

## 2 · Decision

1. **F1 pass-bar sidecars.** `/feature-spec` + `/feature-plan` (headless 007/008 forms; the
   attended slash commands gain the same steps) emit one `qa/pass-bar-<TASK-ID>.yaml` per
   generated task — validator-green against the shipped F1 schema, criteria carrying the
   machine|operator class split (operator-class criteria keyed off the existing
   `operator_handoff` classification, per ST-12), `checkpoint_list_ref` for walk-bearing
   features. Sidecars are written into the **target repo's** qa/ (DF-007: instances are
   repo-owned; templates never carry authoritative instances).
2. **F3 surface claims at plan time.** `/feature-plan` gains the producing step for
   leak-sweep **surface claims only** — "plan claims surfaces as real; the Player updates
   entries as surfaces land," exactly the split `leak_sweep.py`'s docstring already draws.
   Closes the runner-without-producer gap for B3.
3. **`registered_at` fill/verify mechanics defined.** Emitter fills `sha` = HEAD-at-emit
   (parent commit); B2 verifies provenance mechanically via the file's introduction commit
   (`git log --follow --diff-filter=A`) predating the task's first implementation commit.
   Without this, "committed BEFORE implementation" is an honor-system date string.
4. **F13 renderable-fields guarantee — /feature-plan is NOT a second F13 writer.** WS2 pins
   the kickoff-prompt writer as the forge Mode P dispatcher ("render fails on missing
   sections"). The plan's obligation is that its outputs carry the dispatcher-renderable
   fields: `deliverable.gate_ref` resolves to an emitted F1 id; `decisions_already_made` is
   mechanically sourceable from the assumptions manifest. Seam v1 preserved — guardkit never
   couples to forge's session model.
5. **Plan-time authorship guard for the F2 ledger.** A path-based reject-lint fails any
   `/feature-spec`|`/feature-plan` session whose diff touches `qa/known-failures.yaml` —
   a headless planner writing the expected-failure ledger is the false-green channel LPA-09
   exists to close, and B2's specified enforcement checks *when* entries are written, not
   *who* wrote them at plan time. The lint lands **with** session B2.
6. **The writer matrix is referenced, not restated.** WS2 scope-design §2 is already normative
   ("a format written by 'whoever' is written by no one"); the v2 contract cites it. F2 stays
   human/Coach-at-triage-only; F4 stays build-time; F5 stays runner-only.
7. **RIDER 1 (binding): honest bars must be emittable first.** The F1 validator currently
   hard-requires five auth-surface-shaped negative paths from EVERY bar
   (`pass_bar.py:41-49`) — an emitter for authless features (CLI/library/pipeline) can only
   comply by fabricating. The PB-14 schema evolution (dated note in WS2 scope-design §2;
   conditionality of the four auth paths keyed on an auth-surface-bearing flag; B2/B3
   coordinate) lands **with or before** the emitters. Via the format's own dated-note channel —
   not a reopen of `b9f5eff8`. Day-one fabricated bars would poison G2b's eval corpus at birth.
8. **RIDER 2 (binding): one re-pin event.** All byte changes to the pinned templates —
   these emission steps, plus any pending anchor de-duplication or format_version additions —
   batch into **ONE** coordinated migration: dated correction note in
   CONTRACT-feature-spec-plan-outputs.md → round-trip fixtures re-run (expected unchanged;
   run to prove it) → Session C re-pins both sha256s → G2b re-freezes FEAT-EVAL-SPEC seeds
   (extended to grade emitted bars) → Rich approves. One specialist-tool-down window, not four.

## 3 · Consequences

**Positive:** ST-01 becomes enforceable (B2's Coach precondition gets real input); the fs-01
class is countered structurally rather than by prompt instruction; emitted bars are
zero-marginal-cost gradable (`guardkit qa validate pass-bar` shipped); forge's dispatcher can
render complete kickoff prompts from plan artifacts alone; the emission contract exists before
the emitters are built, not after.
**Negative / accepted:** one coordinated tool-down window (bounded, scheduled, and the review's
PB-3 CI gate makes future uncoordinated pin breaks un-mergeable); plans get longer and cost more
plan-time tokens per task — accepted against the measured 50–75 min per missed task; **the
garbage-bar risk is the real one** — a planner under validator pressure can emit
placeholder criteria that validate green but mean nothing. Mitigations: rider §2.7 (honesty is
*possible*), G2b grading bar **quality** (criteria observability, negative-path honesty) as
eval artifacts, and the F2 authorship lint (§2.5) closing the adjacent self-authorization
channel.

## 4 · Companion edits (on acceptance)

- `REGISTER.md`: file DF-012 row; note it amends the FEAT-SPL-007/008 contract via the §2.8
  procedure (dated correction note, never silent edit — the contract's own rule).
- CONTRACT-feature-spec-plan-outputs.md: Part A/B output inventory gains the sidecar family
  (dated correction note; the re-pin event itself executes per §2.8).
- WS1/WS2 build plans: dated notes assigning the emitter half (WS1) and the schema/B2-lint
  half (WS2); WS2 scope-design §2 F1 field list gains the rider-1 dated note.
- Review backlog: PB-4 → owned; PB-14 → rider 1; ADR-D's batching discipline → rider 2 (this
  record enacts the batching for its own scope whether or not ADR-D is separately filed).

## 5 · Revisit conditions

1. G2b's bar-quality grading shows emitted bars degenerating to placeholders despite rider 1
   → pause emission (revert to attended-authored bars) and revisit criteria-quality bars in
   the contract.
2. The re-pin window proves materially disruptive in practice → revisit the batching cadence
   (not the emission itself).
3. B2 lands with a different provenance mechanism than §2.3 → reconcile there via dated note;
   the invariant (mechanically verifiable committed-before-implementation) is the fixed point,
   not the git incantation.
4. WS2 re-pins the F13 writer elsewhere → §2.4's field guarantee follows the new writer;
   the "plan never renders F13" rule stands.

---

*Drafted 2026-07-08 (P11 follow-up). "The bar exists before the build, and a machine can check both halves of that sentence."*
