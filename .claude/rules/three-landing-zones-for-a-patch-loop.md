# Three landing zones for a feature stuck in a patch loop

> **Source**: Decision identified during **TASK-REV-POEX** review of
> **FEAT-POR-EXT** (2026-04-21) and promoted from the retiring Graphiti store
> (FEAT-MEM-09 WS-2b). The originating review lived in the `specialist-agent`
> project, not guardkit — no task file or commit survives in this repo — but the
> decision itself is a guardkit-core feature-build / quality-gate rule.
> Its **corollary** (below) is separately documented in
> [`docs/reviews/TASK-REV-4D012-autobuild-coach-integration-review.md`](../../docs/reviews/TASK-REV-4D012-autobuild-coach-integration-review.md)
> §R4 (Graphiti edge `d3d75a9e`). Companion to
> [`per-task-green-is-not-feature-green.md`](per-task-green-is-not-feature-green.md)
> and the feature-smoke-gate work
> ([`docs/guides/feature-smoke-gates.md`](../../docs/guides/feature-smoke-gates.md),
> [`smoke-gate-is-feedback-not-terminator.md`](smoke-gate-is-feedback-not-terminator.md)):
> those keep a patch loop from *starting*; this rule is the escape menu once one
> already has.

## The rule

When a feature is stuck in a **patch loop** — repeated specialist patches that
each fix a symptom without the feature converging — there are exactly **three**
recoverable landing zones. Pick one deliberately:

- **(a) SHIP THE WORKING SUBSET.** Identify the part that demonstrably works,
  ship it as v1 behind a flag or a scoped tool name, close the feature as "v1
  shipped", and file the broken part as a **new** feature with its own
  architectural review.
- **(b) REDESIGN THE BROKEN PART.** One coherent rethink — *not* another patch.
  Requires a new architectural-review task that produces a design doc; the doc
  is reviewed and accepted; only then does implementation start. Implementation
  is a **single** task, not a cluster of specialist patches, and must carry an
  **integration-gate acceptance criterion**.
- **(c) REVERT THE FEATURE ENTIRELY.** Archive as "tried, not ready", revert to
  pre-feature behaviour, and accept that the motivating need is not addressed by
  this attempt.

**Option (d) "one more patch" is NOT a landing zone** — it is the behaviour to
escape. The three-option menu is a **forcing function**: naming the choice out
loud is what breaks the loop.

## Why this rule exists

FEAT-POR-EXT (a product-owner roadmap-extension feature in the
`specialist-agent` project) entered a patch loop: the Coach kept accepting
iterations while the feature did not actually converge. The TASK-REV-POEX review
recommended **(a)+(b)** — ship Phase A as v1 immediately (Option a), then
redesign Phase B as a delta interaction in a fresh FEAT-POR-EXT-v2 (Option b).
The generalisable output was the decision menu above, applicable to *any*
feature in a patch loop, not just that one.

The same class of failure was analysed independently a few days later in
guardkit's own review [`TASK-REV-4D012`](../../tasks/in_review/TASK-REV-4D012-review-autobuild-coach-integration-gaps.md):
"13 tasks green ≠ feature works" (finding F4), with the PEX-014..020 patch loop
cited as the cost of having no feature-composition gate. That review's
recommendations (feature smoke gates between waves — shipped in
[`TASK-SMK-F703A`](../../tasks/completed/TASK-SMK-F703A/TASK-SMK-F703A.md)) are
the *preventive* side; this rule is the *recovery* side.

### Corollary — Coach needs derived-phase ground truth, not just docs

Any Coach that evaluates a phase **derived** from a prior phase (a schema
consumer, a config consumer, Phase B consuming Phase A's output) must receive
the prior phase's output as **structured Coach input**, not rely on whatever the
current Player echoes. In FEAT-POR-EXT this was the root cause of the Coach
accepting renames: the Phase A stub titles were never piped into the Phase B
Coach input, so the Coach had no reliable source-of-truth to compare against and
semantic drift was undetectable.

This corollary is documented (as a deferred build recommendation) in
[`TASK-REV-4D012`](../../docs/reviews/TASK-REV-4D012-autobuild-coach-integration-review.md)
§R4 ("Coach reads prior-phase outputs for cross-phase validation", Graphiti edge
`d3d75a9e`). **Cite that R4 rather than re-deriving it** — it carries the
`EpicPlan` Phase A→B example and the deferral rationale.

## Symptom

- A feature has been through several specialist patches, each closing one
  Coach/test complaint, without the assembled feature converging.
- The per-task Coach keeps approving (per-task-green) while the end-to-end
  feature is still broken (see
  [`per-task-green-is-not-feature-green.md`](per-task-green-is-not-feature-green.md)).
- The next proposed action is "one more patch" (option d) — the tell that the
  loop has no exit criterion.
- (Corollary variant) A Coach on a derived phase accepts an output that
  contradicts the prior phase's output — because the prior phase's artefact was
  never given to the Coach as structured input.

## Detection recipe

```bash
# 1. This rule + its preventive siblings.
rg -il "landing zone|patch loop|one more patch|forcing function" .claude/rules/ docs/

# 2. The corollary's home (derived-phase Coach input, R4).
rg -n "prior-phase|derived phase|d3d75a9e|structured (Coach )?input" \
   docs/reviews/TASK-REV-4D012-autobuild-coach-integration-review.md

# 3. The preventive side (feature smoke gate between waves).
rg -n "between waves|feature works|smoke" docs/guides/feature-smoke-gates.md
```

## Remediation

1. **Stop patching. Name the three landing zones out loud** (a/b/c) and choose
   one. Refuse option (d).
2. **For (a)**, scope the working subset behind a flag/tool name, close the
   feature, and file the remainder as a new feature *with its own arch review*.
3. **For (b)**, open an architectural-review task first; ship the redesign as a
   single implementation task carrying an integration-gate acceptance criterion
   — do not fan it out into more specialist patches.
4. **For (c)**, revert to pre-feature behaviour and archive honestly.
5. **For the corollary**, when a task derives from a prior task's output, load
   that prior artefact as structured Coach input (per TASK-REV-4D012 §R4) so the
   Coach validates against real ground truth, not the Player's echo.

## Grep-able signature (for next agent)

```bash
# This rule.
rg -l "three landing zones|one more patch.*NOT a landing zone" .claude/rules/
# -> .claude/rules/three-landing-zones-for-a-patch-loop.md

# Corollary cross-reference (must resolve).
rg -n "R4 — Coach reads prior-phase outputs" \
   docs/reviews/TASK-REV-4D012-autobuild-coach-integration-review.md
# -> line 451

# Preventive sibling that shipped (feature smoke gate).
rg -n "smoke gates between autobuild waves" tasks/completed/TASK-SMK-F703A/TASK-SMK-F703A.md
```

## When this rule triggers

- Any time a feature/autobuild run has taken more than one or two corrective
  patches without converging — invoke the menu *before* authorising the next
  patch.
- During a review (`/task-review`, retro) that finds a "green tasks, dead
  feature" pattern.
- Before adding a Coach step that evaluates a phase derived from an earlier
  phase's output — wire the corollary (structured prior-phase input) in from the
  start.

## What it does NOT cover

- **Choosing between (a), (b), and (c)** — that is a judgement call for the
  operator/reviewer; the rule only mandates that the choice be made explicitly
  from those three, never (d).
- **Preventing the patch loop from starting** — that is the feature-smoke-gate /
  composition-gate territory
  ([`per-task-green-is-not-feature-green.md`](per-task-green-is-not-feature-green.md),
  [`docs/guides/feature-smoke-gates.md`](../../docs/guides/feature-smoke-gates.md)).
  This rule is the escape hatch once you are already in one.
- **The mechanical implementation of derived-phase Coach input** — R4 in
  TASK-REV-4D012 is a deferred recommendation, not shipped code; this rule
  records the standing requirement, not a landed feature.
