# Template Validation Checklist Usage Guide

**Version**: 1.0.0
**Status**: Active
**Date**: 2025-01-07

## Overview

The Template Validation Checklist is a comprehensive guide included in every generated CLAUDE.md file to help developers verify template completeness before use.

## Purpose

The validation checklist ensures:
1. ✅ All CRUD operations are present
2. ✅ Layer symmetry is maintained
3. ✅ Pattern completeness (REPR, Repository, etc.)
4. ✅ Consistent naming and placeholder usage

## Location

The validation checklist appears in CLAUDE.md under **Quality Standards**:

```markdown
# Quality Standards

## Testing
[Testing requirements...]

## Code Quality
[Code quality metrics...]

## Template Validation Checklist    ← HERE

Before using this template, verify:

### CRUD Completeness
- [ ] Create operation (endpoint + handler + validator)
- [ ] Read operation (GetById + List + handlers)
- [ ] Update operation (endpoint + handler + validator)
- [ ] Delete operation (endpoint + handler + validator)

### Layer Symmetry
[...]
```

## Checklist Structure

### 1. CRUD Completeness

Verifies all CRUD operations are present:

```markdown
### CRUD Completeness
- [ ] Create operation (endpoint + handler + validator)
- [ ] Read operation (GetById + List + handlers)
- [ ] Update operation (endpoint + handler + validator)
- [ ] Delete operation (endpoint + handler + validator)
```

**What to Check:**
- ✓ Create: POST endpoint, CreateHandler, CreateValidator
- ✓ Read: GET by ID, GET collection (List), handlers for both
- ✓ Update: PUT endpoint, UpdateHandler, UpdateValidator
- ✓ Delete: DELETE endpoint, DeleteHandler

**Common Issues:**
- ❌ Missing List operation (only GetById present)
- ❌ Missing validators for Create/Update
- ❌ Handler present but no endpoint (or vice versa)

### 2. Layer Symmetry

Verifies operations exist across all relevant layers:

```markdown
### Layer Symmetry
- [ ] All UseCases commands have Web endpoints
- [ ] All Web endpoints have UseCases handlers
- [ ] Repository interfaces exist for all operations
```

**What to Check:**
- ✓ UseCases/CreateProduct → Web/Products/Create
- ✓ Web/Products/Update → UseCases/UpdateProduct
- ✓ All operations → IProductRepository methods

**Common Issues:**
- ❌ Web endpoint exists but no UseCases handler
- ❌ UseCases handler exists but no Web endpoint
- ❌ Repository missing methods for some operations

### 3. REPR Pattern (if applicable)

Verifies REPR pattern completeness for FastEndpoints:

```markdown
### REPR Pattern (if using FastEndpoints)
- [ ] Each endpoint has Request/Response/Validator
- [ ] Validators use FluentValidation
- [ ] Routes follow RESTful conventions
```

**What to Check:**
- ✓ Create.cs + CreateRequest.cs + CreateResponse.cs + CreateValidator.cs
- ✓ Validators inherit AbstractValidator<TRequest>
- ✓ Routes: POST /products, GET /products/{id}, etc.

**Common Issues:**
- ❌ Missing Response DTO (using void when should return data)
- ❌ Missing Validator (skipped validation)
- ❌ Non-RESTful routes (GET /createProduct instead of POST /products)

### 4. Pattern Consistency

Verifies consistent patterns across all entities:

```markdown
### Pattern Consistency
- [ ] All entities follow same operation structure
- [ ] Naming conventions consistent
- [ ] Placeholders consistently applied
```

**What to Check:**
- ✓ All entities have same CRUD operations
- ✓ Naming: CreateProduct, CreateOrder, Create{{EntityName}}
- ✓ Placeholders: {{EntityName}}, {{EntityNamePlural}}, {{Namespace}}

**Common Issues:**
- ❌ Some entities have 4 operations, others have 5
- ❌ Inconsistent naming (CreateProduct vs ProductCreate)
- ❌ Inconsistent placeholders ({{Entity}} vs {{EntityName}})

## Usage Workflow

### Step 1: Generate Template
```bash
guardkit template-create \
  --source /path/to/codebase \
  --output /path/to/template \
  --name my-template
```

### Step 2: Open CLAUDE.md
```bash
cd /path/to/template
cat .claude/CLAUDE.md
```

### Step 3: Find Validation Checklist
Search for "## Template Validation Checklist" in CLAUDE.md

### Step 4: Check Each Item
Go through each checkbox and verify in the template:

```bash
# Example: Verify CRUD completeness for Products
find templates/ -name "*Product*" -o -name "*product*"

# Should find:
# - CreateProduct / Create
# - GetProduct / Get (by ID)
# - ListProducts / List
# - UpdateProduct / Update
# - DeleteProduct / Delete
```

### Step 5: Document Results
Mark checkboxes in CLAUDE.md:

```markdown
### CRUD Completeness
- [x] Create operation (endpoint + handler + validator)
- [x] Read operation (GetById + List + handlers)
- [x] Update operation (endpoint + handler + validator)
- [x] Delete operation (endpoint + handler + validator)
```

### Step 6: Fix Issues (if any)
If items are unchecked, add missing files:

```bash
# Example: Add missing List operation
cp templates/Domain/Get{{EntityName}}.cs.template \
   templates/Domain/List{{EntityNamePlural}}.cs.template

# Edit to implement List functionality
```

## Validation Tools

### Manual Validation Script

```bash
#!/bin/bash
# validate_template.sh

TEMPLATE_DIR=$1
ENTITY=$2

echo "Validating CRUD completeness for $ENTITY..."

# Check operations
operations=("Create" "Get" "List" "Update" "Delete")
for op in "${operations[@]}"; do
  if find "$TEMPLATE_DIR" -name "*${op}*${ENTITY}*" -o -name "*${ENTITY}*${op}*" | grep -q .; then
    echo "✓ $op operation found"
  else
    echo "✗ $op operation MISSING"
  fi
done
```

### Automated Validation (Future)

```python
# validate_completeness.py (TASK-040)
from installer.global.lib.validation import validate_template_completeness

result = validate_template_completeness(
    template_path="/path/to/template",
    checklist_path=".claude/CLAUDE.md"
)

if result.is_complete:
    print("✓ All checklist items verified")
else:
    print("✗ Incomplete:")
    for item in result.missing_items:
        print(f"  - {item}")
```

## Integration with Phases

### Phase 1: Completeness Validation (TASK-040)
- Automated validation uses checklist as ground truth
- Validation failures reference specific checklist items
- Checklist updated if validation finds issues

### Phase 2: Stratified Sampling (TASK-041)
- Sampling strategy ensures all checklist items have examples
- If checklist item missing from samples → flagged for manual review

### Phase 3: Enhanced Prompting (TASK-042)
- AI prompted to generate templates that pass checklist
- Checklist items align with prompt requirements
- Defense-in-depth: Prompt + Checklist + Validation

## Customization

### Adding Custom Checklist Items

Edit `installer/global/lib/template_generator/claude_md_generator.py`:

```python
def _generate_validation_checklist(self) -> List[str]:
    checklist = [
        # ... existing items ...
    ]

    # Add custom item
    if self.analysis.has_custom_pattern:
        checklist.extend([
            "### Custom Pattern",
            "- [ ] CustomPattern files present",
            "- [ ] CustomPattern follows conventions",
            "",
        ])

    return checklist
```

### Template-Specific Checklists

Create checklist variants for different template types:

```python
def _generate_validation_checklist(self) -> List[str]:
    if self.analysis.template_type == "web-api":
        return self._generate_web_api_checklist()
    elif self.analysis.template_type == "mobile-app":
        return self._generate_mobile_app_checklist()
    else:
        return self._generate_default_checklist()
```

## Best Practices

### DO ✅
- Use checklist before generating projects from template
- Document why items are unchecked (if intentional)
- Keep checklist up-to-date with template changes
- Reference checklist in PR reviews
- Share checklist with team members

### DON'T ❌
- Skip validation because template "looks complete"
- Assume AI generated complete templates
- Use unchecked template in production
- Modify checklist without updating templates
- Ignore checklist warnings

## Troubleshooting

### Issue: Checklist Missing from CLAUDE.md

**Symptom**: No "Template Validation Checklist" section

**Cause**: CLAUDE.md generated before TASK-042

**Solution**:
```bash
# Regenerate CLAUDE.md with enhanced version
python -m installer.global.lib.template_generator.claude_md_generator \
  --template /path/to/template \
  --regenerate
```

### Issue: Checklist Items Don't Match Template

**Symptom**: Checklist references patterns not in template

**Cause**: Generic checklist not customized for template type

**Solution**:
1. Review template architecture
2. Edit checklist to match actual patterns
3. Document customization in CLAUDE.md

### Issue: All Items Checked But Template Incomplete

**Symptom**: Validation passes but CRUD operations missing

**Cause**: Checklist completed without actual verification

**Solution**:
1. Use validation script to verify programmatically
2. Don't trust human checkbox marking
3. Run TASK-040 completeness validation

## Examples

### Example 1: FastEndpoints Clean Architecture

```markdown
## Template Validation Checklist

Before using this template, verify:

### CRUD Completeness
- [x] Create operation (endpoint + handler + validator)
- [x] Read operation (GetById + List + handlers)
- [x] Update operation (endpoint + handler + validator)
- [x] Delete operation (endpoint + handler + validator)

### Layer Symmetry
- [x] All UseCases commands have Web endpoints
- [x] All Web endpoints have UseCases handlers
- [x] Repository interfaces exist for all operations

### REPR Pattern (if using FastEndpoints)
- [x] Each endpoint has Request/Response/Validator
- [x] Validators use FluentValidation
- [x] Routes follow RESTful conventions

### Pattern Consistency
- [x] All entities follow same operation structure
- [x] Naming conventions consistent
- [x] Placeholders consistently applied
```

### Example 2: MAUI MVVM Application

```markdown
## Template Validation Checklist

Before using this template, verify:

### CRUD Completeness
- [x] Create operation (ViewModel + View + Domain)
- [x] Read operation (List + Detail ViewModels)
- [x] Update operation (ViewModel + View + Domain)
- [x] Delete operation (Command + Domain)

### Layer Symmetry
- [x] All Domain operations have ViewModels
- [x] All ViewModels have Views
- [x] All Views have navigation setup

### MVVM Pattern
- [x] All ViewModels implement INotifyPropertyChanged
- [x] Commands use ICommand interface
- [x] Views bind to ViewModels correctly

### Pattern Consistency
- [x] All entities follow same operation structure
- [x] Naming conventions consistent (EntityViewModel, EntityPage)
- [x] Placeholders consistently applied
```

## Reference

- [Enhanced Prompt Format](../specifications/enhanced-prompt-format.md)
- [Template Generator Implementation](../../installer/global/lib/template_generator/)
- [Completeness Validation (TASK-040)](../../tasks/completed/TASK-040-*.md)
- [TASK-020 Implementation Plan](../implementation-plans/TASK-020-completeness-improvement-plan.md)

## Change Log

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-01-07 | Initial guide for TASK-042 | AI Assistant |

## Feedback

If you find issues with the validation checklist or have suggestions for improvements, please:
1. Document the issue in CLAUDE.md
2. Create a task for enhancement
3. Update this guide after implementation
