# Template Quality Validation Guide

**Purpose**: Comprehensive guide for validating template generation quality
**Audience**: Template creators, QA engineers, developers
**Version**: 1.0
**Date**: 2025-11-07
**Related**: TASK-020 Investigation

---

## Overview

This guide provides systematic procedures for validating template generation quality, focusing on **completeness, accuracy, and usability**.

**Three Quality Dimensions**:
1. **False Positives**: Templates that shouldn't exist (hallucinations)
2. **False Negatives**: Templates that should exist but are missing (gaps)
3. **Fidelity**: Templates match source patterns accurately

---

## Quick Reference

| Validation Type | When to Use | Duration | Target Score |
|----------------|-------------|----------|--------------|
| **Quick Check** | After every generation | 5-10 min | Pass/Fail |
| **Standard Validation** | Before deploying template | 30-45 min | ≥8/10 overall |
| **Comprehensive Audit** | Production templates | 2-3 hours | ≥9/10 overall |

---

## Section 1: False Negative Validation

**Definition**: Missing templates that should have been generated

**Why Critical**: Incomplete templates = broken scaffolding

### 1.1 CRUD Completeness Check

**For Clean Architecture / Layered Systems**:

```bash
# Quick count validation
echo "Expected: 5 operations × 6-7 files = 33 files minimum"
find templates/ -name "*.template" | wc -l

# Operation breakdown
echo "Create operations:"
find templates/ -name "*Create*.template" | wc -l

echo "Update operations:"
find templates/ -name "*Update*.template" | wc -l

echo "Delete operations:"
find templates/ -name "*Delete*.template" | wc -l
```

**Expected Ratios**:
- Create : Update : Delete ≈ 1 : 1 : 1
- If Create = 5 files, Update should ≈ 5 files
- **Warning**: If Create = 5, Update = 0 → Critical gap

**Manual Checklist**:
```markdown
For each entity (e.g., "Contributor", "Product"):

Create Operation:
- [ ] Command/Request class
- [ ] Handler/Service class
- [ ] Web endpoint/controller
- [ ] Validator
- [ ] Response DTO (if applicable)

Read Operations:
- [ ] GetById: Query + Handler + Endpoint
- [ ] List: Query + Handler + Endpoint

Update Operation:
- [ ] Command/Request class
- [ ] Handler/Service class
- [ ] Web endpoint/controller
- [ ] Validator
- [ ] Response DTO (if applicable)

Delete Operation:
- [ ] Command/Request class
- [ ] Handler/Service class
- [ ] Web endpoint/controller
- [ ] Validator (if applicable)
```

### 1.2 Layer Symmetry Check

**Concept**: Operations must exist across all architectural layers

```bash
# Check for symmetry violations
# Example: UseCases has Update but Web doesn't

# List UseCases operations
find templates/UseCases -name "*.template" | sed 's/.*\///' | cut -d'E' -f1 | sort -u

# List Web operations
find templates/Web -name "*.template" | sed 's/.*\///' | cut -d'E' -f1 | sort -u

# Compare: Operations in UseCases should appear in Web
```

**Symmetry Rules**:
1. **UseCases → Web**: Every command/query needs an endpoint
2. **Web → UseCases**: Every endpoint needs a handler
3. **Core → UseCases**: Domain entities need use cases
4. **UseCases → Infrastructure**: Handlers need repository implementations

**Warning Signs**:
- UpdateEntityHandler.cs exists but no Update.cs endpoint → ⚠️ Orphaned handler
- Update.cs endpoint exists but no UpdateEntityHandler.cs → ⚠️ Orphaned endpoint

### 1.3 Supporting File Completeness

**For each primary file, check for supporting files**:

| Primary File | Required Supporting Files | Missing = Issue |
|--------------|--------------------------|-----------------|
| Create.cs (endpoint) | CreateRequest.cs, CreateValidator.cs | High |
| CreateCommand.cs | CreateCommandHandler.cs | Critical |
| Update.cs | UpdateRequest.cs, UpdateResponse.cs, UpdateValidator.cs | High |
| Entity.cs | EntityDTO.cs, EntityConfiguration.cs (EF) | Medium |

### 1.4 False Negative Scoring

**Formula**:
```
False Negative Score = (Templates Generated / Templates Expected) × 10

Where:
  Templates Expected = Entity Count × Operations per Entity × Files per Operation
```

**Example** (ardalis-clean-architecture):
```
Entity Count: 1 (Contributor)
Operations: 5 (Create, GetById, Update, Delete, List)
Files per Operation: 6-7 (command, handler, endpoint, request, response, validator)

Expected: 1 × 5 × 6.5 = 33 files
Generated: 26 files
Score: (26 / 33) × 10 = 7.9/10
```

**Interpretation**:
- **9-10/10**: Excellent (≤10% missing)
- **7-8/10**: Good (11-30% missing)
- **5-6/10**: Fair (31-50% missing)
- **<5/10**: Poor (>50% missing)

**Target**: ≥8/10 for production templates

---

## Section 2: False Positive Validation

**Definition**: Templates that shouldn't exist (hallucinations, wrong patterns)

### 2.1 Pattern Verification

**Check**: Do generated patterns actually exist in source?

```bash
# For each template, verify source file exists
for template in $(find templates/ -name "*.template"); do
    # Extract original path from template metadata or filename
    # Check if source file exists in repository

    echo "Template: $template"
    echo "Source: [check source repo]"
    echo "Exists: [yes/no]"
done
```

**Manual Process**:
1. Open template file
2. Read original_path comment (if present)
3. Check if file exists in source repository
4. Verify pattern is actively used (not deprecated/experimental)

### 2.2 Technology Stack Accuracy

**Verify detected technologies against reality**:

```markdown
Check manifest.json:

Detected Language: C#
✓ Verify: Check source .csproj files

Detected Frameworks:
- ASP.NET Core 9.0 ✓
- FastEndpoints 5.x ✓
- MediatR 12.x ✓

Check: Are these actually used?
- Search source for using statements
- Check NuGet package references
- Verify version numbers
```

### 2.3 Pattern Hallucination Check

**Common Hallucinations**:
- CQRS detected when source uses simple CRUD
- MVVM detected in non-UI project
- Event sourcing detected when not present
- Microservices when it's a monolith

**Validation**:
```markdown
For each pattern in manifest.patterns[]:

Pattern: "CQRS"
Evidence in Source:
- [ ] Separate command/query classes exist
- [ ] Handlers implement ICommandHandler/IQueryHandler
- [ ] MediatR or similar mediator library used
- [ ] Clear command/query separation in codebase

If <3 checkboxes checked → Likely false positive
```

### 2.4 False Positive Scoring

**Formula**:
```
False Positive Score = (1 - (False Positives / Total Templates)) × 10

Where:
  False Positives = Templates that shouldn't exist
  Total Templates = All generated templates
```

**Example**:
```
Generated: 26 templates
False Positives: 0 (all verified)
Score: (1 - 0/26) × 10 = 10/10 (perfect)
```

**Target**: ≥9/10 (≤10% false positives acceptable)

---

## Section 3: Pattern Fidelity Validation

**Definition**: Templates accurately represent source patterns

### 3.1 Code Structure Match

**Pick 3-5 random templates, compare to source**:

```markdown
Template: CreateEntityHandler.cs.template

Source: CleanArchitecture-ardalis/src/.../CreateContributorHandler.cs

Structure Match:
- [ ] Same class hierarchy
- [ ] Same dependencies (interfaces)
- [ ] Same method signatures
- [ ] Same error handling pattern
- [ ] Same return types

Code Quality:
- [ ] Using statements present
- [ ] Namespace structure correct
- [ ] Comments preserved (if relevant)
- [ ] Formatting consistent

Placeholder Quality:
- [ ] "Contributor" → {{EntityName}} ✓
- [ ] "contributors" → {{entityNamePlural}} ✓
- [ ] "CleanArchitecture" → {{ProjectName}} ✓
- [ ] No hard-coded entity names remain
```

**Scoring**:
- 100% match: 10/10
- 90-99% match: 8-9/10
- 80-89% match: 6-7/10
- <80% match: <6/10 (needs revision)

### 3.2 Pattern Consistency

**Check consistency across templates**:

```markdown
Naming Conventions:
- [ ] All commands end with "Command"
- [ ] All handlers end with "Handler"
- [ ] All endpoints follow REST conventions
- [ ] All validators end with "Validator"

Placeholder Consistency:
- [ ] {{EntityName}} used consistently (not {{Entity}} in some files)
- [ ] Case consistency (PascalCase vs camelCase)
- [ ] Namespace patterns consistent

Pattern Application:
- [ ] All handlers use same Result<T> pattern
- [ ] All endpoints use same REPR pattern
- [ ] All validators use same FluentValidation style
```

### 3.3 Documentation Quality

**Check generated CLAUDE.md**:

```markdown
Architecture Section:
- [ ] Accurately describes source architecture
- [ ] Layer responsibilities clear
- [ ] Dependency flow documented
- [ ] No hallucinated patterns

Code Examples:
- [ ] Examples are from actual source
- [ ] Examples demonstrate key patterns
- [ ] Examples compile and run
- [ ] Placeholders correctly applied

Quality Standards:
- [ ] Testing strategies mentioned
- [ ] Coverage expectations specified
- [ ] SOLID principles explained
- [ ] Best practices documented
```

---

## Section 4: Usability Validation

**Definition**: Template is actually usable by developers

### 4.1 Template Application Test

**Best validation: Actually use the template**

```bash
# 1. Create test project
guardkit init [template-name]

# 2. Answer placeholder prompts
# - ProjectName: "TestApp"
# - EntityName: "Product"

# 3. Check generated files
ls -R

# 4. Try to compile
dotnet build  # or npm run build, etc.

# 5. Check for errors
# Expected: Should compile successfully
```

**Checklist**:
- [ ] All files generated (no missing templates)
- [ ] Placeholders replaced correctly
- [ ] Project compiles without errors
- [ ] Tests run (even if they fail due to missing implementation)
- [ ] Directory structure makes sense

### 4.2 Developer Experience

**Put yourself in user's shoes**:

```markdown
As a developer using this template:

Discovery:
- [ ] Can I understand what this template provides?
- [ ] Is the README clear?
- [ ] Are examples helpful?

Getting Started:
- [ ] Can I initialize a project easily?
- [ ] Are placeholder prompts clear?
- [ ] Is the generated project structure intuitive?

Development:
- [ ] Can I add a new entity easily?
- [ ] Do I understand the patterns?
- [ ] Are there code examples to follow?

Troubleshooting:
- [ ] Is documentation helpful?
- [ ] Are error messages clear?
- [ ] Can I find help/examples?
```

### 4.3 Completeness for Real Use

**Can user build a complete feature?**

```markdown
Scenario: User wants to add "Product" entity with full CRUD

With this template, can they generate:
- [ ] Product domain entity
- [ ] All CRUD operations (Create, Read, Update, Delete, List)
- [ ] All web endpoints (POST, GET, PUT, DELETE)
- [ ] All validation logic
- [ ] Database configuration
- [ ] Tests for all operations

If any missing: Template is incomplete for real use
```

---

## Section 5: Automated Validation

### 5.1 Validation Script

**Create automated checker**:

```bash
#!/bin/bash
# template-quality-check.sh

TEMPLATE_DIR=$1
SCORE=0
MAX_SCORE=100

echo "Validating template: $TEMPLATE_DIR"
echo "=================================="

# Check 1: CRUD Completeness (30 points)
echo "1. CRUD Completeness"
create_count=$(find "$TEMPLATE_DIR" -name "*Create*.template" | wc -l)
update_count=$(find "$TEMPLATE_DIR" -name "*Update*.template" | wc -l)
delete_count=$(find "$TEMPLATE_DIR" -name "*Delete*.template" | wc -l)

if [ "$update_count" -eq 0 ] || [ "$delete_count" -eq 0 ]; then
    echo "   ❌ FAIL: Missing Update or Delete operations"
    SCORE=$((SCORE + 0))
else
    echo "   ✅ PASS: All CRUD operations present"
    SCORE=$((SCORE + 30))
fi

# Check 2: Layer Symmetry (30 points)
echo "2. Layer Symmetry"
use_cases_ops=$(find "$TEMPLATE_DIR/templates/UseCases" -name "*.template" 2>/dev/null | wc -l)
web_ops=$(find "$TEMPLATE_DIR/templates/Web" -name "*.template" 2>/dev/null | wc -l)

ratio=$(echo "scale=2; $web_ops / $use_cases_ops" | bc)
if (( $(echo "$ratio >= 0.8" | bc -l) )) && (( $(echo "$ratio <= 1.5" | bc -l) )); then
    echo "   ✅ PASS: Layer symmetry maintained (ratio: $ratio)"
    SCORE=$((SCORE + 30))
else
    echo "   ⚠️  WARN: Layer asymmetry detected (ratio: $ratio)"
    SCORE=$((SCORE + 15))
fi

# Check 3: File Count (20 points)
echo "3. File Count"
total_files=$(find "$TEMPLATE_DIR/templates" -name "*.template" | wc -l)
if [ "$total_files" -ge 30 ]; then
    echo "   ✅ PASS: Sufficient template count ($total_files)"
    SCORE=$((SCORE + 20))
elif [ "$total_files" -ge 20 ]; then
    echo "   ⚠️  WARN: Low template count ($total_files)"
    SCORE=$((SCORE + 10))
else
    echo "   ❌ FAIL: Very low template count ($total_files)"
    SCORE=$((SCORE + 0))
fi

# Check 4: Documentation (20 points)
echo "4. Documentation"
if [ -f "$TEMPLATE_DIR/CLAUDE.md" ] && [ -f "$TEMPLATE_DIR/README.md" ]; then
    echo "   ✅ PASS: Documentation files present"
    SCORE=$((SCORE + 20))
else
    echo "   ❌ FAIL: Missing documentation"
    SCORE=$((SCORE + 0))
fi

# Final Score
echo ""
echo "=================================="
echo "FINAL SCORE: $SCORE / $MAX_SCORE"
echo "=================================="

if [ "$SCORE" -ge 80 ]; then
    echo "✅ QUALITY: Production Ready"
    exit 0
elif [ "$SCORE" -ge 60 ]; then
    echo "⚠️  QUALITY: Needs Improvement"
    exit 1
else
    echo "❌ QUALITY: Not Ready for Use"
    exit 2
fi
```

### 5.2 CI/CD Integration

```yaml
# .github/workflows/template-quality.yml
name: Template Quality Check

on:
  pull_request:
    paths:
      - 'installer/global/templates/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run quality check
        run: |
          for template in installer/global/templates/*/; do
            ./scripts/template-quality-check.sh "$template"
          done

      - name: Fail if score <80
        run: |
          # Check exit codes from above
          # Fail PR if any template scored <80
```

---

## Section 6: Scoring Summary

### 6.1 Overall Quality Score

**Composite Score Formula**:
```
Overall Quality = (
    (False Negative Score × 0.4) +
    (False Positive Score × 0.3) +
    (Fidelity Score × 0.2) +
    (Usability Score × 0.1)
)

Where each component is 0-10
```

**Example** (ardalis-clean-architecture after fixes):
```
False Negative: 10/10 (all CRUD operations present)
False Positive: 10/10 (no hallucinations)
Fidelity: 9/10 (excellent code match)
Usability: 8/10 (compiles, usable, good docs)

Overall = (10×0.4) + (10×0.3) + (9×0.2) + (8×0.1)
        = 4.0 + 3.0 + 1.8 + 0.8
        = 9.6/10 ✅
```

### 6.2 Grade Assignment

| Score | Grade | Meaning | Action |
|-------|-------|---------|--------|
| 9.5-10 | A+ | Exceptional | Deploy immediately |
| 9.0-9.4 | A | Excellent | Minor polish, deploy |
| 8.5-8.9 | A- | Very Good | Fix minor issues |
| 8.0-8.4 | B+ | Good | Fix notable issues |
| 7.0-7.9 | B | Acceptable | Significant work needed |
| <7.0 | C or below | Not Ready | Major rework required |

**Production Threshold**: ≥8.5/10

---

## Section 7: Issue Remediation

### 7.1 Common Issues and Fixes

**Issue**: Missing Update/Delete Operations
**Severity**: Critical
**Fix**:
1. Identify similar operation (e.g., Create)
2. Copy template
3. Modify for Update/Delete
4. Update placeholders
5. Test compilation
6. Re-validate

**Issue**: Layer Asymmetry (handler without endpoint)
**Severity**: Critical
**Fix**:
1. Find handler template
2. Create corresponding endpoint template
3. Wire up handler call in endpoint
4. Add validators and DTOs
5. Test flow

**Issue**: Pattern Hallucination
**Severity**: Medium
**Fix**:
1. Remove hallucinated pattern from manifest
2. Remove templates for that pattern
3. Update CLAUDE.md to not mention pattern
4. Re-validate

### 7.2 Continuous Improvement

**After Each Template Generation**:
1. Run validation checklist
2. Document findings
3. Update validation script for new checks
4. Share lessons learned with team
5. Improve prompts/process

---

## References

- [Root Cause Analysis](../analysis/TASK-020-root-cause-analysis.md)
- [Improvement Proposals](../analysis/TASK-020-improvement-proposals.md)
- [Completeness Validation Checklist](../checklists/template-completeness-validation.md)
- [Implementation Plan](../implementation-plans/TASK-020-completeness-improvement-plan.md)

---

**Document Status**: ✅ Complete
**Version**: 1.0
**Last Updated**: 2025-11-07
