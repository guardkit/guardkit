# Progressive Disclosure Implementation

**Infrastructure Review**: [TASK-REV-426C](../../in_progress/TASK-REV-426C-review-progressive-disclosure-refactor.md) (Phases 0-5)
**Content Migration Review**: [TASK-REV-PD-CONTENT](TASK-REV-PD-CONTENT-content-migration-review.md) (Phase 6)

## Overview

This folder contains the implementation tasks for progressive disclosure in GuardKit's stack templates. The goal is to reduce context window usage by 55-60% while maintaining comprehensive documentation.

## Current Status

**Phases 0-5**: ✅ COMPLETE (Infrastructure)
- Agent scanner excludes `-ext.md` files
- Extended file structure exists (14 core + 14 extended)
- Documentation updated
- Integration tests passing (6/6)

**Phase 6**: ✅ COMPLETE (Content Migration)
- TASK-PD-020 ✅ Content migration rules defined
- TASK-PD-021 ✅ High-priority agents migrated
- TASK-PD-022 ✅ All 14 agents migrated (76.3% reduction achieved)
  - Original: 509KB → Core: 120.5KB
  - Target: ≥55% reduction ✅ EXCEEDED
- TASK-PD-023 ✅ Loading instructions verified (14/14 agents)
- TASK-PD-024 ✅ Final validation and metrics (all criteria passed)

**Final Report**: [docs/reports/progressive-disclosure-final-report.md](../../../docs/reports/progressive-disclosure-final-report.md)

## Total Effort

**19.5-22.5 days** across 7 phases (including Phase 0 and Phase 6)

## Phases

### Phase 0: Measurement Framework (0.5 days) - CRITICAL

| Task | Title | Complexity | Status |
|------|-------|------------|--------|
| [TASK-PD-000](TASK-PD-000-measurement-framework.md) | Establish before/after measurement framework | 4/10 | Backlog |

**Purpose**: Capture baseline metrics before any changes for:
- Validation of 55% reduction target
- Blog post content (telling the GuardKit story)
- Competitive benchmarking vs BMAD/SpecKit

**Deliverables**:
- `scripts/measure-token-usage.py` - Measurement script
- `measurements/baseline.json` - Pre-implementation snapshot
- Benchmark task template (Products feature pattern from TASK-IMP-674A)

**MUST COMPLETE BEFORE Phase 1**

### Phase 1: Foundation (4 days) - HIGH RISK

| Task | Title | Complexity | Status |
|------|-------|------------|--------|
| [TASK-PD-001](TASK-PD-001-refactor-applier-extended-files.md) | Refactor applier.py with create_extended_file() | 7/10 | Backlog |
| [TASK-PD-002](TASK-PD-002-loading-instruction-template.md) | Add loading instruction template | 4/10 | Backlog |
| [TASK-PD-003](TASK-PD-003-update-enhancer-split-support.md) | Update enhancer.py for split support | 5/10 | Backlog |
| [TASK-PD-004](TASK-PD-004-agent-discovery-exclude-ext.md) | Update discovery to exclude -ext.md | 3/10 | Backlog |

**Checkpoint**: Validate with single test agent before Phase 2

### Phase 2: CLAUDE.md Generator (3.5 days) - MEDIUM RISK

| Task | Title | Complexity | Status |
|------|-------|------------|--------|
| [TASK-PD-005](TASK-PD-005-refactor-claude-md-generator.md) | Refactor claude_md_generator.py | 6/10 | Backlog |
| [TASK-PD-006](TASK-PD-006-update-template-orchestrator.md) | Update template orchestrator | 5/10 | Backlog |
| [TASK-PD-007](TASK-PD-007-update-template-claude-model.md) | Update TemplateClaude model | 4/10 | Backlog |

**Checkpoint**: Run `/template-create` on sample codebase

### Phase 3: Automated Agent Migration (3.5 days) - MEDIUM RISK

| Task | Title | Complexity | Status |
|------|-------|------------|--------|
| [TASK-PD-008](TASK-PD-008-create-split-agent-script.md) | Create split-agent.py script | 6/10 | Backlog |
| [TASK-PD-009](TASK-PD-009-define-content-categorization-rules.md) | Define categorization rules | 5/10 | Backlog |
| [TASK-PD-010](TASK-PD-010-run-split-all-global-agents.md) | Run split on 19 global agents | 4/10 | Backlog |
| [TASK-PD-011](TASK-PD-011-validate-all-split-agents.md) | Validate all split agents | 4/10 | Backlog |

**Checkpoint**: All 19 global agents split and validated

### Phase 4: Template Agents (2 days) - LOW RISK

| Task | Title | Complexity | Status |
|------|-------|------------|--------|
| [TASK-PD-012](TASK-PD-012-split-react-typescript-agents.md) | Split react-typescript agents | 4/10 | Backlog |
| [TASK-PD-013](TASK-PD-013-split-fastapi-python-agents.md) | Split fastapi-python agents | 4/10 | Backlog |
| [TASK-PD-014](TASK-PD-014-split-nextjs-fullstack-agents.md) | Split nextjs-fullstack agents | 4/10 | Backlog |
| [TASK-PD-015](TASK-PD-015-split-react-fastapi-monorepo-agents.md) | Split react-fastapi-monorepo agents | 4/10 | Backlog |

**Checkpoint**: All template agents split

### Phase 5: Validation & Documentation (3 days) - LOW RISK ✅ COMPLETE

| Task | Title | Complexity | Status |
|------|-------|------------|--------|
| [TASK-PD-016](../../completed/TASK-PD-016-update-template-validation.md) | Update template validation | 5/10 | ✅ Complete |
| [TASK-PD-017](../../completed/TASK-PD-017/) | Update CLAUDE.md documentation | 3/10 | ✅ Complete |
| [TASK-PD-018](../../completed/TASK-PD-018/) | Update command documentation | 3/10 | ✅ Complete |
| [TASK-PD-019](../../completed/TASK-PD-019/) | Full integration testing | 5/10 | ✅ Complete |

### Phase 6: Content Migration (3-4 days) - ✅ COMPLETE

| Task | Title | Complexity | Status |
|------|-------|------------|--------|
| [TASK-PD-020](../../completed/TASK-PD-020/) | Define content migration rules | 4/10 | ✅ Complete |
| [TASK-PD-021](../../completed/TASK-PD-021/) | Migrate high-priority agents | 5/10 | ✅ Complete |
| [TASK-PD-022](../../completed/TASK-PD-022/) | Migrate remaining agents (12) | 5/10 | ✅ Complete |
| [TASK-PD-023](../../completed/TASK-PD-023/) | Add loading instructions | 3/10 | ✅ Complete |
| [TASK-PD-024](../../completed/TASK-PD-024/) | Final validation and metrics | 4/10 | ✅ Complete |

**Review Task**: [TASK-REV-PD-CONTENT](../../completed/TASK-REV-PD-CONTENT/) ✅ Complete

**Checkpoint**: Token reduction ≥55% achieved, all agents migrated

**Note**: Phase 6 focuses on **global agents only** (14 agents in `installer/global/agents/`). Template agents (28 files across 4 templates) are deferred to Phase 7 to keep Phase 6 focused and manageable.

### Phase 7: Template Agent Migration (0.5-1.5 days) - ✅ COMPLETE

Apply same progressive disclosure migration to template-specific agents.

| Task | Title | Complexity | Status |
|------|-------|------------|--------|
| [TASK-PD-025](../../completed/TASK-PD-025/) | Migrate template agents | 5/10 | ✅ Complete |
| [TASK-PD-026](../../completed/TASK-PD-026/) | Template validation and metrics | 4/10 | ✅ Complete |

**Template Agents** (14 total across 4 templates):

| Template | Agents | Original | Core | Reduction |
|----------|--------|----------|------|-----------|
| react-typescript | 4 | 84.3KB | 30.8KB | 63.6% |
| fastapi-python | 3 | 66.2KB | 26.0KB | 61.7% |
| nextjs-fullstack | 4 | 91.2KB | 29.7KB | 68.4% |
| react-fastapi-monorepo | 3 | 78.4KB | 23.0KB | 71.3% |
| **Total** | **14** | **320.1KB** | **109.7KB** | **70.0%** |

**Checkpoint**: ✅ Token reduction 70.0% achieved (target: ≥55%)

## Dependency Graph

```
PHASES 0-5 (Infrastructure) ✅ COMPLETE
═══════════════════════════════════════
TASK-PD-000 (Baseline) ─► PD-001 ─► PD-002 ─► PD-003 ─► PD-004 ─► [CHECKPOINT 1]
                                                              │
                                                              ▼
                                                         PD-005 ─► PD-006 ─► PD-007 ─► [CHECKPOINT 2]
                                                                                  │
                                                                                  ▼
                                                                             PD-008 ─► PD-009 ─► PD-010 ─► PD-011 ─► [CHECKPOINT 3]
                                                                                                                │
                                                                                                                ▼
                                                                                                     PD-012 ─┬─ PD-016 ─► PD-017 ─► PD-018 ─► PD-019 ✅
                                                                                                     PD-013 ─┤
                                                                                                     PD-014 ─┤
                                                                                                     PD-015 ─┘

PHASE 6 (Content Migration) ✅ COMPLETE
═══════════════════════════════════════════
PD-019 ─► PD-020 ✅ ─► PD-021 ✅ ─► PD-022 ✅ ─► PD-023 ✅ ─► PD-024 ✅ ─► [GLOBAL: 76.3% Reduction]
          (Rules)     (High-Pri)    (Bulk)      (Load)      (Validate)

PHASE 7 (Template Agents) ✅ COMPLETE
═══════════════════════════════════════════
PD-024 ✅ ─► PD-025 ✅ ─► PD-026 ✅ ─► [FINAL: All Agents Complete]
             (Migrate)    (Validate)
```

## Success Metrics

### Phase 6: Global Agents ✅ COMPLETE

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Core agent size (avg) | ≤15KB | 8.6KB | ✅ |
| Token reduction | ≥55% | 76.3% | ✅ |
| Agent discovery | 100% correct | 14/14 | ✅ |
| Loading compliance | 100% | 14/14 | ✅ |
| Content preservation | 100% | +1.6% | ✅ |

### Phase 7: Template Agents ✅ COMPLETE

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Core agent size (avg) | ≤12KB | 7.8KB | ✅ |
| Token reduction | ≥55% | 70.0% | ✅ |
| Agent discovery | 100% correct | 14/14 | ✅ |
| Loading compliance | 100% | 14/14 | ✅ |
| Content preservation | 100% | 0% variance | ✅ |

## Getting Started

### All Phases Complete

Progressive Disclosure implementation is now **fully complete**.

**Final Report**: [docs/reports/progressive-disclosure-final-report.md](../../../docs/reports/progressive-disclosure-final-report.md)

### Summary

| Phase | Status | Reduction |
|-------|--------|-----------|
| Phases 0-5 (Infrastructure) | ✅ Complete | - |
| Phase 6 (Global Agents) | ✅ Complete | 76.3% |
| Phase 7 (Template Agents) | ✅ Complete | 70.0% |
| **Combined** | **✅ Complete** | **73.5%** |

## Benchmark Pattern

Uses the Products feature from VM testing (TASK-IMP-674A) as the benchmark:
- **Complexity 3**: Infrastructure setup (FastAPI app skeleton)
- **Complexity 5**: Products CRUD (103 tests, 98% coverage)
- **Representative**: Real-world feature development
- **Repeatable**: Same tasks can be run before/after for comparison

## Related Documents

- [Progressive Disclosure Analysis](../../../docs/research/progressive-disclosure-analysis.md)
- [Progressive Disclosure Implementation Scope](../../../docs/research/progressive-disclosure-implementation-scope.md)
- [Review Report](../../../.claude/reviews/TASK-REV-426C-review-report.md)
