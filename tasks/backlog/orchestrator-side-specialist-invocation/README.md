# Orchestrator-Side Specialist Invocation for AutoBuild Phases 4 & 5

**Feature**: FEAT-AB59
**Parent review**: TASK-REV-119C1
**Sibling F4A1 follow-ups**: TASK-DIAG-F4A2 (completed), TASK-FIX-F4A3 (completed)

---

## Problem

The Player LLM in the AutoBuild SDK subprocess will not delegate to
`test-orchestrator` and `code-reviewer` specialists via the `Task` tool.
Three runs across two repos (forge-run-3, forge-run-5,
jarvis-FEAT-002-run-2) showed **zero** `Task(subagent_type=...)` invocations
despite explicit prompt mandates. TASK-FIX-7A08 attempted to fix this with
prompt wording and was reverted across three commits — three independent
runs proved the prompt-class fix-class is insufficient.

The Coach's `agent_invocations` gate (TASK-FIX-7A07) correctly fires on the
missing phases, causing Wave-2 tasks to stall on `coach_agent_invocations_stall`.

## Solution

Move specialist invocation **out of the Player's discretion** and **into the
orchestrator's deterministic logic**. After the Player completes Phase 3
(implementation, which it does reliably via inline `Bash`/`Edit`/`Write`),
the `AutoBuildOrchestrator` itself invokes:

- `test-orchestrator` (Phase 4) via a new `specialist_invocations.py` module
  with its own `ClaudeAgentOptions` and SDK session
- `code-reviewer` (Phase 5) via the same module, conditional on Phase 4
  passing, with the Phase 4 summary in its prompt context

The producer-side `agent_invocations_validation` gate is updated to credit
orchestrator-invoked specialists by source-tag (`source: "orchestrator"`)
and to drop any residual Player-emitted Phase 4/5 markers (structural
double-count prevention).

## Why this works

The Player's behaviour is stochastic at inference time — no prompt change
has reliably influenced specialist invocation across three runs. The
orchestrator's logic is **deterministic**: when the turn-loop wiring fires
on every non-`direct` turn, the gate is credited every turn. The fix is
structural, not persuasive.

## What this is NOT

- ❌ Another prompt-class fix (refuted by F4A1)
- ❌ A change to TASK-FIX-7A07's classifier (the diagnostic is sound)
- ❌ A change to the Coach (reads the gate as before)
- ❌ A stack-template change (specialist resolution unchanged)
- ❌ Phase 3 specialist orchestration (deferred — Player implements
  reliably; only Phase 4/5 fail)

## Subtasks

7 subtasks across 5 waves. See [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md)
for the full plan, mandatory diagrams, integration contracts, and risk
register.

| Wave | Task | Title |
|---|---|---|
| 1 | TASK-OSI-001 | Module skeleton `specialist_invocations.py` |
| 1 | TASK-OSI-002 | Validation gate refactor |
| 1 | TASK-OSI-003 | Prompt trim Phase 4/5 |
| 2 | TASK-OSI-004 | `test-orchestrator` runner |
| 3 | TASK-OSI-005 | `code-reviewer` runner |
| 4 | TASK-OSI-006 | Turn-loop wiring in `autobuild.py` |
| 5 | TASK-OSI-007 | Stub-SDK harness + behavioural test |

## Acceptance targets

- **`jarvis-FEAT-J002-run-N` ≥ 18/23 tasks** (vs. 14/23 baseline pre-phase-2)
- **`forge-FEAT-FORGE-002-run-N` ≥ 10/11 Wave-2 tasks** (vs. 0/3 post-phase-1)
- **Pre-merge stub-SDK test** (TASK-OSI-007) passes deterministically in CI
  with no live SDK calls

## Test strategy

The pre-merge behavioural verification test uses a **stub-SDK harness** that
records orchestrator-side `Task(...)` invocations via a monkey-patched
`claude_agent_sdk.query`. This is deterministic, free, and fast — and tests
the orchestrator's deterministic logic, not the Player's stochastic LLM
choice (which was proven insufficient in F4A1).

The complementary slow signal is the nightly canonical-task run with
`GUARDKIT_AUTOBUILD_PRESERVE_DEBUG=1` (TASK-DIAG-F4A2 infrastructure already
in tree at `guardkit/orchestrator/sdk_debug.py`). CI wiring for the nightly
run is **out of scope** for FEAT-AB59 — a follow-up task can wire it once
this feature lands.

## How to work the feature

**Option A — autonomous via AutoBuild**:
```bash
/feature-build FEAT-AB59
```

**Option B — manual, wave by wave**:
```bash
# Wave 1 (parallel-safe via Conductor)
/task-work TASK-OSI-001
/task-work TASK-OSI-002
/task-work TASK-OSI-003

# Wave 2
/task-work TASK-OSI-004
/task-work TASK-OSI-005

# Wave 3
/task-work TASK-OSI-006

# Wave 4 (pre-merge gate)
/task-work TASK-OSI-007
```

After all 7 tasks complete, run the live acceptance tests:
```bash
guardkit autobuild feature jarvis-FEAT-J002 --max-turns=5
guardkit autobuild feature forge-FEAT-FORGE-002 --max-turns=5
```

## References

- Review report: [TASK-REV-119C1-review-report.md](../../../docs/reviews/orchestrator-side-specialist-invocation/TASK-REV-119C1-review-report.md)
- Forge-run-4 analysis: `docs/reviews/bdd-acceptance-wired-up/forge-run-4-analysis.md`
- Sibling: TASK-DIAG-F4A2 (rendered prompt + SDK message stream preservation)
- Refuted fix-class: commits `7f8f14ba`, `86688fc6`, `a8789317` (TASK-FIX-7A08)
