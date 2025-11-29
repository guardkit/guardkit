---
id: TASK-REV-2367
title: Implement /task-review report generation and decision checkpoint (Phase 3)
status: completed
created: 2025-01-20T15:00:00Z
updated: 2025-01-20T18:30:00Z
completed_at: 2025-01-20T19:00:00Z
priority: high
tags: [task-review, reporting, phase-3, decision-checkpoint]
complexity: 5
estimated_effort: 4-6 hours
actual_effort: 3 hours
related_proposal: docs/proposals/task-review-command-proposal.md
parent_initiative: task-review-command-implementation
phase: 3
dependencies: [TASK-REV-A4AB, TASK-REV-3248]
completion_metrics:
  total_duration: 4 hours
  implementation_time: 2.5 hours
  testing_time: 0.5 hours
  test_iterations: 2
  final_coverage: 100%
  tests_passing: 30/30
  files_created: 7
  lines_of_code: 1690
---

# Task: Implement /task-review Report Generation and Decision Checkpoint (Phase 3)

## Context

This is **Phase 3 of 5** for implementing the `/task-review` command.

**Prerequisites**:
- TASK-REV-A4AB (Phase 1 - Core Command) must be complete
- TASK-REV-3248 (Phase 2 - Review Modes) must be complete

**Goal**: Transform raw review results into human-readable reports and implement the interactive decision checkpoint.

## Description

Implement the report generation system (Phase 4 of the workflow) and the human decision checkpoint (Phase 5 of the workflow). This takes structured review results from Phase 2 and formats them for human consumption, then presents decision options.

### Deliverables

1. **Report Generator** (`review_report_generator.py`)
   - Summary format (1-page executive summary)
   - Detailed format (full analysis report)
   - Presentation format (slide deck style)

2. **Recommendation Synthesizer** (Phase 3 function)
   - Aggregate findings across agents
   - Generate actionable recommendations
   - Calculate confidence levels

3. **Decision Checkpoint** (Phase 5 function)
   - Interactive prompt with 4 options
   - Decision validation and routing
   - Implementation task creation flow

4. **Report Templates**
   - Markdown templates for each review mode
   - Consistent formatting across modes

## Acceptance Criteria

### Report Generator
- [x] `review_report_generator.py` module created
- [x] Three output formats implemented:
  - `--output=summary`: 1-page executive summary
  - `--output=detailed`: Full analysis (3-5 pages)
  - `--output=presentation`: Slide deck format
- [x] Mode-specific report sections (architectural, code-quality, etc.)
- [x] Consistent markdown formatting
- [x] Evidence/file references included
- [x] Reports saved to `docs/state/{task_id}/review-report.md`

### Recommendation Synthesis
- [x] `synthesize_recommendations()` function implemented
- [x] Aggregates findings from multiple agents (if applicable)
- [x] Prioritizes recommendations by impact/effort
- [x] Calculates overall confidence level (Low/Medium/High)
- [x] Handles decision-making tasks (option evaluation)

### Decision Checkpoint
- [x] `present_decision_checkpoint()` function implemented
- [x] Interactive prompt displays:
  - Review summary
  - Key findings
  - Recommendations
  - Decision options: [A]ccept / [R]evise / [I]mplement / [C]ancel
- [x] Decision validation (valid input required)
- [x] State transitions based on decision:
  - Accept → IN_REVIEW
  - Revise → IN_PROGRESS (loop back to Phase 2)
  - Implement → IN_REVIEW + create implementation task
  - Cancel → BACKLOG
- [x] Implementation task creation (if [I]mplement chosen)

### Report Templates
- [x] Template for architectural review reports
- [x] Template for code quality review reports
- [x] Template for decision analysis reports
- [x] Template for technical debt reports
- [x] Template for security audit reports

## Implementation Notes

### File Structure

```
installer/global/commands/lib/
├── review_report_generator.py           # NEW
├── review_templates/                    # NEW
│   ├── architectural_review.md.template
│   ├── code_quality_review.md.template
│   ├── decision_analysis.md.template
│   ├── technical_debt.md.template
│   └── security_audit.md.template
└── task_review_orchestrator.py          # Updated
```

### Report Generator Interface

```python
# installer/global/commands/lib/review_report_generator.py

def generate_review_report(
    review_results: Dict[str, Any],
    recommendations: Dict[str, Any],
    output_format: str
) -> str:
    """
    Generate formatted review report.

    Args:
        review_results: Structured results from Phase 2
        recommendations: Synthesized recommendations from Phase 3
        output_format: Output format (summary, detailed, presentation)

    Returns:
        Formatted markdown report
    """
    mode = review_results["mode"]

    if output_format == "summary":
        return generate_summary_report(review_results, recommendations)
    elif output_format == "presentation":
        return generate_presentation_report(review_results, recommendations)
    else:  # detailed
        return generate_detailed_report(review_results, recommendations, mode)

def generate_detailed_report(results, recommendations, mode):
    """Generate full analysis report with mode-specific template."""
    template = load_template(f"{mode}_review.md.template")

    return template.format(
        task_id=results.get("task_id"),
        review_date=datetime.now().strftime("%Y-%m-%d"),
        mode=mode.replace("-", " ").title(),
        overall_score=results.get("overall_score", "N/A"),
        findings=format_findings(results["findings"]),
        recommendations=format_recommendations(recommendations),
        evidence=format_evidence(results.get("evidence", [])),
        decision_matrix=format_decision_matrix(results) if mode == "decision" else ""
    )
```

### Example: Architectural Review Report Template

```markdown
# Architectural Review Report - {task_id}

**Review Type**: Architectural Review
**Review Date**: {review_date}
**Reviewer**: Claude (architectural-reviewer)
**Overall Score**: {overall_score}/100

## Executive Summary

{executive_summary}

## Architecture Assessment

| Principle | Score | Notes |
|-----------|-------|-------|
| Single Responsibility | {solid_srp}/10 | {solid_srp_notes} |
| Open/Closed | {solid_ocp}/10 | {solid_ocp_notes} |
| Liskov Substitution | {solid_lsp}/10 | {solid_lsp_notes} |
| Interface Segregation | {solid_isp}/10 | {solid_isp_notes} |
| Dependency Inversion | {solid_dip}/10 | {solid_dip_notes} |
| DRY | {dry_score}/10 | {dry_notes} |
| YAGNI | {yagni_score}/10 | {yagni_notes} |

## Findings

{findings}

## Recommendations

{recommendations}

## Evidence

{evidence}
```

### Decision Checkpoint Implementation

```python
def present_decision_checkpoint(report: str, recommendations: Dict) -> str:
    """
    Present review findings and prompt for decision.

    Args:
        report: Formatted review report
        recommendations: Synthesized recommendations

    Returns:
        User decision (accept, revise, implement, cancel)
    """
    # Display report summary
    print("\n" + "="*67)
    print("REVIEW COMPLETE")
    print("="*67 + "\n")

    # Show key findings (first 500 chars of report)
    print(report[:500] + "...\n")

    # Show recommendations
    print("KEY RECOMMENDATIONS:")
    for i, rec in enumerate(recommendations.get("recommendations", []), 1):
        print(f"{i}. {rec}")

    # Decision prompt
    print("\n" + "="*67)
    print("DECISION OPTIONS:")
    print("="*67)
    print("[A]ccept  - Accept findings, move to IN_REVIEW")
    print("[R]evise  - Request deeper analysis, return to IN_PROGRESS")
    print("[I]mplement - Accept and create implementation task")
    print("[C]ancel  - Discard review, return to BACKLOG")
    print()

    # Get user input
    while True:
        choice = input("Your choice [A/R/I/C]: ").strip().lower()
        if choice in ['a', 'r', 'i', 'c']:
            decision_map = {
                'a': 'accept',
                'r': 'revise',
                'i': 'implement',
                'c': 'cancel'
            }
            return decision_map[choice]
        else:
            print("Invalid choice. Please enter A, R, I, or C.")

def handle_review_decision(
    task_id: str,
    decision: str,
    recommendations: Dict
) -> None:
    """
    Handle user decision after review.

    Args:
        task_id: Task ID being reviewed
        decision: User decision (accept, revise, implement, cancel)
        recommendations: Recommendations from review
    """
    if decision == "accept":
        # Move to IN_REVIEW
        move_task_to_state(task_id, "in_review")
        print(f"\n✅ Review accepted. {task_id} moved to IN_REVIEW.")

    elif decision == "revise":
        # Keep in IN_PROGRESS, clear review results
        print(f"\n🔄 Review revision requested. {task_id} remains in IN_PROGRESS.")
        print("Run /task-review again with adjusted parameters.")

    elif decision == "implement":
        # Move to IN_REVIEW + create implementation task
        move_task_to_state(task_id, "in_review")

        # Create implementation task based on recommendation
        impl_task_id = create_implementation_task(task_id, recommendations)
        print(f"\n✅ Review accepted. {task_id} moved to IN_REVIEW.")
        print(f"📝 Created implementation task: {impl_task_id}")
        print(f"\nNext step: /task-work {impl_task_id}")

    elif decision == "cancel":
        # Move to BACKLOG
        move_task_to_state(task_id, "backlog")
        print(f"\n❌ Review cancelled. {task_id} returned to BACKLOG.")
```

## Test Requirements

### Unit Tests

File: `tests/unit/commands/test_review_report_generator.py`

```python
def test_generate_summary_report():
    """Test 1-page executive summary generation."""
    results = {"mode": "architectural", "overall_score": 75, "findings": [...]}
    recommendations = {"recommendations": ["Refactor AuthService"]}

    report = generate_review_report(results, recommendations, "summary")

    assert len(report.split("\n")) <= 50  # 1-page = ~50 lines
    assert "Executive Summary" in report
    assert "75" in report  # overall score

def test_generate_detailed_report():
    """Test full analysis report generation."""
    results = {"mode": "architectural", "overall_score": 75, "findings": [...]}
    recommendations = {"recommendations": ["Refactor AuthService"]}

    report = generate_review_report(results, recommendations, "detailed")

    assert "Architecture Assessment" in report
    assert "Findings" in report
    assert "Recommendations" in report

def test_decision_checkpoint_accept():
    """Test accept decision flow."""
    # Mock user input
    with patch('builtins.input', return_value='a'):
        decision = present_decision_checkpoint("Report...", {})
        assert decision == "accept"
```

## Related Tasks

- **TASK-REV-A4AB**: Core command (prerequisite)
- **TASK-REV-3248**: Review modes (prerequisite)
- **TASK-REV-5DC2**: Integration (Phase 4) - Depends on this task
- **TASK-REV-4DE8**: Testing (Phase 5) - Depends on all phases

## Success Criteria

- [x] All 3 output formats work correctly
- [x] Reports are well-formatted and readable
- [x] Decision checkpoint is interactive
- [x] All 4 decision options handled correctly
- [x] Implementation task creation works
- [x] Reports saved to correct location
- [x] All unit tests pass (30/30 passed)
- [ ] Manual testing with real review task successful (deferred to Phase 4 integration)

---

**Note**: This task completes the review workflow. Phase 4 (Integration) will connect task-review to task-create for seamless usage.
