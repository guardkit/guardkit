# Review Report: TASK-A5D6

## Executive Summary

The `--sdk-timeout` CLI parameter **is being passed through correctly** from CLI → FeatureOrchestrator → AutoBuildOrchestrator → AgentInvoker. The evidence log confirms `sdk_timeout=1800s` arrived intact. The described "3600 → 1800" scenario cannot be reproduced from the provided evidence — the actual command used `--sdk-timeout 1800`.

However, the investigation uncovered a real edge-case bug in `_calculate_sdk_timeout()` override detection that could cause unexpected timeout inflation under specific conditions.

## Review Details

- **Mode**: Decision / Bug Investigation
- **Depth**: Standard
- **Duration**: ~30 minutes
- **Reviewer**: Manual code trace + log analysis

## Findings

### F1: Passthrough Chain is Correct (VERIFIED)

The full parameter flow was traced:

| Step | Component | Code Location | Behavior |
|------|-----------|---------------|----------|
| 1 | CLI `--sdk-timeout` | `autobuild.py:507-511` | `default=None`, validated 60-3600 |
| 2 | CLI passes to FeatureOrchestrator | `autobuild.py:631` | Raw `sdk_timeout` (None or int) |
| 3 | FeatureOrchestrator stores | `feature_orchestrator.py:287` | `self.sdk_timeout = sdk_timeout` |
| 4 | Per-task resolution | `feature_orchestrator.py:1438-1444` | CLI > task frontmatter > default 1200 |
| 5 | AutoBuildOrchestrator receives | `autobuild.py:936` | `sdk_timeout_seconds=self.sdk_timeout` |
| 6 | AgentInvoker receives | `agent_invoker.py:593` | `self.sdk_timeout_seconds = sdk_timeout_seconds` |

**Evidence**: Log lines 75, 80 both show `sdk_timeout=1800s` in AutoBuildOrchestrator init.

### F2: Evidence Contradicts Task Description (CLARIFIED)

The task states: *"Running with `--sdk-timeout 3600` still results in the SDK timing out at 1800s"*

The actual log (line 1) shows:
```
guardkit autobuild feature FEAT-AC1A --max-turns 30 --sdk-timeout 1800
```

The command used `1800`, not `3600`. The value `1800` was correctly propagated.

### F3: `_calculate_sdk_timeout()` Override Detection Bug (CONFIRMED)

**Location**: `agent_invoker.py:2142`

```python
if self.sdk_timeout_seconds != DEFAULT_SDK_TIMEOUT:
    return self.sdk_timeout_seconds  # CLI override
```

This value-comparison approach fails when:
- User explicitly passes `--sdk-timeout 1200` (same as `DEFAULT_SDK_TIMEOUT`)
- Dynamic calculation runs and inflates timeout by up to 3x (to 3600s)

**Severity**: Low-Medium. Only triggers when explicit value matches default (1200).

For the FEAT-AC1A run, `1800 != 1200` correctly short-circuited dynamic calculation, so this bug did not manifest.

### F4: No Task Frontmatter Overrides (VERIFIED)

FEAT-AC1A feature YAML has no `autobuild` config sections on any task. No `autobuild.sdk_timeout` frontmatter exists that could override CLI values.

### F5: Default Values Are Consistent (VERIFIED)

All code paths use `1200` as the default SDK timeout:
- CLI help text: 1200
- `FeatureOrchestrator._execute_task()` fallback: 1200
- `AutoBuildOrchestrator.__init__()`: 1200
- `AgentInvoker.DEFAULT_SDK_TIMEOUT`: 1200

## Recommendations

| # | Priority | Recommendation | Effort |
|---|----------|---------------|--------|
| R1 | Low | Fix `_calculate_sdk_timeout()` with sentinel pattern `_sdk_timeout_is_override` | 30 min |
| R2 | Info | If 3600→1800 scenario reproducible, capture new DEBUG log | N/A |
| R3 | Info | Consider whether dynamic timeout calculation should apply in feature orchestration path | Future |

## Acceptance Criteria Assessment

| AC | Status | Notes |
|----|--------|-------|
| AC-001 | Resolved | Evidence shows `--sdk-timeout 1800` was used, not 3600. Value arrived correctly. |
| AC-002 | Resolved | No issue found in CLI parsing, feature orchestrator, or autobuild orchestrator. |
| AC-003 | Verified | `feature` subcommand passes `sdk_timeout` correctly at `autobuild.py:631`. |
| AC-004 | Verified | No `autobuild.sdk_timeout` in FEAT-AC1A task frontmatter. |
| AC-005 | Documented | Fix for F3 documented in TASK-4223. |
| AC-006 | Verified | Tests exist in `test_agent_invoker.py::TestCalculateSDKTimeout`. |

## Implementation Task Created

**TASK-4223**: Fix `_calculate_sdk_timeout()` override detection using sentinel pattern
- Location: `tasks/backlog/TASK-4223-fix-sdk-timeout-override-detection.md`
- Scope: 2 lines in `agent_invoker.py` + test updates
- Complexity: 2

## Decision

Review findings accepted. Implementation task TASK-4223 created for the identified edge-case bug.
