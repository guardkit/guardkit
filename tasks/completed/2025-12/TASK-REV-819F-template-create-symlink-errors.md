---
id: TASK-REV-819F
title: Analyze Template-Create Command Symlink and Module Import Errors
status: completed
task_type: review
created: 2025-12-10T19:50:00Z
updated: 2025-12-10T20:30:00Z
priority: high
tags: [template-create, symlinks, python-imports, debugging, blocking]
complexity: 6
review_mode: decision
review_depth: standard
review_results:
  mode: decision
  depth: standard
  findings_count: 3
  recommendations_count: 3
  decision: implement
  fix_applied: true
  fix_summary: "Updated lib symlink from installer/global/lib to installer/core/lib"
  report_path: .claude/reviews/TASK-REV-819F-review-report.md
  root_cause: "lib symlink at repo root points to non-existent installer/global/lib"
  fix_effort: low
  fix_risk: low
---

# Analyze Template-Create Command Symlink and Module Import Errors

## Problem Statement

The `/template-create` command fails with `ModuleNotFoundError: No module named 'lib'` when executed via the symlinked orchestrator script. This is a follow-up issue to TASK-REV-144B (install script path fix).

## Error Log

```
python3 ~/.agentecflow/bin/template-create-orchestrator --name mydrive 2>&1

Traceback (most recent call last):
  File "/Users/richardwoollcott/.agentecflow/bin/template-create-orchestrator", line 49, in <module>
    _codebase_analyzer_module = importlib.import_module('lib.codebase_analyzer.ai_analyzer')
  ...
ModuleNotFoundError: No module named 'lib'
```

## Context

The orchestrator script is a symlink:
```
~/.agentecflow/bin/template-create-orchestrator →
  /Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/core/commands/lib/template_create_orchestrator.py
```

The script attempts to resolve the repository root by navigating up 5 levels from the script's location:
```python
repo_root = script_path.parent.parent.parent.parent.parent
```

This path resolution is designed for direct execution but breaks when:
1. The script is executed via symlink (symlink path vs target path)
2. The `lib` module is in `installer/core/lib/` not at repo root

## Files to Investigate

1. **Command output log**: `/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/reviews/progressive-disclosure/template-create-output.md`
2. **Generated files**: `/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/reviews/progressive-disclosure/mydrive/`
3. **Orchestrator script**: `installer/core/commands/lib/template_create_orchestrator.py`
4. **Install script**: `installer/scripts/install.sh` (symlink creation logic)
5. **Lib structure**: `installer/core/lib/` directory

## Scope of Review

### 1. Symlink Resolution Issue
- Does `Path(__file__).resolve()` correctly resolve through symlinks?
- Is the 5-level parent navigation correct for the symlinked path?

### 2. PYTHONPATH Configuration
- Should install.sh set up PYTHONPATH for command execution?
- Is there a missing `lib` symlink at repo root?

### 3. Module Import Strategy
- Should imports use relative paths from script location?
- Should orchestrator detect symlink execution vs direct execution?

### 4. Review Generated Output
- Did the command eventually succeed (with workaround)?
- Are there additional errors in the template-create-output.md?
- Quality of generated files in mydrive/

## Acceptance Criteria

- [ ] Root cause of "No module named 'lib'" identified
- [ ] Determine if this is related to TASK-REV-144B (global→core rename)
- [ ] Identify all affected scripts (template-create-orchestrator and others)
- [ ] Document fix recommendations with specific code changes
- [ ] Verify fix doesn't break direct execution from repo

## Review Questions

1. Was this working before the global→core rename?
2. Does the install.sh create a `lib` symlink at repo root?
3. Should symlinked scripts use a different path resolution strategy?
4. Are there other orchestrator scripts with the same issue?

## Execution

```bash
/task-review TASK-REV-819F --mode=decision --depth=standard
```

## Related Tasks

- TASK-REV-144B: Install Script Path Fix (completed)
- TASK-RENAME-GLOBAL: Global to Core Rename (parent)
