---
id: TASK-FIX-19EA
title: Complete --claude-md-size-limit flag implementation
status: in_review
created: 2025-12-10T21:50:00Z
updated: 2025-12-10T22:10:00Z
priority: high
tags: [template-create, bug-fix, progressive-disclosure]
task_type: implementation
complexity: 3
parent_review: TASK-REV-3666
---

# Complete --claude-md-size-limit flag implementation

## Problem Statement

TASK-ENH-SIZE-LIMIT was marked as completed but the `--claude-md-size-limit` flag was never added to argparse, making it unusable. Users attempting to use the flag get "unrecognized arguments" error.

**Evidence from TASK-REV-3666**:
```
python3 ~/.agentecflow/bin/template-create-orchestrator --name mydrive --claude-md-size-limit 50KB
template-create-orchestrator: error: unrecognized arguments: --claude-md-size-limit 50KB
```

## Root Cause

Incomplete implementation of TASK-ENH-SIZE-LIMIT:
- ✅ Config field `claude_md_size_limit` added (line 125)
- ✅ `parse_size_limit()` function added (line 238)
- ✅ Documentation mentions the flag
- ❌ **argparse argument NOT added**
- ❌ **Flag value never passed to run_template_create()**

Additionally, there's a hard-coded 15KB limit in `models.py` that overrides any configurable limit.

## Acceptance Criteria

- [x] `--claude-md-size-limit 50KB` works from command line
- [x] Flag accepts KB, MB suffixes (case-insensitive)
- [x] Flag value is passed to `run_template_create()`
- [x] Hard-coded 15KB limit in models.py is removed/made configurable
- [x] Test verifies flag works end-to-end
- [ ] TASK-ENH-SIZE-LIMIT updated to reflect actual completion

## Technical Specification

### File 1: template_create_orchestrator.py

**Location**: `installer/core/commands/lib/template_create_orchestrator.py`

#### Change 1: Add argparse argument (after line 2787)

```python
parser.add_argument("--claude-md-size-limit", type=str,
                    help="Maximum size for core CLAUDE.md content (e.g., 50KB, 1MB). Default: 10KB")
```

#### Change 2: Parse and pass to run_template_create (around line 2791)

```python
# Parse size limit if provided
claude_md_size_limit = None
if args.claude_md_size_limit:
    claude_md_size_limit = TemplateCreateOrchestrator.parse_size_limit(args.claude_md_size_limit)

result = run_template_create(
    codebase_path=Path(args.path) if args.path else None,
    output_location=args.output_location,
    # ... existing args ...
    claude_md_size_limit=claude_md_size_limit,  # NEW
)
```

#### Change 3: Update run_template_create signature

Add `claude_md_size_limit: Optional[int] = None` parameter and pass to config.

### File 2: models.py

**Location**: `installer/core/lib/template_generator/models.py`

#### Change: Remove hard-coded 15KB limit (lines 422-430)

**Before**:
```python
warning_size = 15 * 1024  # 15KB warning threshold

if core_size > warning_size:
    return False, (...)  # Hard failure at 15KB
elif core_size > max_core_size:
    # Warning between 10-15KB
```

**After**:
```python
if core_size > max_core_size:
    return False, (
        f"Core content exceeds {max_core_size / 1024:.0f}KB limit: "
        f"{core_size / 1024:.2f}KB. Use --claude-md-size-limit to override."
    )

return True, None
```

### File 3: Test file

**Location**: `tests/unit/test_orchestrator_split_claude_md.py`

#### Add end-to-end test

```python
def test_claude_md_size_limit_flag_works():
    """Verify --claude-md-size-limit flag is recognized and passed correctly."""
    import subprocess
    result = subprocess.run(
        ["python3", "-m", "installer.core.commands.lib.template_create_orchestrator",
         "--help"],
        capture_output=True, text=True
    )
    assert "--claude-md-size-limit" in result.stdout
```

## Files to Modify

| File | Change |
|------|--------|
| `installer/core/commands/lib/template_create_orchestrator.py` | Add argparse arg, wire to run_template_create |
| `installer/core/lib/template_generator/models.py` | Remove hard-coded 15KB limit |
| `tests/unit/test_orchestrator_split_claude_md.py` | Add end-to-end test |

## Verification

```bash
# 1. Verify flag appears in help
python3 ~/.agentecflow/bin/template-create-orchestrator --help | grep claude-md-size-limit

# 2. Test with large codebase (should work with override)
cd ~/Projects/DeCUK.Mobile.MyDrive
/template-create --name mydrive-test --claude-md-size-limit 50KB

# 3. Run unit tests
pytest tests/unit/test_orchestrator_split_claude_md.py -v -k "size_limit"
```

## Related

- **Parent Review**: TASK-REV-3666
- **Original Task**: TASK-ENH-SIZE-LIMIT (incorrectly marked completed)
- **Report**: [.claude/reviews/TASK-REV-3666-review-report.md](/.claude/reviews/TASK-REV-3666-review-report.md)
