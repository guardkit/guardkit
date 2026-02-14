# Quality Gate Pipeline

> 10-phase validation pipeline with complexity-gated intensity

## Pipeline Phases

| Phase | Name | Gate | Complexity Gating |
|-------|------|------|-------------------|
| 1.6 | Clarifying Questions | Understanding validation | Skip at complexity 1-2 |
| 2 | Implementation Planning | Plan must exist (markdown) | Always |
| 2.5 | Architectural Review | SOLID/DRY/YAGNI score >= 60/100 | Skip at complexity 1-2 |
| 2.7 | Complexity Evaluation | Routes to approval level | Always |
| 2.8 | Human Checkpoint | Design approval | Required at 7-10, optional at 4-6, skip at 1-3 |
| 3 | Implementation | Code written | Always |
| 4 | Testing | Compilation + test execution | Always |
| 4.5 | Test Enforcement | 100% pass, >= 80% line coverage, >= 75% branch | Auto-fix x3 then block |
| 5 | Code Review | Requirements met, no regressions | Always |
| 5.5 | Plan Audit | Scope variance detection | Flag at >20% variance, block at >50% |

## Adversarial Intensity Gradient

| Complexity | Intensity Level | Coach Validation | Max Turns | Checkpoint |
|-----------|----------------|-----------------|-----------|------------|
| 1-2 | Minimal (`--micro`) | Tests pass only | 3 | Auto-proceed |
| 3-4 | Standard-Light | Requirements met | 5 | Quick (10s timeout) |
| 5-6 | Standard | Requirements + tests | 7 | Quick |
| 7-10 | Strict | Full (requirements + architecture + integration) | 10 | Mandatory |

## Task Types and Quality Profiles

| Task Type | Tests Required | Zero-Test Blocking | Coverage Required | Arch Review Required |
|-----------|---------------|-------------------|-------------------|---------------------|
| FEATURE | Yes | Yes | Yes | Yes |
| REFACTOR | Yes | Yes | Yes | Yes |
| TESTING | Yes | No | Yes | No |
| DOCUMENTATION | No | No | No | No |
| SCAFFOLDING | No | No | No | No |
| INFRASTRUCTURE | Yes | No | No | No |
| INTEGRATION | Yes | No | No | No |

## Key Decision Points

- **Phase 2.7**: Auto-proceed (1-3) vs checkpoint (7-10)
- **Phase 4.5**: Auto-fix vs block (after 3 attempts)
- **Phase 5.5**: Approve vs escalate (>20% variance = flag, >50% = block)
