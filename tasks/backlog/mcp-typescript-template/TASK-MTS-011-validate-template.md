---
id: TASK-MTS-011
title: Validate mcp-typescript template
status: in_review
task_type: testing
created: 2026-01-24 16:45:00+00:00
updated: 2026-01-24 16:45:00+00:00
priority: medium
tags:
- template
- mcp
- typescript
- validation
complexity: 3
parent_review: TASK-REV-4371
feature_id: FEAT-MTS
wave: 4
parallel_group: wave4
implementation_mode: task-work
conductor_workspace: null
dependencies:
- TASK-MTS-001
- TASK-MTS-002
- TASK-MTS-003
- TASK-MTS-004
- TASK-MTS-005
- TASK-MTS-006
- TASK-MTS-007
- TASK-MTS-008
- TASK-MTS-009
- TASK-MTS-010
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-4048
  base_branch: main
  started_at: '2026-01-28T19:23:33.168384'
  last_updated: '2026-01-28T19:33:53.160699'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-01-28T19:23:33.168384'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Validate mcp-typescript template

## Description

Run comprehensive validation on the completed `mcp-typescript` template to ensure it meets GuardKit template standards and all MCP patterns are correctly implemented.

## Reference

Use `docs/guides/template-validation-guide.md` for validation procedures.
Use `installer/core/templates/react-typescript/` as quality reference.

## Validation Steps

### 1. Structural Validation

```bash
# Verify all required files exist
ls -la installer/core/templates/mcp-typescript/

# Expected structure:
# ├── manifest.json
# ├── settings.json
# ├── CLAUDE.md
# ├── README.md
# ├── .claude/
# │   ├── CLAUDE.md
# │   └── rules/
# │       ├── mcp-patterns.md
# │       ├── testing.md
# │       ├── transport.md
# │       └── configuration.md
# ├── agents/
# │   ├── mcp-typescript-specialist.md
# │   ├── mcp-typescript-specialist-ext.md
# │   ├── mcp-testing-specialist.md
# │   └── mcp-testing-specialist-ext.md
# └── templates/
#     ├── server/
#     ├── tools/
#     ├── resources/
#     ├── prompts/
#     ├── config/
#     ├── testing/
#     └── docker/
```

### 2. JSON Validation

```bash
# Validate manifest.json
cat installer/core/templates/mcp-typescript/manifest.json | jq .

# Validate settings.json
cat installer/core/templates/mcp-typescript/settings.json | jq .
```

### 3. Template Validation Command

```bash
/template-validate installer/core/templates/mcp-typescript
```

### 4. Pattern Compliance Check

Verify all 10 critical MCP patterns are documented:

- [ ] Pattern 1: McpServer class usage
- [ ] Pattern 2: Tool registration before connect()
- [ ] Pattern 3: stderr logging only
- [ ] Pattern 4: Streaming two-layer architecture
- [ ] Pattern 5: Error handling for streams
- [ ] Pattern 6: Zod schema validation
- [ ] Pattern 7: Absolute path configuration
- [ ] Pattern 8: ISO timestamp format
- [ ] Pattern 9: Protocol testing
- [ ] Pattern 10: Docker non-root deployment

### 5. Agent Quality Check

Verify agents meet quality standards:

- [ ] Valid frontmatter with all required fields
- [ ] ALWAYS/NEVER boundaries defined
- [ ] Code examples included
- [ ] Extended files contain detailed guidance

### 6. Template Placeholder Check

Verify all placeholders are documented in manifest.json:

- [ ] {{ServerName}}
- [ ] {{ToolName}}
- [ ] {{ResourceName}}
- [ ] {{Description}}
- [ ] All placeholders used in templates are defined

### 7. Integration Test

Create a test project using the template:

```bash
# Create test directory
mkdir -p /tmp/mcp-template-test
cd /tmp/mcp-template-test

# Initialize with template
guardkit init mcp-typescript

# Verify structure
ls -la

# Install dependencies
npm install

# Run tests
npm test

# Run protocol tests
npm run test:protocol
```

## Acceptance Criteria

- [ ] All files exist in expected locations
- [ ] manifest.json and settings.json are valid JSON
- [ ] `/template-validate` passes all checks
- [ ] All 10 MCP patterns documented
- [ ] All agents have valid frontmatter
- [ ] All placeholders defined and documented
- [ ] Integration test creates working project
- [ ] Unit tests pass in generated project
- [ ] Protocol tests pass in generated project

## Validation Report

Document any issues found and their resolutions:

```markdown
## Validation Results

### Structural Validation
- [Pass/Fail] All required files present
- Issues: [None / List issues]

### JSON Validation
- [Pass/Fail] manifest.json valid
- [Pass/Fail] settings.json valid
- Issues: [None / List issues]

### Pattern Compliance
- [Pass/Fail] All 10 patterns documented
- Missing patterns: [None / List]

### Agent Quality
- [Pass/Fail] All agents meet standards
- Issues: [None / List issues]

### Integration Test
- [Pass/Fail] Project creates successfully
- [Pass/Fail] Tests pass
- Issues: [None / List issues]

## Overall Status: [PASS / FAIL]
```

## Post-Validation

After validation passes:

1. Update TASK-REV-4371 status to `completed`
2. Update fastmcp-python-template README to reference mcp-typescript
3. Add template to GuardKit documentation
4. Announce template availability

## Test Execution Log

[Automatically populated by /task-work]
