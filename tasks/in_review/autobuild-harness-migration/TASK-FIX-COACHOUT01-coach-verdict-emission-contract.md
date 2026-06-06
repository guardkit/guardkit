---
id: TASK-FIX-COACHOUT01
title: Replace Coach Bash-heredoc verdict-emission contract with structured-output parsing or constrained Write tool
status: design_approved
task_type: bug
created: 2026-06-06T08:00:00Z
updated: 2026-06-06T11:15:00Z
previous_state: in_progress
state_transition_reason: "Phase 2.8 checkpoint approved (Shape A, score 82/100, strict intensity)"
design:
  status: approved
  approved_at: "2026-06-06T11:15:00Z"
  approved_by: "human"
  implementation_plan_version: v1
  architectural_review_score: 82
  complexity_score: 7
  chosen_shape: A
  design_session_id: "design-TASK-FIX-COACHOUT01-20260606"
  design_notes: "Shape A (Structured-Output Parsing) chosen by architectural-reviewer with high confidence. Three implementation constraints recorded in task body (return_events parameter, COACHSF01 error-string coupling, module-level function). GuardKit-only, ~150 LOC. Live falsifier deferred to HMIG-010 run N+1."
  plan_file: "docs/state/TASK-FIX-COACHOUT01/implementation_plan.md"
  review_file: "docs/state/TASK-FIX-COACHOUT01/architectural_review.md"
priority: critical
complexity: 7
deadline: 2026-06-15
parent_review: TASK-REV-HMIG
parent_task: TASK-HMIG-010
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
implementation_mode: task-work
intensity: strict
effort_hours: 4
blocks:
  - TASK-HMIG-010
  - TASK-HMIG-011  # cutover ceremony — operator wants this fundamentally fixed before cutover
falsifier: "After landing, run N of `guardkit autobuild feature FEAT-AOF --fresh --model qwen36-workhorse` under GUARDKIT_HARNESS=langgraph: Coach LLM verdict-emission rate is ≥95% across at least 6 Coach turns (run-5 baseline was 67%, two-thirds, two real verdicts + one COACHSF01 synthetic). The synthetic-feedback fallback (COACHSF01) fires ≤1 time across the same sample. The Coach LLM does not depend on emitting a multi-line Bash heredoc to persist its verdict."
tags:
  - autobuild
  - langgraph-migration
  - coach
  - substrate-mitigation
  - cutover-blocker
  - cross-repo-likely
---

# Task: Coach verdict-emission contract — close F17 fundamentally before cutover

## Operator decision context

**Filed 2026-06-06 after run 5 (2026-06-05T22:20, 41m31s, UNRECOVERABLE_STALL).**

Five autobuild feature runs against FEAT-AOF have produced this picture:

- **Mechanical migration: COMPLETE** — every F-numbered finding from runs 1–5 has been root-caused, fixed, and empirically validated:
  - F1 (pre-loop bypass) → TASK-HMIG-006.4
  - F4 (worktree manager cwd-branch) → TASK-FIX-WTBC
  - F9 (CLI --model task vs feature) → TASK-FIX-LGFM
  - F10 (AgentInvoker _invoke_with_role vs _invoke_task_work_implement) → TASK-FIX-LGFM2
  - F11 (DeepAgents conversation_history offload) → guardkitfactory 002R-SUMM-ROOT + 002R-MODEL-PROFILE
  - F12 (coach_test role model threading, 4th instance) → TASK-FIX-LGFM3
  - F14 (cancellation race) → TASK-FIX-CTOUT01
  - F17-soft (Coach decision-not-found soft-fail safety net) → TASK-FIX-COACHSF01

- **Substrate quality: VARIABLE** — qwen36-workhorse + LangGraph + the migration stack produces:
  - Correct 1-turn Player approvals SOMETIMES (run 3 IA03, run 4 IA03 — 14/14 tests passing on first try)
  - Multi-turn iteration drift OTHERWISE (run 5 IA03 stalled over 3 turns, never produced passing tests)
  - Coach LLM verdict-emission rate ~67% per run 5 sample (2 real verdicts + 1 COACHSF01 synthetic across 3 Coach turns)

- **Operator decision (2026-06-06)**: "I want this working properly before the cutover." The Coach verdict-emission contract is the architecturally weakest layer in the chain — Coach is expected to construct a multi-line Bash heredoc to persist its verdict, which qwen36-workhorse can only do ~67% reliably. That's the load-bearing constraint on cutover confidence. Close it before TASK-HMIG-011 (cutover ceremony).

## The contract that needs replacing

Current Coach contract per [`agent_invoker.py:2393-2415`](../../../guardkit/orchestrator/agent_invoker.py):

```
Write your decision to:
{worktree_path}/.guardkit/autobuild/{task_id}/coach_turn_{turn}.json

Your decision MUST be valid JSON with these fields:
For APPROVAL:
{ "task_id": ..., "turn": ..., "decision": "approve", "validation_results": {...} }
For FEEDBACK:
{ "task_id": ..., "turn": ..., "decision": "feedback", "feedback": "...", ... }
```

Coach's allowed tools per [`agent_invoker.py:1959`](../../../guardkit/orchestrator/agent_invoker.py):

```python
allowed_tools=["Read", "Bash", "Grep", "Glob"]   # no Write tool
```

So Coach must use `Bash` to write the JSON file — likely via heredoc:

```bash
cat > /worktree/.../coach_turn_1.json << 'EOF'
{
  "task_id": "TASK-XXX",
  "turn": 1,
  "decision": "feedback",
  ...
}
EOF
```

Constructing a multi-line, syntactically-valid, JSON-inside-heredoc Bash command after 140s of reasoning about real test failures is **right at the edge of qwen36-workhorse's reliable instruction-following envelope**. Run-5 evidence: 2 of 3 Coach turns succeeded, 1 failed (relied on COACHSF01 safety net).

This is **canary F2 confirmed at Coach scope** (`canary-analysis.md §3.F2`): "model discusses tool calls in prose but no actual tool_use blocks are emitted."

## Two fix shapes — pick one in Phase 2

### Fix shape A: Structured-output parsing (orchestrator-side)

**Idea**: Coach's prompt asks it to end its response with a fenced JSON block (or specific marker delimiters). The orchestrator parses Coach's final LLM text response, extracts the JSON block, and writes `coach_turn_N.json` from the orchestrator side.

**Coach tools unchanged**: still `[Read, Bash, Grep, Glob]`. Coach's prompt says "End your response with a fenced JSON block like this: \`\`\`json\n{...}\n\`\`\`" instead of "Write your decision to...".

**Pros**:
- Eliminates the Bash-heredoc emission contract entirely
- Coach's read-only invariant strictly preserved (no Write tool)
- Compatible with how LangChain / DeepAgents agents typically work (structured output)
- Smaller LLM cognitive load — write prose then a JSON block, not construct a Bash command containing JSON
- Compatible with future model upgrades (any model that can emit a fenced JSON block at the end of a response works — Sonnet, qwen, anything)

**Cons**:
- Orchestrator-side parsing logic to write + maintain
- Parser needs to handle edge cases (malformed JSON, multiple JSON blocks, JSON missing required fields)
- The current `_load_agent_report` consumer at [`agent_invoker.py:4131`](../../../guardkit/orchestrator/agent_invoker.py) expects a file on disk — must be wired to be populated by orchestrator before being read

### Fix shape B: Constrained Write tool

**Idea**: Grant Coach a constrained version of the `Write` tool that can only write to `coach_turn_*.json` paths within the worktree's autobuild state directory. Coach's prompt and current write-the-file flow unchanged.

**Coach tools**: `[Read, Bash, Grep, Glob, CoachVerdictWrite]` where `CoachVerdictWrite` is a custom tool that validates its `path` argument against a pattern like `.guardkit/autobuild/{task_id}/coach_turn_{N}.json`.

**Pros**:
- Smaller change — Coach's verdict-writing remains a single tool call instead of a multi-step Bash heredoc
- Single-tool emission is much more reliable on qwen36-workhorse than multi-step Bash construction
- Read-only-for-code invariant softly preserved (Write is constrained to verdict path only — a controlled exception, well-documented)
- Tool's `path` parameter validation enforces the constraint at orchestrator level

**Cons**:
- Mildly weakens the read-only invariant (an architectural decision worth recording in `.claude/rules/`)
- Requires adding a custom tool to the LangGraph harness (cross-repo change in guardkitfactory)
- The custom tool needs to be wired through both SDK and LangGraph harnesses to preserve substrate parity

### Operator pick (filled in by /task-work)

| Field | Value |
|---|---|
| chosen_shape | **A** (Structured-Output Parsing) |
| rationale | Root-cause elimination (removes the Bash-heredoc primitive entirely, not just simplifies the tool call). Zero cross-repo blast radius — TASK-HMIG-011 cutover doesn't gain a guardkitfactory release dependency. Structural substrate parity — both `ClaudeSDKHarness` and `LangGraphHarness` already emit `AssistantMessageEvent` carrying full response text; no harness changes. Read-only invariant fully preserved (vs Shape B's documented constrained-write exception). Lower Sonnet regression risk — "end response with fenced JSON block" is strictly simpler than the current heredoc construction. |
| picked_at | 2026-06-06 |
| picked_by | architectural-reviewer (Phase 2.5B, score 82/100, confidence high) |
| review_file | `docs/state/TASK-FIX-COACHOUT01/architectural_review.md` |

**Phase 2 recommendation history**: The original task body recommended Shape A as cleaner long-term and Shape B as smaller blast radius. The Phase 2.5B architectural review confirmed Shape A on the architectural-asymmetry, cross-repo blast radius, and substrate-parity criteria. See review file for full SOLID/DRY/YAGNI scoring (84/82/80) and AC coverage matrix.

## Acceptance Criteria

### Common to both fix shapes

- [ ] AC-001: Phase 2 architectural review picks Fix shape A or B with recorded rationale. Document in this task file's "Operator pick" table above.
- [ ] AC-002: The synthetic-feedback safety net (`_emit_synthetic_coach_feedback` per TASK-FIX-COACHSF01) remains in place as defence-in-depth — even after this fix lands, COACHSF01 still catches any residual verdict-emission failures. Falsifier intent: synthetic-feedback fires ≤1 time per run after this fix; pre-fix run-5 baseline was 1/3 turns.
- [ ] AC-003: Live smoke (HMIG-010 run N+1): Coach verdict-emission rate ≥95% across at least 6 Coach turns. Either a clean run from scratch OR a `--resume` run that exercises 6+ Coach turns.
- [ ] AC-004: Regression tests pin the verdict-emission path under both SDK harness and LangGraph harness for substrate parity. Both must produce the same `coach_turn_N.json` structure.
- [ ] AC-005: The Coach contract change is documented in `.claude/rules/` — either as part of an existing rule or a new rule. The architectural decision (Coach is read-only-for-code with a structured-output-OR-constrained-write exception for its own verdict) should be discoverable by future contributors.
- [ ] AC-006: TASK-HMIG-010 unblocked. AC-008 verdict computation can proceed. Cutover (TASK-HMIG-011) decision can be made on substrate-quality-only criteria, not on substrate-quality-PLUS-architectural-weakness.

### Shape-A specific (if picked)

- [ ] AC-A1: Replace Coach prompt's "Write your decision to: {path}" with "End your response with a fenced JSON block: \`\`\`json\n{...}\n\`\`\`". Specify required fields exactly as the current `_validate_coach_decision` enforces.
- [ ] AC-A2: After `_invoke_with_role` returns for Coach, orchestrator parses the LLM's response text, extracts the JSON block, validates required fields, and writes `coach_turn_N.json` from the orchestrator side.
- [ ] AC-A3: Parser handles edge cases: no JSON block found (treat as F17, fire COACHSF01), multiple JSON blocks (use last one), malformed JSON (treat as F17), missing required fields (treat as `CoachDecisionInvalidError`).
- [ ] AC-A4: Coach's allowed_tools list at [`agent_invoker.py:1959`](../../../guardkit/orchestrator/agent_invoker.py) unchanged: `[Read, Bash, Grep, Glob]`.

### Shape-B specific (if picked)

- [ ] AC-B1: New constrained `CoachVerdictWrite` tool in guardkitfactory's harness — accepts `path: str, content: str`, validates `path` matches `.guardkit/autobuild/{task_id}/coach_turn_\d+.json` pattern under the worktree root, writes file atomically, rejects any other path with explicit error.
- [ ] AC-B2: Coach's allowed_tools list at [`agent_invoker.py:1959`](../../../guardkit/orchestrator/agent_invoker.py) extended: `[Read, Bash, Grep, Glob, CoachVerdictWrite]`.
- [ ] AC-B3: Both SDK harness and LangGraph harness expose `CoachVerdictWrite` with identical contract (substrate parity).
- [ ] AC-B4: Coach prompt updated to use `CoachVerdictWrite` instead of Bash heredoc. New language: "Use the CoachVerdictWrite tool to write your decision to coach_turn_{turn}.json. The tool accepts `path` and `content` parameters."
- [ ] AC-B5: `.claude/rules/feature-build-invariants.md` updated — the "Coach has read-only access" rule explicitly notes the constrained-write exception for verdict emission.

## Why this is strict-intensity work

- **Cross-repo likely** (guardkitfactory if Shape B picked, or shape-A's parsing logic is GuardKit-only — Phase 2 review confirms)
- **Touches Coach prompt** which is the load-bearing architectural contract for adversarial-cooperation correctness
- **Read-only invariant decision** for Shape B is an architectural choice worth recording in `.claude/rules/`
- **Cutover-blocker**: operator-stated requirement that this works "properly" before TASK-HMIG-011 fires
- **Must preserve substrate parity**: SDK harness path (Sonnet) and LangGraph harness path (qwen36-workhorse) must both produce the same `coach_turn_N.json` so the cutover decision is on substrate quality, not output-format divergence

Intensity = strict per [`/task-work` intensity table](../../../installer/core/commands/task-work.md).

## Implementation constraints (from Phase 2.5B review — must hold before Phase 3 ships)

These three constraints close gaps the Phase 2.5B architectural review flagged. The Phase 3 implementer MUST treat them as preconditions, not suggestions. Full justification in `docs/state/TASK-FIX-COACHOUT01/architectural_review.md` "Plan Gaps / Required Revisions".

1. **Event-passing mechanism is the `return_events: bool = False` parameter on `_invoke_with_role`**, NOT an instance attribute. When `True` (set only at the Coach call site `agent_invoker.py:1956`), `_invoke_with_role` returns `(None, harness_events)` instead of `None`. Player and specialist call sites are unchanged. Rejects the `self._last_harness_events` instance-attribute alternative because it carries hidden stale-state risk that any future concurrent-invocation refactor would silently activate.

2. **COACHSF01 error-string coupling must be verified.** `autobuild.py:5676–5678` matches on the literal substrings `"Coach decision not found"` and `"Coach decision invalid"`. The parser MUST raise exceptions whose `str(...)` representation contains those exact substrings — either by re-using `CoachDecisionNotFoundError`/`CoachDecisionInvalidError` (whose existing `__str__` already produces matching strings) or by prefixing custom raise messages with them verbatim. Add ONE unit test asserting that a `CoachDecisionNotFoundError` raised by the parser causes the COACHSF01 safety net to fire in `autobuild.py`.

3. **`coach_output_parser.extract_and_write` is a module-level function, not a method on a stateless class.** A `CoachOutputParser` class with no constructor arguments and no instance state would be a YAGNI violation. If parameterisation is needed for testing (e.g. swappable regex pattern or output-path strategy), the parameters become function kwargs with sensible defaults, not constructor arguments.

## Implementation sequencing recommendation

1. **Phase 2 (Planning)**: architectural review picks Shape A vs B. Reviewer should explicitly consider:
   - Cross-repo touch (guardkitfactory changes for Shape B)
   - Coach prompt evolution risk (changing what Coach is told to do)
   - Substrate parity (SDK Sonnet path keeps working)
   - Test coverage (regression tests for both harnesses)
   - The COACHSF01 safety net's role as defence-in-depth post-fix

2. **Phase 3 (Implementation)**:
   - Shape A: GuardKit-only changes to Coach prompt + post-LLM parsing
   - Shape B: GuardKit prompt change + GuardKitFactory custom tool implementation + cross-repo coordination

3. **Phase 4 (Testing)**: unit tests for the new path, parity tests across both harnesses, COACHSF01 still fires correctly on residual failures

4. **Phase 5 (Code Review)**: architectural review of the chosen shape, especially the read-only-invariant decision for Shape B

5. **Live smoke (post-merge)**: HMIG-010 run N+1 must exercise ≥6 Coach turns. Operator may need to bump SPECHANG cap to 1200s + --task-timeout to 6000s to give Wave 1 IA03 enough runway to actually converge — independent of this task.

## References

- Run-5 log (the failure motivating this task): [`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-5.md`](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-5.md) — lines 1156–1170 show COACHSF01 firing on turn 3 + F7 stall detection
- F17 root cause: [`docs/state/TASK-REV-HMIG/feature-run-incidents.md`](../../../docs/state/TASK-REV-HMIG/feature-run-incidents.md) I-007
- COACHSF01 safety net (defence-in-depth post-fix): [`tasks/completed/2026-06/TASK-FIX-COACHSF01-coach-soft-fail-on-decision-not-found.md`](../../completed/2026-06/TASK-FIX-COACHSF01-coach-soft-fail-on-decision-not-found.md)
- Canary F2 (the root substrate behaviour at Player scope): [`docs/state/TASK-REV-HMIG/canary-analysis.md`](../../../docs/state/TASK-REV-HMIG/canary-analysis.md) §3.F2
- Coach prompt: [`agent_invoker.py:2384-2415`](../../../guardkit/orchestrator/agent_invoker.py)
- Coach allowed_tools: [`agent_invoker.py:1959`](../../../guardkit/orchestrator/agent_invoker.py)
- Coach safety net: [`autobuild.py:5677-5732`](../../../guardkit/orchestrator/autobuild.py) `_emit_synthetic_coach_feedback`
- Feature-build invariants rule (Coach read-only): [`.claude/rules/feature-build-invariants.md`](../../../.claude/rules/feature-build-invariants.md)
- Blocked task: [TASK-HMIG-010](../../blocked/TASK-HMIG-010-full-feature-autobuild-validation.md)
- Cutover ceremony (also blocked): [TASK-HMIG-011](../../backlog/autobuild-harness-migration/TASK-HMIG-011-cutover-ceremony-flip-default-harness.md)

## Notes for the next session (context-limit handoff)

This task was filed at end of session 2026-06-06 after run 5's analysis. The conversation reached its context limit on the Coach output-contract question. Critical context for the next session:

- **Don't restart investigation** — run 5's evidence is complete and well-documented. The substrate-asymmetry root cause (Bash-heredoc emission contract under qwen36-workhorse) is empirically confirmed.
- **Phase 2 reviewer's job** is to pick Shape A vs B with rationale. Recommendation in the task body: A is cleaner long-term, B has smaller blast radius.
- **The COACHSF01 safety net stays** — it's defence-in-depth even after this fix lands.
- **Substrate quality findings (canary F6 multi-turn iteration drift)** are out of scope for this task. They are recorded for the cutover decision but don't gate this work.
- **Timeout-policy bumps** (SPECHANG cap 600s → 1200s, --task-timeout 3000s → 6000s) are independent of this task and recommended for run N+1 once this fix lands.

After this lands, TASK-HMIG-010's AC-008 verdict can be computed. The cutover decision becomes substrate-quality-only, not substrate-quality-PLUS-architectural-weakness.
