---
id: TASK-PD-006
title: Update template_create_orchestrator.py for split output
status: completed
created: 2025-12-03T16:00:00Z
updated: 2025-12-05T13:05:00Z
completed: 2025-12-05T13:05:00Z
priority: high
tags: [progressive-disclosure, phase-2, orchestrator, template-create]
complexity: 4
blocked_by: [TASK-PD-005]
blocks: [TASK-PD-007]
review_task: TASK-REV-426C
completed_location: tasks/completed/TASK-PD-006/
organized_files:
  - TASK-PD-006.md
  - completion-summary.md
test_results:
  status: passed
  coverage: 8%
  tests_passed: 11
  tests_failed: 0
  last_run: 2025-12-05T12:50:00Z
code_review:
  status: approved
  score: 8.5
  reviewer: code-reviewer
  reviewed_at: 2025-12-05T12:55:00Z
  recommendation: "Approve with optional DRY improvements"
architectural_review:
  score: 78
  solid_score: 42
  dry_score: 20
  yagni_score: 16
---

# Task: Update template_create_orchestrator.py for split output

## Phase

**Phase 2: Template Generation - CLAUDE.md Split**

## Description

Update the template creation orchestrator to write split CLAUDE.md output to the correct directory structure.

## Current Output Structure

```
template-output/
├── CLAUDE.md           # Single 20KB file
├── agents/
└── ...
```

## Target Output Structure

```
template-output/
├── CLAUDE.md           # Core ~8KB file
├── docs/
│   ├── patterns/
│   │   ├── README.md   # Pattern index
│   │   └── ...
│   └── reference/
│       ├── README.md   # Reference index
│       └── ...
├── agents/
└── ...
```

## Implementation

### Update Orchestrator Write Logic

```python
def _write_claude_md(self, output_path: Path, generator: ClaudeMdGenerator):
    """Write CLAUDE.md with progressive disclosure split.

    Args:
        output_path: Template output directory
        generator: Configured ClaudeMdGenerator
    """
    # Generate split content
    split_output = generator.generate_split()

    # Write core CLAUDE.md
    claude_path = output_path / "CLAUDE.md"
    claude_path.write_text(split_output.core, encoding='utf-8')

    # Create docs directories
    patterns_dir = output_path / "docs" / "patterns"
    reference_dir = output_path / "docs" / "reference"
    patterns_dir.mkdir(parents=True, exist_ok=True)
    reference_dir.mkdir(parents=True, exist_ok=True)

    # Write patterns documentation
    patterns_readme = patterns_dir / "README.md"
    patterns_readme.write_text(split_output.patterns, encoding='utf-8')

    # Write reference documentation
    reference_readme = reference_dir / "README.md"
    reference_readme.write_text(split_output.reference, encoding='utf-8')

    # Log sizes for validation
    self._log_split_sizes(split_output)

def _log_split_sizes(self, split_output: TemplateSplitOutput):
    """Log split output sizes for validation."""
    print(f"CLAUDE.md (core): {split_output.get_core_size():,} bytes")
    print(f"Patterns: {len(split_output.patterns):,} bytes")
    print(f"Reference: {len(split_output.reference):,} bytes")
    print(f"Total: {split_output.get_total_size():,} bytes")
    print(f"Core reduction: {split_output.get_reduction_percent():.1f}%")
```

### Add Split Flag to Command

```python
def create_template(
    self,
    source_path: Path,
    output_path: Path,
    split_claude_md: bool = True  # Default to progressive disclosure
) -> TemplateCreateResult:
    """Create template from source codebase.

    Args:
        source_path: Path to source codebase
        output_path: Path for template output
        split_claude_md: If True, split CLAUDE.md for progressive disclosure
    """
    # ... existing analysis phases ...

    if split_claude_md:
        self._write_claude_md_split(output_path, generator)
    else:
        self._write_claude_md_single(output_path, generator)
```

## Acceptance Criteria

- [ ] Split output writes to correct directory structure
- [ ] `docs/patterns/README.md` created with pattern content
- [ ] `docs/reference/README.md` created with reference content
- [ ] Core CLAUDE.md includes loading instructions pointing to docs/
- [ ] Size logging shows reduction percentage
- [ ] Backward compatible single-file mode available
- [ ] Integration test: full template-create with split output

## Test Strategy

```python
def test_template_create_split_output():
    """Test template creation with split CLAUDE.md."""
    orchestrator = TemplateCreateOrchestrator()
    result = orchestrator.create_template(
        source_path=bulletproof_react_path,
        output_path=output_dir
    )

    # Verify file structure
    assert (output_dir / "CLAUDE.md").exists()
    assert (output_dir / "docs" / "patterns" / "README.md").exists()
    assert (output_dir / "docs" / "reference" / "README.md").exists()

    # Verify core size
    core_size = (output_dir / "CLAUDE.md").stat().st_size
    assert core_size <= 10 * 1024  # 10KB max

    # Verify loading instructions
    core_content = (output_dir / "CLAUDE.md").read_text()
    assert "docs/patterns/README.md" in core_content
    assert "docs/reference/README.md" in core_content

def test_template_create_single_file_mode():
    """Test backward compatible single file mode."""
    orchestrator = TemplateCreateOrchestrator()
    result = orchestrator.create_template(
        source_path=source_path,
        output_path=output_dir,
        split_claude_md=False
    )

    assert (output_dir / "CLAUDE.md").exists()
    assert not (output_dir / "docs" / "patterns").exists()
```

## Files to Modify

1. `installer/global/lib/template_generator/template_create_orchestrator.py` - Main changes
2. `installer/global/commands/template-create.md` - Document new output structure

## Validation Checkpoint

After completing TASK-PD-005 through TASK-PD-007:

```bash
# Run template-create on sample codebase
/template-create --source ~/Projects/bulletproof-react --output /tmp/test-template

# Verify output structure
ls -la /tmp/test-template/
ls -la /tmp/test-template/docs/patterns/
ls -la /tmp/test-template/docs/reference/

# Check sizes
wc -c /tmp/test-template/CLAUDE.md
# Should be ~8KB

wc -c /tmp/test-template/docs/patterns/README.md
wc -c /tmp/test-template/docs/reference/README.md
```

## Estimated Effort

**1 day**

## Dependencies

- TASK-PD-005 (claude_md_generator refactor)
