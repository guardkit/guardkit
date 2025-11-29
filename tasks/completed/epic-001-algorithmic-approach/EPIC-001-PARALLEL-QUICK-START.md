# EPIC-001 Task Dependency Reference

**Epic**: EPIC-001 - Template Creation Automation
**Total Tasks**: 37
**Organization**: 6 waves based on dependencies
**Use Case**: Solo developer or team using Conductor app

**Note**: For solo developers using Conductor app with Claude Code, see [EPIC-001-SOLO-DEV-GUIDE.md](EPIC-001-SOLO-DEV-GUIDE.md)

---

## Visual Dependency Map

```
WAVE 0 (6 tasks - NO dependencies)
═══════════════════════════════════════════════════════════════
 037A  037   048B  048   049   053
  │     │     │     │     │     │
  │     └─────┼─────┼─────┤     │
  │           │     └─────┤     │
  │           │           │     │
WAVE 1 (7 tasks)                │
═══════════════════════════════════════════════════════════════
 038A  038   045A  048C  054   055   058
  │     │     │     │     │     │     │
  └─────┴─────┤     │     │     └─────┤
        │     │     │     │           │
WAVE 2 (7 tasks)                      │
═══════════════════════════════════════════════════════════════
 039A  039   040   041   042   044   056,057
  │     │     │     │     │     │     │
  │     │     └─────┴─────┴─────┤     │
  │     │                 │     │     │
WAVE 3 (4 tasks)          │     │     │
═══════════════════════════════════════════════════════════════
 045   043,062  050       046   │     │
  │     │       │         │     │     │
  └─────┴───────┴─────────┤     │     │
                          │     │     │
WAVE 4 (3 tasks)          │     │     │
═══════════════════════════════════════════════════════════════
 047   051,052  059       │     │     │
  │     │       │         │     │     │
  └─────┴───────┴─────────┴─────┴─────┘
                          │
WAVE 5 (1 task)           │
═══════════════════════════════════════════════════════════════
 060 ←─────────────────────┘
  │
WAVE 6 (7 tasks)
═══════════════════════════════════════════════════════════════
 061→064  063  065  066  067
```

---

## Wave-by-Wave Execution Guide

### WAVE 0: Foundation - 25 hours

**NO DEPENDENCIES - All 6 tasks can start immediately:**

**Tasks:**
- **TASK-037A**: Universal Language Mapping (3h, Complexity 3/10)
- **TASK-037**: Technology Stack Detection (6h, Complexity 5/10)
- **TASK-048B**: Local Agent Scanner (4h, Complexity 4/10)
- **TASK-048**: Subagents.cc Scraper (6h, Complexity 6/10)
- **TASK-049**: GitHub Agent Parsers (8h, Complexity 7/10)
- **TASK-053**: Template-init QA Flow (6h, Complexity 5/10)

**Exit Criteria**:
- ✅ Language mapping for 50+ languages
- ✅ Stack detection working
- ✅ Local agent scanner discovering 15+ agents
- ✅ External agent sources integrated

---

### WAVE 1: First Tier - 33 hours

**Dependencies**: Wave 0 complete

**Tasks:**
- **TASK-038A**: Generic Structure Analyzer (6h, Complexity 6/10)
  - Requires: TASK-037A ✓
- **TASK-038**: Architecture Pattern Analyzer (7h, Complexity 6/10)
  - Requires: TASK-037 ✓
- **TASK-045A**: Language Syntax Database (4h, Complexity 4/10)
  - Requires: TASK-037A ✓
- **TASK-048C**: Configurable Agent Sources (3h, Complexity 3/10)
  - Requires: TASK-048B ✓
- **TASK-054**: Basic Info Section (4h, Complexity 4/10)
  - Requires: TASK-053 ✓
- **TASK-055**: Technology Section (5h, Complexity 5/10)
  - Requires: TASK-053 ✓
- **TASK-058**: Quality Section (4h, Complexity 4/10)
  - Requires: TASK-053 ✓

**Exit Criteria**:
- ✅ Structure analysis working for any language
- ✅ Architecture patterns detected
- ✅ Syntax database complete
- ✅ Agent sources configurable

---

### WAVE 2: Second Tier - 42 hours

**Dependencies**: Wave 1 complete

**Tasks:**
- **TASK-039A**: Generic Text Extraction (5h, Complexity 5/10)
  - Requires: TASK-037A ✓, TASK-038A ✓
- **TASK-039**: Code Pattern Extraction (8h, Complexity 7/10)
  - Requires: TASK-037 ✓, TASK-038 ✓
- **TASK-040**: Naming Convention Inference (5h, Complexity 5/10)
  - Requires: TASK-038 ✓
- **TASK-041**: Layer Structure Detection (4h, Complexity 4/10)
  - Requires: TASK-038 ✓
- **TASK-042**: Manifest Generator (5h, Complexity 4/10)
  - Requires: TASK-037 ✓, TASK-038 ✓
- **TASK-044**: CLAUDE.md Generator (6h, Complexity 5/10)
  - Requires: TASK-037 ✓, TASK-038 ✓
- **TASK-056**: Architecture Section (5h, Complexity 5/10)
  - Requires: TASK-053 ✓, TASK-055 ✓
- **TASK-057**: Testing Section (4h, Complexity 4/10)
  - Requires: TASK-053 ✓, TASK-055 ✓

**Exit Criteria**:
- ✅ Code pattern extraction for all languages
- ✅ Naming conventions inferred
- ✅ Manifest/CLAUDE.md generators working

---

### WAVE 3: Integration Layer - 29 hours

**Dependencies**: Wave 2 complete

**Tasks:**
- **TASK-043**: Settings Generator (4h, Complexity 4/10)
  - Requires: TASK-040 ✓, TASK-041 ✓
- **TASK-062**: Template Versioning (4h, Complexity 3/10)
  - Requires: TASK-042 ✓
- **TASK-045**: Code Template Generator (8h, Complexity 7/10)
  - Requires: TASK-039 ✓
- **TASK-050**: Agent Matching Algorithm (7h, Complexity 6/10)
  - Requires: TASK-037 ✓, TASK-038 ✓, TASK-048 ✓, TASK-048B ✓, TASK-048C ✓, TASK-049 ✓
- **TASK-046**: Template Validation (6h, Complexity 5/10)
  - Requires: TASK-042 ✓, TASK-043 ✓, TASK-044 ✓, TASK-045 ✓
  - NOTE: Must wait for TASK-043 and TASK-045 from this wave

**Exit Criteria**:
- ✅ Template generation working
- ✅ Agent matching with bonus scoring
- ✅ Validation catching errors

---

### WAVE 4: Command Orchestration - 20 hours

**Dependencies**: Wave 3 complete

**Tasks:**
- **TASK-047**: /template-create Orchestrator (6h, Complexity 6/10)
  - Requires: TASK-037 ✓, TASK-038 ✓, TASK-039 ✓, TASK-042 ✓, TASK-043 ✓, TASK-045 ✓, TASK-046 ✓
- **TASK-051**: Agent Selection UI (5h, Complexity 5/10)
  - Requires: TASK-050 ✓
- **TASK-052**: Agent Download Integration (4h, Complexity 4/10)
  - Requires: TASK-051 ✓
- **TASK-059**: Agent Discovery Integration (5h, Complexity 5/10)
  - Requires: TASK-053 ✓, TASK-050 ✓, TASK-051 ✓

**Exit Criteria**:
- ✅ `/template-create` command working end-to-end
- ✅ Agent selection UI with source grouping
- ✅ Agent download integration

---

### WAVE 5: Template-init - 6 hours

**Dependencies**: Wave 4 complete + all Q&A sections

**Tasks:**
- **TASK-060**: /template-init Orchestrator (6h, Complexity 6/10)
  - Requires: TASK-042 ✓, TASK-043 ✓, TASK-044 ✓, TASK-045 ✓, TASK-046 ✓, TASK-053 ✓, TASK-054 ✓, TASK-055 ✓, TASK-056 ✓, TASK-057 ✓, TASK-058 ✓, TASK-059 ✓

**Exit Criteria**:
- ✅ `/template-init` command working end-to-end

---

### WAVE 6: Distribution & Documentation - 37 hours

**Dependencies**: Wave 5 complete

**Tasks:**
- **TASK-061**: Template Packaging (5h, Complexity 4/10)
  - Requires: TASK-047 ✓, TASK-060 ✓
- **TASK-063**: Template Update/Merge (6h, Complexity 5/10)
  - Requires: TASK-062 ✓
- **TASK-064**: Distribution Helpers (4h, Complexity 3/10)
  - Requires: TASK-061 ✓
- **TASK-065**: Integration Tests (10h, Complexity 7/10)
  - Requires: TASK-047 ✓, TASK-060 ✓
- **TASK-066**: User Documentation (8h, Complexity 5/10)
  - Requires: TASK-047 ✓, TASK-060 ✓, TASK-065 ✓
- **TASK-067**: Example Templates (10h, Complexity 6/10)
  - Requires: TASK-047 ✓

**Exit Criteria**:
- ✅ All tests passing
- ✅ Documentation complete
- ✅ Example templates created

---

## Implementation Timeline

### Solo Developer: 8-12 Weeks

**Standard Pace** (18-20 hours/week):
- Weeks 1-2: Wave 0 (25h) + Wave 1 start
- Weeks 3-4: Wave 1 (33h) + Wave 2 start
- Weeks 5-6: Wave 2 (42h) + Wave 3 start
- Weeks 7-8: Wave 3 (29h) + Wave 4 (20h)
- Weeks 9-10: Wave 5 (6h) + Wave 6 start (37h)
- Weeks 11-12: Wave 6 completion

**Aggressive Pace** (25-30 hours/week):
- Weeks 1-2: Wave 0 (25h) + Wave 1 (33h)
- Weeks 3-4: Wave 2 (42h) + Wave 3 (29h)
- Weeks 5-6: Wave 4 (20h) + Wave 5 (6h) + Wave 6 start
- Weeks 7-8: Wave 6 (37h) + polish
- Week 9: Final testing

**See**: [EPIC-001-SOLO-DEV-GUIDE.md](EPIC-001-SOLO-DEV-GUIDE.md) for detailed solo developer workflow with Conductor app and `/task-work`

---

## Monitoring Progress

### Using Conductor App

- **View all worktrees** in Conductor app sidebar
- **Check task status** by opening worktree and viewing task file
- **Track completion** by moving tasks from `tasks/backlog/` to `tasks/completed/`

### Wave Completion Checklists

Use the success criteria at the end of each wave section above to track progress.

### Integration Checkpoints

After each wave completes, run integration tests:

```bash
# Wave-specific tests
pytest tests/integration/wave_{N}/

# Full integration tests
pytest tests/integration/
```

---

## Success Criteria by Wave

### Wave 0: Foundation ✅
- [ ] 50+ languages mapped
- [ ] Stack detection working
- [ ] 15+ local agents discovered
- [ ] External agent sources integrated
- [ ] Q&A flow structure ready

### Wave 1: First Tier ✅
- [ ] Generic structure analysis working
- [ ] Architecture patterns detected
- [ ] Syntax database complete
- [ ] Agent sources configurable

### Wave 2: Second Tier ✅
- [ ] Text-based extraction for all languages
- [ ] Naming conventions inferred
- [ ] Manifest/CLAUDE.md generators working

### Wave 3: Integration ✅
- [ ] Template generation working
- [ ] Agent matching with bonuses
- [ ] Settings/validation complete

### Wave 4: Commands ✅
- [ ] `/template-create` end-to-end
- [ ] Agent selection UI working
- [ ] Agent download integrated

### Wave 5: Template-init ✅
- [ ] `/template-init` end-to-end
- [ ] All Q&A sections integrated

### Wave 6: Polish ✅
- [ ] All integration tests passing
- [ ] Documentation complete
- [ ] Example templates created

---

## Risk Mitigation

### Blocked Task Protocol

```bash
# If task is blocked, switch to alternative
cd epic001-w0-lang

# Check what's blocking
git log tasks/backlog/TASK-037A*.md

# If truly blocked, switch worktree
cd ../epic001-w0-github  # Different wave 0 task
```

### Merge Conflict Prevention

- ✅ Each task works on different files
- ✅ Conductor's symlink architecture prevents state conflicts
- ✅ Use wave boundaries for integration

### Daily Standup Checklist

1. Which task(s) did you complete yesterday?
2. Which task are you working on today?
3. Any blockers or dependencies waiting?
4. Ready to move to next wave?

---

## Summary

**Total**: 37 tasks, 220 hours, 6 waves
**Solo Timeline**: 8-12 weeks (vs. 12 weeks pure sequential)
**Key Advantage**: Flexible worktree switching with Conductor app prevents blocking

### Task Distribution by Wave:

| Wave | Tasks | Hours | Dependencies |
|------|-------|-------|--------------|
| Wave 0 | 6 | 25h | None - start immediately |
| Wave 1 | 7 | 33h | Wave 0 complete |
| Wave 2 | 7 | 42h | Wave 1 complete |
| Wave 3 | 4 | 29h | Wave 2 complete |
| Wave 4 | 4 | 20h | Wave 3 complete |
| Wave 5 | 1 | 6h | Wave 4 complete |
| Wave 6 | 7 | 37h | Wave 5 complete |

**Complexity Distribution**:
- Simple (3-4): 16 tasks
- Medium (5-6): 17 tasks
- Complex (7+): 4 tasks

---

## Next Steps

### For Solo Developer:

1. **Read**: [EPIC-001-SOLO-DEV-GUIDE.md](EPIC-001-SOLO-DEV-GUIDE.md) for complete workflow
2. **Open Conductor app**
3. **Create first worktree** for Wave 0 task (recommend TASK-037A)
4. **Run `/task-work TASK-037A`** in Claude Code
5. **Complete wave-by-wave** using the dependency structure above

### For Teams:

See [EPIC-001-PARALLEL-IMPLEMENTATION-PLAN.md](EPIC-001-PARALLEL-IMPLEMENTATION-PLAN.md) for multi-developer coordination strategy.

---

**Created**: 2025-11-01
**Updated**: 2025-11-01
**Status**: ✅ **READY FOR IMPLEMENTATION**
**Recommended Start**: Wave 0, Task TASK-037A (Universal Language Mapping)
