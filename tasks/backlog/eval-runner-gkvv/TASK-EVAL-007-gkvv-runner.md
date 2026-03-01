---
id: TASK-EVAL-007
title: Implement GuardKitVsVanillaRunner orchestration
task_type: feature
parent_review: TASK-REV-EAE8
feature_id: FEAT-GKVV
status: in_review
created: 2026-03-01 00:00:00+00:00
priority: high
tags:
- eval-runner
- runner
- orchestration
- comparison
complexity: 6
wave: 3
implementation_mode: task-work
dependencies:
- TASK-EVAL-002
- TASK-EVAL-003
- TASK-EVAL-004
- TASK-EVAL-005
- TASK-EVAL-006
consumer_context:
- task: TASK-EVAL-001
  consumes: EvalBrief
  framework: Pydantic v2 BaseModel
  driver: pydantic
  format_note: GuardKitVsVanillaBrief subclass with input, guardkit_arm, vanilla_arm
    fields
- task: TASK-EVAL-002
  consumes: ForkedWorkspace
  framework: EvalWorkspace.create_forked_pair()
  driver: tempfile + shutil
  format_note: "Returns tuple[ForkedWorkspace, ForkedWorkspace] \u2014 independent\
    \ temp directories"
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-4296
  base_branch: main
  started_at: '2026-03-01T15:08:12.363294'
  last_updated: '2026-03-01T15:24:01.232842'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-03-01T15:08:12.363294'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Implement GuardKitVsVanillaRunner Orchestration

## Description

Implement the main comparison runner that orchestrates the full guardkit_vs_vanilla eval flow: resolve input, provision forked workspaces, run both arms sequentially, extract metrics, and return results for judging.

## Acceptance Criteria

- [ ] `GuardKitVsVanillaRunner.run(brief) -> EvalResult` orchestrates the full comparison
- [ ] Input resolved via `InputResolver` and written to both workspaces as `input.txt`
- [ ] Workspaces provisioned via `EvalWorkspace.create_forked_pair()`
- [ ] Arm A (GuardKit) runs FIRST with GuardKit-specific agent instructions
- [ ] Arm A completes before Arm B starts (sequential execution)
- [ ] Arm B (Vanilla) runs with vanilla agent instructions (no GuardKit commands)
- [ ] Status published between arms: `arm_a_complete`, `arm_b_running` (stdout for CLI mode)
- [ ] Arm A failure recorded but does NOT abort Arm B execution
- [ ] Metrics extracted via `MetricsExtractor` after both arms complete
- [ ] Judge invoked via `EvalJudge.evaluate_comparison()` with trajectories and metrics
- [ ] Post-run inspection: vanilla workspace checked for any GuardKit config created during run
- [ ] Workspace teardown after eval completion
- [ ] Integration tests covering end-to-end flow with mocked agent invocations

## Technical Context

- Location: `guardkit/eval/runners/gkvv_runner.py` (new module)
- Prototype reference: `docs/research/eval-runner/guardkit_vs_vanilla_runner.py`
- Design reference: `docs/research/eval-runner/eval-runner-guardkit-vs-vanilla.md` (Section 5)
- Agent instructions: `docs/research/eval-runner/eval-runner-guardkit-vs-vanilla.md` (Section 6)
- Orchestrator patterns: `.claude/rules/patterns/orchestrators.md`

## BDD Scenario Coverage

- Key example: End-to-end eval with text input
- Key example: Arms execute sequentially with status updates
- Edge case: GuardKit arm failure does not abort vanilla arm
- Edge case: Vanilla workspace checked for GuardKit config after run
- Edge case: Partial GuardKit pipeline still provides comparison data
- Negative: Both arms failing still produces comparison result

## Seam Tests

The following seam tests validate the integration contracts with producer tasks.

```python
"""Seam test: verify EvalBrief contract from TASK-EVAL-001."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("EvalBrief")
def test_eval_brief_format():
    """Verify EvalBrief matches expected format.

    Contract: GuardKitVsVanillaBrief subclass with input, guardkit_arm, vanilla_arm fields
    Producer: TASK-EVAL-001
    """
    from guardkit.eval.schemas import GuardKitVsVanillaBrief

    brief = GuardKitVsVanillaBrief.from_yaml("path/to/brief.yaml")
    assert hasattr(brief, 'input'), "Brief must have input field"
    assert hasattr(brief, 'guardkit_arm'), "Brief must have guardkit_arm field"
    assert hasattr(brief, 'vanilla_arm'), "Brief must have vanilla_arm field"


@pytest.mark.seam
@pytest.mark.integration_contract("ForkedWorkspace")
def test_forked_workspace_format():
    """Verify ForkedWorkspace matches expected format.

    Contract: Returns tuple[ForkedWorkspace, ForkedWorkspace] - independent temp directories
    Producer: TASK-EVAL-002
    """
    from guardkit.eval.workspace import ForkedWorkspace

    # Verify ForkedWorkspace has write_input method
    assert hasattr(ForkedWorkspace, 'write_input'), "ForkedWorkspace must have write_input method"
```

## Implementation Notes

[Space for implementation details]

## Test Execution Log

[Automatically populated by /task-work]
