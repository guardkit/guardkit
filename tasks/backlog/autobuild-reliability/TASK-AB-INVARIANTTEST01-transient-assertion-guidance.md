---
id: TASK-AB-INVARIANTTEST01
title: Transient-assertion ("invariant-not-snapshot") guidance in Player prompts, Coach check, and feature-plan specs
status: backlog
created: 2026-07-04T09:37:00Z
priority: medium
tags: [autobuild, player-prompt, coach, feature-plan, boundary-tests, transient-assertions]
complexity: 4
source: docs/retro/autobuild-retro-xref-2026-07-04.md
---

# Task: Transient-assertion ("invariant-not-snapshot") guidance — three Player-prompt locations + Coach check + plan guidance

> **Implementation in progress 2026-07-04 (same session that filed this task); this
> file is the tracking record.**

## Description

Sourced from the 2026-07-04 retro cross-reference, §5 item 13 (R3 —
study-tutor "self-defeating boundary tests").

In R3, an early task authored boundary tests that pinned a *point-in-time*
state (e.g. asserting a method raises `NotImplementedError`) that a later
task in the SAME feature was specified to implement. When the later task did
its job, the earlier task's test correctly went red — a self-defeating test
by construction. Verified: **nothing anywhere** (Player prompt,
autobuild-player.md, Coach guards, task templates) discourages transient
point-in-time assertions — 0 hits for NotImplementedError/transient/
invariant guidance across the tree.

This fix is **prompt-only by necessity**: there is no cheap structural bound
that can distinguish "asserts a durable invariant" from "asserts a
snapshot of scaffolding state" (xref §5 item 13). Per
`structural-defence-beats-prompt-instruction`, when no structural lever
exists, the prompt instruction is the legitimate lever — but it must be
paired with monitoring: the TASK-AB-STALEATTRIB01 authorship join is that
monitor (it detects when the guidance was ignored, by attributing the red
test to its authoring task).

Three deliverables:

1. **Player-prompt guidance in three locations** (per
   `player-prompt-reinforce-coach-constraint-in-three-locations`): the
   workflow step that writes tests, the anti-patterns table (quoting the
   Coach's detection wording verbatim), and a grounding-principle paragraph
   ("test invariants, not snapshots of scaffolding state").
2. **The matching Coach-side check** (advisory wording in the Coach prompt /
   review criteria that names the anti-pattern in the same terms).
3. **`/feature-plan` task-spec guidance to name boundaries negatively**:
   "never assert `NotImplementedError` (or any not-yet-implemented marker)
   for a method a later task in THIS feature implements". Per xref §7 this
   is arguably a fourth feature-plan defect class alongside the three in
   `docs/guides/feature-plan-task-classification.md`.

## Acceptance Criteria

- [ ] AC-001: The autobuild Player prompt carries the transient-assertion
      rule in **three distinct locations**: (1) the test-writing workflow
      step; (2) the anti-patterns table, quoting the Coach's detection
      wording verbatim; (3) a grounding-principle paragraph explaining why
      (later tasks in the same feature will implement scaffolded
      boundaries).
- [ ] AC-002: The Coach side names the same anti-pattern in the same wording
      (so Player and Coach converge on terminology), as an **advisory**
      review criterion — it does not join the turn-rejecting set.
- [ ] AC-003: `/feature-plan` spec guidance (planner prompt/templates and
      `docs/guides/feature-plan-task-classification.md`) instructs specs to
      name boundaries **negatively**, with the concrete example: "never
      assert NotImplementedError for a method a later task in THIS feature
      implements". The guide gains the fourth plan-defect class.
- [ ] AC-004: Wording explicitly does NOT contradict `anti-stub.md`: stub
      *implementations* in scaffold tasks remain legitimate; the rule
      targets *tests that pin those stubs* as permanent behaviour. The two
      documents cross-reference each other.
- [ ] AC-005: The guidance names TASK-AB-STALEATTRIB01's authorship join as
      the monitor for non-compliance (prompt-only levers need monitoring per
      `structural-defence-beats-prompt-instruction`).
- [ ] AC-006: Grep-able check: the three Player-prompt locations and the
      Coach wording share a distinctive token (e.g. "invariant-not-snapshot")
      so a future audit can verify all locations are present with one `rg`.

## Implementation Notes

Surfaces (from xref §3 R3 + repo conventions):

- Player prompt: `installer/core/agents/autobuild-player.md` and/or the
  focused prompt builder `AgentInvoker._build_player_prompt`
  (`guardkit/orchestrator/agent_invoker.py`) — put the rule where the Player
  re-reads on feedback turns (all three locations, per the rule).
- Coach side: `installer/core/agents/autobuild-coach.md` and/or
  `AgentInvoker._build_coach_prompt` — advisory criterion only.
- Plan guidance: `/feature-plan` task-spec generation
  (`installer/core/commands/feature-plan.md`, planner templates) +
  `docs/guides/feature-plan-task-classification.md` (add the fourth class).
- Evidence of the gap: 0 hits for
  `NotImplementedError|transient|invariant` guidance across Player prompt,
  autobuild-player.md, Coach guards, and task templates (xref §3 R3).

## Regression constraints

From xref §5/§6 — load-bearing, verify each before merging:

- **Three-location redundancy is mandatory, not optional**
  (`.claude/rules/player-prompt-reinforce-coach-constraint-in-three-locations.md`):
  a single-location mention is the documented failure mode — the Player
  re-reads only the section salient to the last feedback and misses a lone
  instruction.
- **Prompt-only is acceptable ONLY because no structural bound exists**
  (`.claude/rules/structural-defence-beats-prompt-instruction.md`): pair the
  instruction with monitoring (the STALEATTRIB01 authorship join). If a
  cheap structural detector emerges later, prefer it.
- **Must not contradict `anti-stub.md`** (xref §5 item 13): stubs in
  scaffold *implementations* stay legitimate; the rule targets *tests that
  pin them*. Review the wording against that file before landing.
- **New heuristics start advisory** (§6): the Coach-side check must not
  become turn-rejecting; a red verdict still requires a real failing signal,
  never a style judgement
  (`.claude/rules/absence-of-failure-is-not-success.md` territory if
  violated).
- **Coach stays read-only** (§6): the Coach-side check is prompt/criteria
  wording, not a new write path.
