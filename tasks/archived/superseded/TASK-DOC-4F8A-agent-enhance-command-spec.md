---
task_id: TASK-DOC-4F8A
title: Create agent-enhance command specification
status: BACKLOG
priority: HIGH
complexity: 3
created: 2025-11-20T21:20:00Z
updated: 2025-11-20T21:20:00Z
assignee: null
tags: [documentation, phase-8, command-spec]
related_tasks: [TASK-PHASE-8-INCREMENTAL, TASK-DOC-F3A3, TASK-DOC-1E7B]
estimated_duration: 2 hours
technologies: [markdown, documentation]
review_source: docs/reviews/phase-8-implementation-review.md
---

# Create Agent-Enhance Command Specification

## Problem Statement

The `/agent-enhance` command has no specification document in `installer/core/commands/`. Users and developers lack reference documentation for this command.

**Review Finding** (Section 6.3, Documentation Gap #3):
> **Command Spec**: No `agent-enhance.md` in commands/
> **Impact**: No reference documentation for command

## Current State

**Missing File**: `installer/core/commands/agent-enhance.md`

**Existing Command Specs** (for reference):
- `installer/core/commands/template-create.md`
- `installer/core/commands/task-work.md`
- `installer/core/commands/task-create.md`

**Gap**: No specification for `/agent-enhance` command.

## Acceptance Criteria

### 1. Command Specification Format
- [ ] Follows same format as existing command specs
- [ ] Includes command syntax
- [ ] Documents all parameters
- [ ] Documents all flags/options
- [ ] Includes exit codes
- [ ] Includes error scenarios

### 2. Content Sections
- [ ] Overview and purpose
- [ ] Syntax and parameters
- [ ] Flags and options
- [ ] Enhancement strategies
- [ ] Examples
- [ ] Error handling
- [ ] Exit codes
- [ ] Related commands

### 3. Technical Details
- [ ] Parameter types documented
- [ ] Default values specified
- [ ] Validation rules explained
- [ ] Edge cases documented

### 4. Cross-References
- [ ] Links to workflow guide
- [ ] Links to Phase 8 spec
- [ ] Links to related commands
- [ ] Links to CLAUDE.md

## Technical Details

### File to Create

**Location**: `installer/core/commands/agent-enhance.md`

**Length**: ~1200-1500 words (similar to other command specs)

**Format**: Markdown following existing command spec template

### Recommended Content Structure

```markdown
# /agent-enhance - Agent Content Enhancement

## Overview

The `/agent-enhance` command enriches agent files with code examples, best practices, and anti-patterns extracted from template source code.

**Purpose**: Transform stub agent files into comprehensive documentation

**Phase**: Phase 8 (Incremental Enhancement)

**Related**: `/template-create --create-agent-tasks`

## Syntax

```bash
/agent-enhance AGENT_FILE TEMPLATE_DIR [OPTIONS]
```

### Parameters

#### AGENT_FILE (required)
- **Type**: Path
- **Description**: Path to agent markdown file to enhance
- **Example**: `~/.agentecflow/templates/my-template/agents/api-specialist.md`
- **Validation**:
  - File must exist
  - File must be .md extension
  - File must have valid frontmatter

#### TEMPLATE_DIR (required)
- **Type**: Path
- **Description**: Path to template directory containing source files
- **Example**: `~/.agentecflow/templates/my-template`
- **Validation**:
  - Directory must exist
  - Must be valid template directory
  - Should contain .template files

### Options

#### --strategy=STRATEGY
- **Type**: Enum[ai, static, hybrid]
- **Default**: hybrid
- **Description**: Enhancement strategy to use
- **Values**:
  - `ai`: AI-powered enhancement (requires TASK-AI-2B37)
  - `static`: Template-based enhancement
  - `hybrid`: Try AI, fall back to static (recommended)

#### --dry-run
- **Type**: Flag (boolean)
- **Default**: false
- **Description**: Preview enhancement without applying changes
- **Usage**: Shows diff of proposed changes

#### --verbose
- **Type**: Flag (boolean)
- **Default**: false
- **Description**: Show detailed enhancement process
- **Usage**: Debugging and transparency

## Enhancement Strategies

### AI Strategy

**Command**:
```bash
/agent-enhance AGENT_FILE TEMPLATE_DIR --strategy=ai
```

**Process**:
1. Invokes `agent-content-enhancer` agent
2. Analyzes template source code
3. Generates context-aware examples
4. Writes specific best practices
5. Documents relevant anti-patterns

**Requirements**:
- AI integration (TASK-AI-2B37)
- Agent-content-enhancer available

**Performance**: ~30-60 seconds

**Quality**: High (9/10)

### Static Strategy

**Command**:
```bash
/agent-enhance AGENT_FILE TEMPLATE_DIR --strategy=static
```

**Process**:
1. Loads template .template files
2. Extracts code patterns via regex
3. Generates basic examples
4. Adds common best practices
5. Template-based enhancement

**Requirements**: None (works offline)

**Performance**: <1 second

**Quality**: Medium (6-7/10)

### Hybrid Strategy (Default)

**Command**:
```bash
/agent-enhance AGENT_FILE TEMPLATE_DIR
# or explicitly:
/agent-enhance AGENT_FILE TEMPLATE_DIR --strategy=hybrid
```

**Process**:
1. Try AI strategy first
2. If AI fails, fall back to static
3. Return best available result

**Requirements**: None (static fallback)

**Performance**: Variable (1-60 seconds)

**Quality**: High when AI works, medium on fallback

**Recommended**: Default for most users

## Examples

### Example 1: Basic Enhancement

```bash
/agent-enhance ~/.agentecflow/templates/fastapi-template/agents/api-route-specialist.md \
               ~/.agentecflow/templates/fastapi-template
```

Output:
```
✅ Enhanced api-route-specialist agent
- Added 4 code examples
- Added 6 best practices
- Added 3 anti-patterns
- Updated "Why This Exists" section
```

### Example 2: Dry-Run Preview

```bash
/agent-enhance ~/.agentecflow/templates/fastapi-template/agents/api-route-specialist.md \
               ~/.agentecflow/templates/fastapi-template \
               --dry-run
```

Output:
```
Enhancement Preview (dry-run mode):

Proposed Changes:
+ ## Code Examples
+
+ ### Example 1: FastAPI Router Configuration
+ ```python
+ from fastapi import APIRouter
+ ...
+ ```

No changes applied (use without --dry-run to apply)
```

### Example 3: Force Static Strategy

```bash
/agent-enhance ~/.agentecflow/templates/my-template/agents/database-specialist.md \
               ~/.agentecflow/templates/my-template \
               --strategy=static
```

Use when:
- Offline work
- AI not available
- Quick enhancement needed

### Example 4: Verbose Mode

```bash
/agent-enhance ~/.agentecflow/templates/my-template/agents/api-specialist.md \
               ~/.agentecflow/templates/my-template \
               --verbose
```

Output shows:
- Agent metadata loading
- Template file discovery
- Enhancement generation process
- Applied changes detail

## Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | Enhancement applied successfully |
| 1 | General error | Check error message |
| 2 | Agent file not found | Verify AGENT_FILE path |
| 3 | Template dir not found | Verify TEMPLATE_DIR path |
| 4 | Invalid agent frontmatter | Fix agent file frontmatter |
| 5 | No template files found | Add .template files to template |
| 6 | AI strategy failed | Use --strategy=static or hybrid |
| 7 | Permission error | Check file/directory permissions |

## Error Scenarios

### Error: Agent File Not Found

```bash
ERROR: Agent file not found: /path/to/agent.md
```

**Solution**: Verify path, ensure file exists

### Error: Invalid Frontmatter

```bash
ERROR: Agent file has invalid frontmatter
```

**Solution**: Fix YAML frontmatter in agent file

### Error: No Template Files

```bash
WARNING: No .template files found in template directory
Enhancement quality may be limited.
```

**Solution**: Acceptable for minimal templates, quality will be lower

### Error: AI Strategy Failed

```bash
ERROR: AI enhancement failed: Connection timeout
Falling back to static enhancement...
```

**Solution**: Automatic fallback with hybrid, or use `--strategy=static`

## Integration with Taskwright

### With Task Workflow

```bash
# 1. Create template with tasks
/template-create --name my-template --create-agent-tasks

# 2. Work on enhancement task
/task-work TASK-AGENT-API-ABC123

# Internally calls /agent-enhance
```

### Direct Invocation

```bash
# Manual enhancement without task system
/agent-enhance AGENT_FILE TEMPLATE_DIR
```

## Output Format

Enhancement result structure:

```
Agent Enhancement Complete

Agent: api-service-specialist
Strategy: hybrid (AI successful)
Duration: 42 seconds

Changes Applied:
✅ Added 4 code examples
✅ Added 6 best practices
✅ Added 3 anti-patterns
✅ Updated "Why This Exists" section

File Updated: ~/.agentecflow/templates/my-template/agents/api-service-specialist.md
```

## Best Practices

1. **Always dry-run first**
   ```bash
   /agent-enhance AGENT_FILE TEMPLATE_DIR --dry-run
   ```

2. **Use hybrid strategy** (default)
   - Best reliability
   - Automatic fallback

3. **Review enhancements**
   ```bash
   cat AGENT_FILE  # After enhancement
   ```

4. **Validate quality**
   - Check code examples compile
   - Verify best practices are accurate
   - Ensure "Why This Exists" is meaningful

## Related Commands

- `/template-create` - Creates stub agents (Phase 6)
- `/template-create --create-agent-tasks` - Generates enhancement tasks
- `/task-work TASK-ID` - Works on enhancement task
- `/template-validate` - Validates enhanced template

## See Also

- [Incremental Enhancement Workflow](../../docs/workflows/incremental-enhancement-workflow.md)
- [Phase 8 Specification](../../tasks/backlog/TASK-PHASE-8-INCREMENTAL-specification.md)
- [CLAUDE.md - Incremental Enhancement](../../CLAUDE.md#incremental-enhancement-workflow)

## Technical Notes

### Implementation

- **Orchestrator**: `installer/core/commands/lib/agent_enhancement/enhancer.py`
- **Prompt Builder**: `installer/core/commands/lib/agent_enhancement/prompt_builder.py`
- **Parser**: `installer/core/commands/lib/agent_enhancement/parser.py`
- **Applier**: `installer/core/commands/lib/agent_enhancement/applier.py`

### Agent Invocation

When using AI strategy:
- Invokes: `agent-content-enhancer`
- Timeout: 300 seconds
- Retry: 3 attempts with exponential backoff (when TASK-AI-2B37 complete)

### State Management

- **Stateless**: No persistent state
- **Idempotent**: Can re-run safely
- **No cleanup**: No temporary files
```

## Success Metrics

### Documentation Completeness
- [ ] All parameters documented
- [ ] All flags documented
- [ ] All strategies explained
- [ ] All exit codes listed
- [ ] Error scenarios covered

### User Clarity
- [ ] User understands command purpose
- [ ] User knows all options
- [ ] User can troubleshoot errors
- [ ] User has concrete examples

### Technical Accuracy
- [ ] Parameter types correct
- [ ] Default values accurate
- [ ] Exit codes match implementation
- [ ] Integration points documented

## Dependencies

**Requires**:
- Understanding of agent enhancement implementation
- Knowledge of all command flags and options

**Blocks**:
- TASK-DOC-9C4E (CLAUDE.md update)
- TASK-DOC-1E7B (workflow guide)
- TASK-DOC-F3A3 (documentation suite)

## Related Review Findings

**From**: `docs/reviews/phase-8-implementation-review.md`

- **Section 6.3**: Documentation Gap #3 (command spec)
- **Section 8**: Recommendations - Short Term #5
- **Section 6.1**: Immediate Priority (documentation)

## Estimated Effort

**Duration**: 2 hours

**Breakdown**:
- Outline structure (15 min)
- Write syntax and parameters (30 min)
- Document strategies (30 min)
- Add examples (25 min)
- Error scenarios (15 min)
- Review and refine (15 min)

## Notes

- **Priority**: HIGH - completes command documentation
- **Format**: Follow existing command spec template
- **Dependencies**: Coordinate with workflow guide and CLAUDE.md
- **Impact**: Provides reference for users and developers
