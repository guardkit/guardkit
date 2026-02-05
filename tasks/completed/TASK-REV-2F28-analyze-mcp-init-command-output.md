---
id: TASK-REV-2F28
title: Analyze MCP Init Command Output - Missing Template Files
status: completed
task_type: review
created: 2026-02-03T00:00:00Z
updated: 2026-02-03T00:00:00Z
priority: high
tags: [init-command, mcp-template, bug-analysis, template-system]
complexity: 5
review_mode: decision
review_depth: standard
review_results:
  mode: decision
  depth: standard
  score: 95
  findings_count: 5
  recommendations_count: 4
  decision: template_alias_and_ux_improvement
  report_path: .claude/reviews/TASK-REV-2F28-review-report.md
  completed_at: 2026-02-03T00:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyze MCP Init Command Output - Missing Template Files

## Description

Analyze the output of the `guardkit init mcp-server-python` command to investigate why only task directories were created and no actual template files were copied.

**Evidence Location**: `docs/reviews/python-mcp/init_1.md`

## Problem Statement

User ran `guardkit init mcp-server-python` expecting to initialize a Python MCP server project with appropriate template files. The command completed with apparent success but:

1. Template `mcp-server-python` was **not found** (line 13: `⚠ Template 'mcp-server-python' not found, using default`)
2. System fell back to `default` template
3. Only basic structure (task directories, agents, rules) was created
4. **No MCP-specific Python template files** were copied

## Key Observations from Output

| Line | Output | Significance |
|------|--------|--------------|
| 13 | `⚠ Template 'mcp-server-python' not found, using default` | **ROOT CAUSE** - Template doesn't exist |
| 14 | `Using template: default` | Fallback occurred |
| 18 | `✓ Copied template files` | Misleading - copied default, not MCP template |
| 37 | `🎨 Template: default` | Confirms default was used |
| 38 | `🔍 Detected Type: unknown` | No Python MCP detection |

## Questions to Answer

1. **Does `mcp-server-python` template exist?**
   - Check `~/.agentecflow/templates/` for available templates
   - Check `installer/core/templates/` for source templates

2. **What templates ARE available?**
   - List current template options
   - Document what each provides

3. **Why did the command appear to succeed?**
   - Should fallback to default be a warning or error?
   - Is the UX misleading when template doesn't exist?

4. **What should `mcp-server-python` template contain?**
   - Python MCP server boilerplate
   - `pyproject.toml` with MCP dependencies
   - Server entry point (`server.py` or similar)
   - Type definitions for MCP tools/resources

5. **Recommended action:**
   - Create the missing template?
   - Improve error messaging?
   - Both?

## Acceptance Criteria

- [ ] Identify root cause of missing template files
- [ ] Document available templates vs requested template
- [ ] Evaluate if fallback behavior is appropriate
- [ ] Provide recommendation: fix template, improve UX, or both
- [ ] If template should exist, outline what it should contain

## Review Outputs Expected

1. **Analysis Report**: Root cause and contributing factors
2. **Template Inventory**: What templates exist vs what was requested
3. **Recommendation**: Create template, improve error handling, or both
4. **Next Steps**: Implementation tasks if changes needed

## Implementation Notes

This is a **review/analysis task**. Use `/task-review TASK-REV-2F28` to execute the analysis.

If the review recommends creating an `mcp-server-python` template, a follow-up implementation task should be created.

## Test Execution Log

[Automatically populated by /task-review]
