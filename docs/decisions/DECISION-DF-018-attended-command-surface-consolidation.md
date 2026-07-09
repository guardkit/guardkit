# DECISION-DF-018 — Attended command-surface consolidation (ADR-C): demote and de-friction, don't multiply

**Status:** **CANDIDATE** — drafted 2026-07-09 by the ADR-C/ADR-D decision-drafting Opus session for Rich's per-item accept/amend. **NOT filed in REGISTER.md; no register row flipped.** DF-018 is the next free fleet number (DF-005 is RESERVED, not free). Two of the five items are **already executed** and are ratified retroactively by this record (see §2.1–§2.2); three are live decisions (§2.3–§2.5). Follows the DF-011/DF-012 drafting-then-acceptance precedent (candidates drafted, then flipped ACCEPTED by Rich in `1c674abe`, register rows filed in ai-transition `72e2133`).
**Scope:** the **attended** command surface only (`installer/core/commands/*.md` + one shared completion routine). Nothing headless, no pinned-template bytes, no F1–F5 semantics, no WS3-calibrated autobuild behaviour. Any pinned-byte change a member item implies is deferred to the DF-019 batched re-pin event, never landed here.
**Consumer:** attended Claude Code users (the command list they load); the PB-3 tombstone/prune surface (`install.sh` prune + `guardkit doctor` drift report); WS3 tracker-reconciliation sweeps (bind the /task-complete item); PB-13 wave-1 (binds the template-create item).
**Companions:** DF-011 (the packaging/prune manifest that the tombstone path rides on), DF-012 (its §2.8 batching absorbs any pinned bytes this bundle produces → DF-019), DF-007/DF-009 (the gate/attendance posture the /task-complete tri-state honours), the two executed DECs (`DEC-task-refine-retirement.md`, `DEC-claude-commands-fork-disposition.md`), PB-3 (tombstone mechanism), PB-13 (template-create skills-shaping — the load-bearing interaction in §2.5b).
**Reasoning trail:** `docs/reviews/guardkit-modernization-review-2026-07-08.md` §9 :599-601 (ADR-C listing) + §5 rows PB-17 :575 / PB-18 :576; `ai-transition/docs/guardkit-command-consolidation-review-findings-2026-07-08.md` (the adversarially-reviewed board session); `ai-transition/docs/task-complete-demotion-scope-2026-07-09.md` (§2.3 design); `docs/reviews/template-create-pivot-review.md` (MODIFY) + `docs/reviews/template-create-pivot-review-REVISED.md` (KEEP+SIMPLIFY) (§2.5b adjudication); `tasks/backlog/design-url-integration/TASK-UX-2DAB-deprecate-old-commands.md` (§2.4).

---

## Summary

The attended command surface has accreted commands that are either dead (a phantom-module command, six require-kit-era orphans), high-friction (a two-step to start a review; a separate completion command nobody runs — the documented cause of fleet-wide tracker rot), or over-broad (five arch/design front doors at 5,578 lines; a design-tool trio at 2,319 frozen lines documenting an unimplemented MCP integration; a template quartet with two unexecuted, contradictory pivot verdicts). The consolidation board session (2026-07-08) reached one consistent verdict across all of them: **demote and de-friction the surface, do not multiply it** — remove what is dead, collapse what nobody runs into an evidence-gated auto-path, and adjudicate the template pivot toward *fewer* front doors, not more. This record bundles the five items so they are decided as one coherent surface change rather than five drive-by edits. Two are already done; three need Rich's go/choice.

## 1 · Context — why one bundle

1. **The board session already reached the verdicts.** `guardkit-command-consolidation-review-findings-2026-07-08.md` (6 mapping agents + an adversarial skeptic/designer pass over ~660k tokens) produced the four headline verdicts this record files: retire `/task-refine` outright; **demote** `/task-complete` (don't delete); **de-friction** `/task-review` (don't loop-engineer it); the two-stage friction is the task-create two-step, not the review stage.
2. **The retirement path is paved and the two cheap items already shipped.** PB-2/PB-3's tombstone → DEC note → MANIFEST regen → `install.sh` prune pattern is proven; two items rode it to completion this week. Deciding the remaining three now means they land on the same rails.
3. **Rich's own closing reflection (recorded):** the original design — separate build/analyze commands, review tasks as durable records, deterministic gates feeding LLM judgment — has *stood the test of time*; the loop-engineering vocabulary caught up with the architecture, not the reverse. This bundle is a hygiene pass on a sound design, not a redesign.

## 2 · Decision (five items)

### 2.1 · `/task-refine` — RETIRE. **✅ EXECUTED (fait accompli; ratified here).**

Landed 2026-07-09 (`DEC-task-refine-retirement.md`, ACCEPTED/executed). Zero inbound references; its claimed core module `refinement_handler.py` never existed (markdown-prose-only); everything it did is a subset of `/task-work` (re-run TASK-XXX) or `/task-review` [I]mplement. Spec deleted, tombstoned in the manifest (count 2→3), ~15 live doc references swept, `iterative-refinement-workflow.md` kept as a dated historical record, install-surface prune verified. **No decision remains; this record ratifies it as item 1 of the bundle.**

### 2.2 · `/task-review` ad-hoc self-creating entry — ADD. **✅ EXECUTED (fait accompli; ratified here).**

Landed 2026-07-08 (guardkit `546a82d4`). `/task-review "description"` now self-creates its `TASK-REV-*` record in a deterministic Phase 0 (`guardkit task create --prefix REV --task-type review`; loud failure with a two-step fallback, no silent fallback from a missing id) and proceeds straight into review — collapsing the `task-create → wait → copy-id → task-review` two-step. This is the board's **de-friction** answer, explicitly *not* a loop-engineered review (iteration on an attended, metered path buys cost without verification power; the celebrated review wins were all one-shot panels, not loops). The ID form is unchanged; `feature-plan.md` untouched (pinned `cb440952`). The pre-registered measure is **record-capture rate**, not speed — the ad-hoc entry makes the durable TASK-REV record ~free (DF-008 in miniature: the proof is the product). **No decision remains; ratified as item 2.**

> *Also already handled, en route:* the PB-2 require-kit orphan disposition (6 never-canonical orphans — `execute-tests`, `formalize-ears`, `gather-requirements`, `generate-bdd`, `task-work-specification`, `update-state`) was executed under `DEC-claude-commands-fork-disposition.md` §(c): deleted from the repo-local fork (require-kit owns its canonical copies; re-homing would create a fourth fork). The review §9.3 listed "require-kit orphans dispositioned" as an ADR-C item — it is done; this record does not reopen it.

### 2.3 · `/task-complete` — DEMOTE to a shared atomic routine + task-work auto-finalize. **GO DECISION (recommend GO, phased).**

**The decision:** demote, don't delete. Extract completion's five side-effecting behaviours (atomic status-flip+file-move, related-file archival, Feature→Epic→Portfolio rollup + PM sync, fleet-memory `capture-outcome`, Conductor git-state commit) into **one shared atomic routine** (harden `task_completion_helper.py:complete_task`), called from two entry points: (A) a new task-work **Phase 6 Finalize** gated on a Forge tri-state (green = auto-complete + human *notified-not-gated* via a verify-then-record evidence banner; amber = pause at IN_REVIEW; red = BLOCKED), and (B) a thin `guardkit task complete TASK-XXX` CLI for the flows that structurally cannot auto-complete. Full design: `task-complete-demotion-scope-2026-07-09.md` §2.

**Why GO:** completion is a separate manual command nobody reliably runs, and that is the *documented* cause of fleet-wide tracker rot (hundreds of stale-status files, gap-analysis §4; WS3 §4's worklist exists to reconcile it). The atomic status-flip+file-move IS the WS3-S8 deliverable — this **discharges** it rather than duplicating it. It answers the register's own objection ("a loop calling itself done is making a claim, not offering a proof"): Phase 6 is gated on evidence the implementer did not author, and the IN_REVIEW dwell survives for exactly the amber/red cases where it earns its keep.

**Non-negotiable carve-outs (verified blockers):** NEVER auto-complete in `--autobuild-mode` (feature-build merges *before* completion — auto-completing would record fleet-memory "success" for unmerged, possibly rejected code); NEVER for `operator_handoff` tasks (they never run task-work; the CLI is their path); fail **closed** through `qa.enforce_tier1` (WS2-B2) so the manual lane has an enforcement call site; CoachValidator producer fields stay byte-identical; the Step 3.5/6.5 anchor names stay stable (PB-12).

**Recommended phasing (from the scope §7):** build **Phases 0–2 first** (Phase 0 resolves the two doc-truth discrepancies the scope flags — `in_progress`-vs-IN_REVIEW and the `--implement-only` removed-vs-invoked contradiction — with dated notes, not papered over; extract the routine + CLI; insert Phase 6 behind `--complete` opt-in, capture the §6 baseline metric before flipping any default). **Phase 3** (feature-plan.md operator-handoff text → the new CLI) is a **pinned-byte change → batch into DF-019**, do not pin twice. **Phase 4** (retire the `/task-complete` *slash* surface via tombstone) lands **last**, after the CLI + Phase 6 have soaked. Coordinate with WS3 tracker sweeps (land Phase 1–2 before/between sweeps, not mid-sweep). Size M, Opus @ high.

**The go/no-go for Rich:** approve the demote-don't-delete design and the phased rollout (Phases 0–2 as the first build; Phase 3 deferred to DF-019; Phase 4 last); or hold.

### 2.4 · PB-17 — design-tool trio disposition (`figma-to-react` 739 / `mcp-zeplin` 802 / `zeplin-to-maui` 778 = 2,319 lines). **CHOICE (recommend Option A).**

The trio documents stack-specific design-to-code plus an MCP integration the orchestrator does not implement. `TASK-UX-2DAB` (2025-11-11) already planned deprecating `/figma-to-react` + `/zeplin-to-maui` in favour of the unified `/task-create design:` workflow, with `removal_planned: 2026-06-01` — a date now **lapsed**.

- **Option A — deprecate-then-remove via the PB-3 tombstone path (RECOMMENDED).** Revive TASK-UX-2DAB, **extend it to `mcp-zeplin.md`**, tombstone all three, prune on the next `install.sh`, `guardkit doctor` reports stragglers; removal after one release. *Rationale:* the unified design workflow is the declared replacement; the MCP integration is unimplemented; 2,319 frozen lines is pure carrying cost + duplicate skill registration surface. No live guardkit/installer consumer references them.
- **Option B — keep-as-deprecated.** Mark all three deprecated but keep them functional for backward compatibility (TASK-UX-2DAB's original AC). Lower disruption, but perpetuates the carrying cost and the duplicate-registration surface indefinitely.
- **Option C — retain one, remove two.** Keep whichever has demonstrable live usage (e.g. `figma-to-react`) and remove the other two. Only justified if usage evidence surfaces.

**Recommendation: Option A.** No evidence of a live consumer; the replacement exists; the trio is a frozen relic and the lapsed removal date is the tell. The disposition is a revived, executed TASK-UX-2DAB, not a fresh design.

### 2.5 · PB-18 — command-surface consolidation. **Two sub-decisions.**

#### 2.5a · arch/design cluster: 5 front doors → ≤3. **GO to consolidate; DESIGN sequenced AFTER WS2 qa-format direction (recommend GO-with-fence).**

`arch-refine` / `design-refine` / `system-arch` / `system-design` / `system-plan` = **5,578 lines** across five attended front doors — a cluster a user cannot navigate by name. **Decision:** commit to collapsing to **≤3 front doors**; **record only the target and the sequencing fence here, not the specific merge map.** Per review :576, this is **sequenced AFTER the WS2 qa-format direction settles** — the qa-format direction can reshape what arch/design outputs must carry, so designing the merge before it lands risks a second consolidation. **Recommendation: GO** on the ≤3 target and the WS2-first fence; the concrete merge map is a follow-up design task opened once WS2 qa-format direction is fixed.

#### 2.5b · template quartet: adjudicate MODIFY vs REVISED KEEP+SIMPLIFY. **ADJUDICATION (recommend REVISED KEEP+SIMPLIFY).**

Two unexecuted, contradictory pivot verdicts stand for `/template-create` (the quartet's anchor; quartet = `template-create` 1,539 / `template-create-qa` 351 / `template-init` 924 / `template-qa` 595):

| | **MODIFY** (`template-create-pivot-review.md`, 2025-11-20) | **REVISED KEEP+SIMPLIFY** (`template-create-pivot-review-REVISED.md`, supersedes) |
|---|---|---|
| Keep `/template-create` automation | ✅ | ✅ |
| Simplify orchestrator (remove agent bridge, −40% LOC) | ✅ | ✅ |
| **Add** `/create-template-task` guided command | ✅ (→ **two** workflows) | ❌ (root cause already fixed by TASK-TMPL-4E89; **one** workflow) |
| Grounding | code-analysis + task results | **+ forensic**: the "regression" was a pre-existing agent-detection limitation *already fixed* 2025-01-11 (29/29 tests, 14%→78–100% coverage) — the guided command was solving a problem that no longer existed |

Both agree on keep-and-simplify; they differ only on whether to **add a command**.

**Recommendation: REVISED KEEP+SIMPLIFY (do NOT add `/create-template-task`).** Four reasons: (1) REVISED supersedes MODIFY chronologically and is the more evidence-grounded verdict (the forensic finding removes MODIFY's stated motivation for the guided command); (2) adding a command runs directly against PB-18's own goal of *reducing* front doors and the whole board session's demote-don't-multiply ethos; (3) **the load-bearing interaction — PB-13 wave-1 already restructures `template-create` into a skill** (core <5k tokens + on-demand refs). That skills-shaping **is** the "simplify" both verdicts call for, delivered structurally rather than as a separate agent-bridge-removal LOC project. So the live decision reduces to: adopt REVISED (no new command) and let **PB-13 wave-1 deliver the simplification** — do not run a standalone orchestrator-LOC-surgery task *and* a skills restructure on the same file; make them **one coordinated effort**; (4) it corrects the review's own §9.3 default ("template quartet per the standing MODIFY verdict"), which selected MODIFY before REVISED was weighed. The broader quartet consolidation (the `template-init`/`-qa` overlap; see `template-init-vs-template-create-analysis.md`) follows the same *fold-toward-fewer* ethos as a downstream design question, not by adding surface.

## 3 · Consequences

**Positive:** the attended command list loses its dead and duplicate entries; the two highest-friction surfaces (review start, completion) collapse to one-command / auto-on-green paths, with the durable records preserved; tracker rot gets a structural fix that *discharges* WS3-S8; the template pivot resolves toward one workflow shaped by PB-13, not two; the arch/design cluster gets a committed ≤3 target without pre-committing a merge map WS2 might invalidate.
**Negative / accepted:** the /task-complete demotion is the one M-sized build in the bundle and carries real blockers (all carved out in §2.3); Phase 4 slash-retirement and the arch/design merge map are deferred, so the surface shrinks in stages, not at once; adopting REVISED means the MODIFY verdict's `/create-template-task` is dropped (accepted — its motivation was forensically retired).
**Contract impact: none from this record.** Every pinned-byte change any item implies (task-complete Phase 3 feature-plan.md operator text; any template-create pin touched by PB-13 wave-2) is **deferred to DF-019's single re-pin event** — no re-pin, no G2b re-freeze is triggered by accepting DF-018 itself.

## 4 · Companion edits (on acceptance, per item)

- `REGISTER.md`: file the DF-018 row (guardkit-scoped; body at this path). Note items 2.1/2.2 are already executed.
- Items 2.1/2.2: no edits — already landed (`DEC-task-refine-retirement.md`; `546a82d4`).
- Item 2.3: on GO, the scope doc §8 kickoff prompt runs (Phases 0–2); dated ✅ notes to WS3-S8 build-plan + gap-analysis §4a; Phase 3 registered as a DF-019 member; Phase 4 filed as a follow-up.
- Item 2.4: on Option A, revive TASK-UX-2DAB (extend to `mcp-zeplin`), execute via the PB-3 tombstone path, DEC note.
- Item 2.5a: open the arch/design merge-map design task, fenced behind WS2 qa-format direction.
- Item 2.5b: on REVISED, close the MODIFY verdict with a dated superseded-by pointer; fold the template-create simplification into the PB-13 wave-1 task (one coordinated effort); mark both pivot-review files resolved.

## 5 · Revisit conditions

1. Usage evidence surfaces for a design-tool command → reconsider §2.4 Option A→C for that one command only.
2. The /task-complete §6 baseline metric shows Phase-6 auto-complete *not* reducing stale-IN_REVIEW counts, or the guard metric fires (a completion recorded for an unmerged autobuild branch) → pause the default-flip, keep the CLI, revisit the tri-state.
3. WS2 qa-format direction reshapes arch/design outputs such that ≤3 is the wrong target → revisit §2.5a's number (not the intent to consolidate).
4. PB-13 wave-1 proves unable to carry the template-create simplification within the skill budget → fall back to REVISED's explicit orchestrator-LOC path (agent-bridge removal), still without adding a command.

---

*Drafted 2026-07-09 (ADR-C candidate). "Demote and de-friction the surface; keep the durable records; don't multiply the front doors."*
