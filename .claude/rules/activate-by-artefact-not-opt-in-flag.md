# Activate by artefact presence, not by an opt-in flag

> **Source**: Seeded by TASK-BDD-E8954 (BDD oracle wiring for `/task-work`),
> 2026-04-21 (`tasks/completed/TASK-BDD-E8954/TASK-BDD-E8954.md`; module landed
> in commit `52de99a2`, task closed in `0a5201083`). Companion to
> [`bdd-per-task-glue.md`](bdd-per-task-glue.md) (the per-task naming half of the
> same oracle). Loosely paired with
> [`absence-of-failure-is-not-success.md`](absence-of-failure-is-not-success.md):
> the two together say "run the oracle whenever the artefact says to, but never
> read a not-run oracle as a pass".

## The rule

When a quality gate / oracle is driven by an artefact another workflow already
produces (here: a `features/*.feature` file whose scenarios carry
`@task:<TASK-ID>`), **activate the gate on the PRESENCE of that artefact, not on
a separate frontmatter/config opt-in flag** (e.g. do NOT gate it behind an
`autobuild.bdd_oracle: true`). Presence-of-artefact ties activation directly to
what the upstream producer emitted, so activation and the thing-being-activated
can never disagree:

- artefact present + tagged for this task + runnable → the gate runs;
- any condition absent → silent skip, behaviour identical to pre-gate.

A flag is a second source of truth that a Player agent can forget to set (or set
while the artefact is missing), producing the two-headed failure mode this rule
exists to prevent: an operator believing the gate ran when it silently didn't
(false confidence), or the flag set with no artefact behind it (the gate looks
armed but has nothing to run).

## Why this rule exists

TASK-BDD-E8954 wired the Gherkin scenarios `/feature-spec` produces into
`/task-work` as a Coach oracle. The parent review (TASK-REV-4D012 §6 R2) found
the `.feature` artefacts reached `/feature-plan` as `--context` and were then
**discarded** — the artefact existed, the pipe was missing. The task's
"Activation trigger — critical" section made the design choice explicit:

> **Activation is by artefact presence, NOT by frontmatter flag.** … A
> frontmatter flag could be forgotten by the Player; operators would think BDD
> ran when it didn't.

And its Non-Goals guardrail: *"Do not add `autobuild.bdd_oracle: true` or any
other activation flag."*

The choice is load-bearing in the shipped code:

- `guardkit/orchestrator/quality_gates/bdd_runner.py` — `run_bdd_for_task(task_id,
  worktree_path) -> Optional[BDDResult]` (`bdd_runner.py:641`). Activation is a
  cheap text scan: `find_feature_files_with_tag(features_dir, task_tag(task_id))`
  (`bdd_runner.py:215`) looks for the literal `@task:<TASK-ID>` string
  (`task_tag` is `f"@task:{task_id}"`, `bdd_runner.py:171`). No match → returns
  `None`, "legitimately skipped / not-applicable" (`bdd_runner.py:673-680`).
- `guardkit/orchestrator/agent_invoker.py` — `_run_bdd_oracle` (`agent_invoker.py:8114`)
  states it verbatim: *"Activation is by artefact presence: if no
  `features/*.feature` file in the worktree carries a `@task:<TASK-ID>` tag … this
  returns `None` and behaviour is identical to before BDD wiring existed."* It
  adds `bdd_results` to `task_work_results.json` only when a result exists.
- `guardkit/orchestrator/quality_gates/coach_validator.py` — `_check_bdd_results`
  (`coach_validator.py:7335`, called from `validate` at
  `coach_validator.py:2481`): *"Absent `bdd_results` key → no gate active, returns
  `([], [])`."* An absent key is a not-applicable gate, not a failure.

There is no `bdd_oracle` frontmatter flag anywhere in the tree — confirmed by
grep (see Grep-able signature). The only `bdd_oracle` references are an
**ergonomics nudge**, `check_bdd_oracle_activation`
(`installer/core/commands/lib/bdd_oracle_nudge.py`), which is the rule's positive
proof: rather than adding a flag, it *nudges the user to add the missing
`@task:` tag to the artefact* when a `.feature` exists with no tags — steering
activation back to the artefact, never to a flag.

## Symptom (the failure mode a flag would have)

- An oracle/gate is reported as "enabled" (a flag is set) but never actually ran,
  because the artefact it needs was never produced — the flag and the artefact
  disagree and nobody notices.
- Conversely: the producing workflow emitted the artefact, but a downstream agent
  forgot to flip the opt-in flag, so the gate silently no-ops and the operator
  believes it was checked.
- Two sources of truth for "should this run?" that must be kept in sync by hand.

## Detection recipe

```bash
# 1. A gate that keys activation off a config/frontmatter boolean rather than
#    the artefact it consumes is a candidate. Look for opt-in booleans near a
#    gate that also has an artefact it could detect instead.
rg -n "\.get\(\"?[a-z_]*_oracle\"?|_enabled\b.*True|bdd_oracle|smoke_gate.*enabled" \
   guardkit/orchestrator/quality_gates/ installer/core/

# 2. Confirm the artefact-presence path: discovery is what decides activation.
rg -n "find_feature_files_with_tag|task_tag\(|return None" \
   guardkit/orchestrator/quality_gates/bdd_runner.py

# 3. Confirm the absent-artefact path is a not-applicable skip, not a failure.
rg -n "Absent .*key.*no gate active|bdd_results.*not " \
   guardkit/orchestrator/quality_gates/coach_validator.py
```

## Remediation

1. **Derive activation from the artefact the upstream producer already emits.**
   If `/feature-spec` (or any producer) writes the input, detect that input; do
   not add a parallel flag the input's existence should have implied.
2. **Make "artefact absent" a silent, behaviour-identical skip** (`return None` /
   omit the results key), so adopting the gate can never regress a project that
   has no artefact.
3. **If ergonomics need a hint, nudge toward the artefact, not toward a flag.**
   The `bdd_oracle_nudge` prints "add `@task:<TASK-ID>` to your `.feature`" — it
   never introduces a config switch.
4. **Do NOT read a not-run gate as a pass** (the
   [`absence-of-failure-is-not-success`](absence-of-failure-is-not-success.md)
   pairing): an absent `bdd_results` key is not-applicable, but a *tagged
   artefact that could not run* (e.g. pytest-bdd not importable) is surfaced as a
   synthetic blocker rather than a vacuous approve — see `bdd_runner.py:682-718`
   (TASK-FIX-BDDM-1). Presence-activation must not become presence-of-artefact →
   silent-green when the runner itself is broken.

## Grep-able signature (for next agent)

```bash
# Artefact-presence activation (MUST resolve): discovery + the verbatim docstring.
rg -n "Activation is by artefact presence" guardkit/orchestrator/agent_invoker.py   # -> 8117
rg -n "def find_feature_files_with_tag|def task_tag" \
   guardkit/orchestrator/quality_gates/bdd_runner.py                                  # -> 215, 171

# No opt-in flag exists (MUST be empty): there is no bdd_oracle frontmatter flag.
rg -n "autobuild\.bdd_oracle|bdd_oracle:\s*true|\"bdd_oracle\"" \
   guardkit/ installer/ .claude/                                                      # -> (no match)

# The nudge-toward-artefact proof (MUST resolve).
rg -n "def check_bdd_oracle_activation" installer/core/commands/lib/bdd_oracle_nudge.py
```

## When this rule triggers

- Before adding a new quality gate / oracle whose input is an artefact some other
  command already produces — detect the artefact, do not add an opt-in flag.
- Before adding an `*_oracle: true` / `*_enabled: true` frontmatter or
  `.guardkit/*.yaml` switch that duplicates the presence of a file.
- During Phase 2.5 review for anything touching `bdd_runner.py`,
  `_run_bdd_oracle`, `_check_bdd_results`, or the `/feature-spec` → `/feature-plan`
  → `/task-work` artefact pipe.

## What this rule does NOT cover

- **Genuine operator policy that has no artefact proxy** — e.g. the smoke-gate
  retry budget (`GUARDKIT_SMOKE_GATE_MAX_RETRIES`) or a backend selection
  (`.guardkit/graphiti.yaml` `backend:`) is a real policy choice with nothing in
  the tree to derive it from; a config value is correct there. This rule is about
  activation that *duplicates* an artefact's existence, not about all config.
- **The absent-signal interpretation** once the gate has run — that is
  [`absence-of-failure-is-not-success.md`](absence-of-failure-is-not-success.md)
  and [`absence-must-survive-every-reconciliation-layer.md`](absence-must-survive-every-reconciliation-layer.md);
  this rule only governs whether the gate *activates*.
- **Per-task glue-file naming** for the same BDD oracle — that is
  [`bdd-per-task-glue.md`](bdd-per-task-glue.md).
