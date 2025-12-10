# Template-Create Implementation Overview

**Date**: 2025-11-18  
**Context**: Solo developer, pre-open source release  
**Strategy**: Rename to legacy, build clean main command  
**Timeline**: 4 weeks (~20 hours total)

---

## The 8-Phase Plan

| # | Task | Hours | What It Fixes |
|---|------|-------|---------------|
| 1 | TASK-ARTIFACT-FILTER | 2-3 | Build artifacts excluded → correct language detection |
| 2 | TASK-AGENT-BRIDGE-COMPLETE | 4-6 | Agent invocation working → 90%+ confidence scores |
| 3 | TASK-PHASE-1-CHECKPOINT | 2-3 | Phase 1 uses AI analysis → 68% → 90%+ confidence |
| 4 | TASK-PHASE-5-CHECKPOINT | 2-3 | Phase 5 uses AI recommendation → 1 agent → 7-9 agents |
| 5 | TASK-PHASE-7-5-CHECKPOINT | 3-4 | Phase 7.5 enhances agents → 34 lines → 150-250 lines |
| 6 | TASK-REMOVE-DETECTOR | 1-2 | Delete 1,045 LOC of hard-coded patterns |
| 7 | TASK-RENAME-LEGACY-BUILD-NEW | 2-3 | Clean main command + undocumented legacy fallback |
| 8 | TASK-OPEN-SOURCE-DOCUMENTATION | 2-3 | User guide + architecture docs |

**Total**: 18-26 hours

---

## Current Problems

### 1. Agent Invocation Not Implemented ❌

**Evidence:**
```
Agent invocation failed: Agent invocation not yet implemented. 
Using fallback heuristics.
```

**Impact**: 68% confidence (should be 90%+)

**Fix**: Phases 2-3

### 2. Build Artifacts Counted ❌

**Evidence:**
```
.NET project: 606 .java files (obj/) + 373 .cs files
Detected as: Java ❌ (should be C#)
```

**Impact**: Wrong language/framework detection

**Fix**: Phase 1

### 3. Minimal Agent Generation ❌

**Current**: 1 agent (14% coverage)  
**Expected**: 7-9 agents (78-100% coverage)

**Fix**: Phase 4

### 4. Basic Agent Files ❌

**Current**: 34 lines (3/10 quality)  
**Expected**: 150-250 lines (9/10 quality) with examples, best practices

**Fix**: Phase 5

### 5. Hard-Coded Detection ❌

**Current**: 1,045 LOC of brittle pattern matching  
**Expected**: AI-first architecture

**Fix**: Phase 6

---

## Quality Improvements

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **Confidence Score** | 68% (heuristic) | 90%+ (AI) | +32% |
| **Agents Detected** | 1 (14%) | 7-9 (78-100%) | +600% |
| **Agent File Quality** | 34 lines (3/10) | 150-250 lines (9/10) | +340-635% |
| **Language Accuracy** | 70% | 95%+ | +25% |
| **Codebase LOC** | 1,045 (detector) | 0 (AI-first) | -100% |

---

## Week-by-Week Breakdown

### Week 1: Foundation (6-9 hours)
- ✅ Build artifacts excluded
- ✅ Agent bridge checkpoint-resume working
- ✅ All tests passing

### Week 2: Checkpoint-Resume (7-10 hours)
- ✅ Phase 1 AI analysis (90%+ confidence)
- ✅ Phase 5 agent recommendation (7-9 agents)
- ✅ Phase 7.5 agent enhancement (150-250 lines)

### Week 3: Integration (3-5 hours)
- ✅ Hard-coded detector removed (1,045 LOC)
- ✅ Legacy renamed
- ✅ Clean main `/template-create` command
- ✅ E2E tests pass on 4 projects

### Week 4: Open Source Prep (2-3 hours)
- ✅ User guide complete
- ✅ Architecture documented
- ✅ No "legacy" in user-facing docs
- ✅ Ready for public release

---

## File Changes Summary

### New Files (4,900 LOC)
```
installer/core/lib/agent_bridge/
├── checkpoint_manager.py        # 200 LOC
├── agent_invoker.py             # 150 LOC
└── response_parser.py           # 100 LOC

installer/core/lib/codebase_analyzer/
└── exclusion_patterns.py        # 200 LOC

tests/ (various)                 # 1,200 LOC

docs/                            # 900 LOC
```

### Renamed Files
```
template-create.md → template-create-legacy.md
template_create_orchestrator.py → template_create_legacy_orchestrator.py
```

### Deleted Files (-1,045 LOC)
```
smart_defaults_detector.py       # -531 LOC
test_smart_defaults_detector.py  # -514 LOC
```

### Net Change
- Added: +4,900 LOC
- Deleted: -1,045 LOC
- Net: +3,855 LOC (mostly tests and docs)

---

## Dependencies

```
Phase 1 (ARTIFACT-FILTER) ──┐
                            ├─► Phase 3 (PHASE-1-CHECKPOINT)
Phase 2 (AGENT-BRIDGE) ─────┼─► Phase 4 (PHASE-5-CHECKPOINT)
                            └─► Phase 5 (PHASE-7-5-CHECKPOINT)
                                        │
                                        ▼
                            Phase 6 (REMOVE-DETECTOR)
                                        │
                                        ▼
                            Phase 7 (RENAME-LEGACY)
                                        │
                                        ▼
                            Phase 8 (DOCUMENTATION)
```

**Can run in parallel**: Phases 1 & 2  
**Critical path**: Phase 2 → Phases 3,4,5 → Phase 6 → Phase 7 → Phase 8

---

## Testing Checkpoints

### After Phase 1
```bash
cd ~/Projects/DeCUK.Mobile.MyDrive
/template-create --validate
# Expected: Detected as C# (not Java)
```

### After Phase 2
```bash
cd /tmp/test
/template-create --validate
# Expected: Exits with code 42, writes .agent-request.json
```

### After Phases 3-5
```bash
cd ~/Projects/bulletproof-react
/template-create --validate
# Expected: 90%+ confidence, 7-9 agents, 150-250 line agent files
```

### After Phase 7 (Final)
```bash
# Test all 4 reference projects
for project in maui react fastapi nextjs; do
  /template-create --validate --name $project
done

# All must pass:
# ✅ Correct language
# ✅ 90%+ confidence
# ✅ 7-9 agents
# ✅ Enhanced agent files
```

---

## Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Agent bridge instability | Medium | High | Keep legacy fallback |
| AI inference less accurate | Low | Medium | Enhanced prompts + testing |
| Performance degradation | Low | Low | Progress indicators |
| Integration issues | Low | Medium | Thorough E2E testing |

**Overall Risk**: LOW (legacy fallback available)

---

## Success Criteria

### Must Have
- [ ] Build artifact filtering (95%+ accuracy)
- [ ] Agent bridge checkpoint-resume complete
- [ ] Phase 1 AI analysis (90%+ confidence)
- [ ] Phase 5 comprehensive agents (7-9)
- [ ] Phase 7.5 enhanced agents (150-250 lines)
- [ ] All tests passing (100%)
- [ ] E2E tests pass on 4 projects

### Nice to Have
- [ ] Performance <2 minutes overhead
- [ ] User satisfaction 8+/10 (you)
- [ ] Clean code (95%+ coverage)

---

## Open Source Readiness

### Before Going Public

**Code:**
- ✅ `/template-create` works perfectly
- ✅ No references to "legacy" in code
- ✅ All tests passing
- ✅ 95%+ test coverage

**Documentation:**
- ✅ User guide (beginner-friendly)
- ✅ Architecture docs (contributors)
- ✅ README updated
- ✅ CLAUDE.md updated
- ✅ Troubleshooting guide

**Quality:**
- ✅ Professional first impression
- ✅ No broken features
- ✅ Clean command structure

### Legacy Command

**Purpose**: Undocumented fallback for solo developer  
**Visibility**: Not in README, not in docs  
**Removal**: After 4 weeks of stable operation  
**Access**: Available via `/template-create-legacy` if needed

---

## Quick Reference

### Start Here
```bash
# 1. Read design proposal
cat TEMPLATE-CREATE-REDESIGN-PROPOSAL.md

# 2. Read quick start guide
cat QUICK-START-GUIDE.md

# 3. Begin Phase 1
cat tasks/backlog/TASK-ARTIFACT-FILTER.md
git checkout -b feature/artifact-filter
```

### Get Help
- Technical design → TEMPLATE-CREATE-REDESIGN-PROPOSAL.md
- Implementation steps → Task files in tasks/backlog/
- Day-by-day guide → QUICK-START-GUIDE.md
- Context → Investigation docs in docs/

---

**Ready to begin?** Start with [QUICK-START-GUIDE.md](./QUICK-START-GUIDE.md)

**Timeline**: 4 weeks  
**Outcome**: Professional template-create ready for open source  
**First Task**: TASK-ARTIFACT-FILTER (2-3 hours)

Good luck! 🚀
