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

Phase 3: Implementation (TaskWright)
├── Tasks created from features with requirement links
├── /task-work with full quality gates
├── BDD scenarios drive test implementation
└── Each task traces back to EARS requirements
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

---

## Practical Next Steps

Potential areas to develop:

1. **Draft the Epic/Feature hierarchy** for the LangGraph orchestration layer based on the research

2. **Create starter EARS requirements** for the core workflow (the "quick win" 2-3 day scope)

3. **Map the research findings to requirement categories** so you can use /gather-requirements more effectively

4. **Create a "requirements gathering session plan"** - essentially the questions RequireKit should ask to capture this domain

The research document gives us a solid architectural blueprint - now it's about translating that into formal requirements that drive implementation.

---

## Related Documents

- [LangGraph-Native Orchestration for TaskWright: Technical Architecture](./LangGraph-Native_Orchestration_for_TaskWright_Technical_Architecture.md)
- [TaskWright Integration with Claude-Flow Orchestration: Feasibility Analysis](./TaskWright_Integration_with_Claude-Flow_Orchestration_Feasibility_Analysis.md)

---

*Generated: November 2025*
*Context: Planning the next phase of TaskWright development - adding LangGraph-based agent orchestration*
