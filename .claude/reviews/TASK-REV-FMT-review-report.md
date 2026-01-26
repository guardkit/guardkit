# Review Report: TASK-REV-FMT

## Executive Summary

**Task**: Analyze MCP Template Feature-Build Attempts (FEAT-FMT & FEAT-4048)
**Review Mode**: Technical Debt
**Review Depth**: Standard
**Duration**: ~30 minutes
**Date**: 2026-01-26

**Root Cause**: All 8 FEAT-FMT tasks use `task_type: implementation`, which is NOT a valid TaskType enum value. The CoachValidator correctly rejects this, causing all tasks to fail validation.

**Impact Assessment**:
- **FEAT-FMT**: 8/8 tasks affected, build FAILED after ~15 minutes
- **FEAT-4048**: 0/11 tasks affected - uses correct task_type values

**Salvageable Work**: Both `manifest.json` and `settings.json` were successfully created and appear complete. Tests were also created in the worktree.

---

## 1. Root Cause Analysis

### 1.1 The Problem

The CoachValidator at [guardkit/orchestrator/quality_gates/coach_validator.py](guardkit/orchestrator/quality_gates/coach_validator.py) uses the `TaskType` enum from [guardkit/models/task_types.py](guardkit/models/task_types.py) to determine quality gate profiles.

**Valid TaskType values** (lines 41-46):
```python
class TaskType(Enum):
    SCAFFOLDING = "scaffolding"
    FEATURE = "feature"
    INFRASTRUCTURE = "infrastructure"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    REFACTOR = "refactor"
```

**FEAT-FMT tasks use**: `task_type: implementation` (INVALID)

### 1.2 Where the Error Originated

- **Commit**: `ba031885` (2026-01-24)
- **Message**: "Complete TASK-REV-A7F3: MCP template consistency review"
- **Author**: Manual creation during review completion

The `TaskType` enum already existed before this commit with the correct 6 values. The person creating the tasks manually used `implementation` which was never a valid value - it's a semantic description, not an enum value.

### 1.3 Why FEAT-4048 Succeeded

The FEAT-4048 (TypeScript MCP Template) tasks were created with correct values:

| Task | task_type | Valid? |
|------|-----------|--------|
| TASK-MTS-001 | scaffolding | ✅ |
| TASK-MTS-002 | scaffolding | ✅ |
| TASK-MTS-003 | feature | ✅ |
| TASK-MTS-004 | feature | ✅ |
| TASK-MTS-005 | feature | ✅ |
| TASK-MTS-006 | scaffolding | ✅ |
| TASK-MTS-007 | feature | ✅ |
| TASK-MTS-008 | documentation | ✅ |
| TASK-MTS-009 | testing | ✅ |
| TASK-MTS-010 | documentation | ✅ |
| TASK-MTS-011 | testing | ✅ |

This confirms the `task_type` validation system works correctly - FEAT-4048 should build successfully.

---

## 2. Worktree Assessment

### 2.1 Location
`.guardkit/worktrees/FEAT-FMT/`

### 2.2 Files Created

Despite the validation failures, the Player agent successfully created:

**Template Files (SALVAGEABLE)**:
- `installer/core/templates/fastmcp-python/manifest.json` (78 lines, 2.6KB)
- `installer/core/templates/fastmcp-python/settings.json` (115 lines, 4.1KB)

**Test Files (SALVAGEABLE)**:
- `tests/templates/test_fastmcp_python_manifest.py` (275 lines)
- `tests/templates/test_fastmcp_python_settings.py` (390 lines)

**AutoBuild Artifacts**:
- `.guardkit/autobuild/TASK-FMT-001/` (5 player turns, 5 coach turns)
- `.guardkit/autobuild/TASK-FMT-002/` (5 player turns, 5 coach turns)
- Implementation plans for both tasks

### 2.3 Quality Assessment

The created files appear complete and high-quality:

**manifest.json**:
- ✅ schema_version: "1.0.0"
- ✅ All required fields populated
- ✅ 10 patterns documented
- ✅ 4 frameworks listed
- ✅ Placeholders defined
- ✅ Quality scores specified

**settings.json**:
- ✅ Naming conventions complete
- ✅ MCP-specific settings (stdout_reserved, stderr logging)
- ✅ Layer mappings defined
- ✅ Testing configuration complete

---

## 3. Gap Analysis

### 3.1 Documentation Gap

The `task_type` field requirements are documented in:
- [installer/core/commands/feature-plan.md](installer/core/commands/feature-plan.md#L945-L976) (lines 945-976)

However, this documentation was added AFTER the FEAT-FMT tasks were created. The original TASK-REV-A7F3 review didn't have access to this guidance.

### 3.2 Semantic vs Enum Mismatch

The word "implementation" makes semantic sense for describing a task's purpose, but it's not a valid enum value. The enum uses more specific terms:
- `feature` → General implementation tasks
- `scaffolding` → Setup/configuration tasks
- `documentation` → Docs tasks
- `testing` → Test-related tasks

### 3.3 Missing Validation at Creation Time

There's no validation when tasks are created to ensure `task_type` uses a valid enum value. The validation only happens at Coach validation time during AutoBuild.

---

## 4. Recommendations

### 4.1 Immediate Fix: Batch Update FEAT-FMT Tasks

Fix all 8 FEAT-FMT tasks with correct `task_type` values:

| Task | Current | Recommended | Rationale |
|------|---------|-------------|-----------|
| TASK-FMT-001 | implementation | scaffolding | Creates manifest.json template config |
| TASK-FMT-002 | implementation | scaffolding | Creates settings.json template config |
| TASK-FMT-003 | implementation | documentation | Creates specialist agent (markdown) |
| TASK-FMT-004 | implementation | documentation | Creates testing specialist agent (markdown) |
| TASK-FMT-005 | implementation | scaffolding | Creates code templates |
| TASK-FMT-006 | implementation | documentation | Creates .claude/rules (markdown) |
| TASK-FMT-007 | implementation | documentation | Creates CLAUDE.md files |
| TASK-FMT-008 | implementation | testing | Validates template |

### 4.2 Resume Strategy

**Option A: Resume Build (Recommended)**
1. Fix task_type values in all 8 tasks
2. Resume FEAT-FMT build with `--resume` flag
3. Worktree already has Wave 1 work complete

**Option B: Fresh Start**
1. Archive worktree work to main branch first
2. Fix task_type values
3. Start fresh build

**Recommendation**: Option A - the worktree has valid work that shouldn't be discarded.

### 4.3 Systemic Improvements

1. **Add task_type validation to task-create**: Validate enum values at task creation time, not just at Coach validation time.

2. **Update feature-plan documentation**: Emphasize that `task_type` must use exact enum values, not semantic descriptions.

3. **Add enum value hints**: When CoachValidator rejects a task_type, show the list of valid values in the error message (already implemented at [coach_validator.py:330](guardkit/orchestrator/quality_gates/coach_validator.py#L330)).

---

## 5. Files Requiring Changes

### 5.1 FEAT-FMT Tasks (8 files)

```
tasks/backlog/fastmcp-python-template/TASK-FMT-001-create-manifest-json.md
tasks/backlog/fastmcp-python-template/TASK-FMT-002-create-settings-json.md
tasks/backlog/fastmcp-python-template/TASK-FMT-003-create-fastmcp-specialist-agent.md
tasks/backlog/fastmcp-python-template/TASK-FMT-004-create-fastmcp-testing-specialist-agent.md
tasks/backlog/fastmcp-python-template/TASK-FMT-005-create-code-templates.md
tasks/backlog/fastmcp-python-template/TASK-FMT-006-create-claude-rules.md
tasks/backlog/fastmcp-python-template/TASK-FMT-007-create-claude-md-files.md
tasks/backlog/fastmcp-python-template/TASK-FMT-008-validate-template.md
```

### 5.2 No Changes Needed for FEAT-4048

All FEAT-4048 tasks already use valid `task_type` values.

---

## 6. Decision Options

| Option | Description | Effort | Risk |
|--------|-------------|--------|------|
| **[A] Accept** | Document findings, no implementation | Low | None |
| **[I] Implement** | Fix task_type values and resume build | Medium | Low |
| **[R] Revise** | Request deeper analysis | Low | None |
| **[C] Cancel** | Discard review | Low | None |

**Recommended**: **[I] Implement** - The fix is straightforward (8 sed commands) and the worktree work can be salvaged.

---

## Appendix A: Validation Error Details

From the build log:

```
INFO:guardkit.orchestrator.agent_invoker:Invalid task_type value: implementation.
Must be one of: scaffolding, feature, infrastructure, documentation, testing, refactor
```

This error occurred on every turn for both TASK-FMT-001 and TASK-FMT-002.

## Appendix B: Worktree Git Diff Summary

```
46 files changed, 2640 insertions(+), 175 deletions(-)
```

Key additions:
- `manifest.json`: 78 lines
- `settings.json`: 115 lines
- `test_fastmcp_python_manifest.py`: 275 lines
- `test_fastmcp_python_settings.py`: 390 lines
- Task plans and coach/player turn artifacts
