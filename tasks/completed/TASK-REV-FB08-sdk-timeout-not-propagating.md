---
id: TASK-REV-FB08
title: Analyze autobuild config not propagating (sdk_timeout + enable_pre_loop)
status: completed
created: 2026-01-11T21:30:00Z
updated: 2026-01-12T00:00:00Z
priority: critical
task_type: review
tags: [feature-build, sdk-timeout, enable-pre-loop, config-propagation, autobuild]
complexity: 7
review_mode: architectural
review_depth: comprehensive
review_decision: implement
review_report: .claude/reviews/TASK-REV-FB08-review-report.md
implementation_tasks:
  - TASK-FB-FIX-009
  - TASK-FB-FIX-010
  - TASK-FB-FIX-011
---

# Task: Analyze autobuild config not propagating (sdk_timeout + enable_pre_loop)

## Description

Following the FB07 fix which allowed the feature-build process to execute (24 SDK turns), the design phase is now timing out. **Two separate configuration bugs** have been identified:

1. **SDK Timeout Bug**: The `--sdk-timeout` CLI flag and YAML config are ignored; hardcoded 600s is always used
2. **Pre-Loop Flag Bug**: The `enable_pre_loop: false` setting in both feature YAML and task frontmatter is ignored

**Evidence from test output (5 failed attempts):**
- CLI invocation: `guardkit-py autobuild feature FEAT-3DEB --fresh --sdk-timeout 1800`
- Orchestrator log shows: `sdk_timeout=1200s` being received at CLI level
- BUT: Error shows `SDK timeout after 600s` - the hardcoded default
- AND: `enable_pre_loop=True` despite config saying `false`

## Key Observations

### Bug 1: SDK Timeout Not Propagating

**Expected Flow:**
```
CLI --sdk-timeout 1800 → FeatureOrchestrator → AutoBuildOrchestrator → PreLoopGates → TaskWorkInterface (1800s)
```

**Actual (Observed):**
```
CLI --sdk-timeout 1800 → FeatureOrchestrator → AutoBuildOrchestrator (1200s logged) → PreLoopGates → TaskWorkInterface (600s!!!)
```

### Bug 2: enable_pre_loop Flag Ignored

**Expected:**
```yaml
# Feature YAML
autobuild:
  enable_pre_loop: false  # Should skip pre-loop phase
```

**Actual Log:**
```
INFO:guardkit.orchestrator.autobuild:AutoBuildOrchestrator initialized:
  ... enable_pre_loop=True ...  # Config ignored!
```

### Log Evidence (Line References from fb_07_test.md)

**Line 194**: AutoBuildOrchestrator shows `enable_pre_loop=True` despite YAML config
```
INFO:guardkit.orchestrator.autobuild:AutoBuildOrchestrator initialized:
repo=..., max_turns=5, resume=False, enable_pre_loop=True, ...
```

**Line 209**: TaskWorkInterface uses 600s despite CLI flag
```
ERROR:guardkit.orchestrator.quality_gates.task_work_interface:SDK timeout after 600s
```

### Attempted Workarounds (All Failed - 5 Attempts)

| Attempt | Configuration | Result |
|---------|--------------|--------|
| 1 | `--sdk-timeout 1200` CLI flag | Ignored (600s used) |
| 2 | `--sdk-timeout 1800` CLI flag | Ignored (600s used) |
| 3 | Feature YAML `autobuild.sdk_timeout: 1800` | Ignored (600s used) |
| 4 | Feature YAML `autobuild.enable_pre_loop: false` | Ignored (True used) |
| 5 | Task frontmatter `autobuild.sdk_timeout: 1800` + `enable_pre_loop: false` | Ignored (both) |

## Scope of Analysis

### Primary Investigation - SDK Timeout

1. **Trace timeout propagation path:**
   - [guardkit/cli/autobuild.py](guardkit/cli/autobuild.py) - Where CLI flag is parsed
   - [guardkit/orchestrator/feature_orchestrator.py](guardkit/orchestrator/feature_orchestrator.py) - How it's passed to tasks
   - [guardkit/orchestrator/autobuild.py](guardkit/orchestrator/autobuild.py) - How it's passed to pre_loop
   - [guardkit/orchestrator/quality_gates/pre_loop.py](guardkit/orchestrator/quality_gates/pre_loop.py) - How it's passed to interface
   - [guardkit/orchestrator/quality_gates/task_work_interface.py](guardkit/orchestrator/quality_gates/task_work_interface.py) - Where timeout is used

2. **Identify the break point:**
   - Where does the 600s default override the CLI value?
   - Is TaskWorkInterface being instantiated with default timeout before CLI value is available?
   - Is there a second TaskWorkInterface instance being created?

### Primary Investigation - enable_pre_loop

3. **Trace pre_loop flag propagation:**
   - Where is `enable_pre_loop` read from feature YAML?
   - Where is it read from task frontmatter?
   - How is it passed to AutoBuildOrchestrator?

4. **Configuration cascade:**
   - What is the priority order? (CLI > task frontmatter > feature YAML > default)
   - Is the cascade implemented correctly?

### Secondary Investigation

5. **Default value locations:**
   - Where is 600s hardcoded for sdk_timeout?
   - Where is True hardcoded for enable_pre_loop?
   - Are there multiple sources of defaults?

6. **Test coverage gaps:**
   - Do existing tests verify config propagation?
   - Are there integration tests for CLI → Orchestrator → Interface?

## Suspect Code Locations

Based on the log evidence, these are likely locations of the bugs:

### sdk_timeout Bug (likely in pre_loop.py or task_work_interface.py)
```python
# SUSPECT: TaskWorkInterface may be instantiated with hardcoded default
self._interface = TaskWorkInterface(worktree_path, sdk_timeout_seconds=600)  # Not using passed value
```

### enable_pre_loop Bug (likely in autobuild.py or feature_orchestrator.py)
```python
# SUSPECT: Feature YAML autobuild config may not be parsed
# or may not be passed when creating AutoBuildOrchestrator
enable_pre_loop = True  # Hardcoded instead of reading from config
```

## Previous Reviews Context

| Review | Finding | Status |
|--------|---------|--------|
| FB01 | Architecture approved | ✅ |
| fb02 | Delegation disabled | Fixed |
| fb03 | CLI command missing | SDK approach |
| FB04 | Mock data returned | SDK integration |
| FB05 | Message parsing bug | ContentBlock fix |
| FB06 | setting_sources missing "user" | 24 turns now! |
| FB07 | Path resolution context | Fixed |
| **FB08** | **Config propagation (2 bugs)** | **This review** |

## Acceptance Criteria

- [ ] Root cause identified for sdk_timeout not propagating
- [ ] Root cause identified for enable_pre_loop being ignored
- [ ] Specific file and line number(s) for each bug
- [ ] Recommendation for fix (implementation task(s) if needed)
- [ ] Verify configuration cascade priority order
- [ ] Test gap analysis for config propagation

## Reference File

Test output: [docs/reviews/feature-build/fb_07_test.md](docs/reviews/feature-build/fb_07_test.md)

## Next Steps

```bash
/task-review TASK-REV-FB08 --mode=architectural --depth=comprehensive
```
