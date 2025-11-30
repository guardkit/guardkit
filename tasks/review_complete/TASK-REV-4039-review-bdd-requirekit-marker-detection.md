---
id: TASK-REV-4039
title: Review BDD mode RequireKit marker file detection
status: review_complete
created: 2025-11-30T12:03:33.885854Z
updated: 2025-11-30T12:08:24.474727Z
priority: high
tags: [bug, bdd-mode, requirekit, marker-file, review]
task_type: review
complexity: 5
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: decision
  depth: standard
  findings_count: 3
  recommendations: create_feature_detection_module
  decision: implement
  report_path: .claude/reviews/TASK-REV-4039-review-report.md
  implementation_task: TASK-BDD-F3EA
  completed_at: 2025-11-30T12:08:24.474919Z
---

# Task: Review BDD mode RequireKit marker file detection

## Description

**Issue**: BDD mode validation in `/task-work --mode=bdd` fails to detect RequireKit installation even when it is correctly installed and the marker file exists.

**Evidence from VM Testing**:

1. **RequireKit is installed and working**:
   - Marker file exists: `~/.agentecflow/require-kit.marker.json`
   - File verified with `ls -la ~/.agentecflow/`
   - RequireKit installation completed successfully
   - All RequireKit commands available

2. **BDD mode validation fails**:
   ```bash
   /task-work TASK-308E --mode=bdd
   
   🔍 Validating BDD mode requirements...
   
   ❌ ERROR: BDD mode requires RequireKit installation
   ```

3. **Validation code being tested** (from TASK-BDD-FIX1):
   ```python
   # Check for RequireKit installation
   home = Path.home()
   marker_paths = [
       home / ".agentecflow" / "require-kit.marker.json",  # New location
       home / "Projects" / "require-kit" / "require-kit.marker"  # Legacy location
   ]
   
   requirekit_installed = any(path.exists() for path in marker_paths)
   ```

**Root Cause Hypothesis**:
- Path resolution issue (home directory expansion)
- File permissions issue
- Path existence check not working as expected
- Code execution context differs from command specification

## Acceptance Criteria

- [ ] Identify why Path.exists() returns False when marker file exists
- [ ] Determine correct marker file detection approach
- [ ] Verify detection works across different environments (local, VM, Conductor)
- [ ] Document findings in review report
- [ ] Recommend fix for TASK-BDD-FIX1 if needed

## Review Focus Areas

1. **Path Resolution**: How does Path.home() resolve? Are there symlink or permission issues?
2. **File System Behavior**: Does Path.exists() work correctly for JSON files?
3. **Alternative Detection Methods**: Should we use os.path.exists() or feature_detection module?
4. **Code Execution Context**: Does the validation code execute in task-work.md as expected?

## Investigation Steps

1. Reproduce the issue on VM
2. Compare detection methods (Path vs os.path vs feature_detection)
3. Review RequireKit installer marker file creation
4. Test alternative implementations

## Expected Deliverables

1. Root Cause Analysis
2. Recommended Fix
3. Test Cases
4. Documentation Updates

## Related Tasks

- TASK-BDD-FIX1: Fix BDD mode validation (COMPLETED) - may need reopening

## Urgency

**Priority: HIGH** - Blocks BDD mode functionality entirely
