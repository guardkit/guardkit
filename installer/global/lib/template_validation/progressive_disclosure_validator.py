"""
Progressive Disclosure Validation

Validates templates for split structure compliance with progressive disclosure pattern.
"""

from pathlib import Path
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass

from .models import ValidationIssue, IssueSeverity, IssueCategory, Finding


@dataclass
class SplitMetrics:
    """Metrics for a split agent or document"""
    name: str
    core_size_kb: float
    ext_size_kb: float
    total_size_kb: float
    reduction_percent: float
    has_loading_instruction: bool
    meets_target: bool  # Core ≤ 20KB for agents, ≤ 10KB for CLAUDE.md


def validate_agent_split_structure(agent_dir: Path) -> Tuple[List[ValidationIssue], List[Finding], Dict[str, Any]]:
    """Validate agent files follow split structure.

    Args:
        agent_dir: Directory containing agent files

    Returns:
        Tuple of (issues, findings, metadata)
    """
    issues: List[ValidationIssue] = []
    findings: List[Finding] = []
    metrics: List[SplitMetrics] = []

    if not agent_dir.exists():
        return issues, findings, {"split_agents": [], "total_agents": 0}

    # Find all core agent files (excluding -ext.md files)
    core_files = [f for f in agent_dir.glob('*.md') if not f.stem.endswith('-ext')]
    ext_files = list(agent_dir.glob('*-ext.md'))

    # Check pairs
    for core in core_files:
        ext = agent_dir / f'{core.stem}-ext.md'

        if not ext.exists():
            # No extended file - not using split structure
            issues.append(ValidationIssue(
                severity=IssueSeverity.INFO,
                category=IssueCategory.AGENTS,
                message=f'Agent {core.name} not using split structure',
                location=str(core),
                fixable=False,
                fix_description='Run split-agent.py on this agent to enable progressive disclosure'
            ))
            continue

        # Check loading instruction
        core_content = core.read_text()
        has_loading_instruction = '## Extended Reference' in core_content

        if not has_loading_instruction:
            issues.append(ValidationIssue(
                severity=IssueSeverity.HIGH,
                category=IssueCategory.AGENTS,
                message=f'Missing loading instruction in {core.name}',
                location=str(core),
                fixable=False,
                fix_description='Add "## Extended Reference" section with loading instructions'
            ))

        # Check size
        core_size = core.stat().st_size
        ext_size = ext.stat().st_size
        total_size = core_size + ext_size
        core_size_kb = core_size / 1024
        ext_size_kb = ext_size / 1024
        total_size_kb = total_size / 1024

        reduction_percent = ((total_size - core_size) / total_size * 100) if total_size > 0 else 0
        meets_target = core_size_kb <= 20

        # Store metrics
        metrics.append(SplitMetrics(
            name=core.stem,
            core_size_kb=core_size_kb,
            ext_size_kb=ext_size_kb,
            total_size_kb=total_size_kb,
            reduction_percent=reduction_percent,
            has_loading_instruction=has_loading_instruction,
            meets_target=meets_target
        ))

        # Check if core exceeds target
        if not meets_target:
            issues.append(ValidationIssue(
                severity=IssueSeverity.MEDIUM,
                category=IssueCategory.AGENTS,
                message=f'{core.name} core exceeds 20KB ({core_size_kb:.1f}KB)',
                location=str(core),
                fixable=False,
                fix_description='Review content categorization - move more content to extended file'
            ))
        else:
            findings.append(Finding(
                title=f'{core.stem} Split Structure',
                description=f'Core: {core_size_kb:.1f}KB, Extended: {ext_size_kb:.1f}KB, Reduction: {reduction_percent:.0f}%',
                is_positive=True,
                impact=f'Reduces initial load by {reduction_percent:.0f}%',
                evidence=f'Loading instruction present: {has_loading_instruction}'
            ))

        # Check if reduction meets minimum threshold (40%)
        if reduction_percent < 40:
            issues.append(ValidationIssue(
                severity=IssueSeverity.LOW,
                category=IssueCategory.AGENTS,
                message=f'{core.name} split reduction below target ({reduction_percent:.0f}% < 40%)',
                location=str(core),
                fixable=False,
                fix_description='Move more content to extended file to achieve 40%+ reduction'
            ))

    # Check orphan extended files
    for ext in ext_files:
        core_stem = ext.stem.replace('-ext', '')
        core = agent_dir / f'{core_stem}.md'
        if not core.exists():
            issues.append(ValidationIssue(
                severity=IssueSeverity.HIGH,
                category=IssueCategory.AGENTS,
                message=f'Orphan extended file: {ext.name}',
                location=str(ext),
                fixable=False,
                fix_description='Create matching core file or remove extended file'
            ))

    # Summary findings
    if metrics:
        split_count = len(metrics)
        total_count = len(core_files)
        avg_reduction = sum(m.reduction_percent for m in metrics) / len(metrics) if metrics else 0

        findings.append(Finding(
            title='Progressive Disclosure Adoption',
            description=f'{split_count}/{total_count} agents using split structure',
            is_positive=split_count > 0,
            impact=f'Average reduction: {avg_reduction:.0f}%',
        ))

    metadata = {
        "split_agents": [
            {
                "name": m.name,
                "core_size_kb": m.core_size_kb,
                "ext_size_kb": m.ext_size_kb,
                "reduction_percent": m.reduction_percent,
                "has_loading_instruction": m.has_loading_instruction,
                "meets_target": m.meets_target,
            }
            for m in metrics
        ],
        "total_agents": len(core_files),
        "split_count": len(metrics),
    }

    return issues, findings, metadata


def validate_claude_md_split(template_dir: Path) -> Tuple[List[ValidationIssue], List[Finding], Dict[str, Any]]:
    """Validate CLAUDE.md follows split structure.

    Args:
        template_dir: Template root directory

    Returns:
        Tuple of (issues, findings, metadata)
    """
    issues: List[ValidationIssue] = []
    findings: List[Finding] = []
    metadata: Dict[str, Any] = {}

    claude_md = template_dir / 'CLAUDE.md'
    patterns_dir = template_dir / 'docs' / 'patterns'
    reference_dir = template_dir / 'docs' / 'reference'

    # Check CLAUDE.md exists and has loading instructions
    if claude_md.exists():
        content = claude_md.read_text()
        size = claude_md.stat().st_size
        size_kb = size / 1024

        metadata['claude_md_size_kb'] = size_kb
        metadata['has_split_structure'] = patterns_dir.exists() or reference_dir.exists()

        # Check for loading instructions
        has_loading_instruction = '## Extended Documentation' in content

        if has_loading_instruction:
            findings.append(Finding(
                title='CLAUDE.md Loading Instructions',
                description='Loading instructions for extended documentation present',
                is_positive=True,
                impact='Enables progressive disclosure for documentation',
            ))
        else:
            # Only warn if split directories exist
            if patterns_dir.exists() or reference_dir.exists():
                issues.append(ValidationIssue(
                    severity=IssueSeverity.MEDIUM,
                    category=IssueCategory.DOCUMENTATION,
                    message='CLAUDE.md missing loading instructions despite split structure',
                    location=str(claude_md),
                    fixable=False,
                    fix_description='Add "## Extended Documentation" section with loading instructions'
                ))

        # Check size
        meets_target = size_kb <= 10

        if meets_target:
            findings.append(Finding(
                title='CLAUDE.md Size Target Met',
                description=f'Core documentation: {size_kb:.1f}KB (target: ≤10KB)',
                is_positive=True,
                impact='Minimal initial context window usage',
            ))
        else:
            severity = IssueSeverity.MEDIUM if size_kb <= 15 else IssueSeverity.HIGH
            issues.append(ValidationIssue(
                severity=severity,
                category=IssueCategory.DOCUMENTATION,
                message=f'CLAUDE.md exceeds 10KB ({size_kb:.1f}KB)',
                location=str(claude_md),
                fixable=False,
                fix_description='Move content to docs/patterns or docs/reference'
            ))

        metadata['meets_target'] = meets_target
        metadata['has_loading_instruction'] = has_loading_instruction

    # Check split directories exist
    if patterns_dir.exists():
        pattern_files = list(patterns_dir.glob('*.md'))
        findings.append(Finding(
            title='Pattern Documentation',
            description=f'{len(pattern_files)} pattern documentation file(s)',
            is_positive=True,
            impact='Extended patterns available on-demand',
        ))
        metadata['patterns_count'] = len(pattern_files)
    else:
        # Not an error - split structure is optional
        metadata['patterns_count'] = 0

    if reference_dir.exists():
        reference_files = list(reference_dir.glob('*.md'))
        findings.append(Finding(
            title='Reference Documentation',
            description=f'{len(reference_files)} reference documentation file(s)',
            is_positive=True,
            impact='Extended reference available on-demand',
        ))
        metadata['reference_count'] = len(reference_files)
    else:
        # Not an error - split structure is optional
        metadata['reference_count'] = 0

    return issues, findings, metadata


def generate_split_validation_report(template_dir: Path) -> str:
    """Generate validation report including split metrics.

    Args:
        template_dir: Template root directory

    Returns:
        Formatted markdown report
    """
    report = []

    report.append("## Progressive Disclosure Validation")
    report.append("")

    # CLAUDE.md metrics
    claude_md = template_dir / 'CLAUDE.md'
    if claude_md.exists():
        size = claude_md.stat().st_size
        size_kb = size / 1024
        status = "✅" if size_kb <= 10 else "⚠️"
        report.append("### CLAUDE.md")
        report.append(f"- Size: {size_kb:.1f}KB {status}")
        report.append(f"- Target: ≤10KB")

        patterns_dir = template_dir / 'docs' / 'patterns'
        reference_dir = template_dir / 'docs' / 'reference'

        if patterns_dir.exists() or reference_dir.exists():
            report.append("- Split Structure: ✅")
            if patterns_dir.exists():
                pattern_count = len(list(patterns_dir.glob('*.md')))
                report.append(f"  - Patterns: {pattern_count} files")
            if reference_dir.exists():
                ref_count = len(list(reference_dir.glob('*.md')))
                report.append(f"  - Reference: {ref_count} files")
        else:
            report.append("- Split Structure: Single-file mode")

        report.append("")

    # Agent metrics
    agents_dir = template_dir / 'agents'
    if agents_dir.exists():
        report.append("### Agents")
        core_files = [f for f in agents_dir.glob('*.md') if not f.stem.endswith('-ext')]

        split_agents = []
        non_split_agents = []

        for core in sorted(core_files):
            ext = agents_dir / f'{core.stem}-ext.md'
            if ext.exists():
                core_size = core.stat().st_size
                ext_size = ext.stat().st_size
                total = core_size + ext_size
                core_size_kb = core_size / 1024
                reduction = ((total - core_size) / total * 100) if total > 0 else 0

                status = "✅" if reduction >= 40 and core_size_kb <= 20 else "⚠️"
                split_agents.append(f"- {core.stem}: {core_size_kb:.1f}KB core, {reduction:.0f}% reduction {status}")
            else:
                non_split_agents.append(f"- {core.stem}: Single-file (no split)")

        if split_agents:
            report.append("")
            report.append("**Split Agents:**")
            report.extend(split_agents)

        if non_split_agents:
            report.append("")
            report.append("**Non-Split Agents:**")
            report.extend(non_split_agents)

        report.append("")

    return "\n".join(report)
