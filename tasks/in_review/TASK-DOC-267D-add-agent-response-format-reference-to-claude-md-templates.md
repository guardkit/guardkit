---
id: TASK-DOC-267D
title: Add agent-response format reference to CLAUDE.md templates
status: backlog
priority: low
complexity: 2
tags: [documentation, templates, agent-response, template-create]
related_tasks: [TASK-FIX-267C]
---

# Add Agent Response Format Reference to CLAUDE.md Templates

## Context

TASK-FIX-267C created comprehensive documentation for the `.agent-response.json` format specification:
- `docs/reference/agent-response-format.md` - Complete format specification
- `docs/validation/agent-response-format-test.py` - Validation test suite

The reference has been added to `installer/core/commands/agent-enhance.md`, but it's not yet in `CLAUDE.md` (project instructions that Claude Code sees).

## Problem

`CLAUDE.md` is generated in **two ways**:
1. **`guardkit init <template>`** - Copies from built-in template CLAUDE.md files
2. **`/template-create`** - Generates from codebase analysis

Both paths need the agent-response format reference so Claude Code has access to it when running `/agent-enhance`.

## Solution

Add a reference to the agent-response format specification in **BOTH**:
1. **Built-in template CLAUDE.md files** (Option 1)
2. **Template generation logic** (Option 2)

This ensures the reference appears regardless of how the project was initialized.

## Acceptance Criteria

1. ✅ Reference added to all template CLAUDE.md files in `installer/core/templates/*/CLAUDE.md`
2. ✅ Reference added to `/template-create` generation logic (CLAUDE.md generator)
3. ✅ Reference includes link to format specification document
4. ✅ Reference mentions TASK-FIX-267C for traceability
5. ✅ Test both paths:
   - `guardkit init react-typescript` → verify CLAUDE.md has reference
   - `/template-create` → verify generated CLAUDE.md has reference
6. ✅ Existing CLAUDE.md in GuardKit repo updated (for dogfooding)

## Implementation

### Option 1: Update Individual Template Files (Simple)

Update each template's CLAUDE.md file:
- `installer/core/templates/react-typescript/CLAUDE.md`
- `installer/core/templates/fastapi-python/CLAUDE.md`
- `installer/core/templates/nextjs-fullstack/CLAUDE.md`
- `installer/core/templates/react-fastapi-monorepo/CLAUDE.md`
- `installer/core/templates/default/CLAUDE.md`

Add section (suggested location: near MCP Integration or Agent sections):

```markdown
## Agent Response Format

When generating `.agent-response.json` files (checkpoint-resume pattern), use the format specification:

**Reference**: [Agent Response Format Specification](../../docs/reference/agent-response-format.md) (TASK-FIX-267C)

**Key Requirements**:
- Field name: `response` (NOT `result`)
- Data type: JSON-encoded string (NOT object)
- All 9 required fields must be present

See the specification for complete schema and examples.
```

### Option 2: Add to Template Generation Logic (Required)

Modify `/template-create` to inject this reference automatically when generating CLAUDE.md.

**Files to Update**:
- `installer/core/lib/template_creation/claude_md_generator.py` (or equivalent)
- Look for CLAUDE.md generation code
- Add agent-response format section to generated output

**Implementation**:
```python
# In CLAUDE.md generator, add section:
agent_response_section = """
## Agent Response Format

When generating `.agent-response.json` files (checkpoint-resume pattern), use the format specification:

**Reference**: [Agent Response Format Specification](docs/reference/agent-response-format.md) (TASK-FIX-267C)

**Key Requirements**:
- Field name: `response` (NOT `result`)
- Data type: JSON-encoded string (NOT object)
- All 9 required fields must be present

See the specification for complete schema and examples.
"""
```

### Recommended Approach

**Implement BOTH options** because:
- ✅ Option 1 covers `guardkit init` path
- ✅ Option 2 covers `/template-create` path
- ✅ Both paths are actively used
- ✅ Ensures consistency across all projects
- ✅ Low risk - documentation only

## Estimated Effort

- **Complexity**: 2/10 (simple - both options needed)
- **Time**: ~20 minutes
  - Option 1: ~10 minutes (6 template files)
  - Option 2: ~10 minutes (generator code + test)
- **Files**:
  - 6 template CLAUDE.md files (Option 1)
  - 1 generator Python file (Option 2)

## Testing

### Test Option 1 (Built-in Templates)
1. Verify reference added to all 6 template CLAUDE.md files
2. Create test project: `mkdir /tmp/test-template && cd /tmp/test-template`
3. Run: `guardkit init react-typescript`
4. Check generated CLAUDE.md includes the agent-response format section
5. Verify links resolve correctly from project root

### Test Option 2 (Template Generation)
1. Create test project with codebase: `mkdir /tmp/test-generate && cd /tmp/test-generate`
2. Add some code files (e.g., React components)
3. Run: `/template-create`
4. Check generated `.claude/CLAUDE.md` includes the agent-response format section
5. Verify links resolve correctly from project root

### Test Integration
1. In a project with CLAUDE.md containing the reference
2. Run: `/agent-enhance <some-agent>`
3. Verify Claude Code can access the format specification
4. Verify generated `.agent-response.json` uses correct format

## Notes

This is a follow-up to TASK-FIX-267C, which created the format specification.

**Why both options are needed**:
- Users who run `guardkit init` get templates from `installer/core/templates/` (Option 1)
- Users who run `/template-create` get generated CLAUDE.md from their codebase (Option 2)
- Both groups need access to the format specification when using `/agent-enhance`

Adding the reference to both paths ensures all future projects generated with GuardKit will have access to the correct format documentation, regardless of initialization method.
