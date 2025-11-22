"""
Review Report Generator for /task-review command.

This module transforms structured review results into human-readable reports
in multiple formats (summary, detailed, presentation) and implements the
interactive decision checkpoint.

Architecture:
    - generate_review_report(): Main entry point for report generation
    - generate_summary_report(): 1-page executive summary
    - generate_detailed_report(): Full analysis (3-5 pages)
    - generate_presentation_report(): Slide deck format
    - synthesize_recommendations(): Aggregate findings from agents
    - present_decision_checkpoint(): Interactive user decision prompt
    - handle_review_decision(): Process user decision and update task state

Example:
    >>> from review_report_generator import generate_review_report
    >>>
    >>> report = generate_review_report(
    ...     review_results={"mode": "architectural", "overall_score": 75},
    ...     recommendations={"recommendations": ["Refactor AuthService"]},
    ...     output_format="summary"
    ... )
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# Report Generation
# ============================================================================

def generate_review_report(
    review_results: Dict[str, Any],
    recommendations: Dict[str, Any],
    output_format: str = "detailed"
) -> str:
    """
    Generate formatted review report.

    Args:
        review_results: Structured results from Phase 2 review
        recommendations: Synthesized recommendations from Phase 3
        output_format: Output format (summary, detailed, presentation)

    Returns:
        Formatted markdown report
    """
    mode = review_results.get("mode", "unknown")

    try:
        if output_format == "summary":
            return generate_summary_report(review_results, recommendations)
        elif output_format == "presentation":
            return generate_presentation_report(review_results, recommendations)
        else:  # detailed (default)
            return generate_detailed_report(review_results, recommendations, mode)
    except Exception as e:
        logger.error(f"Error generating {output_format} report: {e}", exc_info=True)
        return f"# Report Generation Error\n\nFailed to generate {output_format} report: {str(e)}"


def generate_summary_report(
    review_results: Dict[str, Any],
    recommendations: Dict[str, Any]
) -> str:
    """
    Generate 1-page executive summary.

    Args:
        review_results: Review results from Phase 2
        recommendations: Recommendations from Phase 3

    Returns:
        Compact summary report (~50 lines)
    """
    task_id = review_results.get("task_id", "UNKNOWN")
    mode = review_results.get("mode", "unknown").replace("-", " ").title()
    overall_score = review_results.get("overall_score", "N/A")
    review_date = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"# Review Summary - {task_id}",
        "",
        f"**Review Type**: {mode}",
        f"**Review Date**: {review_date}",
        f"**Overall Score**: {overall_score}",
        "",
        "## Executive Summary",
        "",
        _format_executive_summary(review_results, recommendations),
        "",
        "## Key Findings",
        "",
    ]

    # Top 3 findings only
    findings = review_results.get("findings", [])
    for i, finding in enumerate(findings[:3], 1):
        severity = finding.get("severity", "info").upper()
        title = finding.get("title", "Finding")
        lines.append(f"{i}. **[{severity}]** {title}")

    if len(findings) > 3:
        lines.append(f"   _(+{len(findings) - 3} more findings in detailed report)_")

    lines.extend([
        "",
        "## Top Recommendations",
        "",
    ])

    # Top 3 recommendations
    recs = recommendations.get("recommendations", [])
    for i, rec in enumerate(recs[:3], 1):
        lines.append(f"{i}. {rec}")

    if len(recs) > 3:
        lines.append(f"   _(+{len(recs) - 3} more recommendations in detailed report)_")

    lines.extend([
        "",
        "## Confidence Level",
        "",
        f"**{recommendations.get('confidence', 'Medium')}** - {_get_confidence_explanation(recommendations)}",
        "",
        "---",
        "",
        f"_For complete analysis, generate detailed report with `--output=detailed`_"
    ])

    return "\n".join(lines)


def generate_detailed_report(
    review_results: Dict[str, Any],
    recommendations: Dict[str, Any],
    mode: str
) -> str:
    """
    Generate full analysis report with mode-specific template.

    Args:
        review_results: Review results from Phase 2
        recommendations: Recommendations from Phase 3
        mode: Review mode (architectural, code-quality, etc.)

    Returns:
        Complete detailed report (3-5 pages)
    """
    task_id = review_results.get("task_id", "UNKNOWN")
    mode_title = mode.replace("-", " ").title()
    overall_score = review_results.get("overall_score", "N/A")
    review_date = datetime.now().strftime("%Y-%m-%d")

    # Load mode-specific template
    template_content = _load_template(f"{mode}_review.md.template")

    if template_content:
        # Use template if available
        return template_content.format(
            task_id=task_id,
            review_date=review_date,
            mode=mode_title,
            overall_score=overall_score,
            executive_summary=_format_executive_summary(review_results, recommendations),
            findings=_format_findings(review_results.get("findings", [])),
            recommendations=_format_recommendations(recommendations),
            evidence=_format_evidence(review_results.get("evidence", [])),
            decision_matrix=_format_decision_matrix(review_results) if mode == "decision" else "",
            architecture_assessment=_format_architecture_assessment(review_results) if mode == "architectural" else "",
            code_quality_metrics=_format_code_quality_metrics(review_results) if mode == "code-quality" else ""
        )
    else:
        # Fallback to generic template
        return _generate_generic_detailed_report(review_results, recommendations)


def generate_presentation_report(
    review_results: Dict[str, Any],
    recommendations: Dict[str, Any]
) -> str:
    """
    Generate slide deck style report.

    Args:
        review_results: Review results from Phase 2
        recommendations: Recommendations from Phase 3

    Returns:
        Presentation-style report with slides
    """
    task_id = review_results.get("task_id", "UNKNOWN")
    mode = review_results.get("mode", "unknown").replace("-", " ").title()
    overall_score = review_results.get("overall_score", "N/A")

    slides = []

    # Slide 1: Title
    slides.append(_format_slide(
        "Review Report",
        [
            f"**Task**: {task_id}",
            f"**Type**: {mode}",
            f"**Score**: {overall_score}",
            f"**Date**: {datetime.now().strftime('%Y-%m-%d')}"
        ]
    ))

    # Slide 2: Executive Summary
    slides.append(_format_slide(
        "Executive Summary",
        [_format_executive_summary(review_results, recommendations)]
    ))

    # Slide 3: Key Findings
    findings = review_results.get("findings", [])
    finding_lines = []
    for i, finding in enumerate(findings[:5], 1):
        severity = finding.get("severity", "info").upper()
        title = finding.get("title", "Finding")
        finding_lines.append(f"{i}. **[{severity}]** {title}")

    slides.append(_format_slide("Key Findings", finding_lines))

    # Slide 4: Recommendations
    recs = recommendations.get("recommendations", [])
    rec_lines = [f"{i}. {rec}" for i, rec in enumerate(recs[:5], 1)]

    slides.append(_format_slide("Recommendations", rec_lines))

    # Slide 5: Next Steps
    next_steps = _get_next_steps(review_results, recommendations)
    slides.append(_format_slide("Next Steps", next_steps))

    return "\n\n".join(slides)


# ============================================================================
# Recommendation Synthesis
# ============================================================================

def synthesize_recommendations(
    review_results: Dict[str, Any],
    agent_findings: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Synthesize recommendations from review findings.

    Aggregates findings from multiple agents (if applicable), prioritizes
    by impact/effort, and calculates overall confidence level.

    Args:
        review_results: Review results from Phase 2
        agent_findings: Optional list of findings from multiple agents

    Returns:
        Dictionary with:
            - recommendations: List of actionable recommendations
            - confidence: Overall confidence level (Low/Medium/High)
            - priority_order: Recommendations ordered by impact/effort
    """
    findings = review_results.get("findings", [])
    mode = review_results.get("mode", "unknown")

    # Extract recommendations from findings
    recommendations = []

    for finding in findings:
        if "recommendation" in finding:
            recommendations.append(finding["recommendation"])
        elif "suggested_action" in finding:
            recommendations.append(finding["suggested_action"])

    # If agent_findings provided, merge them
    if agent_findings:
        for agent_finding in agent_findings:
            if "recommendations" in agent_finding:
                recommendations.extend(agent_finding["recommendations"])

    # Remove duplicates while preserving order
    seen = set()
    unique_recommendations = []
    for rec in recommendations:
        if rec not in seen:
            seen.add(rec)
            unique_recommendations.append(rec)

    # Prioritize by severity/impact
    prioritized = _prioritize_recommendations(unique_recommendations, findings)

    # Calculate confidence level
    confidence = _calculate_confidence_level(review_results, findings)

    return {
        "recommendations": prioritized,
        "confidence": confidence,
        "priority_order": prioritized,
        "total_findings": len(findings),
        "critical_findings": len([f for f in findings if f.get("severity") == "critical"]),
        "mode": mode
    }


def _prioritize_recommendations(
    recommendations: List[str],
    findings: List[Dict[str, Any]]
) -> List[str]:
    """
    Prioritize recommendations by impact and effort.

    Args:
        recommendations: List of recommendations
        findings: List of findings with severity

    Returns:
        Prioritized list of recommendations
    """
    # Map recommendations to their severity from findings
    rec_priority = {}

    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

    for i, rec in enumerate(recommendations):
        # Find matching finding
        matching_severity = "medium"  # default
        for finding in findings:
            if finding.get("recommendation") == rec or finding.get("suggested_action") == rec:
                matching_severity = finding.get("severity", "medium")
                break

        priority_score = severity_order.get(matching_severity, 2)
        rec_priority[rec] = (priority_score, i)  # (priority, original_order)

    # Sort by priority, then by original order
    sorted_recs = sorted(recommendations, key=lambda r: rec_priority.get(r, (2, 999)))

    return sorted_recs


def _calculate_confidence_level(
    review_results: Dict[str, Any],
    findings: List[Dict[str, Any]]
) -> str:
    """
    Calculate overall confidence level based on review completeness.

    Args:
        review_results: Review results
        findings: List of findings

    Returns:
        Confidence level: "High", "Medium", or "Low"
    """
    overall_score = review_results.get("overall_score", 50)
    critical_count = len([f for f in findings if f.get("severity") == "critical"])
    total_findings = len(findings)

    # High confidence: Clear score, few critical issues
    if overall_score in [0, 100] or (overall_score >= 80 and critical_count == 0):
        return "High"

    # Low confidence: Many critical issues or unclear score
    if critical_count >= 3 or (overall_score < 40 and total_findings > 5):
        return "Low"

    # Medium confidence: Everything else
    return "Medium"


# ============================================================================
# Decision Checkpoint
# ============================================================================

def present_decision_checkpoint(
    report: str,
    recommendations: Dict[str, Any],
    task_id: str
) -> str:
    """
    Present review findings and prompt for decision.

    Interactive checkpoint with 4 options:
    - [A]ccept: Accept findings, move to IN_REVIEW
    - [R]evise: Request deeper analysis, return to IN_PROGRESS
    - [I]mplement: Accept and create implementation task
    - [C]ancel: Discard review, return to BACKLOG

    Args:
        report: Formatted review report
        recommendations: Synthesized recommendations
        task_id: Task ID being reviewed

    Returns:
        User decision (accept, revise, implement, cancel)
    """
    # Display report summary
    print("\n" + "=" * 67)
    print(f"REVIEW COMPLETE - {task_id}")
    print("=" * 67 + "\n")

    # Show key findings (first 500 chars of report)
    print("REVIEW SUMMARY:")
    print("-" * 67)
    summary_lines = report.split("\n")
    char_count = 0
    for line in summary_lines:
        if char_count + len(line) > 500:
            print("...")
            break
        print(line)
        char_count += len(line)

    print()

    # Show recommendations
    print("KEY RECOMMENDATIONS:")
    print("-" * 67)
    recs = recommendations.get("recommendations", [])
    for i, rec in enumerate(recs[:5], 1):
        print(f"{i}. {rec}")

    if len(recs) > 5:
        print(f"   (+{len(recs) - 5} more in full report)")

    print()

    # Confidence level
    confidence = recommendations.get("confidence", "Medium")
    print(f"Confidence Level: {confidence}")
    print()

    # Decision prompt
    print("=" * 67)
    print("DECISION OPTIONS:")
    print("=" * 67)
    print("[A]ccept     - Accept findings, move to IN_REVIEW")
    print("[R]evise     - Request deeper analysis, return to IN_PROGRESS")
    print("[I]mplement  - Accept and create implementation task")
    print("[C]ancel     - Discard review, return to BACKLOG")
    print()

    # Get user input
    while True:
        try:
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
        except (KeyboardInterrupt, EOFError):
            print("\n\nOperation cancelled.")
            return "cancel"


def handle_review_decision(
    task_id: str,
    decision: str,
    recommendations: Dict[str, Any],
    workspace_root: Optional[Path] = None
) -> Tuple[str, Optional[str]]:
    """
    Handle user decision after review.

    Updates task state based on decision and optionally creates
    implementation task.

    Args:
        task_id: Task ID being reviewed
        decision: User decision (accept, revise, implement, cancel)
        recommendations: Recommendations from review
        workspace_root: Optional workspace root path

    Returns:
        Tuple of (new_state, optional_implementation_task_id)
    """
    if workspace_root is None:
        workspace_root = Path.cwd()

    if decision == "accept":
        # Move to IN_REVIEW
        new_state = "in_review"
        _move_task_to_state(task_id, new_state, workspace_root)
        print(f"\n✅ Review accepted. {task_id} moved to IN_REVIEW.")
        return (new_state, None)

    elif decision == "revise":
        # Keep in IN_PROGRESS, clear review results
        print(f"\n🔄 Review revision requested. {task_id} remains in IN_PROGRESS.")
        print("Run /task-review again with adjusted parameters or different mode.")
        return ("in_progress", None)

    elif decision == "implement":
        # Move to IN_REVIEW + create implementation task
        new_state = "in_review"
        _move_task_to_state(task_id, new_state, workspace_root)

        # Create implementation task based on recommendations
        impl_task_id = _create_implementation_task(task_id, recommendations, workspace_root)

        print(f"\n✅ Review accepted. {task_id} moved to IN_REVIEW.")
        print(f"📝 Created implementation task: {impl_task_id}")
        print(f"\nNext step: /task-work {impl_task_id}")
        return (new_state, impl_task_id)

    elif decision == "cancel":
        # Move to BACKLOG
        new_state = "backlog"
        _move_task_to_state(task_id, new_state, workspace_root)
        print(f"\n❌ Review cancelled. {task_id} returned to BACKLOG.")
        return (new_state, None)

    else:
        logger.warning(f"Unknown decision: {decision}")
        return ("in_progress", None)


# ============================================================================
# Helper Functions - Formatting
# ============================================================================

def _format_executive_summary(
    review_results: Dict[str, Any],
    recommendations: Dict[str, Any]
) -> str:
    """Format executive summary section."""
    mode = review_results.get("mode", "unknown")
    overall_score = review_results.get("overall_score", "N/A")
    total_findings = recommendations.get("total_findings", 0)
    critical_findings = recommendations.get("critical_findings", 0)

    summary = f"This {mode.replace('-', ' ')} review identified {total_findings} finding(s)"

    if critical_findings > 0:
        summary += f", including {critical_findings} critical issue(s)"

    summary += f". Overall score: {overall_score}."

    if critical_findings == 0 and overall_score != "N/A" and int(overall_score) >= 80:
        summary += " The implementation shows strong adherence to best practices."
    elif critical_findings > 0:
        summary += " Immediate attention required for critical findings."

    return summary


def _format_findings(findings: List[Dict[str, Any]]) -> str:
    """Format findings section."""
    if not findings:
        return "_No findings to report._"

    lines = []
    for i, finding in enumerate(findings, 1):
        severity = finding.get("severity", "info").upper()
        title = finding.get("title", "Finding")
        description = finding.get("description", "No description provided.")
        location = finding.get("location", "")

        lines.append(f"### {i}. [{severity}] {title}")
        lines.append("")
        lines.append(description)

        if location:
            lines.append("")
            lines.append(f"**Location**: `{location}`")

        if "recommendation" in finding:
            lines.append("")
            lines.append(f"**Recommendation**: {finding['recommendation']}")

        lines.append("")

    return "\n".join(lines)


def _format_recommendations(recommendations: Dict[str, Any]) -> str:
    """Format recommendations section."""
    recs = recommendations.get("recommendations", [])

    if not recs:
        return "_No specific recommendations._"

    lines = []
    for i, rec in enumerate(recs, 1):
        lines.append(f"{i}. {rec}")

    return "\n".join(lines)


def _format_evidence(evidence: List[Dict[str, Any]]) -> str:
    """Format evidence/references section."""
    if not evidence:
        return "_No evidence references._"

    lines = []
    for item in evidence:
        file_path = item.get("file", "")
        line_num = item.get("line", "")
        description = item.get("description", "")

        if file_path:
            ref = f"`{file_path}"
            if line_num:
                ref += f":{line_num}"
            ref += "`"

            if description:
                ref += f" - {description}"

            lines.append(f"- {ref}")

    return "\n".join(lines)


def _format_decision_matrix(review_results: Dict[str, Any]) -> str:
    """Format decision matrix for decision analysis mode."""
    options = review_results.get("options", [])

    if not options:
        return ""

    lines = [
        "## Decision Matrix",
        "",
        "| Option | Pros | Cons | Risk | Score |",
        "|--------|------|------|------|-------|"
    ]

    for option in options:
        name = option.get("name", "Unknown")
        pros = ", ".join(option.get("pros", []))[:30]
        cons = ", ".join(option.get("cons", []))[:30]
        risk = option.get("risk", "Medium")
        score = option.get("score", "N/A")

        lines.append(f"| {name} | {pros} | {cons} | {risk} | {score} |")

    return "\n".join(lines)


def _format_architecture_assessment(review_results: Dict[str, Any]) -> str:
    """Format architecture assessment table for architectural reviews."""
    assessment = review_results.get("architecture_assessment", {})

    if not assessment:
        return ""

    lines = [
        "## Architecture Assessment",
        "",
        "| Principle | Score | Notes |",
        "|-----------|-------|-------|"
    ]

    principles = [
        ("Single Responsibility", "solid_srp"),
        ("Open/Closed", "solid_ocp"),
        ("Liskov Substitution", "solid_lsp"),
        ("Interface Segregation", "solid_isp"),
        ("Dependency Inversion", "solid_dip"),
        ("DRY", "dry_score"),
        ("YAGNI", "yagni_score")
    ]

    for name, key in principles:
        score = assessment.get(key, "N/A")
        notes = assessment.get(f"{key}_notes", "")
        lines.append(f"| {name} | {score}/10 | {notes} |")

    return "\n".join(lines)


def _format_code_quality_metrics(review_results: Dict[str, Any]) -> str:
    """Format code quality metrics for code quality reviews."""
    metrics = review_results.get("code_quality_metrics", {})

    if not metrics:
        return ""

    lines = [
        "## Code Quality Metrics",
        "",
        "| Metric | Value | Status |",
        "|--------|-------|--------|"
    ]

    for metric_name, metric_value in metrics.items():
        status = "✅" if isinstance(metric_value, (int, float)) and metric_value >= 80 else "⚠️"
        lines.append(f"| {metric_name} | {metric_value} | {status} |")

    return "\n".join(lines)


def _format_slide(title: str, content_lines: List[str]) -> str:
    """Format a presentation slide."""
    lines = [
        "---",
        "",
        f"# {title}",
        ""
    ]

    lines.extend(content_lines)

    lines.append("")

    return "\n".join(lines)


def _get_confidence_explanation(recommendations: Dict[str, Any]) -> str:
    """Get explanation for confidence level."""
    confidence = recommendations.get("confidence", "Medium")

    explanations = {
        "High": "Review findings are clear and actionable with minimal ambiguity.",
        "Medium": "Review findings provide good guidance but may require validation.",
        "Low": "Review findings indicate complexity or uncertainty requiring careful consideration."
    }

    return explanations.get(confidence, "Confidence level not specified.")


def _get_next_steps(
    review_results: Dict[str, Any],
    recommendations: Dict[str, Any]
) -> List[str]:
    """Generate next steps based on review results."""
    critical_count = recommendations.get("critical_findings", 0)

    if critical_count > 0:
        return [
            "1. Address critical findings immediately",
            "2. Re-review after fixes",
            "3. Proceed to implementation"
        ]
    else:
        return [
            "1. Review recommendations",
            "2. Decide on implementation approach",
            "3. Proceed with /task-work"
        ]


def _generate_generic_detailed_report(
    review_results: Dict[str, Any],
    recommendations: Dict[str, Any]
) -> str:
    """Generate generic detailed report when template not found."""
    task_id = review_results.get("task_id", "UNKNOWN")
    mode = review_results.get("mode", "unknown").replace("-", " ").title()
    overall_score = review_results.get("overall_score", "N/A")
    review_date = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"# {mode} Review Report - {task_id}",
        "",
        f"**Review Type**: {mode}",
        f"**Review Date**: {review_date}",
        f"**Overall Score**: {overall_score}",
        "",
        "## Executive Summary",
        "",
        _format_executive_summary(review_results, recommendations),
        "",
        "## Findings",
        "",
        _format_findings(review_results.get("findings", [])),
        "",
        "## Recommendations",
        "",
        _format_recommendations(recommendations),
        "",
        "## Evidence",
        "",
        _format_evidence(review_results.get("evidence", [])),
    ]

    return "\n".join(lines)


# ============================================================================
# Helper Functions - File Operations
# ============================================================================

def _load_template(template_name: str) -> Optional[str]:
    """
    Load report template from review_templates directory.

    Args:
        template_name: Name of template file (e.g., "architectural_review.md.template")

    Returns:
        Template content or None if not found
    """
    try:
        # Get templates directory
        current_dir = Path(__file__).parent
        templates_dir = current_dir / "review_templates"
        template_path = templates_dir / template_name

        if template_path.exists():
            return template_path.read_text()
        else:
            logger.warning(f"Template not found: {template_path}")
            return None
    except Exception as e:
        logger.error(f"Error loading template {template_name}: {e}", exc_info=True)
        return None


def _move_task_to_state(task_id: str, new_state: str, workspace_root: Path) -> None:
    """
    Move task file to new state directory.

    Args:
        task_id: Task ID
        new_state: New state (in_review, backlog, etc.)
        workspace_root: Workspace root path
    """
    tasks_dir = workspace_root / "tasks"

    # Find current task file
    current_file = None
    for state_dir in ["in_progress", "backlog", "in_review", "blocked"]:
        state_path = tasks_dir / state_dir
        if state_path.exists():
            for task_file in state_path.glob(f"{task_id}*.md"):
                current_file = task_file
                break
        if current_file:
            break

    if not current_file:
        logger.warning(f"Task file not found for {task_id}")
        return

    # Move to new state
    new_dir = tasks_dir / new_state
    new_dir.mkdir(parents=True, exist_ok=True)

    new_file = new_dir / current_file.name
    current_file.rename(new_file)

    logger.info(f"Moved {task_id} from {current_file.parent.name} to {new_state}")


def _create_implementation_task(
    parent_task_id: str,
    recommendations: Dict[str, Any],
    workspace_root: Path
) -> str:
    """
    Create implementation task based on review recommendations.

    Args:
        parent_task_id: Parent task ID
        recommendations: Review recommendations
        workspace_root: Workspace root path

    Returns:
        New implementation task ID
    """
    # Generate new task ID
    import random
    impl_task_id = f"TASK-IMPL-{random.randint(1000, 9999)}"

    # Create task file
    tasks_dir = workspace_root / "tasks" / "backlog"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    task_file = tasks_dir / f"{impl_task_id}-implement-recommendations.md"

    # Format recommendations as acceptance criteria
    recs = recommendations.get("recommendations", [])
    criteria = "\n".join([f"- [ ] {rec}" for rec in recs])

    content = f"""---
id: {impl_task_id}
title: Implement recommendations from {parent_task_id}
status: backlog
created: {datetime.now().isoformat()}
updated: {datetime.now().isoformat()}
priority: high
parent_task: {parent_task_id}
---

# Task: Implement Recommendations from {parent_task_id}

## Description

Implement the recommendations identified during review of {parent_task_id}.

## Acceptance Criteria

{criteria}

## Related Tasks

- **{parent_task_id}**: Parent review task
"""

    task_file.write_text(content)
    logger.info(f"Created implementation task: {impl_task_id}")

    return impl_task_id


def save_review_report(
    task_id: str,
    report: str,
    workspace_root: Optional[Path] = None
) -> Path:
    """
    Save review report to docs/state directory.

    Args:
        task_id: Task ID
        report: Formatted report content
        workspace_root: Optional workspace root path

    Returns:
        Path to saved report file
    """
    if workspace_root is None:
        workspace_root = Path.cwd()

    # Create state directory
    state_dir = workspace_root / "docs" / "state" / task_id
    state_dir.mkdir(parents=True, exist_ok=True)

    # Save report
    report_file = state_dir / "review-report.md"
    report_file.write_text(report)

    logger.info(f"Saved review report to {report_file}")

    return report_file
