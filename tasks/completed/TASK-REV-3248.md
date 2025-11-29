---
id: TASK-REV-3248
title: Implement /task-review modes with specialized agents (Phase 2)
status: completed
created: 2025-01-20T15:00:00Z
updated: 2025-11-20T13:15:00Z
completed: 2025-11-20T13:15:00Z
priority: high
tags: [task-review, agents, phase-2, review-modes]
complexity: 7
estimated_effort: 8-12 hours
actual_effort: 2 hours
related_proposal: docs/proposals/task-review-command-proposal.md
parent_initiative: task-review-command-implementation
phase: 2
dependencies: [TASK-REV-A4AB]
test_results:
  total_tests: 50
  passed: 50
  failed: 0
  coverage: 100%
  duration: 1.24s
---

# Task: Implement /task-review Modes with Specialized Agents (Phase 2)

## Context

This is **Phase 2 of 5** for implementing the `/task-review` command.

**Prerequisites**: TASK-REV-A4AB (Phase 1 - Core Command) must be complete.

**Goal**: Implement the 5 review modes with specialized agent configurations and analysis logic.

## Description

Enhance the skeleton `execute_review_analysis()` function to support 5 distinct review modes, each with specialized prompts and agent configurations.

### Review Modes to Implement

1. **Architectural Review** (--mode=architectural)
   - Agent: `architectural-reviewer`
   - Evaluates: SOLID, DRY, YAGNI principles
   - Output: Architecture score (0-100), principle scores, recommendations

2. **Code Quality Review** (--mode=code-quality)
   - Agent: `code-reviewer`
   - Evaluates: Complexity, coverage, code smells, style
   - Output: Quality score (0-10), metrics, issue list

3. **Decision Analysis** (--mode=decision)
   - Agent: `software-architect`
   - Evaluates: Multiple options against criteria
   - Output: Option matrix, recommendation, confidence level

4. **Technical Debt Assessment** (--mode=technical-debt)
   - Agents: `code-reviewer`, `architectural-reviewer`
   - Evaluates: Debt inventory, prioritization
   - Output: Debt list with impact/effort/risk scores

5. **Security Audit** (--mode=security)
   - Agent: `security-specialist`
   - Evaluates: OWASP Top 10, dependencies, auth/authz
   - Output: Vulnerability list, risk scores, remediation plan

## Acceptance Criteria

### Mode Infrastructure
- [ ] `execute_review_analysis()` function enhanced (no longer skeleton)
- [ ] Mode-specific agent selection logic implemented
- [ ] Mode-specific prompt builders created
- [ ] Depth parameter affects analysis thoroughness (quick/standard/comprehensive)

### Mode 1: Architectural Review
- [ ] Invokes `architectural-reviewer` agent
- [ ] Analyzes code against SOLID/DRY/YAGNI
- [ ] Returns structured results with scores (0-100)
- [ ] Identifies critical architectural issues
- [ ] Provides refactoring recommendations

### Mode 2: Code Quality Review
- [ ] Invokes `code-reviewer` agent
- [ ] Calculates complexity metrics (cyclomatic, nesting)
- [ ] Analyzes test coverage if available
- [ ] Identifies code smells and anti-patterns
- [ ] Returns quality score (0-10) with justification

### Mode 3: Decision Analysis
- [ ] Invokes `software-architect` agent
- [ ] Evaluates multiple options (A, B, C, D)
- [ ] Scores each option on 4 criteria (0-10 each)
- [ ] Calculates total scores and recommends highest
- [ ] Provides confidence level (Low/Medium/High)

### Mode 4: Technical Debt Assessment
- [ ] Invokes both `code-reviewer` and `architectural-reviewer`
- [ ] Inventories code debt, design debt, test debt
- [ ] Prioritizes using impact/effort/risk matrix
- [ ] Suggests quick wins (low effort, high impact)
- [ ] Estimates paydown effort

### Mode 5: Security Audit
- [ ] Invokes `security-specialist` agent
- [ ] Checks OWASP Top 10 vulnerabilities
- [ ] Analyzes dependencies for known CVEs
- [ ] Reviews authentication/authorization patterns
- [ ] Returns risk-scored vulnerability list

### Cross-Mode Features
- [ ] All modes respect `--depth` parameter:
  - quick: 15-30 min analysis (surface-level)
  - standard: 1-2 hour analysis (thorough)
  - comprehensive: 4-6 hour analysis (exhaustive)
- [ ] All modes return structured data (not just text)
- [ ] All modes include evidence/file references
- [ ] All modes handle missing files gracefully

## Implementation Notes

### File Structure

```
installer/global/commands/lib/
├── review_modes/
│   ├── __init__.py
│   ├── architectural_review.py          # Mode 1
│   ├── code_quality_review.py           # Mode 2
│   ├── decision_analysis.py             # Mode 3
│   ├── technical_debt_assessment.py     # Mode 4
│   └── security_audit.py                # Mode 5
└── task_review_orchestrator.py          # Updated from Phase 1
```

### Mode Interface (Protocol)

```python
from typing import Protocol, Dict, Any

class ReviewMode(Protocol):
    """Interface for review modes."""

    def execute(
        self,
        task_context: Dict[str, Any],
        depth: str
    ) -> Dict[str, Any]:
        """
        Execute review analysis.

        Args:
            task_context: Task metadata and review scope
            depth: Analysis depth (quick, standard, comprehensive)

        Returns:
            Structured review results
        """
        ...
```

### Updated Orchestrator Function

```python
# installer/global/commands/lib/task_review_orchestrator.py

def execute_review_analysis(
    task_context: Dict[str, Any],
    mode: str,
    depth: str
) -> Dict[str, Any]:
    """
    Execute review analysis based on mode and depth.

    Args:
        task_context: Task metadata including review_scope
        mode: Review mode (architectural, code-quality, etc.)
        depth: Analysis depth (quick, standard, comprehensive)

    Returns:
        Structured review results with findings
    """
    # Import mode-specific modules
    from installer.global.commands.lib.review_modes import (
        architectural_review,
        code_quality_review,
        decision_analysis,
        technical_debt_assessment,
        security_audit
    )

    # Map mode to module
    mode_map = {
        "architectural": architectural_review,
        "code-quality": code_quality_review,
        "decision": decision_analysis,
        "technical-debt": technical_debt_assessment,
        "security": security_audit
    }

    # Execute mode
    review_module = mode_map[mode]
    results = review_module.execute(task_context, depth)

    return results
```

### Example: Architectural Review Implementation

```python
# installer/global/commands/lib/review_modes/architectural_review.py

from installer.global.lib.agent_bridge.invoker import AgentInvoker

def execute(task_context: Dict[str, Any], depth: str) -> Dict[str, Any]:
    """Execute architectural review."""

    # Build prompt based on depth
    prompt = build_architectural_prompt(task_context, depth)

    # Invoke architectural-reviewer agent
    bridge = AgentInvoker()
    response = bridge.invoke(
        agent_name="architectural-reviewer",
        prompt=prompt,
        timeout_seconds=get_timeout_for_depth(depth),
        context={"mode": "architectural", "depth": depth}
    )

    # Parse response into structured format
    results = parse_architectural_response(response)

    return {
        "mode": "architectural",
        "depth": depth,
        "overall_score": results["overall_score"],  # 0-100
        "principles": {
            "solid": results["solid_score"],  # 0-100
            "dry": results["dry_score"],      # 0-100
            "yagni": results["yagni_score"]   # 0-100
        },
        "findings": results["findings"],
        "recommendations": results["recommendations"]
    }

def build_architectural_prompt(task_context, depth):
    """Build prompt for architectural review based on depth."""
    scope = task_context.get("review_scope", [])

    if depth == "quick":
        # Surface-level analysis (15-30 min)
        return f"""Quick architectural review of {', '.join(scope)}.

Focus on high-level architecture only:
- Identify major SOLID violations
- Check for obvious DRY issues
- Flag over-engineering (YAGNI)

Time budget: 20 minutes
"""
    elif depth == "comprehensive":
        # Exhaustive analysis (4-6 hours)
        return f"""Comprehensive architectural review of {', '.join(scope)}.

Thorough analysis required:
- Detailed SOLID evaluation (with examples)
- DRY analysis (identify all duplication)
- YAGNI assessment (find unnecessary abstractions)
- Design pattern analysis
- Scalability concerns
- Maintainability assessment

Time budget: 5 hours
"""
    else:  # standard
        # Thorough analysis (1-2 hours)
        return f"""Architectural review of {', '.join(scope)}.

Standard depth analysis:
- SOLID principle evaluation
- DRY principle check
- YAGNI assessment
- Key recommendations

Time budget: 90 minutes
"""
```

## Test Requirements

### Unit Tests

File: `tests/unit/commands/review_modes/test_architectural_review.py`

```python
def test_architectural_review_quick():
    """Test quick architectural review (15-30 min)."""
    task_context = {"review_scope": ["src/auth/"]}
    results = architectural_review.execute(task_context, "quick")

    assert results["mode"] == "architectural"
    assert results["depth"] == "quick"
    assert 0 <= results["overall_score"] <= 100
    assert "solid" in results["principles"]

def test_architectural_review_comprehensive():
    """Test comprehensive architectural review (4-6 hours)."""
    task_context = {"review_scope": ["src/"]}
    results = architectural_review.execute(task_context, "comprehensive")

    assert results["depth"] == "comprehensive"
    assert len(results["findings"]) > 0
    assert len(results["recommendations"]) > 0
```

### Integration Tests

File: `tests/integration/test_review_modes.py`

```python
def test_all_review_modes():
    """Test that all 5 review modes execute successfully."""
    modes = ["architectural", "code-quality", "decision", "technical-debt", "security"]
    task_context = {"review_scope": ["src/auth/"]}

    for mode in modes:
        results = execute_review_analysis(task_context, mode, "standard")
        assert results["mode"] == mode
        assert "findings" in results or "recommendations" in results
```

## Related Tasks

- **TASK-REV-A4AB**: Core command (prerequisite)
- **TASK-REV-2367**: Report generation (Phase 3) - Depends on this task
- **TASK-REV-5DC2**: Integration (Phase 4) - Depends on Phase 3
- **TASK-REV-4DE8**: Testing (Phase 5) - Depends on all phases

## Success Criteria

- [ ] All 5 review modes implemented and working
- [ ] Depth parameter affects analysis thoroughness
- [ ] All modes return structured data
- [ ] All modes invoke correct agents
- [ ] Mode-specific prompts are comprehensive
- [ ] All unit tests pass (5+ tests per mode)
- [ ] Integration test passes for all modes
- [ ] Documentation updated with mode details

---

**Note**: This task implements the core analysis logic. Report generation (formatting the results) is handled in Phase 3.
