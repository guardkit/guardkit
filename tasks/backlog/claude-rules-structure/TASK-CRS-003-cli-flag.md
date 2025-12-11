---
id: TASK-CRS-003
title: Add --use-rules-structure CLI Flag
status: backlog
task_type: implementation
created: 2025-12-11T12:15:00Z
updated: 2025-12-11T12:15:00Z
priority: high
tags: [cli, template-create, rules-structure]
complexity: 3
parent_feature: claude-rules-structure
wave: 3
implementation_mode: direct
conductor_workspace: claude-rules-wave3-1
estimated_hours: 1-2
dependencies:
  - TASK-CRS-002
---

# Task: Add --use-rules-structure CLI Flag

## Description

Add the `--use-rules-structure` flag to `/template-create` command to enable generation of modular `.claude/rules/` directory structure.

## Files to Modify

| File | Change |
|------|--------|
| `installer/core/commands/lib/template_create_orchestrator.py` | Add config field and argument |
| `installer/core/commands/template-create.md` | Document new flag |

## Implementation

### Step 1: Update OrchestrationConfig

```python
@dataclass
class OrchestrationConfig:
    # ... existing fields ...
    use_rules_structure: bool = False  # NEW: Generate .claude/rules/ structure
```

### Step 2: Add CLI Argument Parser

```python
# In the argument parsing section
parser.add_argument(
    "--use-rules-structure",
    action="store_true",
    default=False,
    help="Generate modular .claude/rules/ structure instead of single CLAUDE.md (experimental)"
)
```

### Step 3: Update Orchestrator to Use Flag

```python
def _write_output(self, output_path: Path) -> bool:
    """Write template output."""
    if self.config.use_rules_structure:
        return self._write_rules_structure(output_path)
    else:
        return self._write_claude_md_split(output_path)


def _write_rules_structure(self, output_path: Path) -> bool:
    """Write modular .claude/rules/ structure."""
    try:
        from lib.template_generator.rules_structure_generator import RulesStructureGenerator

        generator = RulesStructureGenerator(
            analysis=self.analysis,
            agents=self.agents,
            output_path=output_path
        )

        rules = generator.generate()

        # Create .claude directory
        claude_dir = output_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

        # Write each rules file
        for rel_path, content in rules.items():
            file_path = claude_dir / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            logger.info(f"Created: {file_path}")

        return True

    except Exception as e:
        logger.error(f"Failed to write rules structure: {e}")
        self.errors.append(f"Rules structure generation failed: {e}")
        return False
```

## Usage Examples

```bash
# Default (single CLAUDE.md with split)
/template-create --path /path/to/codebase

# New rules structure
/template-create --path /path/to/codebase --use-rules-structure

# Combined with other flags
/template-create --path /path/to/codebase --use-rules-structure --validate
```

## Acceptance Criteria

- [ ] `--use-rules-structure` flag added to CLI
- [ ] Flag defaults to `False` (backward compatible)
- [ ] When enabled, calls `RulesStructureGenerator`
- [ ] Output structure matches specification
- [ ] Documentation updated in template-create.md
- [ ] Help text displayed with `--help`

## Testing

```bash
# Test flag parsing
python3 ~/.agentecflow/bin/template-create --help | grep rules-structure

# Test output structure
python3 ~/.agentecflow/bin/template-create \
    --source /tmp/test-codebase \
    --use-rules-structure \
    --output /tmp/test-rules-output

# Verify structure
find /tmp/test-rules-output/.claude -type f -name "*.md"
```

## Notes

- This is Wave 3 (depends on RulesStructureGenerator)
- Direct implementation (simple flag addition)
- Parallel with TASK-CRS-004
