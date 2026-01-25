# Adversarial Intensity and GuardKit Workflow Review

**Date:** January 10, 2026  
**Status:** Research Complete - Principles Validated  
**Triggered By:** Chris Parsons article "Your Agent Orchestrator Is Too Clever"  
**Reference:** https://www.chrismdp.com/your-agent-orchestrator-is-too-clever/

---

## Executive Summary

This document captures a comprehensive review of GuardKit's workflow approach compared to simpler "Ralph loop" methodologies. The review validates GuardKit's adaptive workflow design while identifying a key enhancement: **tuning adversarial intensity based on complexity scoring**.

**Key Finding:** GuardKit's workflow isn't overly complex - it's appropriately layered with adaptive ceremony. The adversarial cooperation pattern for DeepAgents should extend this principle by varying Player-Coach intensity based on task complexity.

**Key Principle Identified:** Adversarial intensity should scale with complexity scoring, complementing the existing `--micro` flag on `/task-work`.

---

## Context: The Ralph Loops Argument

### Chris Parsons' Position

The article argues that with modern models (Opus 4.5, GPT 5.2), simpler orchestration approaches beat elaborate multi-agent systems:

> "The bitter lesson keeps teaching the same thing: simpler methods plus more compute beat clever engineering. In 2026, the agents are good enough that a for loop is a legitimate orchestration strategy."

The Ralph loop technique (created by Geoffrey Huntley) is presented as evidence:

```bash
while :; do
  cat PROMPT.md | claude-code --continue
done
```

### Where Ralph Loops Excel

- Greenfield projects with clear programmatic completion criteria
- Mechanical, repetitive work (migrations, refactoring across many files)
- Single technology stack with familiar patterns
- Tasks where "done" = tests pass

### Where Ralph Loops Fall Short

- Integration seams between technologies
- Subjective completion criteria
- Tasks requiring architectural decisions
- Multi-day features requiring design approval
- Learning from outcomes across projects

---

## Real-World Evidence: MyDrive vs GuardKit Development

### Observation

Rich's experience developing two different projects revealed a pattern:

| Project | Stack | Results |
|---------|-------|---------|
| **MyDrive** | .NET MAUI (single stack) | Good, consistent results |
| **GuardKit** | Multi-technology seams | More variable, often takes iterations |

### Analysis

This aligns with what Ralph practitioners acknowledge:

> "Lesson - for existing codebases, make the change set manageable - we have since set up any ralph-ish desired state loops to run ONCE on a cron overnight, and merge small iterations over time."
> — HumanLayer blog

The variability in GuardKit development stems from:
1. Technology seams (Python + Claude Code + MCP + LangGraph)
2. Integration complexity
3. Bugs occurring at boundaries rather than pure logic
4. Subjective "done" criteria for architectural decisions

---

## GuardKit Workflow Review

### Current Workflow Phases

| Phase | Purpose | Value Assessment |
|-------|---------|------------------|
| **Complexity Scoring (2.7)** | Routes to appropriate review intensity | ✅ Essential - prevents over/under-engineering |
| **Architectural Review (2.5B)** | SOLID/DRY/YAGNI validation | ✅ Essential - prevents technical debt |
| **Clarifying Questions (1.6)** | Validates understanding before coding | ✅ Essential - prevents building wrong thing |
| **Test Fix Loops (4.5)** | Zero tolerance for broken tests | ✅ Essential - ensures quality |
| **Plan Audit (5.5)** | Scope creep detection | ✅ Essential - prevents uncontrolled expansion |
| **Design Patterns MCP** | Pattern suggestions | ⚠️ Optional - not always needed |

### Conclusion: Not Overly Onerous

The workflow is **appropriately layered**, not unnecessarily complex. Each phase prevents a specific failure mode:

- Skip complexity scoring → Over-engineer simple tasks OR under-review complex ones
- Skip architectural review → Technical debt accumulates, costly rework
- Skip clarifying questions → Build the wrong thing
- Skip test fix loops → Broken code reaches review
- Skip plan audit → Uncontrolled feature expansion

The existing `--micro` flag already demonstrates adaptive ceremony - simple tasks don't receive full process overhead.

---

## Key Insight: Adversarial Intensity Gradient

### The Principle

**Adversarial intensity should scale with complexity scoring**, extending the adaptive ceremony principle to the Player-Coach dialectical loop.

This complements:
- The existing `--micro` flag for simple tasks
- Complexity-based human checkpoint routing (AUTO_PROCEED / QUICK_OPTIONAL / FULL_REQUIRED)

### Proposed Intensity Levels

```
┌─────────────────────────────────────────────────────────────────┐
│                 ADVERSARIAL INTENSITY GRADIENT                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Complexity 1-2 (Minimal / --micro equivalent):                  │
│  ├── Skip clarifying questions                                   │
│  ├── Skip architectural review                                   │
│  ├── Auto-proceed (no checkpoint)                                │
│  ├── Player-only OR Coach validates tests pass only              │
│  └── Skip plan audit                                             │
│                                                                  │
│  Complexity 3-4 (Standard-Light):                                │
│  ├── Quick clarifying questions (with timeout)                   │
│  ├── Architectural review (auto-approve if score >60)            │
│  ├── Quick checkpoint (10s timeout)                              │
│  ├── Minimal adversarial - Coach validates requirements met      │
│  └── Plan audit (flag variance >50%)                             │
│                                                                  │
│  Complexity 5-6 (Standard):                                      │
│  ├── Full clarifying questions                                   │
│  ├── Architectural review with recommendations                   │
│  ├── Quick checkpoint                                            │
│  ├── Standard adversarial - Coach reviews requirements + tests   │
│  └── Plan audit (flag variance >20%)                             │
│                                                                  │
│  Complexity 7-10 (Strict):                                       │
│  ├── Full clarifying questions (blocking)                        │
│  ├── Architectural review (human checkpoint if score <70)        │
│  ├── Mandatory checkpoint                                        │
│  ├── Full adversarial - Coach reviews requirements + arch + integration │
│  └── Plan audit (flag any variance)                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Visualisation

```
Complexity │ Phases Active                                      
───────────┼──────────────────────────────────────────────────
    1-2    │ ░░░░░░░░░░░░░░░░░░░░ (minimal - just implement)   
    3-4    │ ████░░░░░░░░░░░░░░░░ (core gates only)            
    5-6    │ ████████████░░░░░░░░ (standard workflow)          
    7-10   │ ████████████████████ (full ceremony)              

Legend: █ = Active phase  ░ = Skipped/auto-approved            
```

---

## Design Patterns MCP: Making It Smarter

### Current State

The design patterns MCP is invoked during implementation planning regardless of task characteristics.

### Recommendation: Conditional Invocation

Make design patterns MCP invocation conditional based on task characteristics:

```python
def should_invoke_design_patterns_mcp(task_context: TaskContext) -> bool:
    """Determine if design patterns MCP adds value for this task."""
    
    # Skip for simple tasks
    if task_context.complexity <= 3:
        return False
    
    # Skip for pure bug fixes (no new architecture)
    if task_context.task_type == "bugfix":
        return False
    
    # Skip if task explicitly references a known pattern
    known_patterns = ["repository", "factory", "singleton", "observer", "strategy"]
    if any(p in task_context.description.lower() for p in known_patterns):
        return False
    
    # Invoke for:
    # - New features with architectural decisions
    # - Refactoring tasks
    # - Tasks touching multiple files/modules
    triggers = [
        task_context.files_affected > 3,
        task_context.task_type in ["feature", "refactor"],
        "architecture" in task_context.description.lower(),
        "design" in task_context.description.lower(),
    ]
    
    return any(triggers)
```

### Configuration Option

```yaml
# .guardkit/config.yaml
mcp:
  design_patterns:
    enabled: true
    complexity_threshold: 5  # Only invoke for complexity >= 5
    task_types: [feature, refactor]  # Skip for bugfix, docs, test
```

---

## Comparison: Ralph Loops vs GuardKit Adversarial

### Fundamental Difference

| Aspect | Ralph Loops | GuardKit Adversarial |
|--------|-------------|---------------------|
| **Core mechanism** | Single agent + bash loop | Player + Coach dialectic |
| **Success validation** | Agent self-report (tests pass) | Independent coach review |
| **Context handling** | Fresh each iteration | Fresh each turn + role separation |
| **Scope control** | None | Plan audit phase |
| **Complexity awareness** | None | 1-10 scoring with routing |
| **Human checkpoints** | None (except cost limits) | Complexity-gated |
| **Multi-tech seams** | Hope it works | Coach validates integration |
| **Learning** | None (stateless by design) | Knowledge graph captures outcomes |

### The Critical Insight from Block AI Research

> "The key insight in the adversarial dyad is to discard the implementing agent's self-report of success and have the coach perform an independent evaluation of compliance to requirements."

This directly addresses the failure mode observed in GuardKit development: without `/task-refine`, conversations "quite often go down a rabbit hole."

### Empirical Evidence (g3 Study)

| Platform | Completeness | Approach |
|----------|--------------|----------|
| **g3 (adversarial)** | **5/5** | Coach-Player dialectic |
| Goose | 4.5/5 | Single agent |
| Antigravity | 3/5 | Single agent |
| OpenHands | 2/5 | Single agent |

**Ablation study:** When coach feedback was withheld from g3, the final implementation was non-functional despite the player claiming success.

---

## Implementation Plan for DeepAgents Version

### Phase 1: Adversarial Intensity Configuration

Add configuration for adversarial intensity tied to complexity:

```yaml
# .guardkit/config.yaml or task frontmatter
adversarial:
  mode: auto  # auto (complexity-based), strict, standard, minimal
  
  # Override intensity thresholds
  thresholds:
    minimal: 2      # complexity <= 2
    standard_light: 4  # complexity <= 4
    standard: 6     # complexity <= 6
    strict: 10      # complexity <= 10 (everything else)
  
  # Per-intensity settings
  minimal:
    coach_validation: tests_only
    max_turns: 3
    skip_plan_audit: true
    
  standard:
    coach_validation: requirements
    max_turns: 5
    skip_plan_audit: false
    
  strict:
    coach_validation: full  # requirements + architecture + integration
    max_turns: 10
    require_human_approval: true
```

### Phase 2: Coach Validation Levels

Implement tiered Coach validation based on intensity:

```python
class CoachValidationLevel(Enum):
    TESTS_ONLY = "tests_only"        # Just verify tests pass
    REQUIREMENTS = "requirements"     # Validate against acceptance criteria
    FULL = "full"                     # Requirements + architecture + integration

def get_coach_instructions(level: CoachValidationLevel) -> str:
    """Return Coach instructions appropriate for validation level."""
    
    base_instructions = COACH_BASE_INSTRUCTIONS
    
    if level == CoachValidationLevel.TESTS_ONLY:
        return base_instructions + """
## Validation Scope: Tests Only

Your only job is to verify that:
1. All tests pass
2. No compilation errors

If tests pass, approve. Don't review code quality or requirements compliance.
"""
    
    elif level == CoachValidationLevel.REQUIREMENTS:
        return base_instructions + """
## Validation Scope: Requirements

Verify that:
1. All tests pass
2. All acceptance criteria are met
3. No scope creep (extra unrequested features)

Don't deeply review architecture or integration patterns.
"""
    
    else:  # FULL
        return base_instructions + COACH_FULL_INSTRUCTIONS
```

### Phase 3: Conditional MCP Invocation

Implement smart design patterns MCP invocation as described above.

### Phase 4: Documentation Update

Update GuardKit workflow documentation to explicitly describe adaptive ceremony:

> **GuardKit uses adaptive ceremony** - workflow intensity scales with task complexity. Simple tasks (complexity 1-3) auto-proceed through most phases. Complex tasks (7-10) receive full architectural review, mandatory checkpoints, and strict plan auditing. This isn't configurable because it's the point: right-sized process for each task.

---

## Addressing the "Too Complex" Critique

### Preemptive Response

When someone argues "Ralph loops are simpler and work just as well":

1. **Agree for greenfield/mechanical work** - They're right that elaborate orchestration isn't always needed for simple, well-bounded tasks

2. **Point to the ablation study** - When coach feedback was withheld from g3, output was non-functional despite passing tests

3. **Emphasise the validation difference** - Ralph loops trust the agent's self-report (via tests). Adversarial cooperation independently validates against requirements.

4. **Reference real-world experience** - Variable results on multi-tech projects vs consistent results on single-stack projects

5. **Show adaptive design** - GuardKit already scales ceremony with complexity. The `--micro` flag exists. This isn't fixed heavy process.

### The Right Question

The question isn't "guardrails vs no guardrails" but:

> **"Who validates success - the implementer or an independent reviewer?"**

GuardKit Agent answers: an independent reviewer (Coach) with the same context but different objectives.

---

## Architectural Decision: Where Adversarial Cooperation Applies

### Current Scope

| Command | Adversarial Pattern | Rationale |
|---------|--------------------|-----------|
| `/feature-build` | ✅ Yes (Player-Coach) | Multi-task features benefit from independent validation |
| `/task-work` | ❌ No (single agent) | Simpler flow, potentially quicker for individual tasks |
| `gka feature work` | ✅ Yes (Player-Coach) | DeepAgents CLI mirrors `/feature-build` |
| `gka task work` | ❓ TBD | May retrofit after proving `/feature-build` |

### Trade-offs

**Benefits of `/task-work` without adversarial cooperation:**
- Simpler flow with fewer agent invocations
- Potentially faster execution (no Coach turn overhead)
- Lower token cost per task
- Existing quality gates (test loops, plan audit) still apply

**Disadvantages:**
- No independent validation of requirements compliance
- Agent self-report of success (the weakness Ralph loops share)
- Quality of output may be lower for complex tasks
- More likely to "go down rabbit holes" without `/task-refine`

### Evolution Path

```
Phase 1: Prove adversarial pattern in /feature-build
    │
    ├── Validate: Does Player-Coach improve completion rates?
    ├── Measure: Token cost vs quality improvement
    └── Learn: Which task types benefit most?
    │
    ▼
Phase 2: Evaluate retrofit to /task-work
    │
    ├── Option A: Add --adversarial flag to /task-work
    │   └── User chooses when to use Player-Coach
    │
    ├── Option B: Complexity-gated adversarial
    │   └── Complexity ≥ N automatically uses Player-Coach
    │
    └── Option C: Keep separate commands
        └── /task-work = simple, /feature-build = adversarial
```

### Decision Criteria for Retrofit

Retrofit `/task-work` to use adversarial cooperation IF:

1. **Quality improvement is measurable** - `/feature-build` shows demonstrably better completion rates
2. **Cost is acceptable** - Token overhead doesn't negate benefits for simple tasks
3. **User feedback supports it** - Real users report wanting Coach validation on individual tasks
4. **Complexity gating works** - We can reliably determine when adversarial adds value

### Recommendation

**Start with separation** - Keep `/task-work` simple and `/feature-build` adversarial. This provides:

- Clear mental model for users ("tasks are quick, features are thorough")
- Real-world data on when adversarial cooperation helps
- Option to retrofit later based on evidence

The adversarial intensity gradient (complexity-based) applies primarily to `/feature-build` and `gka` commands initially. Retrofitting to `/task-work` is a Phase 2 consideration after proving the pattern.

---

## Summary of Decisions

| Decision | Rationale |
|----------|-----------|
| ✅ Keep current workflow phases | Each prevents a specific failure mode |
| ✅ Add adversarial intensity gradient | Extends adaptive ceremony to Player-Coach loop |
| ✅ Make design patterns MCP conditional | Not always needed, tie to complexity/task type |
| ✅ Keep markdown-based configuration | Allows project-specific tuning |
| ✅ Adversarial for `/feature-build` only (initially) | Prove pattern before retrofitting to `/task-work` |
| ⏸️ Consider "Ralph mode" option | For users who want simple loop for mechanical work |
| ⏸️ Retrofit `/task-work` to adversarial | Evaluate after proving `/feature-build` works |

---

## Related Documents

- [Adversarial_Cooperation_Research.md](./Adversarial_Cooperation_Research.md) - Block AI research analysis
- [FEATURE-005-adversarial-orchestrator.md](./FEATURE-005-adversarial-orchestrator.md) - Orchestrator implementation
- [GuardKit_Agent_Product_Specification.md](./GuardKit_Agent_Product_Specification.md) - Full product spec
- [feature-build/README.md](../../tasks/backlog/feature-build/README.md) - Current implementation status

## External References

- Chris Parsons: "Your Agent Orchestrator Is Too Clever" - https://www.chrismdp.com/your-agent-orchestrator-is-too-clever/
- Geoffrey Huntley: Ralph Wiggum technique - https://ghuntley.com/ralph/
- Block AI Research: "Adversarial Cooperation in Code Synthesis"
- g3 implementation - https://github.com/dhanji/g3

---

## Document History

| Date | Author | Changes |
|------|--------|---------|
| 2026-01-10 | Research session | Initial creation from workflow review discussion |
