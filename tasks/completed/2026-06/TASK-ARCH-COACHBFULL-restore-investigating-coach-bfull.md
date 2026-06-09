---
id: TASK-ARCH-COACHBFULL
title: Restore the investigating Coach (B-full) — tool-using gather phase before toolless grammar synthesis
status: backlog
task_type: feature
created: 2026-06-09T00:00:00Z
updated: 2026-06-09T00:00:00Z
priority: high
complexity: 7
parent_task: TASK-ARCH-COACHSPLIT
related: [TASK-ARCH-COACHSPLIT, TASK-FIX-COACHTESTTO, TASK-HMIG-008R, TASK-OPS-COACH31B]
implementation_mode: task-work
intensity: strict
---

# Task: Restore the investigating Coach (B-full)

## Why this task exists

TASK-ARCH-COACHSPLIT shipped **B-min**: the Coach synthesises its verdict
**toolless**, over the deterministic `CoachEvidenceBundle` only. That made
the verdict reliable on the weak local substrate (gemma4:31b on llama.cpp
hard-rejects grammar+tools), but it **removed the Coach's ability to
investigate** — and that is a real departure from the adversarial-
cooperation pattern GuardKit is modelled on.

The Block AI Research paper *"Adversarial Cooperation in Code Synthesis"*
(Dec 2025; ref impl `g3`, coach model `g31` = `gemma4:31b`) describes the
Coach as an **LLM agent that itself "tests compilation and functionality"**
and emits a rich **per-requirement compliance checklist** (✅/❌ per
requirement + "IMMEDIATE ACTIONS NEEDED"). GuardKit's B-min Coach does the
opposite: it cannot test or probe; it reads a Python-gathered dossier and,
in run-19, **rubber-stamped green gates** — every verdict had
`criteria_verification: []` and a ~200-char rationale (see
`docs/state/TASK-REV-HMIG/run-19-artifacts/README.md` caveat #2).

The fix is the **B-full** realization that TASK-ARCH-COACHSPLIT's own title
names ("tool-using **gather** + toolless grammar verdict") and that B-min
explicitly deferred. It restores the paper's investigating Coach **without
sacrificing** the reliable grammar-constrained verdict.

## The design (Phase A + Phase B)

The harness already exposes both primitives (TASK-ARCH-COACHSPLIT):

- `HarnessAdapter.invoke` — tool-bound agentic turn (the Coach can Read /
  Bash / Grep / Glob to investigate).
- `HarnessAdapter.invoke_synthesis` — toolless, GBNF-grammar-enforced
  verdict.

B-full chains them per Coach turn:

1. **Phase A — evidence gather (tool-using LLM).** Invoke the Coach
   tool-bound over the requirements + ACs + Player report + the
   deterministic bundle, asking it to **investigate and produce findings**
   (compile, run the focused test, read the changed files, check the ACs it
   is unsure about) — output is *findings text*, NOT a fenced verdict.
2. **Phase B — verdict synthesis (toolless + grammar).** Hand Phase A's
   findings (as text, not a tool-call transcript) plus the deterministic
   bundle to the existing `invoke_synthesis` call. Unchanged from B-min
   except the prompt now also carries the gather findings.

**Strict dominance over B-min (the load-bearing property).** Phase A is
tool-bound, so the run-18 tool-parse-500 class can recur *there* — but
Phase A's output is not the verdict and needs no grammar. A failed/garbled
gather is **non-fatal**: degrade to B-min (synthesise over the deterministic
bundle alone). So B-full ADDS investigation when the substrate cooperates
and FALLS BACK to today's behaviour when it doesn't. It can only improve
verdict quality, never regress reliability.

## Where (code surface)

- `guardkit/orchestrator/agent_invoker.py` — add the Phase-A gather
  invocation (tool-bound `_invoke_with_role`, `synthesis=False`, role
  `coach`), thread its findings into `_build_coach_prompt`'s synthesis
  variant. Gate behind an env flag (e.g. `GUARDKIT_COACH_GATHER`,
  default the operator chooses) so B-min stays the fallback.
- `guardkit/orchestrator/autobuild.py` — `_invoke_coach_primary` wiring.
- Honour `.claude/rules/harness-cancellation-contract.md` (Phase A is a
  second in-flight invocation per Coach turn — the cancel monitor must
  cover it) and the per-turn budget (two LLM calls now).

## Acceptance criteria

- [ ] **AC-1**: A tool-using Phase-A gather invocation runs before the
  toolless Phase-B synthesis, producing investigation *findings* (text),
  not a verdict. Verified by inspecting the two distinct harness calls per
  Coach turn (one tool-bound, one toolless+grammar).
- [ ] **AC-2 (strict dominance)**: a Phase-A failure (tool-parse error,
  timeout, empty findings) **degrades to B-min** (synthesis over the
  deterministic bundle) and never fails the turn. Regression test drives a
  broken gather and asserts a valid verdict still emerges.
- [ ] **AC-3 (the falsifier)**: construct a case the deterministic bundle
  marks green but where an AC is actually unmet (e.g. tests pass but a
  required behaviour is stubbed / an AC has no corresponding code). B-full
  Coach (investigating) **catches it and returns feedback**; B-min Coach
  (current) approves. This is the empirical proof the investigation adds
  adversarial value.
- [ ] **AC-4**: the synthesis verdict now carries a populated, structured
  `criteria_verification` (per-AC result + notes — the paper's compliance
  checklist), not an empty array. Encourage via prompt and/or grammar
  without over-constraining (respect the coach-verdict.gbnf design notes).
- [ ] **AC-5**: cancellation + per-turn budget hold with two LLM calls per
  turn (the cancel monitor covers Phase A; the combined budget is bounded).
- [ ] **AC-6**: unit/integration tests for the two-phase flow incl. the
  gather-degrades-to-B-min and zero-evidence paths (absence-of-failure:
  an empty gather + empty bundle must NOT auto-approve).

## Notes / sequencing

- Best done **after** TASK-FIX-COACHTESTTO (restores the deterministic
  independent-test leg) so B-full builds on a sound evidence floor.
- The substrate is now settled (TASK-OPS-COACH31B): gemma4:31b is a capable
  Coach; the only reason it ran toolless was verdict-emission reliability,
  which Phase B preserves.
- Surfaced while reviewing run-19 against the Block paper (2026-06-09).
