# TASK-FIX-COACHOUT01: Coach Verdict-Emission Contract — Implementation Plan

**Phase:** 2 (Design Only)
**Intensity:** Strict
**Authored:** 2026-06-06
**Reviewer decision required at:** Phase 2.5B — pick Shape A or B, record in task file lines 134–139

---

## 1. Context Summary

Under the LangGraph harness (qwen36-workhorse), Coach must emit its verdict by constructing a multi-line Bash heredoc that embeds a JSON document, then executing it via the `Bash` tool — after approximately 140 seconds of adversarial reasoning about real test failures. Run-5 of FEAT-AOF measured a ~67% success rate for this operation: 2 of 3 Coach turns produced a real verdict; the third failed and required the COACHSF01 safety net to emit a synthetic feedback decision. The Sonnet/SDK path does this reliably because Sonnet's instruction-following is well above the heredoc-construction envelope; qwen36-workhorse is not. The defect is substrate-asymmetric: the same orchestrator contract behaves differently depending on which harness is active.

This is a direct instance of the pattern documented in `.claude/rules/harness-cancellation-contract.md` — an orchestrator-layer contract (the "write your verdict via Bash") was designed when only the SDK substrate existed and was never stress-tested against the LangGraph substrate. The fix must eliminate the Bash-heredoc emission primitive entirely, replacing it with a mechanism that places equal cognitive load on both models and is not substrate-specific. Two fix shapes exist; the architectural reviewer picks one. Shape A (structured-output parsing) requires no harness changes and no cross-repo work. Shape B (constrained Write tool) requires guardkitfactory changes and a controlled violation of the read-only invariant. Both shapes preserve the COACHSF01 defence-in-depth safety net.

---

## 2. Shape A — Structured Output Parsing (Full Design)

### 2.1 Coach Prompt Change

Replace the entire "Decision Format" block at `agent_invoker.py:2392-2438` with:

```
## Decision Format

End your response with a fenced JSON block. Do NOT use Bash to write a file.
The orchestrator will read your decision directly from your response text.

Your JSON block MUST appear at the end of your response, after all prose reasoning,
in this exact form:

```json
{
  "task_id": "<task_id>",
  "turn": <turn>,
  "decision": "approve" | "feedback",
  ...fields as specified below...
}
```

For APPROVAL, the JSON block must contain:
{
  "task_id": "...",
  "turn": N,
  "decision": "approve",
  "validation_results": {
    "requirements_met": ["..."],
    "tests_run": true,
    "tests_passed": true,
    "test_command": "...",
    "test_output_summary": "...",
    "code_quality": "...",
    "edge_cases_covered": ["..."]
  },
  "criteria_verification": [...],
  "rationale": "..."
}

For FEEDBACK, the JSON block must contain:
{
  "task_id": "...",
  "turn": N,
  "decision": "feedback",
  "issues": [...],
  "criteria_verification": [...],
  "rationale": "..."
}

CRITICAL: The fenced JSON block MUST be the last thing in your response.
Do not write any prose after the closing ``` fence.
```

The `criteria_verification` and `honesty_verification` examples already rendered into the prompt by `_render_evidence_bundle_section` and `_build_coach_prompt` remain unchanged — only the "write to file" instruction is replaced.

### 2.2 Orchestrator-Side Parser

**Location:** New module `guardkit/orchestrator/coach_output_parser.py`

**Design:**

```python
class CoachOutputParser:
    """Extract and persist a Coach verdict from LLM response text.

    Called by invoke_coach() immediately after _invoke_with_role()
    returns and harness_events is populated, before _load_agent_report().
    """

    FENCE_PATTERN = re.compile(
        r"```json\s*\n(\{.*?\})\s*\n```",
        re.DOTALL,
    )

    def extract_and_write(
        self,
        harness_events: list[HarnessEvent],
        task_id: str,
        turn: int,
        output_path: Path,
    ) -> None:
        """Extract last valid fenced JSON block and write coach_turn_N.json.

        Raises:
            CoachDecisionNotFoundError: if no fenced JSON block is present
                in any AssistantMessageEvent.
            CoachDecisionInvalidError: if the last block is malformed JSON
                or is missing required fields.
        """
        ...
```

**Extraction logic:**

1. Collect text from all `AssistantMessageEvent` instances in `harness_events` in order. Concatenate with newline separator to reconstruct the full response text (handles multi-event streaming from both harnesses).
2. Apply `FENCE_PATTERN.findall(full_text)` — returns all captured JSON bodies.
3. If zero matches: raise `CoachDecisionNotFoundError("No fenced JSON block found in Coach response")`. COACHSF01 catches this downstream.
4. If one or more matches: take the **last** match (handles models that emit exploratory JSON mid-reasoning then a corrected final block).
5. Parse with `json.loads(candidate)`. If `JSONDecodeError`: raise `CoachDecisionInvalidError(f"Last fenced JSON block is malformed: {e}")`.
6. Validate required fields: `task_id`, `turn`, `decision` (must be `"approve"` or `"feedback"`). If any missing: raise `CoachDecisionInvalidError(f"Missing required fields: {missing}")`.
7. Atomic write: write to `output_path.with_suffix('.tmp')`, then `os.replace(tmp, output_path)`.

**Edge case matrix:**

| Scenario | Behaviour |
|---|---|
| No JSON block in response | `CoachDecisionNotFoundError` → COACHSF01 fires |
| Multiple JSON blocks | Last block used (handles reasoning-then-corrected-decision pattern) |
| Malformed JSON in last block | `CoachDecisionInvalidError` → COACHSF01 fires |
| Missing `task_id` / `turn` / `decision` | `CoachDecisionInvalidError` → COACHSF01 fires |
| Valid block but `decision` not in `{"approve","feedback"}` | `CoachDecisionInvalidError` |
| Partial JSON mid-stream (block split across events) | Handled by concatenating all `AssistantMessageEvent.text` before regex |
| No `AssistantMessageEvent` at all (harness emitted only `ResultMessageEvent`) | Zero matches → `CoachDecisionNotFoundError` |

### 2.3 Integration Point in `invoke_coach`

Current sequence at `agent_invoker.py:1956-1967`:

```python
await self._invoke_with_role(prompt=prompt, agent_type="coach", ...)
decision = self._load_agent_report(task_id, turn, "coach")
self._validate_coach_decision(decision)
```

New sequence (two lines added between `_invoke_with_role` and `_load_agent_report`):

```python
await self._invoke_with_role(prompt=prompt, agent_type="coach", ..., return_events=True)
# Shape A: parse assistant text, write coach_turn_N.json from orchestrator side
parser = CoachOutputParser()
output_path = self._get_report_path(task_id, turn, "coach")
parser.extract_and_write(self._last_harness_events, task_id, turn, output_path)
# Existing file-based loader unchanged
decision = self._load_agent_report(task_id, turn, "coach")
self._validate_coach_decision(decision)
```

`_invoke_with_role` already populates `harness_events: List[HarnessEvent]` locally (line 2790). The integration needs either: (a) `_invoke_with_role` returns the list, or (b) it writes to a short-lived instance attribute `self._last_harness_events` cleared at the start of each call. Option (b) requires no signature change to `_invoke_with_role`; option (a) is cleaner but touches the method signature used by Player and specialist invocations. Recommendation: instance attribute `_last_harness_events` scoped to `invoke_coach` only, set to `[]` at entry and populated by `_invoke_with_role` via assignment. Either approach is a 2-line change at the call site.

`_load_agent_report` and `_validate_coach_decision` are completely unchanged. The parser writes the file; the loader reads it. One-path change.

### 2.4 Substrate Parity

Both SDK and LangGraph harnesses already yield `AssistantMessageEvent` with `text` populated (harness adapter contract, `adapter.py:33-45`). No harness changes required. The parser operates on the typed event list that `_invoke_with_role` already assembles at line 2790.

### 2.5 COACHSF01 Safety Net

`CoachDecisionNotFoundError` and `CoachDecisionInvalidError` raised by the parser propagate to `invoke_coach`'s `except` block at `agent_invoker.py:1987`, which returns `AgentInvocationResult(success=False, error=...)`. The COACHSF01 check in `autobuild.py:5672-5698` catches exactly this pattern (`"Coach decision not found"` / `"Coach decision invalid"` in `result.error`) and emits synthetic feedback. Defence-in-depth is fully preserved; the parser is just the new primary path that COACHSF01 backs up.

### 2.6 Files Touched (Shape A — GuardKit only)

| File | Change |
|---|---|
| `guardkit/orchestrator/coach_output_parser.py` | **New** — `CoachOutputParser` class, ~80 LOC |
| `guardkit/orchestrator/agent_invoker.py` | Prompt change (~25 lines replaced), parser call (~5 lines added at `invoke_coach`) |
| `tests/unit/test_coach_output_parser.py` | **New** — unit tests for all edge cases, ~100 LOC |
| `tests/integration/test_coach_parity.py` | **New or extend** — parity test driving both SDK and LangGraph harness fakes, ~40 LOC |
| `.claude/rules/feature-build-invariants.md` | Add note: "Coach emits verdict as fenced JSON block in response text; orchestrator writes coach_turn_N.json" |

**Estimated LOC:** ~120–200 new/changed lines, all in GuardKit.

### 2.7 Cross-Repo Impact (Shape A)

**NONE.** guardkitfactory is untouched. No LangGraph tool registration changes. No SDK harness changes.

---

## 3. Shape B — Constrained Write Tool (Full Design)

### 3.1 Tool Design

**Name:** `CoachVerdictWrite`

**Input schema:**
```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Absolute path to coach_turn_N.json within the autobuild state dir"
    },
    "content": {
      "type": "string",
      "description": "JSON string of the Coach verdict"
    }
  },
  "required": ["path", "content"]
}
```

**Path validation pattern:** The tool validates `path` against:
```
^<worktree_root>/\.guardkit/autobuild/TASK-[A-Z0-9-]+/coach_turn_\d+\.json$
```
The `worktree_root` is injected at tool construction time (known by the harness). Any path outside this pattern returns an error response and does NOT write to disk.

**Atomic write semantics:** Write to `<path>.tmp` then `os.replace(tmp, path)` — identical to how the Player writes `task_work_results.json`. Raises tool error on `OSError`.

**Error responses:** Structured `{"error": "...", "code": "INVALID_PATH" | "WRITE_FAILED"}` returned as the tool result so the Coach LLM sees a clear failure message and can attempt to correct the path.

### 3.2 SDK Harness Integration

The Anthropic `claude-agent-sdk` supports custom tool injection via the `ClaudeAgentOptions.tools` list. Each entry is a tool schema dict (`{"name": ..., "description": ..., "input_schema": ...}`) plus a Python callable registered as the tool handler.

**Location:** `guardkit/orchestrator/harness/sdk_harness.py` — add `CoachVerdictWriteTool` as a local class, instantiated with `worktree_root` at harness construction time. Register in the tool list when `role == "coach"`.

The tool handler runs in-process (no subprocess): `sdk_harness.py` already runs tool calls in-process for any custom tools it holds. No subprocess concern.

### 3.3 LangGraph Harness Integration

The LangGraph harness lives in `guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py`. DeepAgents exposes tools as LangChain `BaseTool` subclasses registered on the agent's tool list at agent construction time.

**Location:** `guardkitfactory/src/guardkitfactory/tools/coach_verdict_write.py` — new `CoachVerdictWriteTool(BaseTool)`. The harness passes `worktree_root` at construction. When `role == "coach"`, this tool is added to the agent's tool list before `agent.ainvoke()`.

This is a **cross-repo change**: guardkitfactory must be updated alongside GuardKit. The two repos must be released in coordination.

### 3.4 Coach Prompt Change

The "Decision Format" block changes only the emission instruction:

Replace:
```
Write your decision to:
{self.worktree_path}/.guardkit/autobuild/{task_id}/coach_turn_{turn}.json
```

With:
```
Use the CoachVerdictWrite tool to write your decision. The tool accepts:
  - path: "{self.worktree_path}/.guardkit/autobuild/{task_id}/coach_turn_{turn}.json"
  - content: your verdict JSON as a string

The tool validates the path and writes atomically. Do NOT use Bash for this.
```

The JSON schema examples (approval / feedback) remain identical. The prompt is shorter and simpler than today's because there is no heredoc syntax to demonstrate.

### 3.5 `allowed_tools` Change

`agent_invoker.py:1959`:

```python
# Before
allowed_tools=["Read", "Bash", "Grep", "Glob"]

# After
allowed_tools=["Read", "Bash", "Grep", "Glob", "CoachVerdictWrite"]
```

Note: `Bash` remains in the list. Removing it would be a scope-creep change — Coach may still use Bash for test execution and file inspection. Only the verdict-write instruction changes.

### 3.6 Read-Only Invariant Treatment

The `feature-build-invariants.md` rule currently states implicitly that Coach uses `Read` and `Bash` only (no `Write`). Shape B introduces a constrained write exception. The rule must be updated:

> **Coach access:** Coach uses Read, Bash, Grep, Glob for verification. It also uses `CoachVerdictWrite` to persist its verdict — a single constrained write whose path is validated by the tool to `.guardkit/autobuild/{task_id}/coach_turn_N.json` only. Coach has NO write access to worktree source code or test files.

This is an architectural decision that weakens the "read-only" invariant in a controlled, documented way. It should also be recorded as a new entry in `.claude/rules/` or as an addendum to the existing invariants rule.

### 3.7 COACHSF01 Safety Net

Unchanged. If the Coach LLM fails to call `CoachVerdictWrite` (or calls it with an invalid path, or the tool write fails), `coach_turn_N.json` will not exist on disk. `_load_agent_report` raises `CoachDecisionNotFoundError`. COACHSF01 fires. Defence-in-depth preserved.

### 3.8 Files Touched (Shape B)

| File | Change | Repo |
|---|---|---|
| `guardkit/orchestrator/agent_invoker.py` | Prompt change (~10 lines), `allowed_tools` line | GuardKit |
| `guardkit/orchestrator/harness/sdk_harness.py` | Add `CoachVerdictWriteTool`, register when `role=="coach"` | GuardKit |
| `tests/unit/test_coach_verdict_write_tool.py` | **New** — unit tests for path validation, atomic write, error responses | GuardKit |
| `tests/integration/test_coach_parity.py` | **New or extend** — parity test across both harnesses | GuardKit |
| `.claude/rules/feature-build-invariants.md` | Document constrained-write exception | GuardKit |
| `guardkitfactory/src/guardkitfactory/tools/coach_verdict_write.py` | **New** — `CoachVerdictWriteTool(BaseTool)` | guardkitfactory |
| `guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py` | Register tool when `role=="coach"` | guardkitfactory |
| `guardkitfactory/tests/test_coach_verdict_write.py` | **New** — tool tests in factory repo | guardkitfactory |

**Estimated LOC:** ~80–150 GuardKit + ~60–100 guardkitfactory = ~140–250 total.

**Cross-repo impact:** YES — guardkitfactory must be updated and released before or simultaneously with the GuardKit change.

---

## 4. Shape Comparison Table

| Criterion | Shape A (Structured Output) | Shape B (Constrained Write Tool) |
|---|---|---|
| **Blast radius** | GuardKit only — 3 files changed/created | GuardKit + guardkitfactory — 5 files GuardKit, 3 files guardkitfactory |
| **Cross-repo** | No | Yes — requires coordinated guardkitfactory release |
| **Coach prompt evolution** | Meaningful change — removes "write to file", adds "end with fenced JSON block" | Smaller change — swaps Bash heredoc instruction for CoachVerdictWrite call |
| **Read-only invariant** | Fully preserved — Coach never writes anything | Weakened with a controlled exception — must be documented in invariants rule |
| **Substrate parity risk** | None — `AssistantMessageEvent.text` is emitted by both SDK and LangGraph harnesses today | Requires `CoachVerdictWriteTool` to be wired in both harnesses; parity is a per-substrate impl contract |
| **Model portability** | Any model that can emit fenced JSON at end of response — lower bar than heredoc construction | Any model that can invoke a named tool with two string params — comparable to heredoc but simpler |
| **COACHSF01 still load-bearing** | Yes — `CoachDecisionNotFoundError` / `CoachDecisionInvalidError` propagate unchanged | Yes — tool invocation failure leaves no file on disk, same error path |
| **Test surface** | Unit: parser edge cases (8 cases). Integration: harness-text → file parity. | Unit: tool path validation, write atomicity, error responses. Integration: tool invocation → file parity across both harnesses. |
| **Estimated total LOC** | ~120–200 (GuardKit only) | ~140–250 (GuardKit + guardkitfactory) |
| **Risk if Shape fails partially** | Parser module can be bypassed with a feature flag; COACHSF01 keeps running | Tool missing from one harness → that substrate silently reverts to old behaviour (COACHSF01 catches but parity is broken) |

---

## 5. Recommendation

**Shape A is recommended.**

- **Eliminates the root cause rather than papering over it.** The Bash-heredoc emission contract is the defect. Shape A removes that contract entirely; Shape B replaces a hard tool call (heredoc) with a simpler tool call (`CoachVerdictWrite`) — an improvement, but still depends on the Coach LLM making a correct tool invocation rather than the orchestrator reading its natural output.
- **No cross-repo coordination required.** Shape B requires a coordinated guardkitfactory release, which introduces scheduling risk and makes the fix harder to revert if a regression surfaces post-cutover.
- **Read-only invariant is architecturally cleaner to preserve than to document an exception to.** The invariant exists because Coach write access to arbitrary paths would be a security surface. Shape A keeps that surface exactly as it is today.
- **Cognitive load comparison favours Shape A.** Asking a model to end its response with a JSON block is standard LLM structured-output practice. The JSON schema examples already rendered in the Coach prompt give the model a complete template. Asking it to call a named tool with the correct `path` argument (including the full absolute worktree path) and a stringified JSON `content` argument is comparable complexity to the heredoc — it eliminates the Bash syntax overhead but retains the "compose a structured parameter" requirement.
- **Implementation is bounded.** Shape A touches `agent_invoker.py` in two narrow spots (prompt block and two lines in `invoke_coach`), plus a new parser module with clear error contracts. The changes are easily reviewable and reversible.

The sole genuine advantage of Shape B is that it keeps the prompt instruction closer to today's "call a tool to write the file" framing, which may be easier for models trained on agentic tool-use patterns. If post-cutover evidence shows that Shape A's structured-output extraction is unreliable on future models (e.g. a model that frequently embeds prose after the JSON block), Shape B can be revisited as a follow-up. Shape A should be attempted first because it has no cross-repo dependency.

---

## 6. Files to Create / Modify (Both Shapes)

### Shape A Files

| File | Action | Key Change |
|---|---|---|
| `guardkit/orchestrator/coach_output_parser.py` | Create | `CoachOutputParser.extract_and_write()`, regex extraction, edge-case handling |
| `guardkit/orchestrator/agent_invoker.py` | Modify (lines 2392–2438, 1956–1967) | Replace Decision Format prompt block; add parser call in `invoke_coach` |
| `tests/unit/test_coach_output_parser.py` | Create | 8+ edge-case unit tests |
| `tests/integration/test_coach_parity.py` | Create or extend | SDK-fake and LangGraph-fake harness parity assertion |
| `.claude/rules/feature-build-invariants.md` | Modify | Add note on structured-output verdict emission |

### Shape B Files

| File | Action | Key Change |
|---|---|---|
| `guardkit/orchestrator/harness/sdk_harness.py` | Modify | Add `CoachVerdictWriteTool`, register when `role=="coach"` |
| `guardkit/orchestrator/agent_invoker.py` | Modify (lines 2392–2415, 1959) | Replace prompt emission instruction; extend `allowed_tools` |
| `tests/unit/test_coach_verdict_write_tool.py` | Create | Path validation, atomic write, error response tests |
| `tests/integration/test_coach_parity.py` | Create or extend | Tool invocation → file parity across both harnesses |
| `.claude/rules/feature-build-invariants.md` | Modify | Document constrained-write exception |
| `guardkitfactory/src/guardkitfactory/tools/coach_verdict_write.py` | Create | `CoachVerdictWriteTool(BaseTool)` with path validation |
| `guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py` | Modify | Register `CoachVerdictWriteTool` when `role=="coach"` |
| `guardkitfactory/tests/test_coach_verdict_write.py` | Create | Tool-level tests in factory repo |

---

## 7. Risks and Mitigations

### Risk 1: Substrate parity drift (both shapes)

**Shape A specific:** If a future harness emits assistant text through a mechanism other than `AssistantMessageEvent.text` (e.g. a streaming-chunk event type not yet in the harness ABC), the parser will find an empty text corpus and raise `CoachDecisionNotFoundError`. COACHSF01 fires; no data loss, but the fix regresses silently on that new substrate.

**Mitigation:** The parity test (`test_coach_parity.py`) asserts that both the SDK-fake and LangGraph-fake harnesses produce a parseable `coach_turn_N.json` from a synthetic response. This test must be extended when any new harness is added (same pattern as `harness-cancellation-contract.md` detection recipe step 2).

**Shape B specific:** If the guardkitfactory `CoachVerdictWriteTool` is not registered for `role=="coach"` (e.g. a future harness refactor drops the role-conditional registration), the Coach LLM will attempt `CoachVerdictWrite`, receive a "tool not found" error, and likely fall back to Bash heredoc or emit no verdict. COACHSF01 catches the no-verdict case but does not detect the Bash-fallback case.

**Mitigation:** The parity test must verify that `CoachVerdictWrite` is in the tool list presented to the model when `role=="coach"` for both harnesses.

### Risk 2: Coach prompt regression on Sonnet (SDK harness)

Changing the Coach prompt is the highest-risk line item. Sonnet on the SDK harness currently succeeds at the Bash heredoc ~100% of the time. Any prompt change could disturb other Coach behaviours (honesty gate reading, AC verification, criteria_verification output format).

**Mitigation (Shape A):** The change is surgical — only the "Decision Format" section is modified. All other prompt sections (`## Your Responsibilities`, `## Original Requirements`, the evidence bundle sections, the absence-of-failure guards) are unchanged. The new instruction ("end your response with a fenced JSON block") is strictly simpler for Sonnet to follow than the heredoc. Regression risk is low but must be validated in the AC-003 live smoke.

**Mitigation (Shape B):** Even smaller prompt change — only one sentence changes ("use the CoachVerdictWrite tool" replaces "write to {path} via Bash"). Regression risk is lower than Shape A but cross-repo dependency is higher.

**For both shapes:** The COACHSF01 safety net ensures that a prompt regression does not cause a hard failure — it degrades to synthetic-feedback and the Player retries. The falsifier bound (COACHSF01 fires ≤1 time per run) will surface any degradation empirically.

### Risk 3: COACHSF01 masking residual emission failures

The task falsifier explicitly bounds COACHSF01 to ≤1 fire per run. The risk is that the fix reduces the rate from ~33% (run-5 baseline: 1/3 turns) to, say, 10–15% (2 fires per 20-turn run), which would satisfy no falsifier criterion but would look acceptable if COACHSF01 is counted rather than the raw emission rate.

**Mitigation:** The falsifier requires ≥95% emission rate across ≥6 Coach turns AND ≤1 COACHSF01 fire. Both conditions must hold simultaneously. The live smoke (AC-003) must be evaluated against both numbers. If COACHSF01 fires more than once in the 6-turn sample, the task is not complete regardless of emission rate.

---

## 8. Implementation Phases (Sequencing)

### Phase 1 — New parser module + unit tests (90 minutes)

**Shape A:** Write `guardkit/orchestrator/coach_output_parser.py` with `CoachOutputParser.extract_and_write()`. Write `tests/unit/test_coach_output_parser.py` covering all 8 edge cases from section 2.3. All tests must pass at 100%.

**Shape B:** Write `guardkit/orchestrator/harness/sdk_harness.py` `CoachVerdictWriteTool` + `guardkitfactory/tools/coach_verdict_write.py` `CoachVerdictWriteTool(BaseTool)`. Write unit tests for path validation and atomic write in both repos.

**Exit criterion:** `pytest tests/unit/test_coach_output_parser.py` (Shape A) or equivalent (Shape B) passes at 100% with no stubs.

### Phase 2 — Coach prompt change + integration wiring (45 minutes)

**Shape A:** Replace the Decision Format block at `agent_invoker.py:2392–2438`. Add the parser call in `invoke_coach` at `agent_invoker.py:1963–1967`. Wire `_last_harness_events` or return-value mechanism.

**Shape B:** Replace the prompt emission instruction. Extend `allowed_tools` at line 1959. Register tool in both harnesses.

**Exit criterion:** `pytest guardkit/orchestrator/` passes at 100% (existing unit tests must not regress).

### Phase 3 — Parity + integration tests (45 minutes)

Write or extend `tests/integration/test_coach_parity.py`. The test must:
1. Instantiate a synthetic `AssistantMessageEvent` stream with a valid fenced JSON block (Shape A) or a `ToolUseEvent(name="CoachVerdictWrite", ...)` (Shape B).
2. Run through the new code path.
3. Assert `coach_turn_N.json` is written correctly.
4. Repeat with an SDK-harness fake and a LangGraph-harness fake.

**Exit criterion:** Parity test passes for both substrate fakes.

### Phase 4 — Rule + documentation update (15 minutes)

Update `.claude/rules/feature-build-invariants.md` per the chosen shape. No new rule file required — the existing invariants rule is the right home.

**Exit criterion:** Rule file updated; no orphaned references.

### Phase 5 — End-to-end smoke readiness check (15 minutes)

Confirm the overall test suite passes (`pytest tests/` at coverage thresholds). Confirm the falsifier condition is testable against the live smoke run (AC-003): `guardkit autobuild feature FEAT-AOF --fresh --model qwen36-workhorse` with `GUARDKIT_HARNESS=langgraph`. This phase does not execute the live smoke — it prepares the runtime configuration notes for the operator who will run it post-merge.

**Exit criterion:** Test suite green. Operator notes recorded in task file for post-merge validation.

**Total estimated duration:** 3.5–4 hours.

---

## Context Used

| Source | What it informed |
|---|---|
| `tasks/in_progress/autobuild-harness-migration/TASK-FIX-COACHOUT01-coach-verdict-emission-contract.md` (full) | Problem framing, two fix shapes, ACs, falsifier, operator context |
| `guardkit/orchestrator/agent_invoker.py:1945–1985` | Current `invoke_coach` flow — `_invoke_with_role` → `_load_agent_report` → `_validate_coach_decision` sequence |
| `guardkit/orchestrator/agent_invoker.py:2371–2438` | Exact current "Decision Format" prompt block — the heredoc instruction to be replaced |
| `guardkit/orchestrator/agent_invoker.py:2719–2731, 2769–2971` | `_invoke_with_role` internals — `harness_events: List[HarnessEvent]` already assembled at line 2790; `AssistantMessageEvent` processing at lines 2945–2971 |
| `guardkit/orchestrator/agent_invoker.py:4109–4158` | `_load_agent_report` — file-based reader, raises `CoachDecisionNotFoundError`/`CoachDecisionInvalidError`; unchanged by both shapes |
| `guardkit/orchestrator/harness/adapter.py:33–117` | `AssistantMessageEvent.text` contract confirmed for both harnesses; `HarnessEvent` union |
| `guardkit/orchestrator/autobuild.py:5670–5732` | COACHSF01 safety net — exact error string match (`"Coach decision not found"` / `"Coach decision invalid"`); synthetic feedback emit path |
| `.claude/rules/harness-cancellation-contract.md` | Meta-frame: orchestrator-layer contract paired with specific substrate → substrate-asymmetric when new substrate lands; remediation pattern (push primitive down into adapter) |
| `.claude/rules/feature-build-invariants.md` | Coach read-only invariant text; where Shape B exception must be documented |
| `.claude/rules/absence-of-failure-is-not-success.md` | Informed COACHSF01 masking risk analysis (zero-cardinality false-green meta-frame) |
