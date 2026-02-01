# Job-Specific Context Retrieval

> **What is Job-Specific Context?**
>
> Job-specific context retrieval dynamically provides each task with precisely the knowledge it needs - not everything, not nothing, but exactly relevant context. This prevents wasted tokens and ensures Claude has the right information at the right time.

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Context Categories](#context-categories)
- [AutoBuild Additional Context](#autobuild-additional-context)
- [Budget Allocation](#budget-allocation)
- [Budget Adjustments](#budget-adjustments)
- [Relevance Filtering](#relevance-filtering)
- [Performance](#performance)
- [Context in Action](#context-in-action)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

---

## Overview

### The Problem

Traditional approaches to context loading have significant drawbacks:

| Approach | Problem |
|----------|---------|
| **Load everything** | Wastes tokens, dilutes relevance, hits context limits |
| **Load nothing** | Claude lacks project understanding, makes generic responses |
| **Load by file paths** | Too rigid, misses semantic relationships |

### The Solution

Job-specific context retrieval analyzes each task's characteristics and dynamically allocates a context budget across categories. The result: Claude gets exactly the knowledge needed to succeed.

**Key Benefits:**
- **Precision**: Context matched to task type, complexity, and phase
- **Efficiency**: Token budget respected, no wasted context
- **Learning**: Refinement attempts get more warning/failure context
- **AutoBuild-aware**: Player/Coach boundaries, turn history, quality gates

---

## How It Works

The system follows a 5-step pipeline for every task:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Job-Specific Context Retrieval                       │
│                                                                         │
│  Input: Task + Phase + History                                         │
│         ↓                                                               │
│  1. Task Analysis                                                       │
│     - Analyze type, complexity, novelty, AutoBuild context              │
│         ↓                                                               │
│  2. Budget Calculation                                                  │
│     - Dynamically allocate token budget (2000-6000+ tokens)             │
│         ↓                                                               │
│  3. Context Retrieval                                                   │
│     - Query Graphiti for relevant knowledge across categories           │
│         ↓                                                               │
│  4. Smart Filtering                                                     │
│     - Apply relevance thresholds and deduplication                      │
│         ↓                                                               │
│  5. Prompt Injection                                                    │
│     - Format context for optimal Claude understanding                   │
│                                                                         │
│  Output: Precisely relevant context string                              │
└─────────────────────────────────────────────────────────────────────────┘
```

### Step 1: Task Analysis

The `TaskAnalyzer` examines:

- **Task type**: Implementation, review, planning, refinement, documentation
- **Complexity**: 1-10 scale (determines base budget)
- **Novelty**: Is this the first task of this type? How many similar tasks exist?
- **Refinement status**: Is this a retry? What failed before?
- **AutoBuild context**: Turn number, current actor (Player/Coach), turn history

### Step 2: Budget Calculation

The `DynamicBudgetCalculator` determines:

- **Total tokens**: Based on complexity and adjustments
- **Allocation percentages**: How much budget for each category
- **Priority weights**: Which categories to emphasize

### Step 3: Context Retrieval

The `JobContextRetriever` queries Graphiti for:

- Feature context (if task belongs to a feature)
- Similar outcomes from past tasks
- Relevant patterns from the codebase
- Architecture context for system understanding
- Warnings from past failures
- Domain knowledge for terminology

### Step 4: Smart Filtering

Each result is filtered by:

- **Relevance score**: Below threshold results are discarded
- **Deduplication**: Redundant information removed
- **Budget trimming**: Results trimmed to fit allocation

### Step 5: Prompt Injection

Context is formatted as structured sections with:

- Clear headings per category
- Actionable framing (what to do, what to avoid)
- Budget usage reporting

---

## Context Categories

### Standard Categories

| Category | Description | When Emphasized |
|----------|-------------|-----------------|
| **Feature Context** | Requirements and success criteria for parent feature | Tasks with `feature_id` |
| **Similar Outcomes** | What worked for similar tasks (patterns, approaches) | Testing phase, all tasks |
| **Relevant Patterns** | Codebase patterns that apply to this task | Implementation phase |
| **Architecture Context** | How this fits into the overall system | First-of-type, planning |
| **Warnings** | Approaches to avoid based on past failures | Refinement attempts |
| **Domain Knowledge** | Domain-specific terminology and concepts | All tasks (lower priority) |

### Category Details

**Feature Context**
- Loaded when task has a parent `feature_id`
- Contains requirements, acceptance criteria, success metrics
- Helps maintain feature-level coherence

**Similar Outcomes**
- Patterns and approaches that succeeded in similar work
- Especially valuable for implementation and testing
- Filtered by tech stack for relevance

**Relevant Patterns**
- Codebase-specific patterns (e.g., error handling, API design)
- Loaded from `patterns_{tech_stack}` and generic `patterns` groups
- Guides implementation to match existing code style

**Architecture Context**
- High-level system understanding
- Where this component fits in the architecture
- Emphasized for novel task types

**Warnings**
- Failed approaches from past tasks
- Critical for refinement attempts
- Framed as "do NOT do this" guidance

**Domain Knowledge**
- Business terminology and concepts
- Domain-specific rules and constraints
- Lower priority but ensures consistency

---

## AutoBuild Additional Context

During `/feature-build` workflows, additional context categories are loaded to support the Player-Coach adversarial workflow.

### AutoBuild-Specific Categories

| Category | Description | Purpose |
|----------|-------------|---------|
| **Role Constraints** | Player/Coach boundaries | Prevent role reversal |
| **Quality Gate Configs** | Task-type specific thresholds | Prevent threshold drift |
| **Turn States** | Previous turn context | Enable cross-turn learning |
| **Implementation Modes** | Direct vs task-work guidance | Clarify execution patterns |

### Role Constraints

Defines what each actor can and cannot do:

```
Player:
  Must do:
    - Write code
    - Run tests
    - Fix issues
  Must NOT do:
    - Approve own work
    - Skip tests
    - Modify quality gates
  Ask before:
    - Schema changes
    - Auth/security changes
    - Deployment configs

Coach:
  Must do:
    - Validate against criteria
    - Provide specific feedback
    - Make approval decisions
  Must NOT do:
    - Write implementation code
    - Run commands
    - Modify Player's work directly
```

### Quality Gate Configs

Thresholds loaded per task type:

```
Feature tasks:
  - Coverage: ≥80%
  - Arch review: ≥60
  - Tests required: Yes

Bug fixes:
  - Coverage: ≥75%
  - Arch review: ≥50
  - Tests required: Yes

Documentation:
  - Coverage: N/A
  - Arch review: N/A
  - Tests required: No
```

### Turn States

Previous turn history for cross-turn learning:

```
Turn 1: FEEDBACK
  Progress: Initial implementation, missing tests

Turn 2: REJECTED
  Progress: Added tests, coverage at 65%
  Feedback: "Coverage must be ≥80%. Missing tests for error paths."

Turn 3: (current)
  Loaded context includes turns 1-2 to avoid repeating mistakes
```

### Implementation Modes

Clarifies where files are created:

```
task-work mode:
  Results in: worktree directory
  State via: JSON checkpoints
  Pitfalls: Don't expect files in main repo during execution

direct mode:
  Results in: main repository
  State via: Task file updates
  Pitfalls: Changes visible immediately, no isolation
```

---

## Budget Allocation

### Base Budgets by Complexity

| Task Complexity | Base Budget | Typical Use Cases |
|-----------------|-------------|-------------------|
| **Simple (1-3)** | 2,000 tokens | Typo fixes, small features, documentation |
| **Medium (4-6)** | 4,000 tokens | Standard features, moderate refactoring |
| **Complex (7-10)** | 6,000 tokens | Architecture changes, security features |

### Default Allocation (Standard Tasks)

```
Feature Context:       15%
Similar Outcomes:      25%
Relevant Patterns:     20%
Architecture Context:  20%
Warnings:             15%
Domain Knowledge:       5%
```

### AutoBuild Allocation

When `is_autobuild=True`, allocation shifts to include AutoBuild categories:

```
Feature Context:       10%
Similar Outcomes:      15%
Relevant Patterns:     15%
Architecture Context:  10%
Warnings:             10%
Domain Knowledge:       5%
Role Constraints:      10%
Quality Gate Configs:  10%
Turn States:          10%
Implementation Modes:   5%
```

### Allocation by Task Type

**Review Tasks:**
```
Relevant Patterns:     30%  (what patterns should be used)
Architecture Context:  25%  (does it fit the system)
Similar Outcomes:      15%
Others:               30%
```

**Planning Tasks:**
```
Feature Context:       25%
Architecture Context:  30%
Similar Outcomes:      15%
Others:               30%
```

**Refinement Tasks:**
```
Warnings:             35%  (emphasize what went wrong)
Similar Outcomes:      30%  (how others fixed similar)
Relevant Patterns:     15%
Others:               20%
```

---

## Budget Adjustments

The base budget is adjusted based on task characteristics:

### Adjustment Modifiers

| Condition | Adjustment | Rationale |
|-----------|------------|-----------|
| **First-of-type** | +30% | Novel tasks need more architecture understanding |
| **Few similar tasks (<3)** | +15% | Less precedent to draw from |
| **Refinement attempt** | +20% | Need more context about what failed |
| **AutoBuild Turn >1** | +15% | Load previous turn context |
| **AutoBuild with history** | +10% | Enable cross-turn learning |

### Example Budget Calculations

**Simple first-of-type task:**
```
Base budget:      2,000 tokens
First-of-type:   +30% → 2,600 tokens
Total:            2,600 tokens
```

**Medium refinement task:**
```
Base budget:      4,000 tokens
Refinement:      +20% → 4,800 tokens
Total:            4,800 tokens
```

**Complex AutoBuild turn 3:**
```
Base budget:      6,000 tokens
Turn >1:         +15% → 6,900 tokens
Has history:     +10% → 7,590 tokens
Total:            7,590 tokens
```

---

## Relevance Filtering

### Relevance Thresholds

Results are filtered by semantic similarity score:

| Task Context | Threshold | Rationale |
|--------------|-----------|-----------|
| **Standard tasks** | 0.6 | High precision, avoid noise |
| **First-of-type** | 0.5 | Broader context for novel tasks |
| **Refinement** | 0.5 | Don't miss failure patterns |

### How Thresholds Work

```
Query: "implement user authentication"
Results:
  1. "JWT auth pattern" (score: 0.82) → ✓ Included
  2. "Password hashing guide" (score: 0.71) → ✓ Included
  3. "User model definition" (score: 0.58) → ✗ Below 0.6 threshold
  4. "Rate limiting middleware" (score: 0.45) → ✗ Below threshold
```

### Threshold Tuning

If context is missing relevant information, you can adjust thresholds:

```python
# In relevance_tuning.py
THRESHOLDS = {
    "standard": 0.6,      # Decrease to 0.5 for broader results
    "first_of_type": 0.5, # Already permissive
    "refinement": 0.5     # Already permissive
}
```

---

## Performance

### Measured Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Average retrieval time** | 600-800ms | Concurrent queries across categories |
| **Cache hit rate** | ~40% | Repeated context cached at multiple levels |
| **Budget utilization** | 70-90% | Efficient, rarely exceeds budget |
| **Relevance scores** | 0.65-0.85 avg | High quality matches |

### Performance Optimizations

1. **Concurrent queries**: All category queries run in parallel
2. **Result caching**: Graphiti client caches recent queries
3. **Early termination**: Stop retrieval when budget exhausted
4. **Deduplication**: Avoid loading the same fact twice

### Monitoring

Context retrieval is logged during task execution:

```
[INFO] Retrieved job-specific context (1850/2000 tokens)
  - Similar outcomes: 3 results (0.72 avg relevance)
  - Relevant patterns: 2 results (0.81 avg relevance)
  - Warnings: 1 result (0.68 relevance)
  - Architecture: 2 results (0.75 avg relevance)
```

---

## Context in Action

### Standard Task Execution

```bash
# Context automatically loaded during task execution
/task-work TASK-XXX
```

What happens:
1. Task analyzed (type=implementation, complexity=5, novelty=standard)
2. Budget calculated (4000 tokens)
3. Context retrieved:
   - Similar outcomes (25%)
   - Relevant patterns (20%)
   - Architecture context (20%)
   - Feature context (15%)
   - Warnings (15%)
   - Domain knowledge (5%)
4. Context formatted and injected into prompt

### AutoBuild Execution

```bash
# Context with AutoBuild-specific sections
/feature-build TASK-XXX
```

**Turn 1:**
- Loads role constraints, quality gates, implementation modes
- No turn history yet

**Turn 2+:**
- Loads all Turn 1 context PLUS:
- Previous turn states (what was rejected, why)
- Adjusted allocation (more turn states, fewer general patterns)

### Example Retrieved Context

For a medium-complexity authentication task:

```markdown
## Job-Specific Context

Budget used: 3,200/4,000 tokens

### What Worked for Similar Tasks

*Patterns and approaches that succeeded in similar work*

- **JWT Authentication**: Used refresh tokens with 15min expiry
- **Password Hashing**: Argon2id with memory cost 64MB
- **Session Management**: Redis-backed with sliding expiration

### Recommended Patterns

*Patterns from the codebase that apply here*

- **AuthMiddleware**: See src/middleware/auth.py for pattern
- **TokenService**: Service-based approach, not inline validation

### Architecture Context

*How this fits into the overall system*

- **Auth is a core service**: All other services depend on it
- **API Gateway handles auth**: Services trust internal requests

### Warnings from Past Experience

*Approaches to AVOID based on past failures*

- **DO NOT** store tokens in localStorage (XSS vulnerability)
- **DO NOT** use symmetric keys for JWT (use RS256)
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Context missing information | Knowledge not seeded | Run `guardkit graphiti seed` |
| Context irrelevant | Threshold too low | Increase relevance threshold |
| AutoBuild context missing | Metadata incorrect | Verify `is_autobuild=True` in task |
| Slow retrieval (>2s) | Neo4j performance | Check Neo4j resources, verify network |

### Detailed Troubleshooting

**"Context missing relevant information"**

1. Check if knowledge has been seeded:
   ```bash
   guardkit graphiti status
   ```

2. Verify the task description is specific enough:
   ```yaml
   # Bad: Too vague
   description: "Add feature"

   # Good: Specific for matching
   description: "Add JWT-based authentication with refresh tokens"
   ```

3. Review what was retrieved:
   - Check the `[INFO]` logs for retrieval stats
   - If relevance scores are low, content may not be seeded

**"Context contains irrelevant information"**

1. Increase relevance threshold:
   ```python
   # In relevance_tuning.py
   THRESHOLDS["standard"] = 0.65  # Up from 0.6
   ```

2. Review seeded knowledge quality:
   ```bash
   guardkit graphiti search "your query" --limit 10
   ```

3. Check task characteristics are correctly classified

**"AutoBuild context missing"**

1. Verify task metadata:
   ```yaml
   # Task file must have:
   is_autobuild: true
   ```

2. Check role constraints are seeded:
   ```bash
   guardkit graphiti search "role constraints" --group role_constraints
   ```

3. Verify turn states are persisted:
   ```bash
   guardkit graphiti search "turn state TASK-XXX" --group turn_states
   ```

**"Slow retrieval (>2 seconds)"**

1. Check Neo4j/FalkorDB health:
   ```bash
   docker ps | grep -E "(neo4j|falkordb)"
   ```

2. Reduce context categories for very simple tasks

3. Verify network latency to graph database

4. Consider increasing cache TTL

---

## See Also

- [Graphiti Integration Guide](graphiti-integration-guide.md) - Setup and configuration
- [Graphiti Commands Reference](graphiti-commands.md) - CLI commands
- [AutoBuild Workflow](autobuild-workflow.md) - Player-Coach workflow details
- [Quality Gates Integration](quality-gates-integration.md) - Threshold configuration
- [FEAT-GR-006 Specification](../research/graphiti-refinement/FEAT-GR-006-job-specific-context.md) - Technical details

---

## Technical Reference

### Core Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `TaskAnalyzer` | `guardkit/knowledge/task_analyzer.py` | Analyzes task characteristics |
| `DynamicBudgetCalculator` | `guardkit/knowledge/budget_calculator.py` | Calculates context budgets |
| `JobContextRetriever` | `guardkit/knowledge/job_context_retriever.py` | Retrieves and formats context |
| `RelevanceTuning` | `guardkit/knowledge/relevance_tuning.py` | Configurable thresholds |

### Configuration

Context retrieval settings can be adjusted in `config/graphiti.yaml`:

```yaml
context:
  base_budgets:
    simple: 2000
    medium: 4000
    complex: 6000

  relevance_thresholds:
    standard: 0.6
    first_of_type: 0.5
    refinement: 0.5

  cache_ttl: 300  # seconds
```

### API Integration

For programmatic access:

```python
from guardkit.knowledge.job_context_retriever import JobContextRetriever
from guardkit.knowledge.task_analyzer import TaskPhase

retriever = JobContextRetriever()
context = await retriever.retrieve(
    task=task_dict,
    phase=TaskPhase.IMPLEMENT
)

# Format for prompt injection
prompt_context = context.to_prompt()
```
