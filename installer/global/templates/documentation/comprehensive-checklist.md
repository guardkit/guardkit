# Comprehensive Mode Documentation Checklist

## Purpose

This checklist defines the **comprehensive mode** documentation suite. Comprehensive mode generates full documentation with detailed rationale, examples, and traceability.

**Target**: Complexity 7-10 tasks, security/compliance tasks, or force-triggered tasks

## Core Documents (Required - 6 Files)

### 1. Implementation Plan (`implementation_plan.md`)
- [ ] File structure (files to create/modify)
- [ ] Component architecture with diagrams
- [ ] Pattern selection with justification
- [ ] Dependencies with version rationale
- [ ] Risk assessment with mitigations
- [ ] Estimated effort breakdown
- [ ] Implementation phases

**Estimated**: ~300-500 lines

### 2. Implementation Summary (`implementation_summary.md`)
- [ ] What was implemented (detailed)
- [ ] How it works (architectural overview)
- [ ] Files created/modified with descriptions
- [ ] Dependencies added with rationale
- [ ] Test coverage report
- [ ] Quality gates results
- [ ] Known limitations

**Estimated**: ~200-300 lines

### 3. Architectural Review Report (`architectural_review.md`)
- [ ] SOLID principles evaluation (scores + rationale)
- [ ] DRY principle compliance
- [ ] YAGNI principle adherence
- [ ] Pattern appropriateness analysis
- [ ] Recommendations for improvement
- [ ] Approval decision with reasoning

**Estimated**: ~200-400 lines

### 4. Test Report (`test_report.md`)
- [ ] Test strategy overview
- [ ] Unit test coverage (with examples)
- [ ] Integration test coverage (with scenarios)
- [ ] Edge cases tested
- [ ] Coverage metrics (line, branch, function)
- [ ] Test execution results
- [ ] Performance benchmarks (if applicable)

**Estimated**: ~200-300 lines

### 5. Code Review Report (`code_review.md`)
- [ ] Code quality assessment
- [ ] Best practices compliance
- [ ] Error handling review
- [ ] Security considerations
- [ ] Performance analysis
- [ ] Maintainability score
- [ ] Recommendations

**Estimated**: ~200-300 lines

### 6. Change Log (`CHANGELOG.md` entry)
- [ ] Version number
- [ ] Change type (Added, Changed, Fixed, etc.)
- [ ] User-facing description
- [ ] Breaking changes (if any)
- [ ] Migration guide (if breaking)
- [ ] Related issue/task IDs

**Estimated**: ~50-100 lines

## Conditional Documents (7 Files - Create When Applicable)

### 7. Architecture Decision Records (`docs/adrs/ADR-XXX.md`)

**When to create**:
- Significant architectural choice made
- Trade-off between multiple approaches
- Pattern selection impacts future development

**Contents**:
- [ ] Context (problem being solved)
- [ ] Decision (what was chosen)
- [ ] Consequences (trade-offs, implications)
- [ ] Status (proposed, accepted, superseded)
- [ ] Date and decision-makers

**Estimated**: ~100-200 lines per ADR

### 8. Security Analysis (`security_analysis.md`)

**When to create**:
- Security keywords detected (auth, password, encryption)
- Data handling (PII, sensitive info)
- External API integration
- Authentication/authorization changes

**Contents**:
- [ ] Threat model
- [ ] Security controls implemented
- [ ] Vulnerability assessment
- [ ] Compliance considerations
- [ ] Recommendations

**Estimated**: ~200-400 lines

### 9. Performance Analysis (`performance_analysis.md`)

**When to create**:
- Performance requirements specified
- Database queries optimized
- Caching implemented
- Scalability considerations

**Contents**:
- [ ] Performance requirements
- [ ] Benchmarks (before/after)
- [ ] Optimization techniques used
- [ ] Scalability assessment
- [ ] Recommendations

**Estimated**: ~150-250 lines

### 10. Migration Guide (`migration_guide.md`)

**When to create**:
- Breaking changes introduced
- API changes
- Database schema changes
- Configuration changes

**Contents**:
- [ ] What's changing
- [ ] Why it's changing
- [ ] Step-by-step migration
- [ ] Rollback procedure
- [ ] Timeline

**Estimated**: ~100-200 lines

### 11. API Documentation (`api_documentation.md`)

**When to create**:
- New API endpoints
- API contract changes
- Public interfaces modified

**Contents**:
- [ ] Endpoint specifications
- [ ] Request/response formats
- [ ] Authentication requirements
- [ ] Error codes
- [ ] Examples

**Estimated**: ~200-400 lines

### 12. Requirements Analysis (`requirements_analysis.md`)

**When to create** (require-kit integration):
- EARS requirements linked
- Complex functional requirements
- Non-functional requirements specified

**Contents**:
- [ ] Functional requirements (detailed)
- [ ] Non-functional requirements
- [ ] Acceptance criteria mapping
- [ ] Traceability matrix
- [ ] Gaps identified

**Estimated**: ~200-300 lines

### 13. BDD Scenarios (`bdd_scenarios.feature`)

**When to create** (require-kit integration):
- User-facing features
- BDD scenarios linked
- Behavior-driven development mode

**Contents**:
- [ ] Feature description
- [ ] Scenarios in Gherkin format
- [ ] Step definitions
- [ ] Background context
- [ ] Examples/scenarios outline

**Estimated**: ~100-200 lines

## Total File Count

- **Core**: 6 files (always generated)
- **Conditional**: 0-7 files (based on task characteristics)
- **Total**: 6-13 files

## Naming Conventions

```
docs/state/{task_id}/
├── implementation_plan.md
├── implementation_summary.md
├── architectural_review.md
├── test_report.md
├── code_review.md
├── CHANGELOG_entry.md
├── security_analysis.md (if applicable)
├── performance_analysis.md (if applicable)
├── migration_guide.md (if applicable)
├── api_documentation.md (if applicable)
├── requirements_analysis.md (if require-kit)
└── bdd_scenarios.feature (if require-kit)

docs/adrs/
└── ADR-{number}-{kebab-case-title}.md (if significant decision)
```

## Decision Tree: When to Use Comprehensive Mode

```
START
  |
  ├─ Complexity ≥ 7? ──YES─→ COMPREHENSIVE
  ├─ Security keywords? ──YES─→ COMPREHENSIVE
  ├─ Compliance keywords? ──YES─→ COMPREHENSIVE
  ├─ Breaking changes? ──YES─→ COMPREHENSIVE
  ├─ --docs=comprehensive flag? ──YES─→ COMPREHENSIVE
  |
  └─ All NO? ──→ STANDARD or MINIMAL
```

## Agent Guidance

When in comprehensive mode, agents should:

1. **Generate all core documents** (6 files minimum)
2. **Evaluate conditional triggers** for each of 7 optional docs
3. **Include detailed rationale** for all decisions
4. **Provide examples** for complex concepts
5. **Create traceability** between requirements and implementation
6. **Document trade-offs** and alternatives considered
7. **Include diagrams** where helpful (architecture, sequence, etc.)

## Validation Checklist

Comprehensive mode documentation should:
- [ ] Include all 6 core documents
- [ ] Generate applicable conditional documents
- [ ] Total 6-13 files
- [ ] Provide detailed rationale for decisions
- [ ] Include examples and diagrams
- [ ] Establish traceability
- [ ] Be generated in 30-45 minutes

## Target Metrics

- **Generation time**: 36+ minutes
- **Output length**: 1500-3000 lines total
- **File count**: 6-13 files
- **Token usage**: 500k+ tokens
- **Read time**: 30-60 minutes

## Related

- **Minimal mode**: See `minimal-summary-template.md` for fast documentation
- **Standard mode**: See agent specs for balanced documentation
- **Agent specs**: See `installer/global/agents/*.md` for documentation level behavior
