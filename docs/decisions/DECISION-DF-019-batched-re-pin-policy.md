# DECISION-DF-019 — Batched re-pin policy for pinned-template byte changes (ADR-D): one coordinated re-pin event, not N tool-down windows

**Status:** **ACCEPTED — by Rich, 2026-07-09** (in-session, on the ADR-C/ADR-D decision cards). Filed in REGISTER.md (ai-transition). **Rich's recorded rationale:** accepted as recommended — one coordinated re-pin event beats N specialist-tool-down windows. DF-019 follows DF-018 in the fleet numbering (DF-005 RESERVED, not free). This record **generalizes DF-012 rider 2 (§2.8)** — which already binds this batching *within DF-012's own emission scope* "whether or not ADR-D is separately filed" — into a **standing policy** covering every current and future pinned-template byte change, not just DF-012's F1-sidecar emission items.
**Scope:** the **cadence and procedure** for changing the bytes of the pinned FEAT-SPL-007/008 output-contract templates (`installer/core/commands/feature-spec.md`, pin `79a6c306…`; `installer/core/commands/feature-plan.md`, pin `cb440952…`). This record **changes no byte itself** — it decides that all pending and future byte changes accumulate into **one** coordinated re-pin/re-freeze event instead of landing piecemeal. Fleet-relevant (Session C re-pins; G2b re-freezes).
**Consumer:** Session C template loader (re-pins the two sha256s); G2b / FEAT-EVAL-SPEC (re-freezes eval seeds to grade the new bytes); WS1 emitter sessions (PB-4); the PB-3 pinned-files CI gate (enforces the dated-correction-note discipline on any PINNED-FILES commit); any future session proposing a pinned-template edit.
**Companions:** DF-012 (rider 2 / §2.8 is the seed this promotes to policy; DF-012 enacts the batching for its own scope already), DF-011 (packaging; unaffected — additive, no re-pin), DF-018 (its /task-complete Phase 3 feature-plan.md operator-handoff text is a member of this event), PB-3 (the CI gate that makes future *uncoordinated* pin breaks un-mergeable), `CONTRACT-feature-spec-plan-outputs.md` (the amend target + the procedure's source-of-record).
**Reasoning trail:** `docs/reviews/guardkit-modernization-review-2026-07-08.md` §9 :602-606 (ADR-D listing) + §5 rows PB-10 :569, PB-5 :564, PB-13 :571, PB-15 :573, PB-4 :563 (each row's "re-pin impact" column names this event); `DECISION-DF-012-...md` §2.8 (rider 2, the binding seed).

---

## Summary

The FEAT-SPL-007/008 output contracts are refusal-pinned by content hash: every byte edit to `feature-spec.md` / `feature-plan.md` is a **separate specialist-tool-down window** (dated correction note → round-trip fixtures re-run → Session C re-pin → G2b re-freeze → Rich approval). Five-plus pending items each want to touch those bytes — format_version phase 2, the Integration-Contracts anchor de-dup, any PB-13 wave-2 pinned split, the assumptions-ledger template edit, and PB-4's emitter-half edits (plus DF-018's /task-complete Phase 3 operator text). Landed one at a time, that is five-plus tool-down windows and five-plus G2b re-freezes for what is one logical migration. This record makes the batching a **standing policy**: all pinned-byte changes accumulate into **ONE** coordinated event, the procedure and its cost are stated **once**, and the PB-3 CI gate makes any out-of-band pin break un-mergeable. DF-012 rider 2 already commits its own emission scope to this; DF-019 generalizes the commitment to the whole set.

## 1 · Context — why one event, why a standing policy

1. **The pin is a refusal contract, not a preference.** The two templates are content-hash-pinned; Session C refuses a mismatched byte. So a byte change is never "just an edit" — it is a coordinated re-pin across guardkit (edit), Session C (re-pin), and fleet-evals/G2b (re-freeze the seeds that grade the bytes), gated on Rich.
2. **The pending byte changes are already enumerated** (each modernization-review row carries its re-pin verdict in its own "impact" column): they are known, finite, and mostly independent — exactly the shape that batches cleanly.
3. **DF-012 already proved the batching for its slice** and, in rider 2, explicitly said it "enacts the batching for its own scope whether or not ADR-D is separately filed." DF-019 is that separate filing — promoting a one-decision rider into a policy so the *next* pinned-byte proposal (foreseen or not) inherits the discipline instead of re-litigating it.
4. **The CI backstop exists.** PB-3's pinned-files CI gate requires the dated correction note on any PINNED-FILES commit — so an uncoordinated, out-of-band pin break is *un-mergeable*, which is what makes a batched cadence safe to mandate rather than merely recommend.

## 2 · Decision

1. **One coordinated re-pin event.** All byte changes to the pinned templates accumulate and land together. The current membership (the "when the window opens, everything in it ships") is:
   - **PB-10 phase 2** — `format_version` frontmatter on the **two PINNED** templates. (Phase 1 — the 26 unpinned specs — already shipped, guardkit `1b89804d`; the pinned two were deliberately excluded from phase 1 to wait for this event.)
   - **PB-5 anchor de-dup** — fix the colliding "Integration Contracts" normative anchors in `feature-plan.md` (the report-only structure lint already ships, guardkit `ec1a5124`; the *fix* is the byte change and belongs here — the lint names the surface, this event corrects it).
   - **PB-13 wave-2** — any pinned-template split from the skills-shaped restructure (wave-1 is unpinned attended heavyweights; only wave-2 touches pinned bytes).
   - **PB-15** — the plan-side assumptions-ledger template edit (the sibling-manifest addition on the guardkit template side).
   - **PB-4 emitter half** — the F1-sidecar / F3-surface-claims / `registered_at` emission steps added to `feature-spec.md` + `feature-plan.md`, **plus** the contract correction note (this is DF-012's own scope; it is the anchor tenant of the event).
   - **DF-018 /task-complete Phase 3** — the operator-handoff text in `feature-plan.md` pointing at the new `guardkit task complete` CLI (per DF-018 §2.3; "do NOT let this build pin twice").
2. **The procedure — stated ONCE, applied to the whole batch:**
   1. **Dated correction note** in `CONTRACT-feature-spec-plan-outputs.md` (never a silent edit — the contract's own rule) enumerating every byte change in the batch;
   2. **Round-trip fixtures re-run** (synthesize→transcribe / render→parse) — expected unchanged for structure-preserving edits; *run to prove it*, don't assume;
   3. **Session C re-pins** both sha256s (`79a6c306…` / `cb440952…`) to the new content;
   4. **G2b re-freezes** the FEAT-EVAL-SPEC seeds (extended to grade any newly-emitted artifacts, e.g. PB-4's bars);
   5. **Rich approves** the re-freeze.
   One specialist-tool-down window; one G2b re-freeze.
3. **The cost — stated ONCE:** exactly **one** bounded, scheduled tool-down window and **one** G2b re-freeze for the entire batch, versus one-each if the items land separately. The PB-3 CI gate makes any future *uncoordinated* pin break un-mergeable, so the batched cadence is enforceable, not merely advisory.
4. **Membership is open until the window opens.** Any *new* pinned-byte proposal that arises before the event fires joins the batch by default (that is the policy). A proposal that genuinely cannot wait for the scheduled window is the explicit exception path (§5 revisit condition 2), not the norm.
5. **Additive/non-pinned work does not gate on this event.** Report-only lints, unpinned-spec edits, sidecars written into the *target repo's* qa/, and packaging (DF-011) are byte-unchanged for the pinned templates and land on their own cadence — this policy governs only edits to the **pinned bytes** themselves.

## 3 · Consequences

**Positive:** one tool-down window and one G2b re-freeze instead of five-plus; the contract's evolution is legible (one dated correction note enumerating the whole migration, not five scattered ones); the emission contract (PB-4/DF-012), the format_version completion (PB-10), the anchor hygiene (PB-5), and the ledger/split edits all arrive coherent and co-validated; every future pinned-byte proposal inherits a decided cadence.
**Negative / accepted:** items wait for the window — an item ready early sits until the batch fires (accepted: the window is bounded and scheduled, and the wait is cheaper than an extra re-freeze); the batch has a coordination surface (Session C + fleet-evals + Rich must align once) — but once, not five times.
**Relationship to DF-012:** DF-012 rider 2 remains binding within its own scope and is *not* superseded — DF-019 widens the same rule to the full membership set and to future proposals. If DF-019 is declined, DF-012 rider 2 still enacts the batching for the PB-4 emission items alone; the other members would then each need their own window (the outcome this record exists to prevent).

## 4 · Companion edits (on acceptance)

- `REGISTER.md`: file the DF-019 row (fleet-scoped cadence policy; body at this guardkit path, indexed in the register).
- `CONTRACT-feature-spec-plan-outputs.md`: add a pointer that pinned-byte edits follow the DF-019 batched procedure (the note itself is written when the window opens, per §2.2.i).
- Modernization-review rows PB-10 / PB-5 / PB-13 / PB-15 / PB-4 and DF-018 §2.3 Phase 3: dated cross-reference marking each as a DF-019 event member.
- WS1/WS2/WS4 build plans: dated note that the pinned-byte halves of their items land in the single DF-019 window (WS4 §9 row S12 — "PB-5 consumption, gated on ADR-D anchor de-dup + E1 re-pin" — already anticipates this).

## 5 · Revisit conditions

1. The re-pin window proves materially disruptive in practice (blocks too many items for too long) → revisit the *cadence* (e.g. two scheduled windows a quarter), not the batching principle.
2. A single pinned-byte change is genuinely time-critical and cannot wait for the scheduled window → the explicit exception: run a one-item event through the full §2.2 procedure, with Rich's sign-off that the extra re-freeze is warranted. This is the escape hatch, not the default.
3. The pinning mechanism itself changes (e.g. Session C moves from content-hash refusal to a versioned-schema contract) → this policy's *procedure* follows the new mechanism; the batching intent (don't pay the coordination cost N times) survives.
4. G2b re-freeze becomes zero-cost/automated → the batching pressure drops, but the single-dated-correction-note legibility benefit stands.

---

## 6 · First execution — the 2026-07-11 window (dated note)

The policy ran for the first time on **2026-07-11** (attended, Rich's in-session go/no-go). The
plan of record (specialist-agent `df012-emitter-delta-repin-plan-2026-07-11.md`) added, and this
window **exercised**, the one thing the canonical §2.2 procedure lacked: an **explicit rollback
path**. Because §2.2 puts Rich's approval *last* (step 6), after the Session C re-pin (step 4),
the plan pinned the recovery for a NO: revert the Session C content-hash pins to
`79a6c306…`/`cb440952…`, revert the guardkit step-2 pinned-byte commits + the §0 git-commit pins,
and hold the G2b re-freeze — tools reopen on the OLD contract, batch re-queues. In practice the
whole batch was staged **locally, unpushed**, so a NO would have been a clean local reset (no
public revert-commits); Rich gave GO, so the batch shipped (guardkit `95ea3e08`, specialist-agent
`6684222`, fleet-evals `557d6f9`; pinned-files gate green; 0 net-new). **Members shipped in ONE
event:** PB-4 emission text · PB-10 phase 2 · DF-018 Phase 3 · JOIN-1 (landed ahead `a493bdc9`) ·
PB-5 (inspected → zero bytes). **Deferred (undesigned):** PB-13 wave-2 · PB-15 — each a future
window per §5. The policy held: one correction note, one re-freeze, one tool-down.

---

*Drafted 2026-07-09 (ADR-D candidate). "Every pinned byte pays the coordination cost once — the window opens, everything in it ships, the seeds re-freeze once."*
