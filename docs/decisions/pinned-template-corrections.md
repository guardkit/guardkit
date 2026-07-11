# Pinned-contract correction ledger (guardkit-side mirror)

> **What this is.** The lockstep, guardkit-side record required by the
> pinned-files CI gate (`.github/workflows/pinned-files-gate.yml`). Any change to
> a file in [`PINNED-FILES.txt`](PINNED-FILES.txt) — the six FEAT-SPL-007/008
> output-contract artifacts — must add a **dated entry here in the same diff**, or
> CI goes red and the change is un-mergeable.
>
> **Why a mirror.** guardkit CI cannot read the specialist-agent repo, so it
> cannot verify a correction note in that repo's contract doc
> (`docs/design/contracts/CONTRACT-feature-spec-plan-outputs.md` §0). This ledger
> is the guardkit-side mirror the gate *can* verify. The authoritative re-pin
> still lives in specialist-agent (the `TemplatePin` sha256 + the contract §0
> dated note); this file records the guardkit half so the two move together.
>
> **The procedure a byte change triggers (G2b re-freeze, DF-012 / ADR-D).** A
> change to a pinned template is not an ordinary edit — it is a coordinated,
> batched re-pin event:
>
> 1. dated correction note in the specialist-agent contract doc §0;
> 2. re-run the feature-YAML round-trip fixtures (expected unchanged — run to prove);
> 3. Session C re-pins the `TemplatePin` sha256 (feature-spec 79a6c306… / feature-plan cb440952…);
> 4. Rich approves the G2b / FEAT-EVAL-SPEC re-freeze;
> 5. add the dated entry below.
>
> Batch every pinned-byte change (format_version phase 2, anchor de-dup, template
> split, assumptions-ledger edits) into ONE re-pin event — never four.

## Correction entries

<!-- Newest first. One entry per coordinated pin change. Format:
### YYYY-MM-DD — <what changed> (<pinned file(s)>)
- specialist-agent re-pin commit / contract §0 note: <ref>
- G2b re-freeze: <approved-by / ref>
- reason: <one line>
-->

### 2026-07-11 — DF-019 re-pin window: PB-4 emission text + PB-10 phase 2 + DF-018 Phase 3 (feature-spec.md, feature-plan.md)
- specialist-agent re-pin commit / contract §0 note: the DF-019 window correction note in
  specialist-agent `docs/design/contracts/CONTRACT-feature-spec-plan-outputs.md` §0 (dated
  2026-07-11), enumerating every byte change in the batch. Both content-hash pins re-pinned in
  `src/specialist_agent/templates/pins.py` (Session C):
  `feature-spec.md` `79a6c306…` → `f1bd5e60…` (937 → 947 lines, git-commit pin `ce914f7c` → this window's guardkit commit);
  `feature-plan.md` `cb440952…` → `6e4c87b9…` (2910 → 2925 lines, git-commit pin `5ad48fcf` → this window's guardkit commit).
- G2b re-freeze: Rich's in-window go/no-go is step 6 of the runbook (attended window
  2026-07-11); this ledger entry rides steps 2→4 and is reverted verbatim with the batch if
  Rich declines (plan §2 rollback). Approval recorded in the plan doc + WS1 §4 on GO.
- reason: the ONE DF-019 coordinated re-pin event (DF-012 / ADR-D). Members riding: **PB-4**
  emission-step text (the F1 per-task pass-bar + the feature-grain seed + F3 leak-sweep + the
  F13 guarantee the FEAT-DF12 emitter already writes — `9e47101`); **PB-10 phase 2**
  (`format_version: 1` frontmatter on both templates + hygiene-test flip); **DF-018 Phase 3**
  (feature-plan.md operator text `/task-complete` → `guardkit task complete`, feature-complete
  wiring is the unpinned code half). **JOIN-1** (glue/wiring oracle) landed ahead at `a493bdc9`
  (paired below). **PB-5** anchor de-dup = inspected, **zero bytes** — the duplicate `## §4:
  Integration Contracts` headings sit inside marked Template/Example fences; a fence-aware lint
  does not see them as document anchors. **PB-13 wave-2 + PB-15** = DEFERRED (no design exists;
  a future one is its own window).

### 2026-07-11 — JOIN-1: glue/wiring TaskType class added to the oracle (guardkit/models/task_types.py)
- specialist-agent re-pin commit / contract §0 note: RIDES THE DF-019 WINDOW — per the plan of
  record (specialist-agent `docs/design/df012-emitter-delta-repin-plan-2026-07-11.md` §4
  JOIN-1: "its CONTRACT §0 `task_type` pin + round-trip re-run ride this window"). The §0
  task_type pin update + fixtures re-run land with the window's correction note.
- G2b re-freeze: n/a for this entry (oracle code, not template bytes; templates verified
  byte-identical at `a493bdc9`: `79a6c306…` / `cb440952…`). The window's re-freeze covers the
  batch.
- reason: ADDITIVE enum + strict QualityGateProfile per DF-016 §6(a) (accepted, binding),
  landed ahead of the window so DFEM-013's oracle-green glue cutover has its target
  (guardkit `a493bdc9`, 24 tests). This entry pairs that commit retroactively — the
  pinned-files gate correctly went RED on `a493bdc9` because the pairing was missed; filed
  by the board 2026-07-11.

_Prior state: pinned bytes unchanged since the contract was pinned
(specialist-agent `e1081aa`; templates `ce914f7c` / `5ad48fcf`). DF-011's
packaging change is additive and touched **zero** pinned bytes — no entry
required._
