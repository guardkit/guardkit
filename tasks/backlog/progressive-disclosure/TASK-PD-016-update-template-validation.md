---
id: TASK-PD-016
title: Update template_validation for split structure recognition
status: backlog
created: 2025-12-03T16:00:00Z
updated: 2025-12-03T16:00:00Z
priority: medium
tags: [progressive-disclosure, phase-5, validation, template-validation]
complexity: 5
blocked_by: [TASK-PD-012, TASK-PD-013, TASK-PD-014, TASK-PD-015]
blocks: [TASK-PD-017]
review_task: TASK-REV-426C
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Update template_validation for split structure recognition

## Phase

**Phase 5: Validation & Documentation** (LOW RISK)

## Description

Update the template validation system to recognize and validate the progressive disclosure split structure.

## Current State

- Template validation checks for single CLAUDE.md file
- Agent validation expects single .md files
- No awareness of split structure

## Target State

- Validation recognizes core + extended file pairs
- Validates loading instructions present
- Validates size targets met
- Reports split metrics

## Implementation

### Update Validation Checks

```python
def validate_agent_split_structure(agent_dir: Path) -> ValidationResult:
    """Validate agent files follow split structure.

    Args:
        agent_dir: Directory containing agent files

    Returns:
        ValidationResult with findings
    """
    findings = []

    core_files = [f for f in agent_dir.glob('*.md') if not f.stem.endswith('-ext')]
    ext_files = list(agent_dir.glob('*-ext.md'))

    # Check pairs
    for core in core_files:
        ext = agent_dir / f'{core.stem}-ext.md'

        if not ext.exists():
            findings.append(ValidationFinding(
                level='WARNING',
                message=f'No extended file for {core.name}',
                suggestion='Run split-agent.py on this agent'
            ))
            continue

        # Check loading instruction
        core_content = core.read_text()
        if '## Extended Reference' not in core_content:
            findings.append(ValidationFinding(
                level='ERROR',
                message=f'Missing loading instruction in {core.name}',
                suggestion='Add loading instruction section'
            ))

        # Check size
        core_size = core.stat().st_size
        if core_size > 20 * 1024:
            findings.append(ValidationFinding(
                level='WARNING',
                message=f'{core.name} core exceeds 20KB ({core_size/1024:.1f}KB)',
                suggestion='Review content categorization'
            ))

    # Check orphan extended files
    for ext in ext_files:
        core_stem = ext.stem.replace('-ext', '')
        core = agent_dir / f'{core_stem}.md'
        if not core.exists():
            findings.append(ValidationFinding(
                level='ERROR',
                message=f'Orphan extended file: {ext.name}',
                suggestion='Create matching core file or remove'
            ))

    return ValidationResult(findings=findings)


def validate_claude_md_split(template_dir: Path) -> ValidationResult:
    """Validate CLAUDE.md follows split structure.

    Args:
        template_dir: Template root directory

    Returns:
        ValidationResult with findings
    """
    findings = []

    claude_md = template_dir / 'CLAUDE.md'
    patterns_dir = template_dir / 'docs' / 'patterns'
    reference_dir = template_dir / 'docs' / 'reference'

    # Check CLAUDE.md exists and has loading instructions
    if claude_md.exists():
        content = claude_md.read_text()
        if '## Extended Documentation' not in content:
            findings.append(ValidationFinding(
                level='WARNING',
                message='CLAUDE.md missing loading instructions',
                suggestion='Add Extended Documentation section'
            ))

        size = claude_md.stat().st_size
        if size > 10 * 1024:
            findings.append(ValidationFinding(
                level='WARNING',
                message=f'CLAUDE.md exceeds 10KB ({size/1024:.1f}KB)',
                suggestion='Move content to docs/patterns or docs/reference'
            ))

    # Check split directories exist
    if not patterns_dir.exists():
        findings.append(ValidationFinding(
            level='INFO',
            message='docs/patterns/ not found',
            suggestion='Create patterns documentation or use single-file mode'
        ))

    if not reference_dir.exists():
        findings.append(ValidationFinding(
            level='INFO',
            message='docs/reference/ not found',
            suggestion='Create reference documentation or use single-file mode'
        ))

    return ValidationResult(findings=findings)
```

### Update Validation Report

```python
def generate_split_validation_report(template_dir: Path) -> str:
    """Generate validation report including split metrics."""
    report = []

    report.append("## Progressive Disclosure Validation")
    report.append("")

    # CLAUDE.md metrics
    claude_md = template_dir / 'CLAUDE.md'
    if claude_md.exists():
        size = claude_md.stat().st_size
        status = "✅" if size <= 10 * 1024 else "⚠️"
        report.append(f"### CLAUDE.md")
        report.append(f"- Size: {size/1024:.1f}KB {status}")
        report.append(f"- Target: ≤10KB")
        report.append("")

    # Agent metrics
    agents_dir = template_dir / 'agents'
    if agents_dir.exists():
        report.append("### Agents")
        core_files = [f for f in agents_dir.glob('*.md') if not f.stem.endswith('-ext')]

        for core in sorted(core_files):
            ext = agents_dir / f'{core.stem}-ext.md'
            core_size = core.stat().st_size
            ext_size = ext.stat().st_size if ext.exists() else 0
            total = core_size + ext_size
            reduction = ((total - core_size) / total * 100) if total > 0 else 0

            status = "✅" if reduction >= 40 else "⚠️"
            report.append(f"- {core.stem}: {core_size/1024:.1f}KB core, {reduction:.0f}% reduction {status}")

    return "\n".join(report)
```

## Acceptance Criteria

- [ ] `validate_agent_split_structure()` function implemented
- [ ] `validate_claude_md_split()` function implemented
- [ ] Split metrics included in validation reports
- [ ] `/template-validate` recognizes split structure
- [ ] Validation passes for split templates
- [ ] Backward compatible with non-split templates

## Files to Modify

1. Template validation module (lib/template_validator or similar)
2. Validation report generator

## Estimated Effort

**1 day**

## Dependencies

- TASK-PD-012 through TASK-PD-015 (all agents split)
