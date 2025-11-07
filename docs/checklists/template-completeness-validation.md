# Template Completeness Validation Checklist

**Purpose**: Ensure template generation captures complete patterns, not just representative samples

**When to Use**: After generating templates from existing codebases (Phase 6 of /template-create)

**Status**: TASK-020 Deliverable
**Version**: 1.0
**Date**: 2025-11-07

---

## Overview

This checklist validates that generated templates provide **complete scaffolding** for developers, not just examples. It specifically checks for:

1. **CRUD Completeness**: All Create/Read/Update/Delete/List operations
2. **Layer Symmetry**: Operations exist across all architectural layers
3. **Pattern Consistency**: Supporting files (validators, DTOs, etc.) are complete

---

## Pre-Generation Checklist

**Execute BEFORE running /template-create**

### 1. Source Repository Analysis

- [ ] Repository uses clearly identified architectural pattern (MVVM, Clean Architecture, Hexagonal, etc.)
- [ ] Repository has complete CRUD examples in source code
- [ ] Repository structure is consistent (not mixed patterns)
- [ ] Entity/feature examples are production-quality (not just demos)

### 2. Sampling Strategy

- [ ] Max files setting allows sufficient coverage (recommend ≥20 for CRUD-based systems)
- [ ] Sampling strategy is stratified by pattern type, not random
- [ ] All architectural layers are represented in samples
- [ ] Each operation type (Create, Read, Update, Delete, List) is sampled

### 3. Template Context

- [ ] Q&A session captured template purpose (scaffolding vs examples)
- [ ] CRUD completeness requirements are specified
- [ ] Layer symmetry requirements are documented
- [ ] Expected pattern count is estimated

---

## Post-Generation Checklist (Phase 6.5)

**Execute AFTER template generation, BEFORE package assembly**

### Section 1: CRUD Operation Completeness

For each entity identified in templates:

#### 1.1 Create Operation

- [ ] **UseCases Layer**: CreateEntityCommand.cs.template exists
- [ ] **UseCases Layer**: CreateEntityHandler.cs.template exists
- [ ] **Web Layer**: Create.cs.template (endpoint) exists
- [ ] **Web Layer**: CreateEntityRequest.cs.template exists
- [ ] **Web Layer**: CreateEntityResponse.cs.template exists (if non-void)
- [ ] **Web Layer**: CreateEntityValidator.cs.template exists

**If any missing**: ⚠️ INCOMPLETE CREATE OPERATION

#### 1.2 Read Operations

**GetById Operation**:
- [ ] **UseCases Layer**: GetEntityQuery.cs.template exists
- [ ] **UseCases Layer**: GetEntityHandler.cs.template exists
- [ ] **Web Layer**: GetById.cs.template (endpoint) exists
- [ ] **Web Layer**: GetEntityByIdRequest.cs.template exists
- [ ] **Web Layer**: EntityRecord.cs.template or EntityDTO.cs.template exists

**If any missing**: ⚠️ INCOMPLETE GET OPERATION

**List Operation**:
- [ ] **UseCases Layer**: ListEntitiesQuery.cs.template exists
- [ ] **UseCases Layer**: ListEntitiesHandler.cs.template exists
- [ ] **Web Layer**: List.cs.template (endpoint) exists
- [ ] **Web Layer**: ListEntitiesRequest.cs.template exists (if parameterized)
- [ ] **Web Layer**: ListEntitiesResponse.cs.template exists

**If any missing**: ⚠️ INCOMPLETE LIST OPERATION

#### 1.3 Update Operation

- [ ] **UseCases Layer**: UpdateEntityCommand.cs.template exists
- [ ] **UseCases Layer**: UpdateEntityHandler.cs.template exists
- [ ] **Web Layer**: Update.cs.template (endpoint) exists
- [ ] **Web Layer**: UpdateEntityRequest.cs.template exists
- [ ] **Web Layer**: UpdateEntityResponse.cs.template exists (if non-void)
- [ ] **Web Layer**: UpdateEntityValidator.cs.template exists

**If any missing**: 🚨 **CRITICAL - INCOMPLETE UPDATE OPERATION**

#### 1.4 Delete Operation

- [ ] **UseCases Layer**: DeleteEntityCommand.cs.template exists
- [ ] **UseCases Layer**: DeleteEntityHandler.cs.template exists
- [ ] **Web Layer**: Delete.cs.template (endpoint) exists
- [ ] **Web Layer**: DeleteEntityRequest.cs.template exists
- [ ] **Web Layer**: DeleteEntityValidator.cs.template exists (if needed)

**If any missing**: 🚨 **CRITICAL - INCOMPLETE DELETE OPERATION**

### Section 2: Layer Symmetry Validation

For each operation found in **any layer**, verify it exists in **all relevant layers**:

#### 2.1 UseCases → Web Mapping

For each command/query in UseCases layer:

| UseCases Operation | Required Web Endpoint | Status |
|-------------------|----------------------|--------|
| CreateEntityCommand | Create.cs.template | [ ] Present |
| GetEntityQuery | GetById.cs.template | [ ] Present |
| UpdateEntityCommand | Update.cs.template | [ ] Present |
| DeleteEntityCommand | Delete.cs.template | [ ] Present |
| ListEntitiesQuery | List.cs.template | [ ] Present |

**If any Web endpoint missing**: 🚨 **LAYER ASYMMETRY DETECTED**

#### 2.2 Web → UseCases Mapping (Reverse Check)

For each endpoint in Web layer:

| Web Endpoint | Required UseCases Handler | Status |
|-------------|--------------------------|--------|
| Create.cs | CreateEntityHandler.cs | [ ] Present |
| GetById.cs | GetEntityHandler.cs | [ ] Present |
| Update.cs | UpdateEntityHandler.cs | [ ] Present |
| Delete.cs | DeleteEntityHandler.cs | [ ] Present |
| List.cs | ListEntitiesHandler.cs | [ ] Present |

**If any handler missing**: 🚨 **ORPHANED ENDPOINT (handler missing)**

#### 2.3 Infrastructure Layer (if applicable)

- [ ] Repository interfaces exist for all CRUD operations
- [ ] Specifications/query objects exist for complex queries
- [ ] Database configurations exist for entities

### Section 3: Pattern-Specific Validation

#### 3.1 REPR Pattern (FastEndpoints)

For each endpoint, verify:
- [ ] Request DTO exists
- [ ] Response DTO exists (if non-void)
- [ ] Validator exists
- [ ] Endpoint class has proper configuration

**Count Check**:
- Expected: 5 CRUD operations × 4 files each = 20 files per entity (minimum)
- Actual: ___ files

**If count < 20**: ⚠️ Missing supporting files

#### 3.2 CQRS Pattern (MediatR)

For each operation, verify:
- [ ] Command/Query class exists
- [ ] Handler implements ICommandHandler or IQueryHandler
- [ ] Result type specified (Result<T>, ErrorOr<T>, etc.)

#### 3.3 DDD Pattern (Domain-Driven Design)

For entities:
- [ ] Entity aggregate root template exists
- [ ] Value object templates exist (if used)
- [ ] Domain event templates exist (if event-driven)
- [ ] Specification templates exist (for complex queries)

### Section 4: File Count Validation

#### 4.1 Expected Counts

For a **single entity** in Clean Architecture with CRUD:

| Layer | Expected Files | Actual Files | Status |
|-------|---------------|--------------|--------|
| **Core** | 5-8 | ___ | [ ] |
| Entity, ValueObjects, Events, Specifications | | | |
| **UseCases** | 10-15 | ___ | [ ] |
| 5 Commands/Queries + 5 Handlers + DTOs | | | |
| **Web** | 15-20 | ___ | [ ] |
| 5 Endpoints + 5 Requests + 5 Responses + 5 Validators | | | |
| **Infrastructure** | 2-5 | ___ | [ ] |
| Repositories, EF Configs | | | |
| **TOTAL** | 32-48 | ___ | [ ] |

**If total < 30 for complete CRUD**: 🚨 **TEMPLATES LIKELY INCOMPLETE**

#### 4.2 Ratio Validation

- [ ] Core:UseCases:Web ratio is approximately 1:2:3
- [ ] Each operation has minimum 3 files (command/query, handler, endpoint)
- [ ] Supporting files (validators, DTOs) present for all operations

### Section 5: Quality Validation

#### 5.1 Placeholder Consistency

- [ ] All templates use consistent placeholder naming (e.g., {{EntityName}}, {{ProjectName}})
- [ ] Placeholders are PascalCase
- [ ] Same placeholders used across related files
- [ ] No hard-coded entity names remain

#### 5.2 Pattern Fidelity

- [ ] Templates match source repository patterns
- [ ] No pattern deviations from original code
- [ ] Framework-specific patterns preserved (e.g., FastEndpoints routing)
- [ ] Naming conventions match source

#### 5.3 Code Quality

- [ ] Templates compile (syntax-valid)
- [ ] Using statements/imports present
- [ ] Namespace structure consistent
- [ ] Comments and documentation preserved

---

## Issue Resolution

### If CRUD Incompleteness Detected

**Severity**: 🚨 Critical

**Impact**: Generated projects will have incomplete APIs

**Actions**:
1. **Identify Missing Operations**: Use checklist to list all missing templates
2. **Verify in Source**: Confirm operations exist in source repository
3. **Manual Generation**: Create missing templates using similar operations as reference
4. **Re-validate**: Run checklist again after fixes

**Example**: If Update operation missing:
```bash
# 1. Find similar Create operation in templates
templates/Web/Endpoints/Create.cs.template

# 2. Copy and modify for Update
templates/Web/Endpoints/Update.cs.template

# 3. Update method from POST to PUT
# 4. Update route to include ID parameter
# 5. Update command to UpdateEntityCommand
# 6. Test compilation
```

### If Layer Asymmetry Detected

**Severity**: 🚨 Critical

**Impact**: Handlers without endpoints (unusable) or endpoints without handlers (runtime errors)

**Actions**:
1. **Determine Direction**: UseCases missing Web? or Web missing UseCases?
2. **Generate Missing Layer**: Create templates for missing layer
3. **Verify Integration**: Check handler is called from endpoint
4. **Test Flow**: Trace request through all layers

### If Pattern Inconsistency Detected

**Severity**: ⚠️ Medium

**Impact**: Mixed patterns, confusing for users

**Actions**:
1. **Identify Pattern**: REPR? MVC? Custom?
2. **Standardize**: Ensure all operations follow same pattern
3. **Update Documentation**: Note any intentional variations in CLAUDE.md

---

## Automated Validation Script

**Future Enhancement**: Automate this checklist with script

```bash
#!/bin/bash
# template-completeness-check.sh

TEMPLATE_DIR=$1

echo "Validating template completeness: $TEMPLATE_DIR"

# Check CRUD operations
for entity in $(find $TEMPLATE_DIR/templates/UseCases -type d -depth 1); do
    entity_name=$(basename $entity)

    echo "Checking entity: $entity_name"

    # Check operations
    operations=("Create" "Get" "Update" "Delete" "List")
    for op in "${operations[@]}"; do
        # Check UseCases
        if [ ! -f "$TEMPLATE_DIR/templates/UseCases/$op/${op}${entity_name}Handler.cs.template" ]; then
            echo "  ❌ Missing UseCases/$op handler"
        else
            echo "  ✅ UseCases/$op handler present"
        fi

        # Check Web
        if [ ! -f "$TEMPLATE_DIR/templates/Web/Endpoints/${op}.cs.template" ]; then
            echo "  ❌ Missing Web/$op endpoint"
        else
            echo "  ✅ Web/$op endpoint present"
        fi
    done
done
```

---

## False Negative Score Calculation

**Purpose**: Quantify template completeness

**Formula**:
```
False Negative Score = (Files Generated / Files Expected) × 10

Where:
- Files Expected = Total CRUD operations × Files per operation
- Files Generated = Actual template count
```

**Example** (ardalis-clean-architecture):
```
Expected: 5 operations × 6-7 files each = 33 files
Generated: 26 files
Score: (26 / 33) × 10 = 7.9/10

With fixes: 33/33 × 10 = 10/10
```

**Interpretation**:
- **9-10/10**: Excellent - minimal gaps
- **7-8/10**: Good - minor gaps
- **5-6/10**: Fair - significant gaps
- **<5/10**: Poor - critical gaps

**Target**: ≥8/10 for production templates

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-07 | Initial checklist from TASK-020 investigation | Task-Manager |

---

## References

- **Root Cause Analysis**: [TASK-020-root-cause-analysis.md](../analysis/TASK-020-root-cause-analysis.md)
- **Improvement Proposals**: [TASK-020-improvement-proposals.md](../analysis/TASK-020-improvement-proposals.md)
- **Template Creation Command**: [template-create.md](../../installer/global/commands/template-create.md)

---

**Document Status**: ✅ Complete
**Usage**: Use after every template generation
**Enforcement**: Recommended for all brownfield templates
