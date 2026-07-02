# Reinforce a Coach-enforced structural constraint in three Player-prompt locations

> **Source**: Promoted from the retiring Graphiti design-rule node
> *"TASK-FFID — Three-location pattern for Player prompt reinforcement"*
> (`guardkit__project_decisions`) during FEAT-MEM-09 WS-2b, 2026-07-01.
> **Provenance note:** the originating task (TASK-FFID, "Add filename-fidelity
> rules to 5 PO player prompts") and its cited artifacts — `player_extract.md`,
> the five Product-Owner player prompts, and the review TASK-REV-E4A7 that first
> surfaced the pattern — are **no longer present in the current guardkit tree**
> (`find tasks -iname '*ffid*'` → 0, `git log --all | grep TASK-FFID` → 0). This
> rule therefore records the *generalized principle* and describes the mechanism
> against the machinery that still exists (the Player/Coach adversarial prompt
> pair), not the retired PO prompts. Companion of the Player/Coach machinery
> rules [`feature-build-invariants.md`](feature-build-invariants.md) and
> [`autobuild.md`](autobuild.md).

## The rule

When the Coach enforces a **structural constraint** on a Player output field
that references the Player's input — e.g. the Coach checks that a produced
document echoes the exact `## File:` header from a `## Product Documentation`
input block, or any "your output field X must preserve/match structure Y from
the input" contract — the Player prompt MUST reinforce that same structural
expectation in **three distinct locations**:

1. **The workflow step** that reads or uses that input (where the Player first
   encounters field Y).
2. **The anti-patterns table/list** that names the *exact* detection pattern
   the Coach uses to reject a violation (so the Player sees the failure mode in
   the Coach's own terms).
3. **A grounding-principle paragraph** — either inside a `*-Specific Rules`
   section or a dedicated `## Source Grounding` section — that states *why* the
   structure must be preserved.

A single-location instruction is insufficient. The three placements are
**redundant on purpose**: they guarantee the rule appears in whichever section
the Player happens to re-read when Coach feedback arrives mid-loop.

**Applies to:** any Player/Coach prompt pair where the Coach enforces a
structural constraint on a Player output field that references the input. Does
**not** apply to Coach constraints on freeform output with no input-structure
dependency (see "What it does NOT cover").

## Why this rule exists

The Player is an LLM that, on a revision pass, does not re-read its entire
prompt — it re-reads the section most salient to the Coach feedback it just
received. If the load-bearing structural rule lives in only one place and the
Player re-enters through a different section, the rule is effectively invisible
on that turn and the Player re-emits the same violation. The adversarial loop
then burns turns on a defect the prompt "already covered".

The pattern was proven empirically in the originating work (TASK-FFID): across
five Product-Owner player prompts with three operating modes, `player_extract.md`
(carrying the three-location reinforcement, inherited from an earlier review,
TASK-REV-E4A7) **passed the Coach's filename-fidelity check**, while the
`evolve` and `scope` modes **failed** — precisely because they lacked the
reciprocal instructions in the anti-patterns table and grounding paragraph.
Same Coach constraint, same input structure; the only difference was whether the
Player prompt reinforced it in one place or three. (Those prompt files have
since been removed from the tree; the empirical result is preserved here.)

The still-live machinery this generalizes to is guardkit's own Player/Coach
prompt pair: the Coach prompt is assembled in
`AgentInvoker._build_coach_prompt` and the Player prompt in
`AgentInvoker._build_player_prompt` (both in
`guardkit/orchestrator/agent_invoker.py`). When a Coach guard added to
`_build_coach_prompt` enforces structure on a Player output field — the
`INDEPENDENT-TEST ABSENT GUARD` ("guard #6", from TASK-FIX-COACHFG01) is a live
example of such a Coach-side constraint in that builder
(`agent_invoker.py:3477`, made load-bearing at `agent_invoker.py:5360`) — the
reciprocal Player-side reinforcement should follow the three-location pattern
rather than a lone mention.

## Symptom

- The Coach repeatedly rejects the same structural violation across consecutive
  turns even though the Player prompt "documents" the rule once.
- One mode/variant of a shared Player prompt passes the Coach's structural check
  while a sibling mode fails, and diffing the two prompts shows the passing one
  carries the rule in the anti-patterns table and/or a grounding paragraph that
  the failing one omits.
- A Coach detection pattern (the literal string/shape the Coach greps for)
  appears in the Coach prompt but has **no verbatim counterpart** in the Player
  prompt's anti-patterns section.

## Detection recipe

```bash
# 1. Find the Player/Coach prompt-builder machinery (the surface this governs).
rg -n "_build_coach_prompt|_build_player_prompt" guardkit/orchestrator/agent_invoker.py

# 2. For any Coach-enforced structural constraint, confirm the Player prompt
#    carries an anti-patterns table/list that could hold location (2).
rg -lc "Anti-Pattern|anti-pattern" installer/core/agents/*.md

# 3. For a given constraint term (e.g. a required header like '## File:'),
#    count its occurrences across the Player prompt. Fewer than 3 distinct
#    sections is the hazard fingerprint.
rg -n "<constraint-term>" <player-prompt-file>

# 4. Cross-check the sibling Player/Coach machinery rules.
rg -l "Player|Coach" .claude/rules/feature-build-invariants.md .claude/rules/autobuild.md
```

## Remediation

1. **Locate the Coach's detection pattern.** Read the Coach constraint (in the
   Coach agent prompt or in `_build_coach_prompt`) and extract the *exact*
   structural token it checks for.
2. **Place it in all three Player-prompt locations:** (1) the workflow step that
   consumes the input, (2) the anti-patterns table — quoting the Coach's
   detection pattern verbatim so the Player recognizes the failure in the
   Coach's terms, and (3) a grounding-principle paragraph explaining *why*.
3. **Diff sibling modes/variants.** If a shared prompt has multiple modes,
   confirm every mode carries the same three-location reinforcement; a mode
   missing the reciprocal instructions is the next Coach false-reject.
4. **Do not rely on a single "documented once" placement** — that is the exact
   failure this rule exists to prevent.

## Grep-able signature (for next agent)

```bash
# Player/Coach prompt-builder surface (confirmed present today):
rg -n "_build_player_prompt|_build_coach_prompt" guardkit/orchestrator/agent_invoker.py

# Anti-patterns tables (location 2) exist across agent prompts (confirmed):
rg -lc "Anti-Pattern|anti-pattern" installer/core/agents/*.md

# Originating artifacts are ABSENT (honest state — do not expect a match):
find tasks -iname '*ffid*'                     # -> (empty)
git log --all --oneline | grep -i "TASK-FFID"  # -> (empty)

# Sibling machinery rules for cross-link:
ls .claude/rules/feature-build-invariants.md .claude/rules/autobuild.md
```

## When this rule triggers

- Before adding or modifying a Coach constraint that checks structure on a
  Player output field which references the Player's input.
- When authoring or refactoring a Player/Coach prompt pair (guardkit's own
  adversarial machinery, or PO/RequireKit-style prompt authoring).
- During Phase 2.5 architectural review for any task touching
  `_build_player_prompt` / `_build_coach_prompt` or an agent prompt whose Coach
  enforces an input-referencing structural constraint.
- During a diagnostic session investigating "the Coach keeps rejecting the same
  structural violation and the prompt already says not to do it."

## What it does NOT cover

- **Coach constraints on freeform output** with no dependency on input
  structure — there is no input-referencing field to reinforce.
- **Non-structural Coach constraints** (thresholds, counts, verdict logic) —
  those belong to the low-fidelity-oracle family
  ([`absence-of-failure-is-not-success.md`](absence-of-failure-is-not-success.md)),
  not to prompt-reinforcement redundancy.
- **The exact `## File:` / `## Product Documentation` / `## Source Grounding`
  tokens** from the originating PO prompts — those were illustrative of the
  *class* of constraint and their source files no longer exist; apply the
  three-location shape to whatever the current constraint's structural token is.
- **Coach-side prompt authoring.** This rule governs the *Player* prompt's
  reinforcement of a Coach-enforced constraint, not how the Coach constraint
  itself is expressed.
