---
id: TASK-2E9E
title: Review BDD restoration plan and design RequireKit integration
status: review_complete
created: 2025-11-28T11:47:38.869106+00:00
updated: 2025-11-28T12:45:00.000000+00:00
priority: high
tags: [architecture, bdd, integration, requirekit, langgraph, agentic-systems]
complexity: 0
task_type: review
decision_required: true
review_mode: architectural
review_depth: standard
review_results:
  score: 94
  recommendation: approve_full_restoration
  findings_count: 4
  critical_findings: 2
  recommendations_count: 1
  decision: approve_with_implementation
  report_path: .claude/reviews/TASK-2E9E-architectural-review-FINAL.md
  previous_reports:
    - .claude/reviews/TASK-2E9E-architectural-review.md
    - .claude/reviews/TASK-2E9E-architectural-review-REVISED.md
  revision_count: 2
  revision_reason: "Verified --mode=bdd flag was completely removed, requires full restoration"
  use_case: "BDD workflow for formal agentic orchestration systems (LangGraph)"
  implementation_required: true
  estimated_effort_hours: 3-5
  completed_at: 2025-11-28T12:45:00.000000+00:00
  review_duration_hours: 3.0
test_results:
  status: passed
  coverage: null
  last_run: 2025-11-28T12:45:00.000000+00:00
---

# Task: Review BDD restoration plan and design RequireKit integration

## Context

BDD mode was removed from taskwright on November 2, 2025 (commit `08e6f21`) due to:
- Dependency Inversion Principle violation
- 45-70 hours estimated implementation effort
- Low expected standalone usage (<5%)
- Better served by require-kit for full EARS → Gherkin → Implementation workflow

**Now reconsidering**: Reinstating BDD support specifically for taskwright + require-kit integration scenarios.

## Description

This is a **review and planning task** to evaluate whether and how to reinstate BDD mode support in taskwright when used in conjunction with require-kit.

**Key Questions**:
1. Should BDD mode be reinstated at all?
2. If yes, should it ONLY work when require-kit is detected (avoiding DIP violation)?
3. What's the minimal viable restoration approach?
4. How should taskwright and require-kit interact for BDD workflows?
5. What's different now vs when it was removed?

## Documents to Review

### Removal Documentation
1. **Decision Document**: `docs/research/bdd-mode-removal-decision.md`
   - Original rationale for removal
   - Complexity analysis (45-70 hours)
   - Alternatives considered

2. **Removal Task**: `tasks/completed/TASK-037/TASK-037-remove-bdd-mode.md`
   - What was deleted (11 files)
   - What was modified (8 files)
   - Commit: `08e6f21e67983aa731f4ef5dd5415c2bf87587b2`

3. **Restoration Guide**: `docs/research/restoring-bdd-feature.md`
   - Complete 11-phase restoration plan
   - Estimated effort: 2-3 hours
   - Decision checklist

### Files That Were Removed
- `.claude/agents/bdd-generator.md` - Main BDD generation agent
- `installer/global/instructions/core/bdd-gherkin.md` - BDD methodology
- Template-specific BDD agents (MAUI, etc.)

## Analysis Required

### 1. Dependency Inversion Analysis

**Original Problem**: Taskwright depending on require-kit violated DIP
- Taskwright (higher-level) should not depend on require-kit (lower-level)
- BDD functionality scattered across both repositories

**Proposed Solution**: Feature detection pattern
```python
# In taskwright
def supports_bdd() -> bool:
    """Check if BDD available via require-kit."""
    return is_package_installed('require-kit')

# In task-work command
if mode == 'bdd' and not supports_bdd():
    raise Error("BDD mode requires require-kit installation")
```

**Question**: Does feature detection + conditional availability respect DIP?

### 2. Integration Architecture

**Option A: Lightweight Integration** (Recommended for evaluation)
- Taskwright: Minimal BDD mode stub (detects require-kit, delegates to it)
- Require-Kit: Owns all BDD logic (agents, instructions, generation)
- No code duplication, clear ownership

**Option B: Full Restoration** (Original approach)
- Restore all deleted BDD files to taskwright
- Independent BDD support without require-kit
- 45-70 hours implementation (as documented)

**Option C: Hybrid Approach**
- Taskwright: Basic Gherkin generation from task descriptions
- Require-Kit: Enhanced EARS → Gherkin with full traceability
- Some code duplication, but clear differentiation

**Decision Point**: Which option best balances value, effort, and architectural integrity?

### 3. User Experience Design

**When require-kit NOT installed**:
```bash
/task-work TASK-042 --mode=bdd
# Error: BDD mode requires require-kit
# Install: cd require-kit && ./installer/scripts/install.sh
# Alternative: Use --mode=tdd or --mode=standard
```

**When require-kit IS installed**:
```bash
/task-work TASK-042 --mode=bdd
# ✅ BDD MODE: Using require-kit for Gherkin generation
# [delegates to require-kit's bdd-generator agent]
```

**Question**: Is conditional feature availability acceptable UX?

### 4. Scope Definition

**Minimal BDD Support** (1-2 hours):
- Feature detection in task-work
- Error messages with installation guidance
- Documentation updates
- No file restoration, pure delegation

**Standard BDD Support** (5-10 hours):
- Restore bdd-generator agent to require-kit (if not there)
- Feature detection in taskwright
- Integration tests
- Documentation for both repos

**Full BDD Support** (45-70 hours):
- Complete independent implementation
- Not recommended (violates original removal rationale)

**Decision Point**: What's the minimum viable BDD support?

## Acceptance Criteria

### For This Review Task

- [ ] Analyze DIP implications of each integration approach
- [ ] Evaluate user demand evidence (do we have >20% requesting BDD?)
- [ ] Design minimal viable BDD restoration (if proceeding)
- [ ] Define clear ownership boundaries (taskwright vs require-kit)
- [ ] Assess implementation effort for chosen approach
- [ ] Create decision document with recommendation
- [ ] If approved: Create implementation task(s)

### Decision Outputs

**Document to Create**: `docs/research/bdd-restoration-decision-2025.md`

**Must answer**:
1. ✅ or ❌ Reinstate BDD mode?
2. If yes: Which integration option (A/B/C)?
3. If yes: Estimated effort and timeline
4. If yes: DIP compliance strategy
5. If no: Alternative recommendations for users

### Implementation Task (If Approved)

If decision is to proceed, create follow-up task:
- **TASK-BDD-RESTORE**: Implement BDD mode with require-kit integration
- Estimated effort: [TBD based on chosen approach]
- Acceptance criteria: [TBD based on design]

## Key Considerations

### 1. Has Anything Changed Since Removal?

**Then (Nov 2025)**:
- No clear user demand
- Estimated <5% usage
- DIP violation concern
- 45-70 hours effort deterrent

**Now (Nov 2025)**:
- User requesting reinstatement (data point: 1 request)
- Require-kit exists as separate package
- Feature detection pattern available
- Restoration guide already documented

**Question**: Is 1 user request sufficient evidence? Or wait for more demand?

### 2. DIP Compliance Check

**Dependency Inversion Principle**:
> High-level modules should not depend on low-level modules. Both should depend on abstractions.

**Current situation**:
- Taskwright = higher-level (task workflow orchestration)
- Require-kit = lower-level (requirements management)

**Compliant approach**:
```python
# Abstraction (interface)
class BDDGenerator(ABC):
    @abstractmethod
    def generate_scenarios(task) -> List[Scenario]:
        pass

# Require-kit implements abstraction
class RequireKitBDDGenerator(BDDGenerator):
    def generate_scenarios(task):
        # Use EARS → Gherkin logic
        pass

# Taskwright depends on abstraction, not implementation
def task_work_bdd_mode(task):
    generator = discover_bdd_generator()  # Plugin discovery
    scenarios = generator.generate_scenarios(task)
```

**Question**: Do we need full plugin architecture, or is feature detection sufficient?

### 3. Resource Allocation

**Available time**: [TBD]
**Competing priorities**: [TBD]
**User impact**: [TBD based on demand data]

**Effort comparison**:
| Approach | Effort | Value | DIP Compliant? |
|----------|--------|-------|----------------|
| Minimal (delegation) | 1-2h | Low-Medium | Yes |
| Standard (integration) | 5-10h | Medium | Yes (with care) |
| Full (restoration) | 45-70h | High | No |

## Success Metrics

### For Review Task
- Clear architectural decision documented
- DIP compliance evaluated
- Implementation approach defined (if proceeding)
- Effort estimate accurate (±20%)

### For Implementation (If Approved)
- BDD mode available when require-kit installed
- Clear error message when require-kit not installed
- Zero DIP violations
- Documentation complete
- Integration tests passing

## References

### Documentation
- [BDD Mode Removal Decision](../docs/research/bdd-mode-removal-decision.md)
- [TASK-037 Removal](../tasks/completed/TASK-037/TASK-037-remove-bdd-mode.md)
- [Restoration Guide](../docs/research/restoring-bdd-feature.md)
- [Feature Detection](../installer/global/lib/feature_detection.py)

### Commit History
- Removal: `08e6f21e67983aa731f4ef5dd5415c2bf87587b2`
- Files before removal: `08e6f21~1`

## Next Steps

1. **Execute this review task**: `/task-review TASK-2E9E --mode=architectural`
2. **Review findings**: Evaluate recommendation
3. **Make decision**: Approve/Reject/Modify restoration plan
4. **If approved**: Create implementation task
5. **If rejected**: Document reasons and alternatives

## Notes

- This is a **review task**, not an implementation task
- Use `/task-review` not `/task-work`
- Decision should be data-driven (user demand, effort, value)
- DIP compliance is non-negotiable
- Consider waiting for more user requests before committing resources
