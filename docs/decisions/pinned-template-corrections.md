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

_None yet. The pinned bytes are unchanged since the contract was pinned
(specialist-agent `e1081aa`; templates `ce914f7c` / `5ad48fcf`). DF-011's
packaging change is additive and touched **zero** pinned bytes — no entry
required._
