# Implementation Guide: FEAT-DMCP

## Execution Strategy

### Wave 1: 3 tasks (parallel)

All three fixes are independent and can be implemented simultaneously.

**TASK-FIX-DMCP-001**: `guardkit/orchestrator/agent_invoker.py`
- Method: `_write_direct_mode_results` (~line 2855)
- Add `requirements_addressed` and `requirements_met` to results dict

**TASK-FIX-DMCP-002**: `guardkit/orchestrator/quality_gates/coach_validator.py`
- Method: `_validate_requirements` (~line 1578)
- Change text matching to check both field names

**TASK-FIX-DMCP-003**: `guardkit/orchestrator/agent_invoker.py`
- Method: `_write_player_report_for_direct_mode` (~line 2937)
- Add `_synthetic` flag propagation

### Wave 2: 1 task (sequential)

**TASK-FIX-DMCP-004**: `guardkit/orchestrator/agent_invoker.py`
- Synthetic report creation block (~line 2662-2670)
- Use full spec parser instead of YAML-only frontmatter parser
- Depends on DMCP-003 (synthetic flag must be propagated for full benefit)

## Testing Strategy

### Unit Tests
- Verify `task_work_results.json` contains `requirements_addressed` after `_write_direct_mode_results`
- Verify Coach text matching finds requirements under `requirements_addressed` field name
- Verify `_synthetic` flag survives write/load round-trip
- Verify synthetic reports have file-existence promises when acceptance criteria available

### Integration Verification
- Resume preserved worktree: `guardkit autobuild feature FEAT-3CC2 --resume`
- Verify Turn 1 would now approve (7/7 criteria met)
