---
id: TASK-REV-FBVAL
title: "Review: Validate feature-build command with FastAPI test project"
status: completed
created: 2026-01-23T14:00:00Z
updated: 2026-01-23T16:00:00Z
priority: high
tags: [feature-build, validation, fastapi, autobuild, integration-testing, quality-assurance]
task_type: review
complexity: 6
related_tasks:
  - TASK-REV-CSC1
  - TASK-REV-FB22
related_features:
  - FEAT-4C15
review_results:
  mode: decision
  depth: standard
  findings_count: 5
  recommendations_count: 2
  decision: implement
  report_path: .claude/reviews/TASK-REV-FBVAL-review-report.md
  completed_at: 2026-01-23T16:00:00Z
  tasks_created:
    - TASK-FIX-ARCH
    - TASK-FIX-SCAF
---

# Review: Validate feature-build command with FastAPI test project

## Background

We need to validate that the `/feature-build` command works correctly for "normal" coding tasks before implementing the context-sensitive coach (FEAT-4C15). The best way to validate this is to create a real-world test scenario using a new FastAPI Python project.

### Context

- **FEAT-4C15** (Context-Sensitive Coach) aims to fix issues where simple configuration code fails quality gates designed for complex implementations
- Before implementing the fix, we need baseline data showing where feature-build succeeds and fails
- A FastAPI project provides an ideal test bed because it includes:
  - Configuration/initialization code (often fails current gates)
  - Standard CRUD operations (should pass gates)
  - Database integration (medium complexity)
  - API endpoint patterns (well-understood)

## Review Objectives

1. **Design Test Strategy**: Define a sequence of tasks that would validate feature-build across varying complexity levels
2. **Identify Validation Metrics**: What should we measure to determine "working correctly"?
3. **Plan Project Structure**: How should the test FastAPI project be organized?
4. **Map Expected Outcomes**: Which tasks should pass/fail with current gates?
5. **Document Baseline**: Create reference data for FEAT-4C15 implementation

## Proposed Test Scenario

### Phase 1: Project Foundation (task-work - manual baseline)

Use standard `/task-work` commands to establish project foundation:

1. **TASK-FAPI-001**: Create FastAPI project structure
   - `main.py` with app initialization
   - `pyproject.toml` with dependencies
   - Basic directory structure (`app/`, `tests/`)
   - **Expected**: Low complexity, likely to pass

2. **TASK-FAPI-002**: Add configuration management
   - Pydantic Settings model
   - Environment variable handling
   - `.env.example` template
   - **Expected**: Configuration code - may struggle with coverage gates

3. **TASK-FAPI-003**: Database setup with SQLAlchemy
   - Database connection configuration
   - Session management
   - Alembic migrations setup
   - **Expected**: Infrastructure code - declarative models may fail coverage

### Phase 2: Feature Testing (feature-plan → feature-build)

Use `/feature-plan` to generate features, then `/feature-build` to implement:

4. **Feature: Health Endpoints**
   - `/health` - Basic health check
   - `/health/ready` - Readiness probe
   - `/health/live` - Liveness probe
   - **Expected**: Simple endpoints - should pass

5. **Feature: Products CRUD**
   - Product model (SQLAlchemy + Pydantic schemas)
   - CRUD endpoints (GET, POST, PUT, DELETE)
   - List with pagination
   - Search/filter capability
   - **Expected**: Standard patterns - good test of feature-build

6. **Feature: Categories (Optional)**
   - Category model with Product relationship
   - Nested CRUD operations
   - **Expected**: Relationship handling - tests more complex scenarios

### Phase 3: Analysis

7. **TASK-FAPI-ANALYSIS**: Analyze results
   - Collect pass/fail data from each task
   - Document where quality gates blocked progress
   - Identify patterns in failures
   - Create baseline report for FEAT-4C15

## Validation Metrics

For each task/feature, track:

| Metric | Description |
|--------|-------------|
| **Completion Status** | APPROVED / MAX_TURNS / ERROR |
| **Turns Required** | Number of Player-Coach iterations |
| **Gate Failures** | Which quality gates failed and why |
| **Coverage Achieved** | Line/branch coverage percentages |
| **Arch Review Score** | SOLID/DRY/YAGNI scores |
| **Time to Complete** | Total execution duration |
| **Human Intervention** | Any manual fixes required |

## Questions to Answer

1. **Feature-build reliability**: What percentage of tasks complete successfully?
2. **Quality gate calibration**: Are current thresholds appropriate for different task types?
3. **Context sensitivity need**: Do we see the patterns FEAT-4C15 aims to fix?
4. **Process improvements**: What other workflow issues emerge?

## Proposed Project Location

```
~/Projects/test-projects/fastapi-feature-build-validation/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── product.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── product.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py
│   │   └── products.py
│   └── crud/
│       ├── __init__.py
│       └── products.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_health.py
│   └── test_products.py
├── alembic/
│   └── versions/
├── pyproject.toml
├── .env.example
└── README.md
```

## Scope

### In Scope
- Design validation strategy for feature-build
- Define task sequence and expected outcomes
- Specify project structure and technology choices
- Create metrics framework for analysis
- Recommend next steps based on review

### Out of Scope
- Actually creating the FastAPI project (implementation follows review)
- Implementing FEAT-4C15 (separate task set)
- Performance benchmarking of feature-build itself
- Comparison with other AI coding tools

## Acceptance Criteria

- [ ] Clear validation strategy documented
- [ ] Task sequence defined with complexity estimates
- [ ] Expected outcomes mapped for each task
- [ ] Metrics framework specified
- [ ] Project structure approved
- [ ] Technology choices justified
- [ ] Risk assessment included
- [ ] Decision checkpoint: Proceed with implementation?

## Decision Options

At review completion:
- **[I]mplement**: Create the test project and run validation tasks
- **[A]ccept**: Approve strategy for future implementation
- **[R]evise**: Request changes to validation approach
- **[C]ancel**: Abandon validation effort

## References

- **Related Review**: TASK-REV-CSC1 (Context-Sensitive Coach planning)
- **Related Analysis**: TASK-REV-FB22 (Feature-build post-FB21 analysis)
- **Feature to Validate**: FEAT-4C15 (Context-Sensitive Coach)
- **FastAPI Template**: `installer/core/templates/fastapi-python/`
- **AutoBuild Docs**: `.claude/rules/autobuild.md`

## Notes

This review task is intentionally designed to:
1. Validate feature-build before relying on it for FEAT-4C15 implementation
2. Generate real-world baseline data showing where current quality gates struggle
3. Provide concrete evidence for context-sensitive coach design decisions
4. Create a reusable test project pattern for future GuardKit validation
