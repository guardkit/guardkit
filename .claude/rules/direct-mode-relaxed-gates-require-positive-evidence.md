# Direct-mode relaxed gates still require positive AC/wiring/producer evidence

> **Source**: Seeded by TASK-FIX-DIRECTFG01 (2026-06,
> `tasks/completed/2026-06/TASK-FIX-DIRECTFG01-direct-mode-ac-level-verification.md`)
> from the FEAT-9DDE run-3 blocker; exercised live in the FEAT-9DDE 2026-06-15
> handoff (commit `ddade8548`). Promoted from Graphiti to git by FEAT-MEM-09 WS-2b.
> A member of the absent-signal meta-frame family and the **INVERSE** of
> [`absence-of-failure-is-not-success.md`](absence-of-failure-is-not-success.md);
> reuses the manifest + authored-files scoping from
> [`evidence-boundary-narrower-than-write-surface.md`](evidence-boundary-narrower-than-write-surface.md).

## The rule

In autobuild's `implementation_mode=direct`, relaxing quality gates to
`required=False` (for test/coverage thresholds) is legitimate — direct mode trusts
the Player on "simple" tasks — but that relaxation **must NOT extend to assuming
acceptance-criteria delivery**. A binary `APPROVE` with **no positive AC-level /
wiring / producer evidence** behind it is a false-green.

Pair the deliberate gate relaxation with a **positive-evidence precondition**: a
deterministic gate that runs in **both** Coach paths, **after** the evidence-repo
gate and **before** the LLM Coach, and blocks the turn (feedback, not approve)
when the positive evidence is absent. The block must be **deterministic at the
orchestrator layer** — never delegated to the LLM Coach's leniency (relying on the
model to honour an in-bundle partial-gate abort re-opens the false-green, the same
lesson the evidence-repo gate learned in BDDW-002).

## Why this rule exists

**2026-06 — FEAT-9DDE run-3.** A direct-mode task (TSJ-002) was `APPROVE`d with a
**non-functional bin-entry wrapper** (it raised `ModuleNotFoundError` and emitted
no JSON) and an unmet acceptance criterion. The relaxed gates waved it through; the
defect was caught only by later on-disk verification. A local-coder Player on a
"simple" task makes plausible-but-spec-violating choices, and relaxed gates have no
positive-evidence floor to stop them.

The fix is `_direct_mode_evidence_gate`
([`autobuild.py:6387`](../../guardkit/orchestrator/autobuild.py#L6387)), invoked in
**both** Coach paths
([`autobuild.py:5912`](../../guardkit/orchestrator/autobuild.py#L5912) and
[`autobuild.py:6147`](../../guardkit/orchestrator/autobuild.py#L6147)), which blocks
the turn via `_emit_synthetic_coach_feedback`
([`autobuild.py:6095`](../../guardkit/orchestrator/autobuild.py#L6095)) when:

- **AC1** — an acceptance criterion has no disk/promise evidence behind it.
- **AC2** — a registered authored bin-entry is UNWIRED.
- **AC3** — a registered authored CLI producer raises on `python <path>`
  (traceback / non-zero-exit-with-empty-stdout / timeout = an **ABSENT** producer
  signal).

The registered-bin-entry set comes from the `bin-entries.txt` manifest via
`_read_bin_entries`
([`autobuild.py:615`](../../guardkit/orchestrator/autobuild.py#L615)) — the same
manifest + authored-files scoping the evidence-boundary work established.

## Meta-frame

This is the absent-signal family's **direct-mode-relaxation** member — the inverse
of `absence-of-failure-is-not-success`:

| Rule | Spurious "no signal" comes from… | Direction |
|---|---|---|
| `absence-of-failure-is-not-success` | a zero counter read as a pass when zero attempts ran | false-green |
| **`direct-mode-relaxed-gates-require-positive-evidence`** | **a deliberate gate relaxation read as "AC delivery confirmed"** | **false-green** |

Both pair a binary verdict with a positive-evidence precondition. There the
precondition is `count_attempted > 0`; here it is *an AC has disk/promise evidence,
its bin-entry is wired, and its producer runs*.

## Symptom

- A direct-mode (`implementation_mode=direct`) task is `APPROVE`d while an
  acceptance criterion is unmet, or a shipped bin-entry/CLI producer does not run
  (`ModuleNotFoundError`, empty stdout, traceback) when invoked standalone.
- The Coach verdict shows relaxed (`required=False`) test/coverage gates and no
  AC-level / wiring / producer evidence.

## Detection recipe

```bash
# 1. The deterministic gate must run in BOTH Coach paths, after the evidence-repo
#    gate, before the LLM Coach. MUST MATCH.
rg -n "_direct_mode_evidence_gate" guardkit/orchestrator/autobuild.py       # def + 2 call sites

# 2. It must block via synthetic feedback (deterministic), not LLM judgement.
rg -n "_emit_synthetic_coach_feedback" guardkit/orchestrator/autobuild.py

# 3. Registered bin-entries come from the manifest (shared with evidence-boundary).
rg -n "_read_bin_entries|bin-entries.txt" guardkit/orchestrator/autobuild.py

# 4. A direct-mode APPROVE path that does NOT call _direct_mode_evidence_gate is the
#    hazard — every direct-mode Coach path must gate.
```

## Remediation

1. **Run the gate in every Coach path.** A direct-mode approve path that skips
   `_direct_mode_evidence_gate` re-opens the false-green.
2. **Keep the block deterministic.** Emit synthetic feedback from the orchestrator;
   do not delegate the partial-gate abort to the LLM Coach's leniency.
3. **AC3 producer execution is stack-aware by necessity** (per
   [`stack-plugin-architecture.md`](stack-plugin-architecture.md)): it *runs* Python
   entries and degrades non-Python entries to a non-blocking advisory — never crash,
   never false-pass.
4. **Run the producer with a clean worktree-only `PYTHONPATH`** (per
   [`namespace-hygiene.md`](namespace-hygiene.md)) as a subprocess — never import it —
   so guardkit's own installed `src` cannot mask the producer's missing import.

## Grep-able signature (for next agent)

```bash
rg -n "def _direct_mode_evidence_gate" guardkit/orchestrator/autobuild.py    # -> 6387
rg -n "_direct_mode_evidence_gate\(" guardkit/orchestrator/autobuild.py      # both Coach paths
rg -n "def _read_bin_entries" guardkit/orchestrator/autobuild.py            # -> 615
rg "direct-mode-relaxed-gates|absence-of-failure|evidence-boundary-narrower" .claude/rules/
```

## When this rule triggers

- Before relaxing any quality gate for a mode/task-type — pair the relaxation with a
  positive-evidence precondition, do not let it imply AC delivery.
- Before adding a new direct-mode Coach path — it MUST call
  `_direct_mode_evidence_gate`.
- During Phase 2.5 architectural review for anything touching direct-mode gating,
  `_direct_mode_evidence_gate`, `_emit_synthetic_coach_feedback`, or the
  `bin-entries.txt` manifest.

## What this rule does NOT cover

- The gate-relaxation itself — relaxing test/coverage thresholds in direct mode is
  the deliberate, correct behaviour; this rule only forbids letting it imply AC
  delivery.
- Non-Python bin-entries — AC3 degrades them to a non-blocking advisory (accepted
  false-negative, per `stack-plugin-architecture.md`).
- The full-mode (non-direct) Coach path — that path already runs the standard gates;
  this rule governs the *relaxed* direct-mode path.

## Prior art

- **Inverse rule (false-green, zero-count)**:
  [`absence-of-failure-is-not-success.md`](absence-of-failure-is-not-success.md).
- **Shared manifest / authored-files scoping**:
  [`evidence-boundary-narrower-than-write-surface.md`](evidence-boundary-narrower-than-write-surface.md)
  (the gate reuses `bin-entries.txt` + authored-files scoping).
- **Stack-aware execution**:
  [`stack-plugin-architecture.md`](stack-plugin-architecture.md).
- **Clean-PYTHONPATH subprocess**:
  [`namespace-hygiene.md`](namespace-hygiene.md).
- **Assembly-aperture sibling**:
  [`per-task-green-is-not-feature-green.md`](per-task-green-is-not-feature-green.md).
- **Originating fix**: TASK-FIX-DIRECTFG01, task at
  `tasks/completed/2026-06/TASK-FIX-DIRECTFG01-direct-mode-ac-level-verification.md`;
  motivated by FEAT-9DDE run-3 (TSJ-002).
