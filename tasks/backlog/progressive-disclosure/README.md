# Progressive Disclosure Implementation

**Review Task**: [TASK-REV-426C](../../in_progress/TASK-REV-426C-review-progressive-disclosure-refactor.md)
**Review Report**: [.claude/reviews/TASK-REV-426C-review-report.md](../../../.claude/reviews/TASK-REV-426C-review-report.md)

## Overview

This folder contains the implementation tasks for progressive disclosure in GuardKit's stack templates. The goal is to reduce context window usage by 55-60% while maintaining comprehensive documentation.

## Total Effort

**16.5-18.5 days** across 6 phases (including Phase 0)

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

### Phase 5: Validation & Documentation (3 days) - LOW RISK

| Task | Title | Complexity | Status |
|------|-------|------------|--------|
| [TASK-PD-016](TASK-PD-016-update-template-validation.md) | Update template validation | 5/10 | Backlog |
| [TASK-PD-017](TASK-PD-017-update-claude-md-documentation.md) | Update CLAUDE.md documentation | 3/10 | Backlog |
| [TASK-PD-018](TASK-PD-018-update-command-documentation.md) | Update command documentation | 3/10 | Backlog |
| [TASK-PD-019](TASK-PD-019-integration-testing.md) | Full integration testing | 5/10 | Backlog |

## Dependency Graph

```
TASK-PD-000 (Baseline) ─► PD-001 ─► PD-002 ─► PD-003 ─► PD-004 ─► [CHECKPOINT 1]
                                                              │
                                                              ▼
                                                         PD-005 ─► PD-006 ─► PD-007 ─► [CHECKPOINT 2]
                                                                                  │
                                                                                  ▼
                                                                             PD-008 ─► PD-009 ─► PD-010 ─► PD-011 ─► [CHECKPOINT 3]
                                                                                                                │
                                                                                                                ▼
                                                                                                     PD-012 ─┬─ PD-016 ─► PD-017 ─► PD-018 ─► PD-019 ─► [FINAL: Measure After]
                                                                                                     PD-013 ─┤
                                                                                                     PD-014 ─┤
                                                                                                     PD-015 ─┘
```

## Success Metrics

| Metric | Target |
|--------|--------|
| Core CLAUDE.md size | ≤8KB |
| Core agent size (avg) | ≤15KB |
| Token reduction | ≥55% |
| Agent discovery | 100% correct |
| Loading compliance | 100% |
| Content preservation | 100% |

## Getting Started

```bash
# Phase 0: Capture baseline FIRST (critical!)
/task-work TASK-PD-000

# Then start Phase 1
/task-work TASK-PD-001
```

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
