# Review Report: TASK-REV-8BCC

## Executive Summary

The `'Feature' object has no attribute 'config'` error is caused by **uncommitted code** in [feature_orchestrator.py:888](guardkit/orchestrator/feature_orchestrator.py#L888) that attempts to access a non-existent `config` attribute on the `Feature` dataclass. This is a **bug introduced in recent uncommitted changes**, not a regression in committed code.

**Root Cause**: The SDK timeout resolution code was added but incorrectly assumed the `Feature` dataclass has a `config` attribute for storing feature-level configuration. The `Feature` dataclass does not have this attribute.

**Impact**: **Critical** - Feature builds fail immediately on first task execution.

**Fix Complexity**: **Low** - Single file fix, 3 lines of code.

## Review Details

- **Mode**: Code Quality Review
- **Depth**: Standard
- **Duration**: ~15 minutes
- **Files Analyzed**: 5

## Root Cause Analysis

### Where the Bug Is

**File**: [guardkit/orchestrator/feature_orchestrator.py:887-889](guardkit/orchestrator/feature_orchestrator.py#L887-L889)

```python
# Resolve SDK timeout: CLI > feature YAML > task frontmatter > default (300)
effective_sdk_timeout = self.sdk_timeout
if effective_sdk_timeout is None:
    # Try feature YAML autobuild.sdk_timeout
    feature_autobuild = feature.config.get("autobuild", {})  # BUG: Feature has no 'config' attribute
    effective_sdk_timeout = feature_autobuild.get("sdk_timeout")
```

### Why It Fails

The `Feature` dataclass in [feature_loader.py:242-283](guardkit/orchestrator/feature_loader.py#L242-L283) does not have a `config` attribute:

```python
@dataclass
class Feature:
    id: str
    name: str
    description: str
    created: str
    status: Literal["planned", "in_progress", "completed", "failed", "paused"]
    complexity: int
    estimated_tasks: int
    tasks: List[FeatureTask]
    orchestration: FeatureOrchestration
    execution: FeatureExecution = field(default_factory=FeatureExecution)
    file_path: Optional[Path] = None
    # NOTE: No 'config' attribute exists!
```

### When It Was Introduced

This bug exists in **uncommitted changes** (working directory modifications). The git diff shows:

```
git diff HEAD -- guardkit/orchestrator/feature_orchestrator.py
```

The code was added as part of the SDK timeout resolution feature but was not tested before the feature build was attempted.

## Impact Assessment

### Affected Code Paths

| Path | Status | Impact |
|------|--------|--------|
| `guardkit autobuild feature FEAT-XXX` | **BLOCKED** | All feature builds fail |
| `guardkit autobuild task TASK-XXX` | OK | Task builds unaffected |
| Unit tests | **INCOMPLETE** | No test coverage for this code path |

### Why Unit Tests Didn't Catch It

1. The test file [test_feature_orchestrator.py](tests/unit/test_feature_orchestrator.py) mocks `AutoBuildOrchestrator` entirely
2. The `_execute_task` method is not directly tested with real `Feature` objects
3. The SDK timeout resolution code was added without corresponding tests

## Fix Recommendations

### Option 1: Remove Feature YAML Config Layer (Recommended)

**Rationale**: The feature YAML does not currently have an `autobuild` section, and there's no generation code for it. Simplest fix is to remove this layer from the cascade.

**Before** (buggy):
```python
# Resolve SDK timeout: CLI > feature YAML > task frontmatter > default (300)
effective_sdk_timeout = self.sdk_timeout
if effective_sdk_timeout is None:
    # Try feature YAML autobuild.sdk_timeout
    feature_autobuild = feature.config.get("autobuild", {})  # BUG
    effective_sdk_timeout = feature_autobuild.get("sdk_timeout")
if effective_sdk_timeout is None:
    # Try task frontmatter autobuild.sdk_timeout
    task_autobuild = task_data.get("autobuild", {})
    effective_sdk_timeout = task_autobuild.get("sdk_timeout", 300)
```

**After** (fixed):
```python
# Resolve SDK timeout: CLI > task frontmatter > default (300)
effective_sdk_timeout = self.sdk_timeout
if effective_sdk_timeout is None:
    # Try task frontmatter autobuild.sdk_timeout
    task_autobuild = task_data.get("autobuild", {})
    effective_sdk_timeout = task_autobuild.get("sdk_timeout", 300)
```

**Pros**:
- Simple fix (remove 3 lines)
- No schema changes required
- Matches current capabilities

**Cons**:
- Removes documented feature (feature YAML config layer) - but it wasn't working anyway

### Option 2: Add `config` Attribute to Feature Dataclass

**Rationale**: If feature-level config is desired, add the attribute properly.

**Changes Required**:
1. Add `config: Dict[str, Any] = field(default_factory=dict)` to `Feature` dataclass
2. Update `FeatureLoader._parse_feature()` to populate `config` from YAML
3. Update `FeatureLoader._feature_to_dict()` to serialize `config`
4. Update `generate_feature_yaml.py` to support `autobuild` section

**Pros**:
- Enables feature-level configuration
- Matches CLAUDE.md documentation

**Cons**:
- More changes required
- Schema change affects all feature YAMLs
- Higher risk of regressions

### Recommendation

**Option 1 (Remove Feature YAML Config Layer)** is recommended because:
1. It's the minimal fix
2. Feature YAML config is not currently used anywhere
3. Task frontmatter already provides per-task SDK timeout
4. Documentation can be updated to reflect CLI > task > default cascade

## Test Case to Prevent Regression

Add to `tests/unit/test_feature_orchestrator.py`:

```python
def test_execute_task_resolves_sdk_timeout(temp_repo, sample_feature, mock_worktree_manager, mock_worktree):
    """Test that _execute_task correctly resolves SDK timeout without accessing feature.config."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
        sdk_timeout=None,  # Force resolution cascade
    )

    # Create minimal task file
    task = sample_feature.tasks[0]
    task_file = temp_repo / task.file_path
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text("""---
id: TASK-T-001
title: Test Task
status: pending
autobuild:
  sdk_timeout: 600
---

# Test Task
Requirements here.
""")

    # Mock AutoBuildOrchestrator to capture sdk_timeout
    with patch("guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator") as mock_orch_class:
        mock_orch = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.total_turns = 1
        mock_result.final_decision = "approved"
        mock_result.error = None
        mock_orch.orchestrate.return_value = mock_result
        mock_orch_class.return_value = mock_orch

        result = orchestrator._execute_task(task, sample_feature, mock_worktree)

        # Verify sdk_timeout was passed from task frontmatter
        call_kwargs = mock_orch_class.call_args[1]
        assert call_kwargs.get("sdk_timeout") == 600
```

## Documentation Updates

Update CLAUDE.md SDK Timeout Configuration Cascade from:

```markdown
**Configuration Cascade** (highest priority first):
1. CLI flag: `--sdk-timeout 600`
2. Task frontmatter: `autobuild.sdk_timeout: 600`
3. Feature YAML: `autobuild.sdk_timeout: 600` (feature command only)
4. Default: 300 seconds
```

To:

```markdown
**Configuration Cascade** (highest priority first):
1. CLI flag: `--sdk-timeout 600`
2. Task frontmatter: `autobuild.sdk_timeout: 600`
3. Default: 300 seconds
```

## Files Changed Summary

| File | Change | Risk |
|------|--------|------|
| `guardkit/orchestrator/feature_orchestrator.py` | Remove 3 lines | Low |
| `CLAUDE.md` | Update documentation | Low |
| `tests/unit/test_feature_orchestrator.py` | Add regression test | Low |

## Acceptance Criteria Status

- [x] Root cause identified with specific file:line reference
- [x] Regression source identified (uncommitted changes, not in any commit)
- [x] Impact on other features assessed
- [x] Fix recommendation with code example provided
- [x] Test case to prevent regression defined

## Next Steps

1. **[I]mplement** - Create implementation task to apply Option 1 fix
2. **[A]ccept** - Accept findings and close review
3. **[R]evise** - Request additional analysis
4. **[C]ancel** - Discard review
