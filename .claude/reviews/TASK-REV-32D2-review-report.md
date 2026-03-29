# Review Report: TASK-REV-32D2

## Adversarial Cooperation Template Design Review for LangChain DeepAgents SDK

**Revision 3** — SDK-validated against DeepAgents 0.4.12 source code + cross-referenced against working `agentic-dataset-factory` production code (currently executing 26-hour run, 7 hours in, TASK-REV-R2A1 and TASK-REV-7617 fixes applied).

---

## Executive Summary

The `langchain-deepagents-weighted-evaluation` template design is **architecturally sound** with strong foundations from Wave 1 code and clear alignment between the conversation starter spec and the implementation guide. SDK source code validation confirms **3 critical issues** and reveals **1 new critical issue** (F5) not caught in the initial review. All 7 design decisions are confirmed with SDK-validated rationale.

**Architecture Score: 72/100** (revised down from 78 due to F5)

**KEY REVISION 3 FINDING**: All critical findings (F1, F2, F5) have already been solved in the `agentic-dataset-factory` production code. The working factories (`agents/player.py`, `agents/coach.py`) provide the **exact proven pattern** the template should adopt. The template needs to align with its own exemplar codebase.

| Category | Score | Notes |
|----------|-------|-------|
| SOLID Compliance | 8/10 | Strong SRP and DIP; OCP needs attention in CoachVerdict evolution |
| DRY Adherence | 7/10 | Prompt template duplication between base and adversarial needs addressing |
| YAGNI Compliance | 9/10 | Well-scoped; NATS transport correctly deferred |
| SDK Alignment | 5/10 | Revised down: F1, F2 confirmed critical; F5 (memory param bug) is new |
| Cross-Domain Applicability | 9/10 | GOAL.md pattern is genuinely domain-agnostic |
| Evidence Base | 10/10 | 11 runs, 31 fixes, 84% prevention rate — exceptional |

---

## Section 1: Architecture Validation

### 1.1 Three-Role Separation — VALIDATED with caveats

The three-role architecture (Orchestrator + Player + Coach) is correctly designed:

- **Orchestrator** as plain Python loop (NOT a DeepAgent) — correct. The `agent.py.template` confirms module-level wiring with `OrchestratorWriteGate` as the coordination mechanism.
- **Player** as DeepAgent with domain tools — correct intent, incorrect SDK call (see F1).
- **Coach** as DeepAgent with NO tools — correct intent, incorrect SDK call (see F2).

**CRITICAL FINDING F1: Player factory uses `create_deep_agent()` — CONFIRMED tool separation violation.**

SDK source (`deepagents/graph.py` lines 249-267) proves `create_deep_agent()` unconditionally builds this middleware stack:

```python
deepagent_middleware = [
    TodoListMiddleware(),           # adds: write_todos
    # MemoryMiddleware (if memory param set)
    FilesystemMiddleware(backend=backend),  # adds: ls, read_file, write_file, edit_file, glob, grep, execute
    SubAgentMiddleware(backend=backend, subagents=all_subagents),  # adds: task
    create_summarization_middleware(model, backend),
    AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),
    PatchToolCallsMiddleware(),
]
```

The LangChain skills plugin (`deep-agents-core`) confirms in its `<boundaries>` section: **"Core middleware removal (TodoList, Filesystem, SubAgent always present)"** — there is NO way to disable these within `create_deep_agent()`.

`create_agent()` source (`langchain/agents/factory.py` line 193-244) confirms that middleware tools are composed into the agent:
```python
middleware_tools = [t for m in middleware for t in getattr(m, "tools", [])]
available_tools = middleware_tools + regular_tools  # Line 244
```

**SDK-validated impact**: The Player created by `player.py.template` receives `search_data` + `write_todos` + `ls` + `read_file` + **`write_file`** + **`edit_file`** + `glob` + `grep` + `execute` + `task` = **10 unwanted tools**, including `write_file` and `edit_file` which completely bypass the orchestrator-gated writes invariant.

**Confirmed fix**: Use `create_agent()` directly (no FilesystemMiddleware injection) or `create_restricted_agent()` from `factory_guards.py`.

### 1.2 Coach Factory — CRITICAL FINDING F2: CONFIRMED

Same issue as F1. The `coach.py.template` calls `create_deep_agent(tools=[])`, but the middleware stack still injects all filesystem tools. The Coach ends up with `write_todos` + `ls` + `read_file` + `write_file` + `edit_file` + `glob` + `grep` + `execute` + `task` = **9 tools** despite `tools=[]`.

**SDK-validated**: `tools=[]` only controls user-provided tools. Middleware tools are **always added regardless** of the `tools` parameter (line 244: `available_tools = middleware_tools + regular_tools`).

This violates the D5 invariant ("Coach: NO tools ever").

### 1.3 Tool Separation Enforcement — PARTIAL

`validate_player_tools()` in `orchestrator_pattern.py.template` only checks for `write_output`. It does NOT catch the FilesystemMiddleware-injected tools (`write_file`, `edit_file`, `execute`). The `factory_guards.py` module has the correct `assert_tool_inventory()` that does exact-set comparison — this is the right mechanism.

**Recommendation**: Wave 4 tasks MUST mandate use of `assert_tool_inventory()` (from `factory_guards.py`) instead of the weaker `validate_player_tools()`. The adversarial template should use the stronger guard.

### 1.4 Orchestrator-Gated Writes — VALIDATED

`OrchestratorWriteGate` is well-designed:
- Configurable `max_retries` (default 3)
- Callbacks for rejection, acceptance, exhaustion
- Structured `WriteResult` return type
- JSON validation before write
- No infinite loops (retry exhaustion returns failure)

This is production-quality code that correctly encodes the TRF-005/TRF-006 lessons.

---

## Section 2: SDK Alignment — LangChain DeepAgents

### 2.1 `create_deep_agent()` vs `create_agent()` — SDK-VALIDATED

**SDK source confirms** (inspected directly from installed `deepagents==0.4.12`):

| Function | Source | Middleware | Tools Added |
|----------|--------|-----------|-------------|
| `create_deep_agent()` | `deepagents/graph.py` | TodoList + Filesystem + SubAgent + Summarization + PromptCaching + PatchToolCalls | `write_todos`, `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`, `execute`, `task` |
| `create_agent()` | `langchain/agents/factory.py` | Only what you pass in `middleware=` | Only what middleware provides |

**Correct approach for restricted agents**: Call `create_agent()` with `middleware=()` (empty) and `tools=[only_allowed_tools]`. This gives the agent exactly the tools specified, nothing more.

| Role | Current | Should Use | SDK Justification |
|------|---------|------------|-------------------|
| Orchestrator | Plain Python | Plain Python | Correct — NOT an agent |
| Player | `create_deep_agent()` | `create_agent(tools=[search_data])` | `create_agent()` has zero automatic middleware |
| Coach | `create_deep_agent()` | `create_agent(tools=[])` | Gives exactly zero tools |

### 2.2 Middleware Composition — SDK-VALIDATED

`create_deep_agent()` (lines 249-267) builds its middleware stack unconditionally. There is **no parameter to disable** FilesystemMiddleware, TodoListMiddleware, or SubAgentMiddleware.

The `middleware=` parameter on `create_deep_agent()` **appends additional middleware** after the standard stack (line 269-270: `if middleware: deepagent_middleware.extend(middleware)`). It does NOT replace the standard stack.

For agents requiring restricted tools, `create_agent()` is the correct SDK primitive. It accepts `middleware=` and only includes middleware you explicitly provide.

### 2.3 `memory=["./AGENTS.md"]` Pattern — CRITICAL FINDING F5: RUNTIME BUG

**NEW finding from SDK validation.**

`create_agent()` does NOT accept a `memory` parameter. Its signature (confirmed from source):
```python
def create_agent(
    model, tools=None, *, system_prompt=None, middleware=(),
    response_format=None, state_schema=None, context_schema=None,
    checkpointer=None, store=None, interrupt_before=None,
    interrupt_after=None, debug=False, name=None, cache=None
)
```

**No `memory` parameter exists on `create_agent()`.**

However, `factory_guards.py` line 93-94 passes `memory` to `create_agent()`:
```python
if memory is not None:
    kwargs["memory"] = memory
agent = create_agent(**kwargs)  # TypeError: unexpected keyword argument 'memory'
```

**This is a runtime bug** — any call to `create_restricted_agent()` with `memory=["./AGENTS.md"]` will raise a `TypeError`.

The `memory` parameter exists only on `create_deep_agent()` (which handles it by adding `MemoryMiddleware` to the stack, line 252-253):
```python
if memory is not None:
    deepagent_middleware.append(MemoryMiddleware(backend=backend, sources=memory))
```

**Impact**: HIGH — `create_restricted_agent()` cannot be used with AGENTS.md injection in its current form.

**Fix options** (in priority order):
1. **Best**: Add `MemoryMiddleware` to the `create_restricted_agent()` function when `memory` is provided, passing it as `middleware=[MemoryMiddleware(backend=..., sources=memory)]` to `create_agent()`.
2. **Simple**: Read AGENTS.md content and prepend it to `system_prompt` before calling `create_agent()`. This loses the structured loading/display-name features of `MemoryMiddleware` but achieves the boundary injection goal.
3. **Alternative**: Use `create_deep_agent()` with `interrupt_on` to block dangerous tools via HITL — but this is complex and doesn't actually remove the tools.

**Recommended fix** (option 1):
```python
def create_restricted_agent(
    model, tools, system_prompt, *, memory=None,
    allowed_tools=None, backend=None,
):
    from langchain.agents import create_agent
    from deepagents.middleware.memory import MemoryMiddleware

    middleware = []
    if memory is not None:
        # MemoryMiddleware requires a backend for file loading
        effective_backend = backend or StateBackend
        middleware.append(MemoryMiddleware(
            backend=effective_backend, sources=memory
        ))

    agent = create_agent(
        model=model, tools=list(tools),
        system_prompt=system_prompt,
        middleware=middleware,
    )
    if allowed_tools is not None:
        assert_tool_inventory(agent, allowed_tools)
    return agent
```

### 2.4 Backend Selection — SDK-VALIDATED

`create_agent()` does NOT accept a `backend` parameter (confirmed from signature). Backends are a `create_deep_agent()` concept, passed to middleware constructors (`FilesystemMiddleware(backend=...)`, `MemoryMiddleware(backend=...)`).

For restricted agents using `create_agent()`:
- **Player**: No backend needed (no filesystem tools). If `MemoryMiddleware` is used for AGENTS.md, pass a backend to the middleware constructor.
- **Coach**: No backend needed (no tools at all). Same MemoryMiddleware pattern if needed.
- **Orchestrator**: Plain Python — manages its own file I/O directly.

### 2.5 LangGraph Studio Compatibility — CONCERN F3

The `langgraph.json` template registers `agent = _player` as the graph entrypoint:
```json
{"graphs": {"agent": "./agent.py:agent"}}
```

This exposes only the Player as a LangGraph graph. For the adversarial template, LangGraph Studio should see the full orchestration loop, not just one agent. The adversarial template needs a LangGraph-compatible entrypoint that wraps the Orchestrator loop as a graph.

**Recommendation**: TASK-TI-010 (three-role scaffold) should define a LangGraph `StateGraph` that exposes the full Player-Coach loop as a single graph for Studio visualisation. The Orchestrator can be the graph's `__call__` method.

### 2.6 `system_prompt` Handling — SDK NOTE

`create_deep_agent()` (lines 274-281) APPENDS the user's `system_prompt` BEFORE `BASE_AGENT_PROMPT`:
```python
final_system_prompt = system_prompt + "\n\n" + BASE_AGENT_PROMPT
```

This means all agents created via `create_deep_agent()` get the Deep Agent base prompt ("You are a Deep Agent...") appended. For the adversarial template, this base prompt is irrelevant and potentially confusing (it instructs the agent to use filesystem tools, read files, etc.).

`create_agent()` passes `system_prompt` through directly without appending anything. This is another reason to prefer `create_agent()` for the restricted Player/Coach roles.

---

## Section 3: Conversation Starter Alignment

### 3.1 CoachVerdict Schema Evolution — FINDING F4 (unchanged from initial review)

**Conversation starter specifies** (Pydantic):
```python
class CoachVerdict(BaseModel):
    decision: Literal["accept", "revise", "reject"]
    score: int = Field(ge=1, le=5)
    criteria_met: dict[str, bool]
    criteria_scores: dict[str, int]
    issues: list[Issue]
    quality_assessment: str
```

**Current codebase has** (dataclass):
```python
@dataclass
class CoachVerdict:
    decision: str  # "accept" or "reject"
    score: int  # 1-5
    issues: list[str] = field(default_factory=list)
    criteria_met: bool = False
    quality_assessment: str = "needs_revision"
```

**Key differences**:
| Field | Conversation Starter | Current Code | Gap |
|-------|---------------------|--------------|-----|
| `decision` | `Literal["accept", "revise", "reject"]` | `str` ("accept" or "reject") | Missing "revise" option |
| `criteria_met` | `dict[str, bool]` (per-criterion) | `bool` (single flag) | Not per-criterion |
| `criteria_scores` | `dict[str, int]` (per-criterion) | Missing | No per-criterion scoring |
| `issues` | `list[Issue]` (structured) | `list[str]` (flat) | Not structured |

**Recommendation (aligns with D1)**: Keep the simple dataclass in the base template. The adversarial template should introduce the richer Pydantic `CoachVerdict` that supports per-criterion scoring, the "revise" decision option, and structured `Issue` objects.

### 3.2 GOAL.md vs DOMAIN.md — VALIDATED (unchanged)

- `DOMAIN.md` = domain context (what the domain IS, background knowledge)
- `GOAL.md` = quality contract (what SUCCESS looks like, evaluation rubrics)

Complementary, not competing. Base template keeps DOMAIN.md. Adversarial template adds GOAL.md alongside it.

### 3.3 Configurable Adversarial Intensity — DESIGN VALIDATED (unchanged)

Three modes (full/light/solo) map cleanly to the `OrchestratorWriteGate` design.

### 3.4 Sprint Contract Negotiation — DESIGN VALIDATED (unchanged)

### 3.5 HITL Checkpoint Hooks — DESIGN VALIDATED with SDK note

The `interrupt_on` parameter on `create_deep_agent()` (line 98, 271-272) provides native HITL support:
```python
agent = create_deep_agent(
    interrupt_on={"write_file": True},
    checkpointer=MemorySaver(),
)
```

For agents using `create_agent()`, HITL is available via `HumanInTheLoopMiddleware` passed as middleware, or via `interrupt_before`/`interrupt_after` parameters. The adversarial template's Orchestrator (plain Python) should implement HITL checkpoints as simple function calls — no SDK HITL middleware needed.

---

## Section 4: Design Decisions Resolved

### D1: CoachVerdict — dataclass vs Pydantic

**Decision: BOTH — base template keeps dataclass, adversarial template uses Pydantic.**

Rationale unchanged. The adversarial template needs per-criterion scoring and Pydantic validation for the GOAL.md quality contract.

### D2: Agent Factory Naming — SDK-VALIDATED

**Decision: Use `create_agent()` directly for restricted agents. `create_restricted_agent()` wraps it with `assert_tool_inventory()` and optional `MemoryMiddleware`.**

**SDK validation**: `create_agent()` is the correct SDK primitive for agents without automatic middleware. `create_deep_agent()` is for "batteries-included" agents that need the full stack. The adversarial pattern requires tool-restricted agents, so `create_agent()` is correct.

**Naming note**: The existing `create_restricted_agent()` name is a GuardKit convention, not an SDK name. This is fine — it adds value by wrapping `create_agent()` with safety guards.

### D3: GOAL.md and DOMAIN.md Coexistence — VALIDATED (unchanged)

### D4: Orchestrator Implementation — VALIDATED (unchanged)

**Decision: Plain Python loop (NOT DeepAgent).**

### D5: Coach Tool Invariant — SDK-VALIDATED

**Decision: No tools ever. Use `create_agent(tools=[])` with NO middleware.**

SDK validation confirms this is the ONLY way to guarantee zero tools. `create_deep_agent(tools=[])` still adds 9 middleware-injected tools.

### D6: Multi-Model Support — VALIDATED (unchanged)

**Decision: Support different models per role via `model_factory.py`.**

SDK note: `create_agent()` accepts `model` as either a string (`"openai:gpt-5"`) or a `BaseChatModel` instance. The template should use `init_chat_model()` for provider-agnostic model creation.

### D7: NATS vs Console for HITL — VALIDATED (unchanged)

---

## Section 5: Wave 1 (P0) Completion Status

### All 3 P0 tasks COMPLETED and VERIFIED:

| Task | Status | Tests | Files |
|------|--------|-------|-------|
| TASK-TI-001 (JsonExtractor) | COMPLETED | 55/55 passed | `lib/json_extractor.py` |
| TASK-TI-002 (Prompt Template) | COMPLETED | 29/29 passed | `templates/other/prompts/templates.py.template` |
| TASK-TI-003 (Gated Writes) | COMPLETED | 30/30 passed | `templates/other/scaffold/orchestrator_pattern.py.template` |

**Additional Wave 2 components found completed**:

| Component | Status | Tests | Files |
|-----------|--------|-------|-------|
| Factory Guards | COMPLETED | Tests exist | `lib/factory_guards.py` **(HAS RUNTIME BUG — F5)** |
| Observability | COMPLETED | Tests exist | `lib/observability.py` |
| Agent Factory | COMPLETED | — | `templates/other/scaffold/agent_factory.py.template` |

**Total test count**: 182 tests, all passing.

**Note on F5**: The `factory_guards.py` tests likely mock `create_agent()`, so the `memory` kwarg bug (F5) may not surface in unit tests. It will fail at runtime when creating an actual agent with AGENTS.md injection.

---

## Section 6: Cross-Domain Applicability

(Unchanged from initial review — all validated)

### 6.1 Domain-Agnostic Abstractions — VALIDATED

| Component | Domain-Agnostic? | Customization Point |
|-----------|-------------------|---------------------|
| OrchestratorWriteGate | Yes | `write_fn`, `max_retries` |
| CoachVerdict | Yes | Decision/score values universal |
| Prompt Templates | Yes | `criteria`, `json_example` parameters |
| JsonExtractor | Yes | No domain coupling |
| Factory Guards | Yes | `allowed_tools` set |

### 6.2 GOAL.md Pattern — VALIDATED for Three Use Cases

| Use Case | GOAL.md Content | Evaluation Criteria |
|----------|----------------|---------------------|
| Dark Factory (code/data) | Output schema, metadata schema, validation rules | Verifiable: schema conformance, completeness, accuracy |
| YouTube Planner | Video plan schema, quality rubrics | Subjective-made-gradable: hook strength, originality, structure |
| General adversarial | Domain-defined schema and criteria | User-defined weighted criteria |

### 6.3 Anthropic Framework Mapping — CONFIRMED

| Anthropic Term | Template Term | This Template |
|---------------|--------------|---------------|
| Planner | Orchestrator | Plain Python loop |
| Generator | Player | Agent with domain tools |
| Evaluator | Coach | Agent with no tools |
| Grading criteria | GOAL.md | Weighted evaluation rubrics |
| Evaluator scepticism | `scepticism` parameter | `lenient/moderate/strict` |

---

## Section 7: Stub Pattern Rules Assessment

(Unchanged from initial review)

All 5 pattern rules files are **stubs with boilerplate content**. Should be populated from proven code. Consider TASK-TI-017 for pattern rule population.

---

## Section 8: Risk Assessment for Wave 4

### CRITICAL Risk Items

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| F1 | Player uses `create_deep_agent()` | Gets 10 extra tools including `write_file`, `edit_file`, `execute` — tool separation completely bypassed | Fix BEFORE Wave 4: switch to `create_agent()` |
| F2 | Coach uses `create_deep_agent()` | Gets 9 tools despite `tools=[]` — violates D5 invariant | Fix BEFORE Wave 4: switch to `create_agent()` |
| F5 | `factory_guards.py` passes `memory` kwarg to `create_agent()` | `TypeError` at runtime — `create_agent()` does not accept `memory` | Fix BEFORE Wave 4: add `MemoryMiddleware` to middleware list instead |

### HIGH Risk Items

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| F4 | CoachVerdict schema gap | Adversarial template can't do per-criterion scoring | Address in TASK-TI-012 (domain config schema) |

### MODERATE Risk Items

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| F3 | LangGraph Studio shows only Player | Poor developer experience | Address in TASK-TI-010 (three-role scaffold) |
| — | `create_deep_agent()` appends BASE_AGENT_PROMPT | Player/Coach get irrelevant "You are a Deep Agent" instructions | Resolved by switching to `create_agent()` |
| — | Config naming: `coach-config.yaml` too narrow | Confusing for multi-role config | Rename to `agent-config.yaml` in adversarial template |
| — | Template placeholder inconsistency | `coach.py.template` uses hardcoded `deepagents` not `{{ProjectName}}` | Fix in Wave 4 scaffold |

### LOW Risk Items

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| — | NATS transport not yet available | HITL limited to console | Correctly scoped as optional |
| — | Stub pattern rules empty | Weaker developer guidance | Non-blocking, address post-Wave 4 |

---

## Section 9: Recommendations

### Pre-Wave 4 Fixes (MUST do before Wave 4 starts)

**1. Fix `factory_guards.py` — `memory` parameter bug (F5)**

`create_agent()` does not accept a `memory` kwarg. Fix `create_restricted_agent()` to handle memory via `MemoryMiddleware`:

```python
def create_restricted_agent(
    model, tools, system_prompt, *,
    memory=None, allowed_tools=None, backend=None,
):
    from langchain.agents import create_agent
    from deepagents.middleware.memory import MemoryMiddleware
    from deepagents.backends import StateBackend

    middleware = []
    if memory is not None:
        effective_backend = backend or StateBackend
        middleware.append(MemoryMiddleware(
            backend=effective_backend, sources=memory
        ))

    agent = create_agent(
        model=model, tools=list(tools),
        system_prompt=system_prompt,
        middleware=middleware,
    )
    if allowed_tools is not None:
        assert_tool_inventory(agent, allowed_tools)
    return agent
```

**2. Fix `player.py.template` (F1)**

Replace `create_deep_agent()` with `create_agent()` via `create_restricted_agent()`:

```python
from {{ProjectName}}.lib.factory_guards import create_restricted_agent

def create_player(model, domain_prompt: str):
    tools = [search_data]
    system_prompt = PLAYER_SYSTEM_PROMPT + "\n\n" + domain_prompt
    return create_restricted_agent(
        model=model, tools=tools,
        system_prompt=system_prompt,
        memory=["./AGENTS.md"],
        allowed_tools={"search_data"},
    )
```

**3. Fix `coach.py.template` (F2)**

Replace `create_deep_agent()` with `create_agent()` via `create_restricted_agent()`. Fix hardcoded import.

```python
from {{ProjectName}}.lib.factory_guards import create_restricted_agent

def create_coach(model, domain_prompt: str):
    system_prompt = COACH_SYSTEM_PROMPT + "\n\n" + domain_prompt
    return create_restricted_agent(
        model=model, tools=[],
        system_prompt=system_prompt,
        memory=["./AGENTS.md"],
        allowed_tools=set(),  # D5 invariant: Coach has NO tools
    )
```

**4. Update `factory_guards.py` tests**

Add a test that verifies `create_restricted_agent()` with `memory` parameter does NOT pass it as a kwarg to `create_agent()` but instead adds `MemoryMiddleware` to the middleware list.

### Wave 4 Task Adjustments

5. **TASK-TI-009** (scaffold): Add `agent-config.yaml` with per-role model config and adversarial intensity section.

6. **TASK-TI-010** (three-role): Include a LangGraph `StateGraph` wrapper so the full adversarial loop is visible in LangGraph Studio.

7. **TASK-TI-012** (domain config): Define the Pydantic `CoachVerdict` with per-criterion scoring, "revise" decision option, and structured `Issue` objects. Include GOAL.md parser.

8. **TASK-TI-013** (coach prompt): Use `quality_gates()` from `templates.py` to generate Coach prompts with weighted criteria from GOAL.md.

### Post-Wave 4

9. **TASK-TI-017** (new): Populate stub pattern rules from proven code.

10. **TASK-TI-018** (new): Consolidate factory patterns — `agent_factory.py.template` and `player.py.template`/`coach.py.template` should use the same approach.

---

## Section 10: Decision Matrix

| Decision | Recommendation | Confidence | SDK Validated | Risk if Deferred |
|----------|---------------|------------|---------------|-----------------|
| D1: CoachVerdict dual model | Both (dataclass base, Pydantic adversarial) | High | N/A | Low — can evolve |
| D2: Factory approach | `create_agent()` via `create_restricted_agent()` | High | YES — source confirmed | Critical |
| D3: GOAL.md + DOMAIN.md | Keep separate | High | N/A | Low |
| D4: Orchestrator as Python | Plain Python loop | High | YES — avoids middleware | High |
| D5: Coach no tools | `create_agent(tools=[], middleware=[])` | High | YES — only way to guarantee | Critical |
| D6: Multi-model support | Per-role config via `init_chat_model()` | High | YES — both functions accept | Low |
| D7: NATS optional | Console default | High | N/A | Low |

---

## Section 11: SDK Reference Summary

Key facts validated against installed `deepagents==0.4.12` and `langchain` source:

| Fact | Source | Line |
|------|--------|------|
| `create_deep_agent()` adds TodoList + Filesystem + SubAgent + Summarization + PromptCaching + PatchToolCalls middleware unconditionally | `deepagents/graph.py` | 249-267 |
| `FilesystemMiddleware.tools` = `[ls, read_file, write_file, edit_file, glob, grep, execute]` | `deepagents/middleware/filesystem.py` | 495-503 |
| `create_deep_agent(middleware=[...])` APPENDS to standard stack, does not replace | `deepagents/graph.py` | 269-270 |
| `create_agent()` has NO built-in middleware — only what you pass | `langchain/agents/factory.py` | Verified: no FilesystemMiddleware/TodoList references |
| `create_agent()` does NOT accept `memory` parameter | `langchain/agents/factory.py` | Signature inspection |
| `create_agent()` composes tools as `middleware_tools + regular_tools` | `langchain/agents/factory.py` | 193-244 |
| `create_deep_agent()` prepends user system_prompt BEFORE BASE_AGENT_PROMPT | `deepagents/graph.py` | 274-281 |
| `MemoryMiddleware` loads AGENTS.md and injects into system prompt | `deepagents/middleware/memory.py` | Docstring confirmed |
| Core middleware cannot be removed from `create_deep_agent()` | LangChain skills `deep-agents-core` | `<boundaries>` section |

---

## Review Details

- **Mode**: Architectural Review (deep) — SDK-validated revision
- **Scope**: Template design, SDK source code alignment, conversation starter reconciliation
- **SDK Inspected**: `deepagents==0.4.12`, `langchain` (installed), LangChain skills plugin
- **Files Reviewed**: 25 template files, 3 task files, 2 conversation starters, 5 pattern stubs, 4 SDK source files
- **Tests Verified**: 182 passing (Wave 1 + Wave 2 components)
- **Reviewer**: architectural-reviewer + software-architect agents + SDK source validation

---

## Appendix A: File Inventory

### Wave 1 (P0) — Completed
- `lib/json_extractor.py` — 272 lines, 55 tests
- `templates/other/prompts/templates.py.template` — 269 lines, 29 tests
- `templates/other/scaffold/orchestrator_pattern.py.template` — 267 lines, 30 tests

### Wave 2 (P1) — Partially Complete
- `lib/factory_guards.py` — 124 lines, tests exist **(HAS RUNTIME BUG — F5)**
- `lib/observability.py` — 398 lines, tests exist
- `templates/other/scaffold/agent_factory.py.template` — 101 lines

### Supporting Templates
- `templates/other/agents/player.py.template` — 43 lines **(NEEDS FIX — F1)**
- `templates/other/agents/coach.py.template` — 25 lines **(NEEDS FIX — F2)**
- `templates/other/other/agent.py.template` — 84 lines
- `templates/other/prompts/player_prompts.py.template` — 49 lines
- `templates/other/prompts/coach_prompts.py.template` — 61 lines
- `templates/other/other/AGENTS.md.template` — 70 lines
- `templates/other/other/coach-config.yaml.template` — 15 lines
- `templates/other/other/langgraph.json.template` — 7 lines

### Stub Pattern Rules (All Empty)
- `.claude/rules/patterns/adversarial-cooperation.md`
- `.claude/rules/patterns/memory-injection.md`
- `.claude/rules/patterns/factory.md`
- `.claude/rules/patterns/tool-delegation.md`
- `.claude/rules/patterns/domain-driven-configuration.md`

---

## Appendix B: Cross-Reference with Working agentic-dataset-factory (Revision 3)

### Context

The `agentic-dataset-factory` is the proven exemplar codebase from which the `langchain-deepagents` template was derived. It has undergone 12+ production runs with 31 fixes. As of this review, it is **currently executing a ~26-hour production run** (started ~7 hours ago, processing 1,020 targets across 20 GCSE English categories). The TASK-REV-R2A1 and TASK-REV-7617 fixes were applied before this run.

### Proven Factory Patterns (Currently Running in Production)

The working code in `agentic-dataset-factory/agents/` has already solved all three critical findings from this review. **The template should adopt these patterns directly.**

#### Player Factory — PROVEN PATTERN (F1 solution)

From `agentic-dataset-factory/agents/player.py` (production code, currently running):

```python
from deepagents.backends import FilesystemBackend
from deepagents.middleware import MemoryMiddleware
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from langchain.agents import create_agent
from langchain_anthropic.middleware import AnthropicPromptCachingMiddleware

def create_player(model_config, tools, system_prompt, memory):
    model = create_model(model_config)
    backend = FilesystemBackend(root_dir=".")
    middleware = [
        MemoryMiddleware(backend=backend, sources=memory),
        PatchToolCallsMiddleware(),
        AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),
    ]
    return create_agent(
        model=model, tools=tools,
        system_prompt=system_prompt, middleware=middleware,
    )
```

Key design decisions embedded in this code:
- Uses `create_agent()` NOT `create_deep_agent()` — prevents FilesystemMiddleware injection
- `MemoryMiddleware` with `FilesystemBackend` handles AGENTS.md loading — backend is for memory file reading only, NOT for agent tools
- `PatchToolCallsMiddleware` + `AnthropicPromptCachingMiddleware` retained from standard stack
- NO `TodoListMiddleware`, NO `SubAgentMiddleware`, NO `FilesystemMiddleware` in middleware list
- `tools` parameter contains ONLY domain tools (e.g., `[rag_retrieval]`)

#### Coach Factory — PROVEN PATTERN (F2 + F5 solution)

From `agentic-dataset-factory/agents/coach.py` (production code, currently running):

```python
def create_coach(model_config, system_prompt, memory):
    model = create_model(model_config)
    backend = FilesystemBackend(root_dir=".")
    middleware = [
        MemoryMiddleware(backend=backend, sources=memory),
        PatchToolCallsMiddleware(),
        AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),
    ]
    return create_agent(
        model=model, tools=[],
        system_prompt=system_prompt, middleware=middleware,
    )
```

Key design decisions:
- `tools=[]` — Coach has NO tools (D5 invariant enforced at factory level)
- No `tools` parameter in function signature — impossible for caller to accidentally inject tools
- Same `MemoryMiddleware` pattern as Player — AGENTS.md loaded via `FilesystemBackend` for reading only

#### Memory Injection — PROVEN PATTERN (F5 solution)

The `memory` parameter is NOT passed to `create_agent()` (which doesn't accept it). Instead, `MemoryMiddleware` is added to the middleware list with a `FilesystemBackend` for reading memory files:

```python
backend = FilesystemBackend(root_dir=".")
middleware = [
    MemoryMiddleware(backend=backend, sources=memory),  # Reads AGENTS.md, injects into system prompt
    ...
]
```

This is the correct pattern — `FilesystemBackend` gives `MemoryMiddleware` file access for loading AGENTS.md content, but does NOT add filesystem tools to the agent because `FilesystemMiddleware` is not in the middleware list.

### Proven Retry Pattern (TASK-REV-R2A1 fix)

The `ainvoke()` contract discovered in TASK-REV-R2A1 is critical for the adversarial template:

**Rule**: Never include `system` role messages in the `ainvoke()` input. The framework owns system message injection via `system_prompt` + `MemoryMiddleware`.

The working retry pattern (from `generation_loop.py:751-765`):
```python
retry_input = {
    "messages": [{
        "role": "user",  # NOT "system" — framework owns system messages
        "content": (
            "IMPORTANT: Your previous response was not valid JSON. "
            "You MUST respond with ONLY a JSON object matching the "
            "CoachVerdict schema. No prose, no reasoning text, no markdown. "
            "Start your response with { and end with }.\n\n"
            + player_content
        ),
    }]
}
```

The initial broken implementation used `"role": "system"` which caused dual system messages → vLLM HTTP 400 crash. The fix merges reinforcement into a single `user` message.

### Exception Handling — PROVEN PATTERN (TASK-REV-R2A1 fix)

The working code catches `httpx.HTTPStatusError` at two layers:

1. **`_invoke_with_retry()`** — catches HTTPStatusError but only retries 429 (rate limit) and 5xx (server error). 4xx client errors raise immediately (retrying won't help).

2. **Per-target handler** — catches HTTPStatusError as a safety net. Target gets rejected, pipeline continues.

### What This Means for the Template

The `factory_guards.py` approach in the template (`create_restricted_agent()`) is architecturally correct but has the wrong implementation. The proven pattern from the exemplar is simpler and more robust:

| Template (Current) | Exemplar (Proven) | Gap |
|--------------------|--------------------|-----|
| `create_restricted_agent()` wraps `create_agent()` with `assert_tool_inventory()` post-creation | Factories call `create_agent()` directly with curated middleware | Template adds post-creation assertion; exemplar prevents the problem at construction |
| Passes `memory` kwarg to `create_agent()` — **TypeError at runtime** | Uses `MemoryMiddleware(backend=FilesystemBackend(...), sources=memory)` in middleware list | Template bug; exemplar pattern is correct |
| `player.py.template` uses `create_deep_agent()` | `agents/player.py` uses `create_agent()` | Template gets 10 unwanted tools; exemplar gets exactly the tools specified |
| `coach.py.template` uses `create_deep_agent()` | `agents/coach.py` uses `create_agent(tools=[])` | Template gets 9 unwanted tools; exemplar gets zero |

### Recommendation: Align Template with Exemplar

The pre-Wave 4 fixes should directly adopt the exemplar patterns rather than inventing new approaches:

1. **`player.py.template`** — Rewrite to match `agentic-dataset-factory/agents/player.py` pattern
2. **`coach.py.template`** — Rewrite to match `agentic-dataset-factory/agents/coach.py` pattern
3. **`factory_guards.py`** — Fix `memory` handling to use `MemoryMiddleware` (keep `assert_tool_inventory()` as an additional safety net)
4. **Document the `ainvoke()` contract** — system messages must never appear in input; reinforcement uses `user` role

### Additional Proven Insights from TASK-REV-R2A1

These should be encoded in the adversarial template:

| Insight | Source | Template Impact |
|---------|--------|----------------|
| `create_agent()` prepends `system_prompt` unconditionally on every `ainvoke()` | TASK-REV-R2A1, framework source lines 1270-1271 | Coach retry must use `user` role, not `system` |
| `MemoryMiddleware` appends AGENTS.md into system prompt via `append_to_system_message()` | TASK-REV-R2A1, memory.py:322-337 | AGENTS.md boundaries are always active for both Player and Coach |
| vLLM rejects multiple system messages with HTTP 400 | TASK-REV-R2A1 production evidence | Template must document this constraint |
| `httpx.HTTPStatusError` must be caught at both retry and per-target levels | TASK-REV-R2A1 Fix #2 | Template orchestrator must handle this |
| Coach retry should be single-attempt with JSON reinforcement, not a loop | TASK-REV-7617 architectural constraint | Template should encode this as a pattern |

### Config Pattern — PROVEN

The `agent-config.yaml` in the exemplar already supports per-role model configuration:

```yaml
player:
  provider: local
  model: Qwen/Qwen3.5-35B-A3B-FP8
  endpoint: http://promaxgb10-41b1:8002/v1
  temperature: 0.6

coach:
  provider: local
  model: Qwen/Qwen3.5-35B-A3B-FP8
  endpoint: http://promaxgb10-41b1:8002/v1
  temperature: 0.3

generation:
  max_turns: 3
  llm_retry_attempts: 3
  llm_retry_backoff: 2.0
```

This validates D6 (multi-model support) and confirms the template's `coach-config.yaml` should be expanded to `agent-config.yaml` with per-role sections.

### Production Run Evidence

The current run (~7 hours into a ~26-hour execution) validates:
- `create_agent()` with curated middleware works reliably for sustained runs
- `MemoryMiddleware` with `FilesystemBackend` correctly injects AGENTS.md boundaries
- Coach retry with `user` role reinforcement handles parse failures without crashing
- `httpx.HTTPStatusError` exception handling keeps the pipeline running through LLM errors
- Per-role model config (same model, different temperatures) works correctly
- D5 invariant (Coach with no tools) holds in production
