---
id: TASK-BRF-005
title: Add Ablation Mode for Testing
status: backlog
task_type: implementation
created: 2026-01-24T16:30:00Z
updated: 2026-01-24T16:30:00Z
priority: low
tags: [autobuild, testing, ablation, block-research, validation]
complexity: 4
parent_review: TASK-REV-BLOC
feature_id: FEAT-BRF
wave: 3
implementation_mode: task-work
conductor_workspace: block-research-fidelity-wave3-1
dependencies: [TASK-BRF-001, TASK-BRF-002]
---

# Task: Add Ablation Mode for Testing

## Description

Add an ablation testing mode (`--ablation` or `--no-coach`) that demonstrates the system is non-functional without Coach feedback, validating the Block research finding about adversarial cooperation necessity.

**Problem**: Block research includes ablation studies showing the system is non-functional without coach feedback. GuardKit lacks a way to validate this finding.

**Solution**: Add an ablation mode that runs Player-only (no Coach) for comparison testing.

## Acceptance Criteria

- [ ] AC-001: Add `--ablation` CLI flag that disables Coach validation loop
- [ ] AC-002: In ablation mode, Player runs but receives no feedback between turns
- [ ] AC-003: Ablation mode auto-approves after each turn (simulating no-coach scenario)
- [ ] AC-004: Add warning banner when ablation mode is active
- [ ] AC-005: Track and report ablation vs normal mode metrics for comparison
- [ ] AC-006: Document ablation mode purpose and usage in workflow guide
- [ ] AC-007: Integration tests comparing ablation vs normal mode outcomes

## Technical Approach

### CLI Flag

```python
# guardkit/cli/autobuild.py
@click.option(
    "--ablation",
    is_flag=True,
    default=False,
    help="Run in ablation mode (no Coach feedback) for testing Block research findings",
)
```

### Orchestrator Changes

```python
# guardkit/orchestrator/autobuild.py
class AutoBuildOrchestrator:
    def __init__(self, ..., ablation_mode: bool = False):
        self.ablation_mode = ablation_mode
        if ablation_mode:
            logger.warning(
                "⚠️ ABLATION MODE ACTIVE - Coach feedback disabled. "
                "This mode is for testing only and will produce inferior results."
            )

    def _execute_turn(self, ...):
        # ... Player phase unchanged ...

        if self.ablation_mode:
            # Skip Coach, auto-approve
            self._progress_display.complete_turn(
                "warning",
                "[ABLATION] Skipping Coach validation - auto-approving",
            )
            return TurnRecord(
                turn=turn,
                player_result=player_result,
                coach_result=None,
                decision="approve",  # Auto-approve in ablation mode
                feedback=None,
                timestamp=timestamp,
            )

        # ... normal Coach phase ...
```

### Ablation Metrics

```python
@dataclass
class AblationMetrics:
    mode: str  # "ablation" or "normal"
    total_turns: int
    final_decision: str
    tests_passed_final: bool
    code_quality_score: Optional[int]
    implementation_time_seconds: float
```

### Expected Findings

When running ablation mode, we expect:
1. **Higher failure rate** - Player without feedback will make more mistakes
2. **Lower code quality** - No architectural review feedback
3. **More turns needed** - No guidance toward convergence
4. **Lower test coverage** - No Coach enforcing coverage

These findings validate Block research conclusions.

## Related Files

- `guardkit/cli/autobuild.py` - CLI flag
- `guardkit/orchestrator/autobuild.py` - Ablation logic
- `tests/integration/test_ablation_mode.py` - Comparison tests
- `docs/guides/autobuild-workflow.md` - Documentation

## Notes

Nice-to-have feature for validating Block research findings. Lower priority than the critical gap fixes.
