# Stack-Specific Haiku Agent Implementation

## Overview

This epic implements stack-specific Haiku agents for Phase 3 implementation, completing the model optimization strategy defined in TASK-EE41 while deferring Opus 4.5 integration based on architectural review TASK-895A.

**Parent Task**: TASK-895A (Model Selection Strategy Review)
**Decision**: Defer Opus 4.5, complete Haiku agent implementation
**Status**: Ready for implementation
**Timeline**: Before blog post/documentation update

## Business Value

### Cost Impact
- **Current**: $0.30 per task (33% savings vs all-Sonnet)
- **Target**: $0.20 per task (48-53% total savings)
- **Annual Savings**: +$100/year (1000 tasks) vs current, +$250/year vs baseline

### Performance Impact
- **Phase 3 Speed**: 4-5x faster with Haiku (code generation)
- **Overall Task Time**: 40-50% faster completion
- **Quality**: Maintained at 90%+ (via Phase 4.5 test enforcement)

### Strategic Value
- Completes TASK-EE41 model optimization vision
- Enables AI-powered agent discovery (no hardcoding)
- Zero disruption to 15 recently enhanced agents (Nov 25 08:05)
- Sets foundation for blog post showcasing full optimization story

## Critical Constraints

### Zero Disruption to Existing Agents
**Problem**: 15 global agents just enhanced via `/agent-enhance` (Nov 25 08:05)
**Solution**: Add discovery metadata ONLY to 3 new agents
**Impact**: No re-enhancement work required

### Graceful Degradation Required
**Problem**: System must work with agents WITH and WITHOUT metadata
**Solution**: AI discovery skips agents without `phase` field (opt-in)
**Impact**: Backward compatible, no breaking changes

### No Hardcoding Allowed
**Problem**: Traditional approach hardcodes stack → agent mapping
**Solution**: AI-powered discovery reads metadata, matches context
**Impact**: Extensible, maintains AI-first philosophy

## Task Breakdown

### Phase 1: Foundation (1.5 hours)
- **TASK-HAI-001**: Design Discovery Metadata Schema

### Phase 2: Agent Creation (6 hours, parallelizable)
- **TASK-HAI-002**: Create Python API Specialist Agent
- **TASK-HAI-003**: Create React State Specialist Agent
- **TASK-HAI-004**: Create .NET Domain Specialist Agent

### Phase 3: Discovery System (5 hours, sequential)
- **TASK-HAI-005**: Implement AI Discovery Algorithm
- **TASK-HAI-006**: Integrate Discovery with /task-work

### Phase 4: Finalization (3.5 hours, sequential)
- **TASK-HAI-007**: Update Documentation
- **TASK-HAI-008**: End-to-End Integration Testing

**Total Effort**: 16 hours sequential, **12 hours with parallelization**

## Dependencies

```
HAI-001 (Schema)
     │
     ├──► HAI-002 (Python) ────┐
     │                         │
     ├──► HAI-003 (React)  ────┼──► HAI-005 (Discovery) ──► HAI-006 (Integration)
     │                         │                                  │
     └──► HAI-004 (.NET)   ────┘                                  │
                                                                  ▼
                                                            HAI-007 (Docs) ──► HAI-008 (Tests)
```

**Critical Path**: HAI-001 → HAI-002 → HAI-005 → HAI-006 → HAI-008 (9.5 hours)

**Parallel Opportunities**:
- HAI-002, HAI-003, HAI-004 can run simultaneously (saves 4 hours)

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing agents | LOW | HIGH | Zero changes to existing agents |
| Discovery algorithm bugs | MEDIUM | MEDIUM | Comprehensive unit tests, graceful fallback |
| Integration issues | MEDIUM | MEDIUM | Rollback strategy (<5 min recovery) |
| Documentation gaps | LOW | LOW | Review checklist in HAI-007 |

**Highest Risk Area**: TASK-HAI-005 (Discovery Algorithm)
- **Mitigation**: 15+ test cases covering edge cases
- **Mitigation**: Graceful degradation ensures no breakage
- **Mitigation**: Can disable discovery if issues arise

## Rollback Strategy

### Per-Task Rollback
| Task | Rollback | Recovery Time |
|------|----------|---------------|
| HAI-001 | Delete schema file | 30 seconds |
| HAI-002/003/004 | Delete agent files | 1 minute |
| HAI-005 | Remove discovery module | 2 minutes |
| HAI-006 | Revert Phase 3 integration | 2 minutes |
| HAI-007 | Revert documentation | 1 minute |
| HAI-008 | N/A (testing only) | N/A |

### Full System Rollback
```bash
# Option A: Git revert
git revert <commit-range>

# Option B: Manual cleanup
rm installer/global/agents/{python-api-specialist,react-state-specialist,dotnet-domain-specialist}.md
rm installer/global/commands/lib/agent_discovery.py
git checkout installer/global/commands/lib/phase_execution.py CLAUDE.md
```

**Total Recovery Time**: < 5 minutes

## Success Criteria

### Functional Requirements
- [x] 3 new stack-specific agents created with discovery metadata
- [x] Discovery metadata schema defined and documented
- [x] AI discovery algorithm implemented with graceful degradation
- [x] Phase 3 integration suggests appropriate specialists
- [x] Documentation updated (CLAUDE.md, guides, schemas)
- [x] All unit and integration tests passing

### Quality Requirements
- [x] Zero impact on 15 existing agents (no file modifications)
- [x] Backward compatibility: agents without metadata still work
- [x] Graceful fallback: no errors when no specialist found
- [x] Test coverage >90% for discovery algorithm, >80% overall

### User Experience Requirements
- [x] Phase 3 automatically detects and suggests specialists
- [x] Clear feedback when specialist used vs fallback
- [x] Documentation guides users on migration path

## Migration Path (Optional)

Existing agents can be enhanced with discovery metadata incrementally:

```bash
/agent-enhance installer/global/agents/database-specialist.md
```

**Benefits**:
- Existing agents become discoverable
- Better AI-powered matching
- Consistent metadata across all agents

**No Pressure**:
- Migration is **optional**
- Existing agents work fine without metadata
- Can migrate 1 agent at a time

## Related Tasks

**Completed**:
- TASK-EE41: Original model optimization (Oct 2025)
- TASK-895A: Model selection strategy review (Nov 2025)

**Blocked By This Epic**:
- Blog post about model optimization
- Documentation update for public launch

**Future Enhancements**:
- Add more stack-specific agents (Go, Rust, etc.)
- Enhance existing agents with metadata (optional)
- Complexity-based model routing (if needed)

## Timeline

**Recommended Schedule** (5-day sprint before blog post):

**Day 1** (Mon):
- Morning: HAI-001 (schema) - 1.5h
- Afternoon: Start HAI-002 (Python agent) - 2h

**Day 2** (Tue):
- Morning: Complete HAI-002 - 0.5h
- Afternoon: HAI-003 (React agent) - 2h

**Day 3** (Wed):
- Morning: HAI-004 (.NET agent) - 2h
- Afternoon: Start HAI-005 (discovery) - 2h

**Day 4** (Thu):
- Morning: Complete HAI-005 - 1h
- Afternoon: HAI-006 (integration) - 2h

**Day 5** (Fri):
- Morning: HAI-007 (documentation) - 1.5h
- Afternoon: HAI-008 (E2E testing) - 2h

**Blog Post**: Weekend or following Monday

## Quick Reference

**Architectural Design**: Software Architect analysis (comprehensive design document)
**Parent Decision**: TASK-895A (defer Opus 4.5, complete Haiku agents)
**Model Optimization**: TASK-EE41 (original strategy)
**Cost Savings**: 48-53% total (vs all-Sonnet baseline)
**Zero Disruption**: No changes to 15 existing agents
**AI-First**: Discovery via metadata, no hardcoded mappings

---

**Status**: ✅ Ready for implementation
**Approved By**: Architectural review (TASK-895A)
**Priority**: HIGH (blocks blog post)
**Complexity**: 7/10 (medium-complex, well-designed)
