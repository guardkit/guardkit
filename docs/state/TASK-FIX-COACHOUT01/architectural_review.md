# TASK-FIX-COACHOUT01: Architectural Review

**Task**: TASK-FIX-COACHOUT01 — Coach Verdict-Emission Contract
**Reviewer**: architectural-reviewer
**Date**: 2026-06-06
**Review Phase**: 2.5B (Pre-Implementation, Design-Only)
**Plan reviewed**: `docs/state/TASK-FIX-COACHOUT01/implementation_plan.md`

---

## Verdict

| Field | Value |
|---|---|
| Chosen shape | **A** (Structured-Output Parsing) |
| Confidence | High |
| Overall score | **82/100** (strict threshold: 70 — APPROVED) |
| SOLID | 84/100 |
| DRY | 82/100 |
| YAGNI | 80/100 |

The plan passes the strict-intensity threshold. One integration-point ambiguity (Gap 1) must be resolved in the task file's implementation notes before Phase 3 starts. No blocker prevents Phase 2.7/2.8 from proceeding immediately.

---

## Rationale (paste verbatim into task file lines 134–139)

- **Root-cause elimination, not symptom mitigation.** Shape A removes the Bash-heredoc emission primitive entirely. Shape B replaces one fragile tool invocation (heredoc) with a simpler one (`CoachVerdictWrite`) but still depends on the Coach LLM executing a correct tool call with a correct `path` argument — it reduces cognitive load without eliminating the LLM-instruction-following dependency for verdict persistence.
- **Zero cross-repo blast radius.** Shape A is GuardKit-only. Shape B requires a coordinated guardkitfactory release. TASK-HMIG-011 (cutover ceremony) is already blocked on this fix; adding a cross-repo coordination dependency increases scheduling risk with no architectural benefit over Shape A.
- **Substrate parity is structural, not contractual.** Both `ClaudeSDKHarness` (`sdk_harness.py:340`) and `LangGraphHarness` (`langgraph_harness.py:370`) emit exactly one `AssistantMessageEvent` per turn carrying the full response text. The parser consumes `harness_events` without touching either harness. Verified directly against both implementations. Shape B parity is a per-harness implementation obligation that future refactors can silently break.
- **Read-only invariant is preserved entirely.** Preserving the invariant without exception (Shape A) is architecturally preferable to documenting a controlled exception (Shape B). The constraint exists to prevent Coach write access to worktree source files; a "constrained write" exception requires every future contributor to understand and enforce the constraint boundary.
- **Lower prompt regression risk on the working Sonnet path.** "End your response with a fenced JSON block" is standard instruction-tuned model behaviour. Shape B's "call CoachVerdictWrite with the full absolute worktree path as a string parameter" retains a structured-parameter composition step of comparable complexity to the heredoc, just with different syntax.

**picked_at**: 2026-06-06
**picked_by**: architectural-reviewer

---

## Substrate Parity Assessment

**Result: Shape A has structural parity. No harness changes required.**

**SDK harness** (`sdk_harness.py:319–340`): For every `AssistantMessage` from the SDK stream, `_extract_assistant_text(message)` joins text content blocks, and `yield AssistantMessageEvent(text=text, raw=message)` is emitted. The Coach's full prose + JSON block lands in `AssistantMessageEvent.text`. This event is appended to `harness_events` at `agent_invoker.py:2971`.

**LangGraph harness** (`langgraph_harness.py:357–370`): `extract_last_ai_message(result)` walks `result["messages"]` in reverse and returns the first non-empty `AIMessage.content` string (`extractors.py:17–49`). This is yielded as `AssistantMessageEvent(text=text, raw=result)`. For qwen36-workhorse via DeepAgents, the Coach's entire response — prose reasoning plus final JSON block — lands in this single field.

**Parity property**: SDK may emit multiple `AssistantMessageEvent` per turn (one per `AssistantMessage` in the stream); LangGraph emits exactly one. The plan's concatenation strategy (join all `AssistantMessageEvent.text` fields) is correct for SDK and identity-correct for LangGraph. The "take last JSON block" rule handles any exploratory JSON emitted mid-reasoning on either substrate.

**Shape B parity note** (for the record): `CoachVerdictWriteTool` would need to be registered in both harnesses when `role == "coach"`. This is a per-harness obligation not enforced by the ABC. A future harness refactor that drops the role-conditional registration silently reverts to the old behaviour with no test failure unless the parity test explicitly asserts tool-list membership.

---

## Plan Gaps / Required Revisions

### Gap 1 (revision required before Phase 3): `_invoke_with_role` event-return mechanism is underspecified

Plan section 2.3 correctly identifies that the parser needs access to `harness_events` but leaves the mechanism open: "instance attribute `self._last_harness_events`" vs. "return the list." This must be committed before writing Phase 3 code.

**The instance-attribute option** (`self._last_harness_events = []` at entry, populated inside `_invoke_with_role`) risks stale state if any concurrent invocation overwrites it. The orchestrator is currently single-threaded per task, so the race does not exist today, but the pattern is fragile as a long-term contract.

**Recommended mechanism**: Add an optional `return_events: bool = False` parameter to `_invoke_with_role`. When `True` (set only at the Coach call site), return `(None, harness_events)` instead of `None`. The Coach call site at `agent_invoker.py:1956` destructures the tuple. Player and specialist call sites are unchanged. This is a 4-line change: one parameter default, one conditional return, one destructuring at the Coach site, one pass-through to the parser.

**Add to task file implementation notes**: Commit to the `return_events` parameter approach. Implementer must not use `self._last_harness_events`.

### Gap 2 (verification item, not a blocker): COACHSF01 error-string coupling

`autobuild.py:5676–5678` matches on the literal substrings `"Coach decision not found"` and `"Coach decision invalid"`. The `invoke_coach` except block at `agent_invoker.py:1987` catches `(CoachDecisionNotFoundError, CoachDecisionInvalidError)` and returns `AgentInvocationResult(success=False, error=str(e))`. The parser must ensure `str(CoachDecisionNotFoundError(...))` contains `"Coach decision not found"` and `str(CoachDecisionInvalidError(...))` contains `"Coach decision invalid"`.

**Verify** that these exception classes produce matching string representations (check `agent_invoker.py` where they are defined). If they use `__str__` = message only, the parser's raise messages must use those exact substrings as prefixes. Add one unit test asserting that a `CoachDecisionNotFoundError` raised by the parser causes COACHSF01 to fire in the `autobuild.py` safety-net path.

### Gap 3 (implementation constraint): `CoachOutputParser` as class vs. function

Plan section 2.2 sketches `CoachOutputParser` as a class with `extract_and_write` as an instance method. The class carries no constructor arguments and no instance state in the sketch. A stateless class is a YAGNI violation. If no state is needed, implement `extract_and_write` as a module-level function in `coach_output_parser.py`. The class form is only justified if the regex pattern or output-path strategy needs to be parameterised at construction time (e.g. for test injection of a different pattern). If so, document the parameterisation explicitly.

---

## AC Coverage Matrix

| AC | Status | Note |
|---|---|---|
| AC-001 | Covered | This review provides the pick with rationale. Operator fills the task file table. |
| AC-002 | Covered | Plan section 2.5 traces `CoachDecisionNotFoundError` → `AgentInvocationResult(success=False)` → COACHSF01. Defence-in-depth preserved. |
| AC-003 | Partially covered | Live smoke is correctly deferred to post-merge. Plan section 8 Phase 5 acknowledges this. The deferred scope is intentional. |
| AC-004 | Covered | Plan section 8 Phase 3 specifies SDK-fake and LangGraph-fake parity tests with explicit exit criterion. |
| AC-005 | Covered | Plan section 2.6 lists `.claude/rules/feature-build-invariants.md` modification; Phase 4 is the exit criterion. |
| AC-006 | Partially covered | TASK-HMIG-010 unblocking is implicit in the plan but not stated. Add one sentence to the task file completion notes. Not a Phase 3 blocker. |
| AC-A1 | Covered | Plan section 2.1 gives the full replacement prompt block. |
| AC-A2 | Covered with Gap 1 caveat | Plan section 2.3 describes the integration. Gap 1 revision resolves the mechanism ambiguity before Phase 3. |
| AC-A3 | Covered | Plan section 2.3 edge-case table maps all 7 scenarios to typed exceptions or write success. |
| AC-A4 | Covered | Plan section 2.5 and the Shape B contrast in section 3.5 both confirm `allowed_tools` is unchanged. |

---

## Specific Question Answers

### 1. Substrate parity

Verified. Both harnesses emit `AssistantMessageEvent` with `text` populated. SDK: `sdk_harness.py:340`. LangGraph: `langgraph_harness.py:370`. No harness changes required for Shape A. Shape B cross-repo touch point is real: `langgraph_harness.py` would need a new `CoachVerdictWriteTool` registration block when `role == "coach"`. The plan's description of this change at section 3.3 is accurate.

### 2. Coach prompt regression risk

Shape A has lower regression risk on the working Sonnet path. The existing "Decision Format" block requires Sonnet to construct a Bash heredoc containing JSON — which it does reliably. The replacement instruction asks Sonnet to end its response with a fenced JSON block, which is strictly simpler. All other prompt sections (`## Your Responsibilities`, `## Original Requirements`, the evidence bundle, honesty guards) are unchanged. Shape B's smaller literal prompt change (one sentence swap) has even lower regression risk in isolation, but the new `CoachVerdictWrite` tool registration introduces a new integration surface that could fail silently if the tool is not registered correctly in the SDK harness.

### 3. "Absence of failure is not success" interaction

Shape A satisfies the rule. The parser oracle **runs** unconditionally after every `_invoke_with_role` Coach call. On every failure path (no JSON block, malformed JSON, missing fields), it raises a typed exception — a **negative signal**, not an absent signal. COACHSF01 then fires as the safety-net response to a negative signal. The false-green shape would require the parser to return `None` (no signal) and the orchestrator to treat `None` as approval. The plan's `extract_and_write` design has no return-`None` path — it either writes the file or raises. This is architecturally correct and satisfies the rule.

### 4. YAGNI: new module vs. 30-line inline

The module is justified at strict intensity. Eight distinct test cases, an atomic-write side effect, and a regex with a DOTALL flag across a potentially multi-kilobyte response text are not safely expressed as inline `if/elif` guards at the `invoke_coach` call site. At standard intensity, inline would be marginal. At strict intensity, the module boundary is correct. The YAGNI caution is the class-vs-function question in Gap 3.

### 5. AC coverage

See AC Coverage Matrix above. No AC is not-covered. AC-003 and AC-006 are partially covered by design (one is a post-merge gate, one is implicit).

### 6. Falsifier feasibility

The falsifier is tractable post-merge for Shape A. The claim "asking qwen36-workhorse to end its response with a fenced JSON block is reliably within its instruction-following envelope" is supported by the analogy to standard fine-tuning: instruction-tuned models answer questions in JSON format reliably because it is a common training pattern. The heredoc construction task is not — it requires composing a shell command containing a JSON document with escaped braces, in one syntactically correct pass, after extended reasoning. Removing the heredoc requirement directly targets the failure mode observed in run 5. The ≤1 COACHSF01 fire bound is reachable if the model produces well-formed fenced JSON at end-of-response in ≥5 of 6 turns.

---

## Risks Accepted / Risks Deferred

### Accepted (residual, mitigated)

1. **Coach prompt regression on Sonnet.** The "Decision Format" section changes. Mitigation: COACHSF01 defence-in-depth means regression degrades to synthetic feedback, not hard failure. AC-004 parity tests catch regression in the test suite before merge.

2. **LangGraph single-message extraction.** If qwen36-workhorse's final output is a tool-call-only `AIMessage` with empty `content`, `extract_last_ai_message` returns `None`, `text=""`, and the parser raises `CoachDecisionNotFoundError` → COACHSF01 fires. This is the correct safety-net path, not a data loss scenario. Mitigation: falsifier (AC-003) surfaces this in the live smoke.

3. **JSON-block collision: model emits valid JSON mid-reasoning.** The "take last block" rule and the `task_id` + `turn` field validation together filter most false positives. Mitigation: AC-A3 unit tests must explicitly assert that a mid-reasoning JSON block with a mismatched `task_id` is rejected in favour of the correct final block, or that the last block wins even if it has wrong field values (which would then raise `CoachDecisionInvalidError`).

### Deferred to post-merge

1. **Falsifier (AC-003).** HMIG-010 run N+1 under `GUARDKIT_HARNESS=langgraph`, ≥6 Coach turns, ≥95% emission rate, ≤1 COACHSF01 fire. Operator should run with SPECHANG cap 1200s and task-timeout 6000s per the task's implementation notes.

2. **New harness substrate support.** Any future harness must emit `AssistantMessageEvent` with non-empty `text`. The parity test must be extended. Same obligation as `harness-cancellation-contract.md` for `cancel()` implementations.

---

## Recommended Next Step

Revise plan with these three changes (all are notes/constraints, not structural plan changes):

1. **Section 2.3**: Commit to `return_events: bool = False` parameter on `_invoke_with_role` as the event-passing mechanism. Remove the instance-attribute option. Add this as an implementation constraint in the task file.

2. **Section 2.3**: Add a verification note — `str(CoachDecisionNotFoundError(...))` must contain `"Coach decision not found"` (the COACHSF01 match string). Add one unit test asserting this.

3. **Section 2.2**: Implement `extract_and_write` as a module-level function unless constructor parameterisation is required.

Once these notes are added to the task file's implementation notes section:

**Approve plan → Phase 2.7 → Phase 2.8 checkpoint with this rationale prefilled:**

> Shape A chosen (architectural-reviewer, 2026-06-06, score 82/100). GuardKit-only change (~150 LOC). Integration-point mechanism committed to `return_events` parameter. COACHSF01 defence-in-depth preserved and verified. Substrate parity confirmed against both harnesses without harness changes. Read-only invariant fully preserved. Cross-repo blast radius: none. Falsifier deferred to HMIG-010 run N+1.
