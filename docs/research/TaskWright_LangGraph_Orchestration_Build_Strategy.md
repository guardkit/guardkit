# TaskWright LangGraph Orchestration: Build Strategy Analysis

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

## Critical Clarification: What LangGraph Can and Cannot Do

### What LangGraph CANNOT Do

**LangGraph cannot directly call Claude Code slash commands like `/task-create`, `/task-work`, `/task-review`.**

Those slash commands are:
1. **Claude Code UI constructs** - They're interpreted by Claude Code's interface, not executable from external Python code
2. **Prompt injections** - They trigger Claude to read the corresponding `.md` command file and follow its instructions
3. **Not CLI commands** - There's no `taskwright /task-create` binary that LangGraph could subprocess

### What This Means

TaskWright's logic currently lives in **markdown command specifications** (`.claude/commands/*.md`) that instruct Claude how to behave. These are not callable Python functions. Building a LangGraph orchestrator means **reimplementing the workflow logic in Python**, not wrapping the existing slash commands.

### The Three Realistic Options

#### Option A: LangGraph as a Parallel Implementation (Recommended)
- Build a Python LangGraph workflow that does what `/task-work` does
- It calls Anthropic API for the AI-powered parts (planning, code generation, review)
- It manages state, checkpoints, and retries explicitly
- **Effort**: 2-3 weeks to replicate core workflow
- **Benefit**: Clean architecture, testable, deployable independently of Claude Code

#### Option B: Continue with Claude Code, Add LangGraph Later
- Keep using `/task-work` as-is for implementation
- Use RequireKit for the specification layer (this works today)
- Build LangGraph orchestrator as a future phase when needed
- **Effort**: Zero for now, defer orchestrator work
- **Benefit**: Ship features now, defer complexity

#### Option C: Hybrid - LangGraph for Outer Loop, Claude Code for Inner (Complex)
```
LangGraph Orchestrator (Python)
    │
    ├── Phase: Requirements ──► RequireKit commands (if extracted to Python)
    │
    ├── Phase: Task Creation ──► Write task markdown files directly
    │
    ├── Phase: Implementation ──► Call Anthropic API directly
    │                              (NOT Claude Code - it has no programmatic API)
    │
    └── Phase: Review ──► Parse outputs, update state
```

The challenge with Option C is that Claude Code doesn't have a clean programmatic API - it's an interactive tool designed for human use.

---

## Recommended Path: Parallel Implementation

The LangGraph orchestrator should be built as a **new implementation** that:

1. **Reads the same task files** - Compatible with existing `.claude/tasks/` structure
2. **Follows the same phases** - 2 → 2.5B → 2.7 → 2.8 → 3 → 4/4.5 → 5/5.5
3. **Uses the same agent specs** - Reads `.claude/agents/*.md` for context
4. **Calls Anthropic API directly** - For planning, implementation, review
5. **Manages state in LangGraph** - Using SqliteSaver/PostgresSaver

This means the LangGraph version and Claude Code version can coexist:
- Use Claude Code for interactive development (today)
- Use LangGraph for automated/CI pipelines (future)
- Same task files, same agent specs, different execution engines

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

- [LangGraph-Native Orchestration for TaskWright: Technical Architecture](./LangGraph-Native_Orchestration_for_TaskWright_Technical_Architecture.md)
- [AgenticFlow MCP vs LangGraph Orchestrator: Integration Analysis](./AgenticFlow_MCP_vs_LangGraph_Orchestrator_Analysis.md)

---

*Generated: December 2025*
*Updated: December 2025 - Added clarification that LangGraph cannot call Claude Code slash commands*
*Context: Planning the next phase of TaskWright development - adding LangGraph-based agent orchestration*
