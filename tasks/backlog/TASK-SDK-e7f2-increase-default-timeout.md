---
id: TASK-SDK-e7f2
title: Increase default SDK timeout for feature-level orchestration
status: backlog
created: 2026-01-08T12:09:00Z
updated: 2026-01-08T12:09:00Z
priority: low
tags: [sdk-timeout, configuration, feature-build, defaults]
parent_task: TASK-REV-9AC5
complexity: 2
estimated_effort: 1-2 hours
review_recommendation: R5
related_findings: [Finding-1]
depends_on: [TASK-SDK-a7f3]
---

# Task: Increase default SDK timeout for feature-level orchestration

## Context

**From Review**: TASK-REV-9AC5 Recommendation R5 (LOW priority)

The default SDK timeout is 300s for both single tasks and multi-task features. Features inherently take longer due to:
- Multiple tasks executed sequentially
- Wave-based orchestration overhead
- More complex implementations

**Suggestion**: Different defaults for task vs feature level (300s vs 600s).

## Acceptance Criteria

- [ ] Add `DEFAULT_FEATURE_SDK_TIMEOUT` constant (600s)
- [ ] Feature commands use 600s default
- [ ] Task commands continue using 300s default
- [ ] Environment variable `GUARDKIT_FEATURE_SDK_TIMEOUT` supported
- [ ] Configuration cascade respects new defaults
- [ ] Update documentation with timeout guidance
- [ ] Add unit tests for default selection logic

## Implementation Notes

**File to Modify**:
- `guardkit/orchestrator/agent_invoker.py:44`

**Implementation**:
```python
# SDK timeout in seconds
DEFAULT_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_SDK_TIMEOUT", "300"))
DEFAULT_FEATURE_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_FEATURE_SDK_TIMEOUT", "600"))
```

**Usage** (in feature orchestrator):
```python
effective_timeout = (
    cli_sdk_timeout  # --sdk-timeout flag (highest priority)
    or feature.get("autobuild", {}).get("sdk_timeout")  # Feature YAML
    or DEFAULT_FEATURE_SDK_TIMEOUT  # 600s for features (new)
)
```

**Usage** (in task orchestrator):
```python
effective_timeout = (
    cli_sdk_timeout  # --sdk-timeout flag (highest priority)
    or task.get("autobuild", {}).get("sdk_timeout")  # Task frontmatter
    or DEFAULT_SDK_TIMEOUT  # 300s for single tasks (existing)
)
```

## Testing Strategy

**Unit Tests**:
```python
def test_feature_default_timeout_is_600():
    """Verify feature orchestrator uses 600s default."""
    orchestrator = FeatureOrchestrator(...)

    # No CLI flag, no frontmatter
    timeout = orchestrator._get_effective_timeout()

    assert timeout == 600


def test_task_default_timeout_is_300():
    """Verify task orchestrator uses 300s default."""
    orchestrator = AutoBuildOrchestrator(...)

    # No CLI flag, no frontmatter
    timeout = orchestrator._get_effective_timeout()

    assert timeout == 300


def test_env_var_overrides_default():
    """Verify environment variable works."""
    with patch.dict(os.environ, {"GUARDKIT_FEATURE_SDK_TIMEOUT": "900"}):
        orchestrator = FeatureOrchestrator(...)
        timeout = orchestrator._get_effective_timeout()

        assert timeout == 900
```

## Documentation Updates

**CLAUDE.md**:
```markdown
## SDK Timeout Defaults

- **Single tasks**: 300s (5 minutes)
- **Features**: 600s (10 minutes)

Override via:
1. CLI flag: `--sdk-timeout 900`
2. Frontmatter: `autobuild.sdk_timeout: 900`
3. Environment: `GUARDKIT_SDK_TIMEOUT=900` or `GUARDKIT_FEATURE_SDK_TIMEOUT=900`
```

## Dependencies

**TASK-SDK-a7f3** (R1): Should be completed first to establish timeout configuration infrastructure.

## Estimated Complexity: 2/10

**Breakdown**:
- Add constant: 1/10 (trivial)
- Update orchestrators: 1/10 (simple)
- Testing: 1/10 (straightforward)
- Documentation: 1/10 (simple)

## Priority Justification

**LOW**: This is a quality-of-life improvement. With R1 implemented, users can set `--sdk-timeout 600` for features. The different defaults are nice-to-have but not critical.

## Alternative Approaches

**Alternative 1**: Auto-detect timeout based on task count
```python
estimated_timeout = 300 + (task_count * 60)  # +60s per task
```

**Alternative 2**: Keep single default (300s), rely on R1 CLI flag

**Recommendation**: Keep it simple - two constants (300s/600s) as proposed in R5.

## References

- Review Report: `.claude/reviews/TASK-REV-9AC5-review-report.md`
- Recommendation R5: Lines 926-937
- Location: guardkit/orchestrator/agent_invoker.py:44
