# DEC — Env-var overrides split around the `INTENSITY_OVERRIDES` merge in `load_adversarial_config`

**Status:** ACCEPTED (implemented) · **Date:** 2026-04-18 · **Task:** TASK-LCL-012 · **Commit:** `dbc47bc5`

## Context

The `langchain-deepagents-weighted-evaluation` template lets consumers tune three
runtime knobs via env vars — `ADVERSARIAL_INTENSITY` (full | light | solo),
`ACCEPTANCE_THRESHOLD` (0.0–1.0), and `MAX_RETRIES` (positive int). TASK-LCL-012
(FEAT-LTL1 Wave 3, from the TASK-REV-LES1 review §MEDIUM-3) added the
`.env.example.template` surface documenting these vars and wired them through
`config/adversarial_config.py::load_adversarial_config()`.

The wiring cannot be a single override block, because the three vars target two
different layers of the merge. `ADVERSARIAL_INTENSITY` is *config-selection* input:
it decides which `INTENSITY_OVERRIDES` bucket (`full` / `light` / `solo`) gets
deep-merged into the config. `ACCEPTANCE_THRESHOLD` and `MAX_RETRIES` are *leaf
values* — and the `solo` bucket deliberately sets `acceptance_threshold: 0.0`
(auto-accept everything, `adversarial_config.py:89`) and `max_retries: 0`. A naive
"apply all env overrides in one place" would have to pick a side: apply them all
before the bucket merge and the solo bucket clobbers an operator's explicit
`ACCEPTANCE_THRESHOLD=0.8`; apply them all after and the intensity env var arrives
too late to select the right bucket.

## Decision

Split the env overrides into two stages around the `INTENSITY_OVERRIDES` merge in
`load_adversarial_config()`:

1. Read `ADVERSARIAL_INTENSITY` **before** bucket selection, so the correct
   `INTENSITY_OVERRIDES` preset is chosen.
2. Apply `ACCEPTANCE_THRESHOLD` and `MAX_RETRIES` **after** the bucket merge, so an
   explicit shell value wins over the intensity preset (e.g. `ACCEPTANCE_THRESHOLD=0.8`
   beats solo mode's `0.0`).

## Rationale

The ordering is dictated by what each var affects. An env var that drives
*downstream merge selection* must be read before the merge or its effect is lost; an
env var that targets a *merged value* must be applied after the merge or the merge
overwrites it. Collapsing both into one block forces an incorrect precedence for one
of the two var classes — precisely the solo-mode clobber the two-stage split avoids.

Generalised: **env vars that select which config gets merged go before the merge;
env vars that set final config values go after it.** This is the canonical shape
whenever a single override source feeds both selection logic and leaf values.

## Consequences / Implementation

In `installer/core/templates/langchain-deepagents-weighted-evaluation/config/adversarial_config.py`,
inside `load_adversarial_config()` (`:96`):

- **Stage 1 — intensity, pre-bucket** (`:137-138`): `if _env_intensity :=
  os.environ.get("ADVERSARIAL_INTENSITY"): config["intensity"] = _env_intensity`,
  immediately before `overrides = INTENSITY_OVERRIDES.get(intensity, {})` and its
  `_deep_merge` (`:142-143`).
- **Stage 2 — leaf knobs, post-bucket** (`:147-150`): `ACCEPTANCE_THRESHOLD` (coerced
  `float`) and `MAX_RETRIES` (coerced `int`) applied after the bucket merge, so shell
  wins over the preset.
- The two inline comments (`:135-136`, `:145-146`) state the ordering contract in
  place.
- The `solo` bucket that motivates stage 2's ordering is `INTENSITY_OVERRIDES["solo"]`
  (`:87-92`), notably `acceptance_threshold: 0.0` (`:89`).

Regression coverage in
`installer/core/templates/langchain-deepagents-weighted-evaluation/tests/test_scaffold.py`,
class `TestAdversarialConfig` (`:422`):

- `test_env_override_intensity_selects_bucket` (`:466`) — intensity env var picks the
  `light` bucket (`max_retries == 1`), proving stage-1 ordering.
- `test_env_override_acceptance_threshold` (`:460`) / `test_env_override_max_retries`
  (`:474`) — leaf overrides land.
- `test_env_threshold_beats_solo_intensity` (`:480`) — the load-bearing precedence
  case: `ADVERSARIAL_INTENSITY=solo` + `ACCEPTANCE_THRESHOLD=0.8` yields
  `acceptance_threshold == 0.8`, not the bucket's `0.0`.

The documented surface is
`installer/core/templates/langchain-deepagents-weighted-evaluation/templates/other/other/.env.example.template`
(`ACCEPTANCE_THRESHOLD`, `ADVERSARIAL_INTENSITY`, `MAX_RETRIES`).

## References

- **Task:** `tasks/completed/TASK-LCL-012/TASK-LCL-012.md`
- **Commit:** `dbc47bc5157392496ccf0ee55961bad19032f0f3` — "Apply lessons learned from
  the specialist agent to the templates" (added the task file, the two-stage env
  wiring, and the tests together).
- **Review:** `.claude/reviews/TASK-REV-LES1-review-report.md` (§MEDIUM-3 — the
  weighted-eval env-override surface this task closed).
- **Sibling record (same commit / feature family):**
  `docs/decisions/DEC-load-config-empty-dict-preserves-precedence-attribution.md`
  (TASK-LCL-006 — the orchestrator template's env > yaml > default precedence chain).
