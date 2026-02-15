---
id: TASK-ACO-005
title: Add unit tests for prompt builders and auto-detection
task_type: testing
parent_review: TASK-REV-A781
feature_id: FEAT-ACO
wave: 3
implementation_mode: task-work
complexity: 4
dependencies:
  - TASK-ACO-002
  - TASK-ACO-003
  - TASK-ACO-004
status: pending
priority: high
---

# TASK-ACO-005: Unit Tests for Prompt Builders and Auto-Detection

## Objective

Create comprehensive unit tests for the new AutoBuild prompt builders and expanded direct mode auto-detection, ensuring correctness and preventing regression.

## Deliverables

### 1. `tests/unit/test_autobuild_prompt_builders.py`

Test the implementation prompt builder:
- Verify prompt contains task requirements section
- Verify prompt contains execution protocol (phases 3-5)
- Verify prompt contains PLAYER_REPORT_SCHEMA
- Verify prompt includes Coach feedback when available
- Verify prompt includes Graphiti context when available
- Verify prompt includes turn context (approaching_limit)
- Verify prompt respects documentation level constraints
- Verify prompt respects development mode (TDD/BDD/standard)

Test the design prompt builder:
- Verify prompt contains task requirements section
- Verify prompt contains design protocol (phases 1.5-2.8)
- Verify prompt encodes phase skipping (1.6, 2.1, 2.5A skipped)
- Verify prompt specifies lightweight 2.5B (no subagent)
- Verify prompt specifies auto-approve for 2.8
- Verify prompt includes complexity evaluation criteria
- Verify prompt includes architectural review criteria

### 2. `tests/unit/test_direct_mode_detection.py`

Test auto-detection logic:
- complexity 1, no risk keywords → "direct"
- complexity 2, no risk keywords → "direct"
- complexity 3, no risk keywords → "direct"
- complexity 3, title contains "security" → "task-work"
- complexity 3, title contains "auth" → "task-work"
- complexity 3, body contains "database migration" → "task-work"
- complexity 4, no risk keywords → "task-work"
- complexity 5 (default), no risk keywords → "task-work"
- complexity not set in frontmatter → "task-work" (default 5)
- explicit `implementation_mode: direct` → "direct" (overrides complexity)
- explicit `implementation_mode: task-work` → "task-work" (overrides auto-detect)

### 3. `tests/unit/test_sdk_session_config.py`

Test SDK session configuration:
- Verify `setting_sources=["project"]` for implementation sessions
- Verify `setting_sources=["project"]` for design sessions
- Verify interactive `/task-work` still uses `["user", "project"]` (no regression)

## Acceptance Criteria

- [ ] All prompt builder tests pass
- [ ] All auto-detection tests pass
- [ ] All SDK session config tests pass
- [ ] Tests cover edge cases (missing frontmatter, empty body, etc.)
- [ ] No mocking of the protocol file loading (test actual file reads)
- [ ] Tests verify no regression to interactive path

## Files Created

| File | Description |
|------|-------------|
| `tests/unit/test_autobuild_prompt_builders.py` | Prompt builder tests |
| `tests/unit/test_direct_mode_detection.py` | Auto-detection tests |
| `tests/unit/test_sdk_session_config.py` | SDK configuration tests |
