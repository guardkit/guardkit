---
id: TASK-ARCH-COACHSPLIT
title: Split the AutoBuild Coach into tool-using gather + toolless grammar-enforced verdict synthesis (D-3)
status: backlog
task_type: feature
created: 2026-06-09T00:00:00Z
updated: 2026-06-09T00:00:00Z
priority: high
complexity: 7
effort_hours: 12
parent_task: TASK-HMIG-010
related: [TASK-OPS-COACH31B, TASK-OPS-COACHGRAMMAR, TASK-FIX-COACHSCHEMA, TASK-HMIG-008R, TASK-HMIG-013]
implementation_mode: task-work
intensity: strict
blocker: true
---

# Task: Split the Coach into gather + toolless grammar-enforced verdict (D-3)

## Why this task exists

The TASK-OPS-COACH31B substrate investigation (runs 14→18, 2026-06-08/09)
**answered the substrate question and isolated the remaining blocker to the
Coach's architecture, not the model.** Each run peeled a layer:

| run | config | failure | layer fixed → exposed |
|---|---|---|---|
| 14 | gemma4:26b (MoE, 3.8B active) | F24 — no verdict ever | substrate capability wall |
| 15 | gemma4:31b (dense 30.7B) | **F24 BROKEN** (real verdict turn 1!); F23A OOM turn 2 | capability → memory |
| 16 | 31b, full fleet | F23A OOM turn 1 (71-file payload) | memory |
| 17 | 31b, **minimal fleet** + `--no-context`, ctx 65536 | F23A fixed; **F20** ctx overflow (66 687 tok) | memory → context |
| 18 | 31b, minimal fleet, **ctx 98304** | F20 fixed; **tool-parse HTTP 500** (`�`/U+FFFD) deep in the tool loop | context → tool-loop parser |

**The 31B dense substrate is viable** — run-15 turn-1 produced a real,
schema-valid Coach verdict that independently caught a Player honesty
discrepancy (first verdict in 15 runs). The model's reasoning is fine. The
remaining blocker is that the Coach runs **verdict synthesis inside a
tool-bound agentic loop** on the llama.cpp + Gemma-4-q4_0 stack, which is
fragile in two independent ways already on record:

1. **run-13 (TASK-OPS-COACHGRAMMAR):** route-level GBNF `--grammar-file` is a
   **no-op when a request carries `tools`** — llama.cpp bypasses the grammar
   for tool-bound requests. So we cannot guarantee the verdict schema while the
   Coach is tool-bound.
2. **run-18 (TASK-OPS-COACH31B):** the tool-bound Coach intermittently emits a
   malformed token (`�` = U+FFFD) inside its `<|channel>…<|tool_call>…` output;
   llama.cpp's tool-call parser then hard-fails (`HTTP 500 Failed to parse input
   at pos 0`). A *clean* tool conversation parses fine (GB10 reproducer), so it
   is a non-deterministic generation/parse artifact that grows more likely the
   longer the tool loop runs.

Both vanish if the **verdict is synthesised in a toolless call**: no `tools` ⇒
GBNF grammar applies (fixes #1); no tool-call markers to re-parse ⇒ no
parse-500 (fixes #2). This is "Path 2 / D-3", the architectural pivot the
run-13 grammar-no-op finding pointed to.

> Full forensics: [`docs/state/TASK-REV-HMIG/run-15-artifacts/`](../../docs/state/TASK-REV-HMIG/run-15-artifacts/README.md),
> [`run-16-artifacts/`](../../docs/state/TASK-REV-HMIG/run-16-artifacts/README.md),
> [`run-17-artifacts/`](../../docs/state/TASK-REV-HMIG/run-17-artifacts/README.md),
> [`run-18-artifacts/`](../../docs/state/TASK-REV-HMIG/run-18-artifacts/README.md),
> [`docs/state/TASK-OPS-COACH31B/`](../../docs/state/TASK-OPS-COACH31B/README.md).

## The design

The Coach is invoked tool-bound today via
`AgentInvoker._invoke_with_role(role="coach")`
([`agent_invoker.py:1985`](../../guardkit/orchestrator/agent_invoker.py),
`allowed_tools=["Read","Bash","Grep","Glob"]`) and must emit the fenced JSON
verdict in the *same* agentic loop. The verdict prompt + schema are built by
`_build_coach_prompt`; the verdict is parsed by
[`coach_output_parser.py`](../../guardkit/orchestrator/coach_output_parser.py).

Split it into two phases:

- **Phase A — evidence gather (tool-using, unchanged-ish).** The Coach may use
  tools to investigate (read files, run tests). Its output is *evidence /
  findings*, NOT required to be a fenced verdict. Tool-parse hiccups here are
  non-fatal (retry / fall back to the deterministic bundle).
- **Phase B — verdict synthesis (TOOLLESS + grammar-enforced).** A separate LLM
  call with `allowed_tools=[]` (no `tools` in the request), given the gathered
  evidence + the task ACs + the Player report, constrained by a **GBNF grammar**
  (or the harness's structured-output) that forces ONLY the fenced JSON verdict
  `{task_id, turn, decision, validation_results|issues, criteria_verification,
  rationale}`. No tools ⇒ grammar applies; no tool markers ⇒ no fragile
  re-parse. The existing `coach_output_parser` consumes the result unchanged.

### Two realizations (evaluate both; prefer the simpler if it suffices)

- **(B-min, recommended first) Toolless synthesis over the deterministic
  bundle.** `CoachValidator.gather_evidence(...)` already produces a
  `CoachEvidenceBundle` ([`coach_evidence.py:76`](../../guardkit/orchestrator/quality_gates/coach_evidence.py),
  TASK-HMIG-008R) — deterministic coverage / tests / plan_audit / bdd /
  arch_review / honesty. **Phase A may be unnecessary**: feed the bundle +
  Player report to a single toolless grammar-enforced synthesis call. Cheapest
  to implement; eliminates the tool loop entirely for the verdict. Risk: loses
  the LLM Coach's free-form investigation (but the deterministic bundle is
  exactly the evidence the gather phase would seek).
- **(B-full) Two-phase tool-gather → toolless-synthesis.** Keep the tool-using
  LLM gather for cases the deterministic bundle doesn't cover, then hand its
  findings (as text, not tool-call transcript) to the toolless synthesis call.
  More faithful to "independent investigation"; more code.

## Where (code surface)

- `guardkit/orchestrator/agent_invoker.py` — `_invoke_with_role` (`role="coach"`
  vs a new `role="coach_synthesis"`), `_build_coach_prompt` (split into a gather
  prompt and a synthesis prompt), the per-role `allowed_tools`.
- The LangGraph harness (`guardkitfactory` `langgraph_harness.py`) — must support
  a **toolless** invocation that passes the GBNF grammar / structured-output to
  llama-swap (no `tools` in the request, so `--grammar-file` or an inline
  grammar takes effect — verify against the run-13 finding).
- `guardkit/orchestrator/quality_gates/coach_validator.py` — wire the synthesis
  call after `gather_evidence`; keep `CoachVerifier` honesty checks.
- `guardkit/orchestrator/coach_output_parser.py` — unchanged (still parses the
  last fenced JSON block); confirm the grammar emits exactly that shape.
- GBNF grammar for the verdict schema (mirror the approach started in
  TASK-OPS-COACHGRAMMAR, now applicable because synthesis is toolless).

## Acceptance criteria

- [ ] **AC-1**: Coach verdict synthesis is a **separate toolless** model call
  (`tools` absent from the request) constrained by a GBNF grammar / structured
  output that enforces the verdict schema. Verified by inspecting the request
  llama-swap receives for the synthesis role (no `tools`; grammar present).
- [ ] **AC-2**: the run-18 tool-parse-500 class is eliminated for the verdict —
  the synthesis call carries no tool-call markers to re-parse. Regression test
  feeds a synthesis prompt and asserts a valid fenced verdict, no HTTP 500.
- [ ] **AC-3**: grammar enforcement is **active** in synthesis (closes the
  run-13 grammar-no-op: grammar is bypassed only when `tools` are present, which
  the synthesis call avoids). Test asserts a malformed-prone prompt still yields
  schema-valid JSON.
- [ ] **AC-4 (falsifier — run-19)**: an autobuild run with `gemma4:31b` as Coach
  (minimal `coach31` fleet, ctx 98304, `--no-context`) **completes ≥1 wave** with
  ≥1 real fenced-JSON Coach verdict and **no** F20/F23A/tool-parse-500 — the bar
  runs 15–18 could not reach. (This is the original TASK-OPS-COACH31B AC-3.)
- [ ] **AC-5**: unit/integration tests for the two-phase flow incl. the
  zero-evidence and gather-failure paths (respect `absence-of-failure-is-not-
  success.md` — a toolless synthesis over an empty bundle must NOT auto-approve).
- [ ] **AC-6**: `CoachVerifier` honesty verification still runs on the synthesis
  output (do not regress the deterministic-path honesty wiring from
  TASK-AB-FIX-INVAB1).

## Implementation notes / escalation

- **Substrate is settled**: keep `gemma4:31b` (dense 30.7B) as the Coach — it
  produces high-quality verdicts (run-15). Do NOT swap to 12B for this (same
  q4_0/llama.cpp stack ⇒ same parse path; 12B is only a memory/speed lever).
- **GB10 config is already tuned for run-19**: `coach31` matrix.set = `qw & g31`,
  g31 `--ctx-size 98304`, keepalive OFF during runs, run with `--no-context`.
  See [`docs/state/TASK-OPS-COACH31B/run-15-recipe.md`](../../docs/state/TASK-OPS-COACH31B/run-15-recipe.md).
- **Verify the grammar-applies-when-toolless claim early** (run-13 said grammar
  is bypassed *with* tools; confirm it *is* honoured *without* tools on the
  current llama.cpp build before building the whole flow on it).
- If toolless grammar is ALSO unreliable on this llama.cpp build, the fallback
  is the cheaper-but-uncertain **llama.cpp upgrade** (b9570+; no targeted
  Gemma-4 tool-parse fix in the changelog as of 2026-06-09, so it is a gamble)
  or a higher-quant / alt-source g31 GGUF.

## Related

- **Substrate investigation + forensics**: [TASK-OPS-COACH31B](TASK-OPS-COACH31B-evaluate-gemma4-31b-qat-as-coach-substrate.md)
- **Path 1A (grammar, no-op for tools)**: [TASK-OPS-COACHGRAMMAR](autobuild-harness-migration/TASK-OPS-COACHGRAMMAR-enforce-coach-verdict-schema-via-llama-cpp-gbnf.md)
- **Path 1B (prompt-tightening, insufficient)**: [TASK-FIX-COACHSCHEMA](autobuild-harness-migration/TASK-FIX-COACHSCHEMA-tighten-coach-prompt-schema-emission.md)
- **Deterministic evidence bundle (Phase A backbone)**: TASK-HMIG-008R, `coach_evidence.py`
- **Design rules to honour**: [`absence-of-failure-is-not-success.md`](../../.claude/rules/absence-of-failure-is-not-success.md), [`path-string-mismatch-is-not-dishonesty.md`](../../.claude/rules/path-string-mismatch-is-not-dishonesty.md)
