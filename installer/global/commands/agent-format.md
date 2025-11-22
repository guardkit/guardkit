# /agent-format - Format Agent Documentation

Automatically format agent markdown files according to GitHub best practices research (2,500+ repositories).

## Quick Start

```bash
# Format single agent
/agent-format installer/global/agents/architectural-reviewer.md

# Format all global agents
/agent-format installer/global/agents/*.md

# Preview changes without applying
/agent-format agent.md --dry-run --report

# Validate quality metrics only
/agent-format installer/global/agents/ --validate-only
```

## Description

Pattern-based command that formats agent documentation to meet GitHub structural best practices. Works on ANY agent file (global, template, or user-created) without requiring template context.

**Key Features:**
- ✅ Pattern-based transformations (no AI dependency)
- ✅ 100% content preservation
- ✅ Batch processing support
- ✅ Dry-run and validation modes
- ✅ Automatic backup creation

## Command Signature

```bash
/agent-format <path> [options]
```

### Arguments

**Required:**
- `path` - Agent file path, glob pattern, or directory
  - Single file: `agent.md` or `/path/to/agent.md`
  - Glob pattern: `installer/global/agents/*.md`
  - Directory: `installer/global/agents/` (formats all .md files)

**Optional Flags:**
- `--dry-run` - Preview changes without applying (default: false)
- `--report` - Generate detailed validation report (default: false)
- `--validate-only` - Check quality metrics only, no formatting (default: false)
- `--backup` - Create `.bak` backup before formatting (default: true)
- `--no-backup` - Disable backup creation
- `--verbose, -v` - Show detailed progress
- `--fail-on-warn` - Exit with error on warnings (default: false)

## Formatting Rules

Based on GitHub research analyzing 2,500+ repositories:

### 1. Time to First Example (<50 lines) - CRITICAL
- **Goal**: First code example within 50 lines of frontmatter
- **Action**: Moves first example to lines 21-50 if needed
- **Threshold**: <50 lines = PASS, ≥50 = FAIL

### 2. Example Density (40-50%) - CRITICAL
- **Goal**: 40-50% of content should be code examples
- **Action**: Adds `[NEEDS_CONTENT]` markers indicating where examples needed
- **Threshold**: ≥40% = PASS, 30-39% = WARN, <30% = FAIL

### 3. Boundary Sections (ALWAYS/NEVER/ASK) - REQUIRED
- **Goal**: Explicit decision framework for agent behavior
- **Action**: Adds missing boundary sections with templates
- **Threshold**: All 3 present = PASS, any missing = FAIL

### 4. Commands-First Structure (<50 lines) - CRITICAL
- **Goal**: Working command example in first 50 lines
- **Action**: Adds Quick Start section with command example
- **Threshold**: <50 lines = PASS, ≥50 = FAIL

### 5. Code-to-Text Ratio (≥1:1) - CRITICAL
- **Goal**: At least one code snippet per paragraph
- **Action**: Adds ratio markers for improvement
- **Threshold**: ≥1:1 = PASS, 0.8-0.9 = WARN, <0.8 = FAIL

### 6. Specificity Score (≥8/10) - MAINTAINED
- **Goal**: Clear, specific role definition
- **Action**: Adds warning if score <8
- **Threshold**: ≥8/10 = PASS, <8 = FAIL

## Quality Status

Agents are classified into three status levels:

- **✅ PASS**: All critical thresholds met, example density ≥40%, ratio ≥1:1
- **⚠️ WARN**: All critical thresholds met, but density 30-39% or ratio 0.8-0.9
- **❌ FAIL**: Any critical threshold not met

## Usage Examples

### Single Agent Formatting

```bash
# Format with backup (default)
/agent-format architectural-reviewer.md

# Format without backup
/agent-format architectural-reviewer.md --no-backup

# Preview changes only
/agent-format architectural-reviewer.md --dry-run

# Preview with detailed report
/agent-format architectural-reviewer.md --dry-run --report
```

### Batch Operations

```bash
# Format all global agents
/agent-format installer/global/agents/*.md

# Format all agents in directory
/agent-format installer/global/agents/

# Format with verbose progress
/agent-format installer/global/agents/*.md --verbose

# Generate reports for all agents
/agent-format installer/global/agents/*.md --report
```

### Validation Only

```bash
# Check single agent quality
/agent-format architectural-reviewer.md --validate-only

# Check all agents without formatting
/agent-format installer/global/agents/*.md --validate-only

# Fail on warnings (useful for CI/CD)
/agent-format installer/global/agents/*.md --fail-on-warn
```

## Output Examples

### Success Output

```
✅ Formatted architectural-reviewer.md

Validation Report:
  time_to_first_example: 28 lines ✅ (was 150)
  example_density: 42% ✅ (was 25%)
  boundary_sections: ALWAYS ✅, NEVER ✅, ASK ✅ (was 0/3)
  commands_first: 22 lines ✅ (was -1)
  code_to_text_ratio: 1.2:1 ✅ (was 0.6:1)
  specificity_score: 9/10 ✅ (unchanged)

Overall Status: PASS ✅ (was FAIL)

Changes applied:
  + Moved first example to line 28
  + Added ALWAYS/NEVER/ASK boundary sections
  + Added Quick Start section with command example
  + Added 3 code example markers for density improvement

Backup: architectural-reviewer.md.bak
```

### Batch Output

```
Found 15 agent(s) to process

[1/15] Processing architectural-reviewer.md... ✅ FAIL → PASS
[2/15] Processing task-manager.md... ✅ WARN → PASS
[3/15] Processing code-reviewer.md... ✅ FAIL → WARN
...
[15/15] Processing software-architect.md... ✅ WARN → PASS

============================================================
SUMMARY
============================================================
Total: 15 agents
Successful: 15
Failed: 0

Quality Status Distribution:
  ✅ PASS: 12 (80.0%)
  ⚠️  WARN: 3 (20.0%)
  ❌ FAIL: 0 (0.0%)

Time: 12.5 seconds
Avg: 0.8 seconds/agent
```

### Dry-Run Output

```
[DRY RUN] architectural-reviewer.md

Proposed Changes:
  - Move first example from line 150 to line 28
  - Add ALWAYS section after Quick Start (5 rules needed)
  - Add NEVER section after ALWAYS (5 rules needed)
  - Add ASK section after NEVER (3 scenarios needed)
  - Add Quick Start section with command example
  - Add 3 [NEEDS_CONTENT] markers for density improvement

Quality Impact:
  time_to_first_example: 150 → 28 lines ✅
  example_density: 25% → 30% ⚠️
  boundary_sections: 0/3 → 3/3 ✅
  commands_first: -1 → 22 lines ✅
  code_to_text_ratio: 0.6 → 0.8 ⚠️
  specificity_score: 9/10 → 9/10 ✅

Overall Status: FAIL → WARN

[DRY RUN] No changes applied
```

## Exit Codes

- `0` - Success (all agents formatted successfully)
- `1` - File not found or processing error
- `4` - Quality warnings (only with `--fail-on-warn`)

## Implementation Details

**Pattern-Based Transformations:**
- No AI generation (fast, deterministic)
- Preserves all original content (100%)
- Uses `[NEEDS_CONTENT]` markers instead of synthetic examples
- Idempotent (formatting twice yields same result)

**Performance:**
- Single agent: <30 seconds
- 15 global agents: <15 minutes
- 25+ agents: <25 minutes
- Memory usage: <500MB for batch operations

**Content Preservation:**
- Original content never removed
- Reorganization preserves all text
- Reference comments mark moved content
- Automatic rollback on validation errors

## Best Practices

### When to Use

- Before sharing agents with team
- After creating new agents
- During agent development
- As part of CI/CD pipeline
- For quality audits

### Workflow

1. **Format**: Run `/agent-format` on new/modified agents
2. **Review**: Check `[NEEDS_CONTENT]` markers
3. **Enhance**: Add domain-specific examples and rules
4. **Validate**: Re-run with `--validate-only` to verify PASS status

### Markers Guide

**`[NEEDS_CONTENT: ...]`** - Human action required:
- Add specific code examples
- Define boundary rules (ALWAYS/NEVER/ASK)
- Write command examples
- Fill in expected outputs

**Do NOT:**
- Generate synthetic examples
- Create fake command outputs
- Add generic placeholder content

**DO:**
- Add authentic examples from your domain
- Write specific boundary rules for the agent
- Include real command usage
- Provide actual expected outputs

## Related Commands

- `/agent-enhance` - AI-enhanced agent improvement (requires template context)
- `/template-create` - Create templates from projects
- `/template-validate` - Comprehensive template quality audit

## Notes

- Works on any agent file (global, template, or user-created)
- No template context required
- Complements `/agent-enhance` (different use cases)
- Idempotent (can run multiple times safely)
- Automatic backup by default (restore with `.bak` file)

---

**Created**: 2025-01-22
**Type**: Pattern-based formatting
**Dependencies**: None (standalone)
**Performance**: 50-80x faster than manual enhancement
