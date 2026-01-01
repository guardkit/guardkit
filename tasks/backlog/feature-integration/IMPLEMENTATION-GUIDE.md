# Implementation Guide: Feature Integration (TWD + SEC)

## Wave Breakdown

### Wave 1: Integration Tasks (3-4 hours)

**Prerequisites**: TWD Waves 1-3 and SEC Waves 1-2 must be complete.

#### TASK-INT-001: Unified Coach Validation Flow
- **Method**: task-work
- **Parallel**: Yes (with INT-002)
- **Workspace**: `feature-integration-wave1-1`
- **Priority**: HIGH

Integrate security, honesty, and promise verification into single coherent validation flow.

#### TASK-INT-002: Integration Tests
- **Method**: task-work
- **Parallel**: Yes (with INT-001 - can start after INT-001 design is clear)
- **Workspace**: `feature-integration-wave1-2`
- **Priority**: MEDIUM

Create comprehensive tests for combined functionality.

---

## Execution Strategy

```
PREREQUISITES (must be complete before starting):
═══════════════════════════════════════════════════

TWD Feature                         SEC Feature
├── Wave 1 (TWD-001, TWD-002)      ├── Wave 1 (SEC-001, SEC-002)
├── Wave 2 (TWD-003, TWD-004)      └── Wave 2 (SEC-003, SEC-004)
└── Wave 3 (TWD-005, TWD-006)

INTEGRATION (this feature):
═══════════════════════════════════════════════════

Wave 1 (Parallel):
  INT-001 ─────┬───► Complete
  INT-002 ─────┘

OPTIONAL ENHANCEMENTS (after integration):
═══════════════════════════════════════════════════

TWD Feature (Quality Enhancements)
├── Wave 4 (TWD-007, TWD-008)
└── Wave 5 (TWD-009)

SEC Feature (Testing & Docs)
└── Wave 3 (SEC-005, SEC-006)
```

## Key Files Modified

| File | Owner | Changes |
|------|-------|---------|
| `guardkit/orchestrator/quality_gates/coach_validator.py` | INT-001 | Validation order integration |
| `.claude/agents/autobuild-coach.md` | INT-001 | Validation flow documentation |
| `tests/integration/test_coach_combined_validation.py` | INT-002 | New test file |
| `tests/fixtures/coach_validation_fixtures.py` | INT-002 | Test fixtures |

## Risk Mitigation

1. **Dependency Timing**: Don't start until TWD Waves 1-3 and SEC Waves 1-2 are merged
2. **Merge Conflicts**: Both tasks modify `coach_validator.py` - coordinate closely
3. **Test Coverage**: INT-002 should cover all integration paths before merging INT-001

## Success Criteria

1. Security checks run in correct order (before honesty)
2. All validation sections populated in decision JSON
3. Priority ordering applied for multiple issues
4. Existing TWD and SEC tests still pass
5. New integration tests pass
6. Both features work correctly together

## Conductor Workspace Names

| Task | Workspace |
|------|-----------|
| TASK-INT-001 | `feature-integration-wave1-1` |
| TASK-INT-002 | `feature-integration-wave1-2` |
