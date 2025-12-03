# TaskWright LangGraph Workflow Automation: Build Strategy Analysis

## Terminology Note

This document discusses workflow automation options, comparing LangGraph with the Claude Agent SDK.
The term "orchestration" appears in places but the more accurate description is **workflow automation** -
automating a developer's manual process, not multi-agent swarm coordination.

See [TaskWright vs Swarm Systems](./Claude_Agent_SDK_Two_Command_Feature_Workflow.md#taskwright-vs-swarm-systems) for the distinction.

---

## The "Dogfooding Discovery" vs "Spec-First Build" Tradeoff

Your instinct is sound. TaskWright's evolution made sense as discovery - you were simultaneously figuring out *what* the tool should do while building *how* it does it. The domain was unclear, requirements emerged through use, and the feedback loop of using it daily to build itself was invaluable.

But for a LangGraph orchestration layer, the situation is fundamentally different:

### What You Now Know (That You Didn't When Starting TaskWright)

- The exact 7-phase workflow structure (2 → 2.5B → 2.7 → 2.8 → 3 → 4/4.5 → 5/5.5)
- The three approval levels and their routing logic
- The test retry pattern (max 3 attempts)
- The design-first checkpoint/resume pattern
- The agent selection criteria (stack, phase, capabilities)
- The state that needs to flow between phases
- How RequireKit and TaskWright integrate

This is no longer exploratory - it's **implementation of a known architecture**. That's exactly where spec-driven development shines.

---

## Critical Update: Claude Agent SDK Changes Everything

### NEW: Claude Agent SDK (Recommended Path)

**The Claude Agent SDK can directly invoke TaskWright slash commands** like `/task-work`, `/task-create`, etc. This dramatically changes the effort equation.

See: [Claude Agent SDK: Fast Path to TaskWright Orchestration](./Claude_Agent_SDK_Fast_Path_to_TaskWright_Orchestration.md)

```python
from claude_agent_sdk import query, ClaudeAgentOptions

# This DIRECTLY invokes your /task-work command!
async for message in query(
    prompt=f"/task-work {task_id}",
    options=ClaudeAgentOptions(cwd=project_path)
):
    print(message)
```

**Effort**: ~1 week (vs 3-4 weeks for LangGraph reimplementation)

### What LangGraph CANNOT Do (Still True)

**LangGraph cannot directly call Claude Code slash commands** - but the Claude Agent SDK can!

Those slash commands are:
1. **Claude Code UI constructs** - Interpreted by Claude Code's interface
2. **Prompt injections** - Trigger Claude to read `.md` command files
3. **Not CLI commands** - No `taskwright /task-create` binary exists

**However**, the Claude Agent SDK provides the programmatic bridge we need.

### The Four Realistic Options (Updated)

#### Option A: Claude Agent SDK (NEW - Fastest Path) ⭐
- Build Python orchestrator that invokes existing slash commands via SDK
- Uses existing `.claude/commands/*.md` without modification
- Uses existing `.claude/agents/*.md` automatically
- **Effort**: ~1 week
- **Trade-off**: Vendor lock-in to Anthropic
- **Benefit**: Fastest path, reuses all existing work

#### Option B: LangGraph as a Parallel Implementation
- Build a Python LangGraph workflow that reimplements `/task-work`
- Calls Anthropic API for AI-powered parts
- Manages state, checkpoints, and retries explicitly
- **Effort**: 3-4 weeks
- **Benefit**: Multi-LLM ready, clean architecture

#### Option C: Continue with Claude Code, Add Orchestration Later
- Keep using `/task-work` as-is for implementation
- Use RequireKit for specification layer
- Build orchestrator as a future phase
- **Effort**: Zero for now
- **Benefit**: Ship features now, defer complexity

#### Option D: Phased Approach (Recommended) ⭐
1. **Phase 1**: Claude Agent SDK orchestrator (~1 week)
2. **Phase 2**: Validate patterns in production
3. **Phase 3**: LangGraph reimplementation IF multi-LLM needed

This validates orchestration patterns before committing to full reimplementation.

---

## Recommended Path: Claude Agent SDK First, LangGraph Later

### Phase 1: Claude Agent SDK Orchestrator (~1 week)

Build a Python orchestrator that:

1. **Invokes existing commands** - `query(prompt="/task-work TASK-XXX")`
2. **Uses existing task files** - Compatible with `.claude/tasks/` structure
3. **Uses existing agents** - Auto-detected from `.claude/agents/`
4. **Manages state in SQLite** - Track checkpoint progress
5. **Handles human checkpoints** - Parse messages, prompt for approval

### Phase 2: Validate and Enhance (~2 weeks)

1. Add `--design-only` and `--implement-only` flags
2. Add progress streaming and better UI
3. Add retry logic and error handling
4. Document the integration

### Phase 3: LangGraph IF Needed (Future)

If you need multi-LLM support:

1. **Extract workflow patterns** learned from SDK usage
2. **Reimplement as LangGraph StateGraph**
3. **Add multi-LLM support** (OpenAI, Gemini, etc.)
4. **Keep same CLI interface** - just swap backend

The Claude Agent SDK phase is NOT wasted work - it validates orchestration patterns before committing to reimplementation.

---

## Why RequireKit Makes Sense Here

Using RequireKit to spec this out would give you:

### 1. EARS Requirements That Map Directly to LangGraph Node Behaviors

- "When complexity_score ≥ 7, the system shall invoke FULL_REQUIRED checkpoint with interrupt()"
- "While test_attempt_count < 3 AND tests_failed, the system shall retry implementation"

### 2. BDD Scenarios That Become Your Acceptance Tests

- Given a task with complexity 4 / When design-only flag is set / Then workflow stops after Phase 2.8 with checkpoint persisted

### 3. Epic/Feature Hierarchy That Structures the Build

- **Epic**: LangGraph Orchestration Layer
  - **Feature**: Core Workflow Graph
  - **Feature**: Human-in-the-Loop Checkpoints
  - **Feature**: Test Enforcement Loop
  - **Feature**: Agent Selection Router
  - **Feature**: CLI Integration

### 4. Clear Scope Boundaries

Preventing the "death by a thousand bug fixes" architectural drift you've experienced.

---

## Revised Effort Estimates

Given that this is a **reimplementation** rather than a wrapper:

| Component | Effort | Description |
|-----------|--------|-------------|
| **Core StateGraph** | 3-5 days | Node definitions, edges, state schema |
| **Anthropic API Integration** | 2-3 days | LLM calls for planning, implementation, review |
| **Checkpoint/Resume** | 2-3 days | SqliteSaver integration, design-first workflow |
| **Complexity Routing** | 1-2 days | Conditional edges for approval levels |
| **Test Enforcement Loop** | 2-3 days | Retry logic, test execution, result parsing |
| **Agent Selection** | 2-3 days | Stack detection, agent matching, context injection |
| **CLI Integration** | 2-3 days | Click commands, progress display, interrupt handling |
| **Testing & Polish** | 3-5 days | Unit tests, integration tests, documentation |

**Total: 3-4 weeks** for a production-ready implementation (not 2-3 days as initially suggested for "quick wins").

---

## Proposed Approach

A hybrid approach using RequireKit's full power:

```
Phase 1: Requirements Gathering (RequireKit)
├── /gather-requirements for each feature area
├── /formalize-ears to create unambiguous specs
├── /generate-bdd for acceptance criteria
└── /epic-create + /feature-create for hierarchy

Phase 2: Architecture Validation
├── Review EARS requirements against LangGraph capabilities
├── Identify any gaps or conflicts
├── Create architecture decision records (ADRs)
└── Validate state schema covers all requirements

Phase 3: Implementation (TaskWright + Claude Code)
├── Tasks created from features with requirement links
├── /task-work with full quality gates (using Claude Code)
├── BDD scenarios drive test implementation
└── Each task traces back to EARS requirements

Phase 4: Validation
├── LangGraph orchestrator passes all BDD scenarios
├── Can execute same tasks as Claude Code version
├── State persistence verified across restarts
└── Human checkpoints work correctly
```

---

## What This Buys You

### For the Blog Post Context
You'd have a concrete example of the full RequireKit → TaskWright pipeline building something non-trivial. That's powerful demonstration content.

### For the Implementation
You'd avoid the trap of "I'll just add this one thing" that leads to architectural drift. Each change would need to trace back to a requirement.

### For Maintainability
Future contributors (or future you) can understand *why* something was built a certain way by following requirement → feature → task → code.

### For Validation
BDD scenarios give you a clear definition of "done" for each capability.

### For Flexibility
Having both Claude Code and LangGraph execution paths means:
- Interactive development stays fast (Claude Code)
- CI/CD automation becomes possible (LangGraph)
- Team-scale deployment has a path (LangGraph + MCP servers)

---

## Practical Next Steps

Potential areas to develop:

1. **Draft the Epic/Feature hierarchy** for the LangGraph orchestration layer based on the research

2. **Create starter EARS requirements** for the core workflow

3. **Map the research findings to requirement categories** so you can use /gather-requirements more effectively

4. **Create a "requirements gathering session plan"** - essentially the questions RequireKit should ask to capture this domain

5. **Decide on coexistence strategy** - How will LangGraph version interact with existing Claude Code workflows?

The research document gives us a solid architectural blueprint - now it's about translating that into formal requirements that drive implementation.

---

## Related Documents

- [Claude Agent SDK: Two-Command Feature Workflow](./Claude_Agent_SDK_Two_Command_Feature_Workflow.md) ⭐ RECOMMENDED - Two-command workflow with manual override
- [Claude Agent SDK: True End-to-End Orchestrator](./Claude_Agent_SDK_True_End_to_End_Orchestrator.md) - Full automation specification
- [Claude Agent SDK: Fast Path to TaskWright Orchestration](./Claude_Agent_SDK_Fast_Path_to_TaskWright_Orchestration.md) - Initial SDK analysis
- [LangGraph-Native Orchestration for TaskWright: Technical Architecture](./LangGraph-Native_Orchestration_for_TaskWright_Orchestration.md)
- [AgenticFlow MCP vs LangGraph Orchestrator: Integration Analysis](./AgenticFlow_MCP_vs_LangGraph_Orchestrator_Analysis.md)

---

*Generated: December 2025*
*Updated: December 2025 - Added Claude Agent SDK as fastest path option*
*Context: Planning the next phase of TaskWright development - adding orchestration capabilities*
