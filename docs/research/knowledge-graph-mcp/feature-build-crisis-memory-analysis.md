# Feature-Build Crisis Analysis: Memory Integration as the Solution

> **Purpose**: Analyze the systemic issues causing `/feature-build` failures and demonstrate how Graphiti knowledge graph integration addresses the root causes.
>
> **Date**: January 2025
> **Status**: Analysis Complete
> **Related**: `graphiti-prototype-integration-plan.md`, `graphiti-deepagents-integration-architecture.md`

---

## Executive Summary

The `/feature-build` command has been struggling through a series of cascading failures, each fix revealing another underlying issue. Analysis of the reviews reveals a **systemic problem**: Claude Code sessions lack persistent context about:

1. **What was already tried** (and failed)
2. **Where we are in the overall architecture**
3. **What the correct integration patterns are** for this codebase

This is exactly the problem that Graphiti integration solves. The reviews document a pattern where:
- Each Claude Code session starts fresh without prior context
- The same mistakes get repeated across sessions
- Architecture decisions are inconsistent because they're made without historical context
- Quality gates are bypassed or produce mock data because the full workflow isn't understood

**Key Insight**: The feature-build issues are not primarily code bugs - they are **context and memory failures** that Graphiti is designed to solve.

---

## Issue Pattern Analysis

### The Cascade of Failures (from Reviews)

| Review | Issue Found | Root Cause | Why It Wasn't Caught Earlier |
|--------|-------------|------------|------------------------------|
| FB01 | SDK Integration gaps | AgentInvoker placeholder code | No context about what was already built |
| FB02 | Task-work results not found | Delegation disabled by default | Decision made in isolation |
| FB03 | CLI command doesn't exist | Architecture mismatch | No memory of original design |
| FB04 | Pre-loop returns mock data | TaskWorkInterface stub never replaced | No tracking of incomplete work |
| FB49 | JSON parsing failures | Large response handling | Pattern not learned from prior failures |

### The Recurring Pattern

```
Session 1: Implements partial solution
    ↓
Session 2: Doesn't know Session 1's work, implements differently
    ↓
Session 3: Finds inconsistency, "fixes" by breaking Session 1's work
    ↓
Session 4: Discovers breakage, doesn't understand why original approach was taken
    ↓
[Repeat until developer intervention]
```

This is the **stochastic development problem** you identified - without memory, each session is a roll of the dice.

---

## Critical Integration Points Missing from Current Plan

Based on the review analysis, here are the **specific memory integration touch points** that would have prevented these issues:

### 1. Pre-Session Context Loading

**The Problem**: Each `/feature-build` attempt starts without knowledge of:
- Previous attempts on the same feature
- What files were created/modified
- What errors were encountered
- What approaches failed

**Graphiti Solution**:
```python
# Before starting feature-build
async def pre_feature_build_context(feature_id: str) -> str:
    """Load all relevant context before starting."""
    
    results = await graphiti.search(
        query=f"feature {feature_id} implementation attempts errors",
        group_ids=[
            f"feature_{feature_id}",           # This feature's history
            "failed_approaches",               # What didn't work
            "successful_patterns",             # What did work
            "architecture_decisions"           # Design decisions
        ],
        num_results=15
    )
    
    # Build context that includes:
    # - "Previous attempt on 2025-01-10 failed because pre-loop returned mock data"
    # - "TaskWorkInterface needs SDK integration, not subprocess"
    # - "Coach expects task_work_results.json in feature worktree, not task worktree"
    
    return format_as_warnings_and_context(results)
```

**What it would have caught**:
- FB03: "Previous decision: use SDK query() not subprocess to CLI"
- FB04: "WARNING: TaskWorkInterface.execute_design_phase() returns mock data"

### 2. Architecture Decision Tracking

**The Problem**: Key architecture decisions are made and forgotten:
- Use SDK `query()` vs subprocess
- Worktree path structure (feature vs task)
- Report file locations and formats
- Delegation vs direct invocation

**Graphiti Solution**:
```python
# After making an architecture decision
async def capture_architecture_decision(
    decision: str,
    context: str,
    alternatives_rejected: List[str],
    rationale: str
):
    """Capture architecture decision for future reference."""
    
    episode = {
        "decision_type": "architecture",
        "decision": decision,
        "context": context,
        "alternatives": alternatives_rejected,
        "rationale": rationale,
        "made_by": "feature-build development",
        "date": datetime.now().isoformat(),
        "status": "active"
    }
    
    await graphiti.add_episode(
        name=f"arch_decision_{hash(decision)[:8]}",
        episode_body=json.dumps(episode),
        group_id="architecture_decisions"
    )
```

**Decisions that should have been captured**:
- "SDK `query()` for Player invocation, not subprocess to non-existent CLI"
- "Coach path should use feature worktree ID, not task ID"
- "task-work delegation writes to task_work_results.json"
- "Pre-loop should actually invoke /task-work --design-only"

### 3. Integration Point Documentation

**The Problem**: The codebase has multiple technology intersections that aren't documented in a queryable way:
- Claude Code slash commands
- Python CLI
- Claude Agents SDK
- Subagent markdown files
- Quality gate phases

**Graphiti Solution**:
```python
# Capture integration point knowledge
async def capture_integration_point(
    name: str,
    connects: List[str],
    protocol: str,
    inputs: Dict,
    outputs: Dict,
    edge_cases: List[str]
):
    """Document an integration point between components."""
    
    episode = {
        "integration_point": name,
        "connects_components": connects,
        "protocol": protocol,  # "sdk_query" | "subprocess" | "file_exchange"
        "inputs": inputs,
        "outputs": outputs,
        "known_edge_cases": edge_cases
    }
    
    await graphiti.add_episode(
        name=f"integration_{name}",
        episode_body=json.dumps(episode),
        group_id="integration_points"
    )
```

**Integration points for feature-build**:
```json
{
  "integration_point": "autobuild_to_taskwork",
  "connects_components": ["AutoBuildOrchestrator", "task-work command"],
  "protocol": "sdk_query",
  "inputs": {
    "task_id": "TASK-XXX",
    "mode": "--implement-only | --design-only",
    "worktree_path": "path to feature worktree"
  },
  "outputs": {
    "task_work_results.json": "quality gate results",
    "files_created": "list of files"
  },
  "known_edge_cases": [
    "subprocess to CLI doesn't work - CLI command doesn't exist",
    "Path must use feature worktree ID not task ID"
  ]
}
```

### 4. Failure Pattern Recognition

**The Problem**: Same failures repeat:
- Mock data returned instead of real execution
- Path construction bugs (task ID vs feature ID)
- Missing file errors
- Timeout issues masking real errors

**Graphiti Solution**:
```python
# Capture failure for future avoidance
async def capture_failure_pattern(
    error_type: str,
    symptom: str,
    root_cause: str,
    fix_applied: str,
    how_to_avoid: str
):
    """Capture failure pattern so it's not repeated."""
    
    episode = {
        "error_type": error_type,
        "symptom": symptom,
        "root_cause": root_cause,
        "fix_applied": fix_applied,
        "prevention": how_to_avoid,
        "occurrences": 1
    }
    
    await graphiti.add_episode(
        name=f"failure_{error_type}_{hash(symptom)[:8]}",
        episode_body=json.dumps(episode),
        group_id="failure_patterns"
    )
```

**Failures that should be captured**:
```json
{
  "error_type": "missing_file",
  "symptom": "Task-work results not found at .guardkit/worktrees/TASK-XXX/...",
  "root_cause": "Coach constructs path using task ID instead of feature worktree ID",
  "fix_applied": "Use feature worktree path: .guardkit/worktrees/FEAT-XXX/...",
  "prevention": "When in feature mode, always use feature_worktree_id for paths"
}
```

### 5. Component State Tracking

**The Problem**: Components have incomplete implementations but no tracking:
- `TaskWorkInterface.execute_design_phase()` returns mock data
- `AgentInvoker._invoke_with_role()` had NotImplementedError
- CLI feature-mode not implemented

**Graphiti Solution**:
```python
# Track component implementation status
async def capture_component_status(
    component: str,
    method: str,
    status: str,  # "implemented" | "stub" | "partial" | "deprecated"
    notes: str
):
    """Track component implementation status."""
    
    episode = {
        "component": component,
        "method": method,
        "status": status,
        "notes": notes,
        "last_updated": datetime.now().isoformat()
    }
    
    await graphiti.add_episode(
        name=f"component_{component}_{method}",
        episode_body=json.dumps(episode),
        group_id="component_status"
    )
```

**Components to track**:
```json
[
  {"component": "TaskWorkInterface", "method": "execute_design_phase", "status": "stub", "notes": "Returns mock data, needs SDK integration"},
  {"component": "AgentInvoker", "method": "_invoke_task_work_implement", "status": "partial", "notes": "Subprocess to non-existent CLI"},
  {"component": "CLI", "method": "feature-mode", "status": "not_implemented", "notes": "Task tool fallback works, CLI optional"}
]
```

---

## Updated Graphiti Integration Touch Points

Based on this analysis, here are the **specific additions** to the prototype integration plan:

### Phase 0: Critical Pre-Session Context (ADD THIS)

**Before any command execution**:
```python
async def load_session_context() -> SessionContext:
    """Load critical context at session start."""
    
    # 1. Load recent failures for this project
    failures = await graphiti.search(
        query="error failure bug",
        group_ids=["failure_patterns", "failed_approaches"],
        num_results=10
    )
    
    # 2. Load incomplete components
    incomplete = await graphiti.search(
        query="stub partial not_implemented",
        group_ids=["component_status"],
        num_results=10
    )
    
    # 3. Load architecture decisions
    decisions = await graphiti.search(
        query="architecture decision integration",
        group_ids=["architecture_decisions"],
        num_results=10
    )
    
    # 4. Load integration points
    integrations = await graphiti.search(
        query="integration protocol",
        group_ids=["integration_points"],
        num_results=10
    )
    
    return SessionContext(
        warnings=format_as_warnings(failures),
        incomplete_work=format_incomplete(incomplete),
        architecture_context=format_decisions(decisions),
        integration_knowledge=format_integrations(integrations)
    )
```

### New Group IDs for Feature-Build

Add these group IDs to the schema:

```
group_ids/
├── architecture_decisions     # Design decisions and rationale
├── integration_points         # Component integration documentation
├── component_status           # Implementation status tracking
├── failure_patterns           # Captured failures with fixes
├── feature_{FEAT-XXX}         # Feature-specific history
└── session_outcomes           # What happened in each session
```

### Updated Command Hooks

#### `/feature-build FEAT-XXX`

**Pre-execution** (new):
```python
async def pre_feature_build(feature_id: str) -> FeatureBuildContext:
    """Load comprehensive context before feature-build."""
    
    context = await load_session_context()
    
    # Feature-specific context
    feature_history = await graphiti.search(
        query=f"feature {feature_id} attempt outcome",
        group_ids=[f"feature_{feature_id}"],
        num_results=10
    )
    
    # Task patterns for this type of feature
    similar_features = await graphiti.search(
        query=extract_feature_type(feature_id),  # e.g., "infrastructure setup"
        group_ids=["feature_completions"],
        num_results=5
    )
    
    return FeatureBuildContext(
        session_context=context,
        previous_attempts=feature_history,
        similar_feature_patterns=similar_features
    )
```

**Post-execution** (enhanced):
```python
async def post_feature_build(
    feature_id: str,
    outcome: FeatureBuildOutcome,
    session_transcript: str
):
    """Capture comprehensive outcome."""
    
    # Capture overall outcome
    await capture_feature_attempt(feature_id, outcome)
    
    # Extract and capture any architecture decisions made
    decisions = extract_architecture_decisions(session_transcript)
    for decision in decisions:
        await capture_architecture_decision(**decision)
    
    # Extract and capture any failures encountered
    failures = extract_failure_patterns(session_transcript)
    for failure in failures:
        await capture_failure_pattern(**failure)
    
    # Update component status if changed
    status_changes = extract_component_changes(session_transcript)
    for change in status_changes:
        await capture_component_status(**change)
```

---

## How This Would Have Prevented Each Issue

### FB03: CLI Command Doesn't Exist

**Without Graphiti**:
- TASK-FB-DEL1 enabled delegation
- Delegation calls subprocess to `guardkit task-work`
- Command doesn't exist
- Silent failure, no learning

**With Graphiti**:
```
Pre-session context would include:
- Architecture Decision: "Use SDK query() for task-work invocation, not subprocess"
- Integration Point: "autobuild_to_taskwork uses sdk_query protocol"
- Previous Failure: "Subprocess to guardkit task-work fails - command not implemented"

Claude would know immediately: "I should use SDK query(), not subprocess"
```

### FB04: Pre-Loop Returns Mock Data

**Without Graphiti**:
- TaskWorkInterface has stub implementation
- Returns mock data (complexity=5, arch_score=80)
- No implementation plan created
- Player fails because plan doesn't exist

**With Graphiti**:
```
Pre-session context would include:
- Component Status: "TaskWorkInterface.execute_design_phase() is STUB - needs SDK integration"
- Architecture Decision: "Pre-loop must invoke /task-work --design-only to generate plan"
- Failure Pattern: "Player fails with 'implementation plan not found' when pre-loop uses stub"

Claude would know: "I need to implement execute_design_phase() with real SDK calls"
```

### FB02: Task-Work Results Not Found (Wrong Path)

**Without Graphiti**:
- Coach constructs path using task ID
- File is in feature worktree, not task worktree
- Coach can't find results
- Validation fails

**With Graphiti**:
```
Pre-session context would include:
- Integration Point: "Coach expects results at .guardkit/worktrees/FEAT-XXX/.../task_work_results.json"
- Failure Pattern: "Path construction using task ID fails in feature mode"
- Architecture Decision: "In feature mode, use feature_worktree_id for all paths"

Claude would know: "Path must use FEAT-XXX, not TASK-XXX"
```

---

## Implementation Priority

Given the current feature-build crisis, here's the recommended implementation order:

### Immediate (This Week)

1. **Session Context Loading**: Implement basic `load_session_context()` that queries for:
   - Recent failures
   - Architecture decisions
   - Integration points

2. **Failure Capture**: Add `capture_failure_pattern()` to post-task hooks

3. **Manual Seeding**: Create initial episodes for:
   - The known architecture decisions (SDK vs subprocess, path structure)
   - The known failures (FB02, FB03, FB04)
   - The integration points (autobuild → task-work)

### Short-Term (Next 2 Weeks)

4. **Architecture Decision Capture**: Add hooks to capture decisions during development

5. **Component Status Tracking**: Add `capture_component_status()` for stub/partial implementations

6. **Feature-Specific History**: Add `capture_feature_attempt()` for feature-build outcomes

### Medium-Term (With DeepAgents Migration)

7. **Full Middleware Integration**: GraphitiMiddleware in DeepAgents stack

8. **Automated Pattern Extraction**: Use LLM to extract decisions/failures from session transcripts

9. **Cross-Feature Learning**: Query similar features for pattern suggestions

---

## Conclusion

The feature-build issues are fundamentally **memory and context problems**, not just code bugs. Each review reveals a pattern where:

1. A decision was made in isolation
2. That decision created an inconsistency with other decisions
3. A future session didn't know about either decision
4. The inconsistency manifested as a "bug"

Graphiti integration addresses this by:

1. **Persisting architecture decisions** so they're queryable
2. **Capturing failure patterns** so they're not repeated
3. **Documenting integration points** so protocols are consistent
4. **Tracking component status** so stubs aren't forgotten

The prototype integration plan should be updated to prioritize:
- Session context loading (pre-execution hooks)
- Failure pattern capture (post-execution hooks)
- Architecture decision tracking (during development)

This will break the cycle of "fix one bug, create another" that has plagued feature-build development.

---

## Appendix: Manual Seeding Episodes

To immediately help feature-build, manually add these episodes:

### Architecture Decisions

```json
[
  {
    "decision": "Use SDK query() for task-work invocation",
    "not": "subprocess to guardkit CLI",
    "rationale": "CLI command doesn't exist, SDK query() invokes slash commands directly",
    "group_id": "architecture_decisions"
  },
  {
    "decision": "In feature mode, paths use FEAT-XXX worktree ID",
    "not": "individual TASK-XXX IDs",
    "rationale": "Feature worktree is shared, task IDs are for task management not filesystem",
    "group_id": "architecture_decisions"
  },
  {
    "decision": "Pre-loop must invoke /task-work --design-only",
    "not": "return mock data from stub",
    "rationale": "Implementation plan must exist for Player to read",
    "group_id": "architecture_decisions"
  }
]
```

### Failure Patterns

```json
[
  {
    "error_type": "missing_command",
    "symptom": "subprocess.CalledProcessError: guardkit task-work",
    "root_cause": "CLI command not implemented",
    "fix": "Use SDK query() instead",
    "group_id": "failure_patterns"
  },
  {
    "error_type": "missing_file",
    "symptom": "Task-work results not found at .../TASK-XXX/...",
    "root_cause": "Path uses task ID instead of feature worktree ID",
    "fix": "Use feature_worktree_id for path construction",
    "group_id": "failure_patterns"
  },
  {
    "error_type": "mock_data",
    "symptom": "Pre-loop returns complexity=5, arch_score=80",
    "root_cause": "TaskWorkInterface.execute_design_phase() is stub",
    "fix": "Implement with SDK query() to /task-work --design-only",
    "group_id": "failure_patterns"
  }
]
```

### Integration Points

```json
[
  {
    "name": "autobuild_to_taskwork",
    "connects": ["AutoBuildOrchestrator", "task-work command"],
    "protocol": "sdk_query",
    "correct_pattern": "query('/task-work TASK-XXX --implement-only', cwd=worktree_path)",
    "wrong_pattern": "subprocess.run(['guardkit', 'task-work', ...])",
    "group_id": "integration_points"
  },
  {
    "name": "coach_result_path",
    "connects": ["CoachValidator", "task_work_results.json"],
    "correct_pattern": ".guardkit/worktrees/FEAT-XXX/.guardkit/autobuild/TASK-XXX/task_work_results.json",
    "wrong_pattern": ".guardkit/worktrees/TASK-XXX/.guardkit/autobuild/...",
    "group_id": "integration_points"
  }
]
```

### Component Status

```json
[
  {
    "component": "TaskWorkInterface",
    "method": "execute_design_phase",
    "status": "stub",
    "needs": "SDK query() integration to invoke /task-work --design-only",
    "group_id": "component_status"
  },
  {
    "component": "AgentInvoker",
    "method": "_invoke_task_work_implement",
    "status": "incorrect",
    "problem": "Uses subprocess to non-existent CLI",
    "needs": "SDK query() instead",
    "group_id": "component_status"
  }
]
```

---

## References

- [TASK-REV-FB01 Review Report](../.claude/reviews/TASK-REV-FB01-review-report.md)
- [TASK-REV-FB02 Review Report](../.claude/reviews/TASK-REV-FB02-review-report.md)
- [TASK-REV-FB03 Review Report](../.claude/reviews/TASK-REV-fb03-review-report.md)
- [TASK-REV-FB04 Review Report](../.claude/reviews/TASK-REV-FB04-review-report.md)
- [Graphiti Prototype Integration Plan](./graphiti-prototype-integration-plan.md)
- [Graphiti DeepAgents Architecture](./graphiti-deepagents-integration-architecture.md)
