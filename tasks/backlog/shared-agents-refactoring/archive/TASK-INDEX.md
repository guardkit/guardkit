# Shared Agents Refactoring - Task Index

**Based on**: TASK-ARCH-DC05 Architectural Review (Score: 82/100)
**Total Tasks**: 38 tasks across 6 phases
**Estimated Duration**: 7 days (with parallel execution)
**Status**: Tasks created, ready for execution

---

## Phase 0: Prerequisites (Critical - Must Complete First)

**Duration**: 2 days
**Status**: 5 tasks created ✅

| Task ID | Title | Priority | Effort | Status |
|---------|-------|----------|--------|--------|
| TASK-SHA-000 | Verify agent duplication | Critical | 2h | ✅ Created |
| TASK-SHA-001 | Implement conflict detection | Critical | 4h | ✅ Created |
| TASK-SHA-002 | Define integration test cases | Critical | 4h | ✅ Created |
| TASK-SHA-003 | Document rollback procedures | Critical | 3h | ✅ Created |
| TASK-SHA-004 | Add checksum validation | High | 2h | ✅ Created |

**Phase Gate**: All Phase 0 tasks must complete before Phase 1

---

## Phase 1: Create Shared Agents Repository

**Duration**: 1 day
**Dependencies**: Phase 0 complete
**Status**: 5 tasks to be created

| Task ID | Title | Priority | Effort | Status |
|---------|-------|----------|--------|--------|
| TASK-SHA-P1-001 | Create repository structure | High | 1h | 📋 Planned |
| TASK-SHA-P1-002 | Migrate universal agents | High | 1h | 📋 Planned |
| TASK-SHA-P1-003 | Create manifest file | High | 1h | 📋 Planned |
| TASK-SHA-P1-004 | Set up GitHub Actions | High | 2h | 📋 Planned |
| TASK-SHA-P1-005 | Create v1.0.0 release | High | 1h | 📋 Planned |

---

## Phase 2: Update GuardKit

**Duration**: 2 days
**Dependencies**: Phase 1 complete
**Can run in parallel**: Yes (with Phase 3)
**Status**: 7 tasks to be created

| Task ID | Title | Priority | Effort | Status |
|---------|-------|----------|--------|--------|
| TASK-SHA-P2-001 | Add version pinning file | High | 0.5h | 📋 Planned |
| TASK-SHA-P2-002 | Update installer script | Critical | 4h | 📋 Planned |
| TASK-SHA-P2-003 | Create fallback agents directory | Medium | 1h | 📋 Planned |
| TASK-SHA-P2-004 | Remove duplicate agents | High | 1h | 📋 Planned |
| TASK-SHA-P2-005 | Update agent discovery | High | 3h | 📋 Planned |
| TASK-SHA-P2-006 | Update documentation | Medium | 2h | 📋 Planned |
| TASK-SHA-P2-007 | Test GuardKit standalone | Critical | 2h | 📋 Planned |

---

## Phase 3: Update RequireKit

**Duration**: 2 days (parallel with Phase 2)
**Dependencies**: Phase 1 complete
**Can run in parallel**: Yes (with Phase 2)
**Status**: 7 tasks to be created

| Task ID | Title | Priority | Effort | Status |
|---------|-------|----------|--------|--------|
| TASK-SHA-P3-001 | Add version pinning file (RequireKit) | High | 0.5h | 📋 Planned |
| TASK-SHA-P3-002 | Update installer script (RequireKit) | Critical | 4h | 📋 Planned |
| TASK-SHA-P3-003 | Create fallback agents directory (RequireKit) | Medium | 1h | 📋 Planned |
| TASK-SHA-P3-004 | Remove duplicate agents (RequireKit) | High | 1h | 📋 Planned |
| TASK-SHA-P3-005 | Update agent discovery (RequireKit) | High | 3h | 📋 Planned |
| TASK-SHA-P3-006 | Update documentation (RequireKit) | Medium | 2h | 📋 Planned |
| TASK-SHA-P3-007 | Test RequireKit standalone | Critical | 2h | 📋 Planned |

---

## Phase 4: Integration Testing

**Duration**: 2 days
**Dependencies**: Phase 2 AND Phase 3 complete
**Status**: 7 tasks to be created

| Task ID | Title | Priority | Effort | Status |
|---------|-------|----------|--------|--------|
| TASK-SHA-P4-001 | Combined installation testing | Critical | 3h | 📋 Planned |
| TASK-SHA-P4-002 | Version pinning testing | High | 2h | 📋 Planned |
| TASK-SHA-P4-003 | Offline fallback testing | Medium | 1h | 📋 Planned |
| TASK-SHA-P4-004 | Conflict detection testing | Critical | 2h | 📋 Planned |
| TASK-SHA-P4-005 | Rollback testing | Critical | 2h | 📋 Planned |
| TASK-SHA-P4-006 | CI/CD pipeline testing | High | 3h | 📋 Planned |
| TASK-SHA-P4-007 | Agent discovery testing | High | 2h | 📋 Planned |

---

## Phase 5: Documentation & Release

**Duration**: 2 days
**Dependencies**: Phase 4 complete
**Status**: 7 tasks to be created

| Task ID | Title | Priority | Effort | Status |
|---------|-------|----------|--------|--------|
| TASK-SHA-P5-001 | Update README files | Medium | 2h | 📋 Planned |
| TASK-SHA-P5-002 | Create migration guide | High | 3h | 📋 Planned |
| TASK-SHA-P5-003 | Update CHANGELOG | Medium | 1h | 📋 Planned |
| TASK-SHA-P5-004 | Create release announcements | Medium | 2h | 📋 Planned |
| TASK-SHA-P5-005 | Tag and release GuardKit | High | 1h | 📋 Planned |
| TASK-SHA-P5-006 | Tag and release RequireKit | High | 1h | 📋 Planned |
| TASK-SHA-P5-007 | Announce to users | Low | 1h | 📋 Planned |

---

## Task Execution Strategy

### Recommended Approach

1. **Start with Phase 0** (all 5 tasks sequentially)
   - TASK-SHA-000: Verify duplication first
   - TASK-SHA-001-004: Can run in parallel after verification

2. **Phase 1** (sequential, depends on Phase 0 results)
   - Use verified agent list from TASK-SHA-000

3. **Phase 2 + Phase 3** (parallel execution)
   - Assign to different team members
   - Same implementation patterns
   - Reduces calendar time by 2 days

4. **Phase 4** (sequential, comprehensive testing)
   - Critical quality gate
   - Must pass before Phase 5

5. **Phase 5** (partially parallel)
   - Documentation can be written in parallel
   - Releases must be sequential

### Using Task Commands

```bash
# Start Phase 0
/task-work TASK-SHA-000  # Verify duplication FIRST
/task-work TASK-SHA-001  # Conflict detection
/task-work TASK-SHA-002  # Test cases
/task-work TASK-SHA-003  # Rollback procedures
/task-work TASK-SHA-004  # Checksum validation

# After Phase 0 complete, start Phase 1
/task-work TASK-SHA-P1-001
# ... and so on
```

---

## Critical Path

**Critical path tasks** (must complete on schedule):

1. **Phase 0**: All tasks (2 days) - blocks everything
2. **Phase 1**: All tasks (1 day) - blocks Phases 2-5
3. **Phase 2/3**: P2-002, P2-007, P3-002, P3-007 (installer + testing)
4. **Phase 4**: All tasks (2 days) - quality gate
5. **Phase 5**: P5-005, P5-006 (releases)

**Total Critical Path**: 7 days

---

## Risk-Adjusted Timeline

| Phase | Estimated | Buffer | Total |
|-------|-----------|--------|-------|
| Phase 0 | 2 days | 0.5 days | 2.5 days |
| Phase 1 | 1 day | 0.5 days | 1.5 days |
| Phase 2+3 | 2 days | 0.5 days | 2.5 days |
| Phase 4 | 2 days | 0.5 days | 2.5 days |
| Phase 5 | 2 days | 0 days | 2 days |

**Total**: 11 days (with contingency) vs 7 days (optimistic)

---

## Success Metrics

### Phase 0 Success Criteria
- [ ] All high-severity risks mitigated
- [ ] Verified agent duplication list approved
- [ ] Conflict detection tested (zero data loss)
- [ ] Rollback procedures documented and tested

### Overall Success Criteria
- [ ] Zero data loss incidents
- [ ] Zero breaking changes to existing users
- [ ] CI/CD reliability ≥99%
- [ ] All 38 tasks completed
- [ ] Architectural review score maintained (≥80/100)

---

## Next Steps

1. **Complete Phase 0 task creation** (TASK-SHA-002, 003, 004)
2. **Review all Phase 0 tasks** with team
3. **Begin execution** with TASK-SHA-000 (verification)
4. **Gate review** after Phase 0 completion
5. **Proceed to Phase 1** only after Phase 0 approval

---

**Last Updated**: 2025-11-28T20:30:00Z
**Parent Task**: TASK-ARCH-DC05
**Review Report**: `.claude/reviews/TASK-ARCH-DC05-shared-agents-architectural-review.md`
