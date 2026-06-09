# AC-3 live confirmation — B-full investigating Coach (gemma4:31b / GB10)

> Status: **PENDING operator run.** The deterministic CI leg of AC-3 is landed
> (`tests/integration/orchestrator/test_coach_bfull_falsifier.py`) and is the
> regression guard. This file is the companion **live** leg of the "both"
> decision — a one-off confirmation against the real substrate, which cannot run
> in CI (no GPU). Fill in the Results section after the run.

## Why a live leg at all

The deterministic test proves the *wiring* (gather findings flip an honest
synthesis from approve→feedback). It uses a fake harness, so it does NOT prove
that the **real** gemma4:31b coach, when given Read/Bash/Grep/Glob, actually
investigates and surfaces a stubbed AC. The live leg closes that gap.

## Procedure

1. Seed a falsifier task whose deterministic gates go green but an AC is unmet —
   e.g. a FEATURE task with a primary deliverable stubbed to `return None`, a
   passing-but-vacuous test, and an AC requiring the real behaviour.
2. Run autobuild against it twice on the GB10, holding everything else equal:

   ```bash
   # Leg A — B-min (control): expect APPROVE (rubber-stamp of the green bundle)
   GUARDKIT_COACH_GATHER=0 guardkit autobuild task TASK-<falsifier>

   # Leg B — B-full: expect FEEDBACK (gather investigates, finds the stub)
   GUARDKIT_COACH_GATHER=1 guardkit autobuild task TASK-<falsifier>
   ```

3. Capture, for Leg B, the llama-swap log lines showing **two** g31 calls in the
   Coach turn — a tool-bound gather then a toolless synthesis (this is also
   promotion criterion P-2).

## Results (fill in)

| Leg | `GUARDKIT_COACH_GATHER` | Coach verdict | Two g31 calls observed? | coach_turn_N.json |
|-----|-------------------------|---------------|-------------------------|-------------------|
| A (B-min control) | 0 | _e.g. approve_ | n/a (one call) | `<path>` |
| B (B-full)        | 1 | _e.g. feedback_ | _yes/no_ | `<path>` |

- Divergence confirmed (A approve, B feedback): _yes/no_
- `criteria_verification` populated per AC in Leg B (AC-4): _yes/no_
- Degrade-to-B-min observed on any gather hiccup (P-3): _yes/no / forced via fault injection_

## Notes

- This run also feeds promotion criteria P-1…P-5 in the task's "Flag default +
  promotion criteria" section. A clean Leg B here is one data point toward P-1;
  promotion to default-ON needs ≥2 consecutive green end-to-end runs.
