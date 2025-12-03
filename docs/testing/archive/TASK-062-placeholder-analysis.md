# TASK-062: Placeholder Inconsistency Analysis

## Overview

A detailed analysis of the placeholder mismatch between manifest.json definitions and actual usage in template files.

## Current State Analysis

### Defined Placeholders (In manifest.json)

```json
{
  "placeholders": {
    "ProjectName": {
      "name": "{{ProjectName}}",
      "pattern": "^[a-z][a-z0-9-]*$",
      "example": "my-fullstack-app"
    },
    "FeatureName": {
      "name": "{{FeatureName}}",
      "pattern": "^[a-z][a-z0-9-]*$",
      "example": "discussion"
    },
    "EntityName": {
      "name": "{{EntityName}}",
      "pattern": "^[A-Z][A-Za-z0-9]*$",
      "example": "User"
    },
    "EntityNamePlural": {
      "name": "{{EntityNamePlural}}",
      "pattern": "^[a-z][a-z0-9_]*$",
      "example": "users"
    },
    "ServiceName": {
      "name": "{{ServiceName}}",
      "pattern": "^[a-z][a-z0-9-]*$",
      "example": "worker-service"
    },
    "ApiBaseUrl": {
      "name": "{{ApiBaseUrl}}",
      "pattern": "^https?://.*$",
      "example": "http://localhost:8000"
    }
  }
}
```

**Total Defined**: 6 placeholders

### Actually Used Placeholders (In .template files)

#### Backend Templates

**router.py.template** (87 lines):
```python
from app.schemas.{{entity_name}} import {{EntityName}}Public
from app.crud import {{entity_name}} as crud_{{entity_name}}

@router.get("/", response_model=List[{{EntityName}}Public])
def list_{{entity_name_plural}}(...)
    {{entity_name_plural}} = crud_{{entity_name}}.get_{{entity_name_plural}}(db, ...)

@router.get("/{{{entity_name}}_id}", ...)
def get_{{entity_name}}({{entity_name}}_id: int, ...)
    {{entity_name}} = crud_{{entity_name}}.get_{{entity_name}}(...)

@router.post("/", response_model={{EntityName}}Public, ...)
def create_{{entity_name}}({{entity_name}}_in: {{EntityName}}Create, ...)
```

**Placeholders Used**:
- `{{EntityName}}` ✅ (defined)
- `{{entity_name}}` ❌ (NOT DEFINED)
- `{{entity_name_plural}}` ❌ (NOT DEFINED)

**crud.py.template** (45 lines):
```python
def get_{{entity_name}}(db: Session, {{entity_name}}_id: int):
    return db.query({{EntityName}}).filter(...).first()

def get_{{entity_name_plural}}(db: Session, skip: int = 0, limit: int = 100):
    return db.query({{EntityName}}).offset(skip).limit(limit).all()

def create_{{entity_name}}(db: Session, {{entity_name}}_in: {{EntityName}}Create):
    db_{{entity_name}} = {{EntityName}}(**{{entity_name}}_in.model_dump())
```

**Placeholders Used**:
- `{{EntityName}}` ✅ (defined)
- `{{entity_name}}` ❌ (NOT DEFINED)
- `{{entity_name_plural}}` ❌ (NOT DEFINED)

**schema.py.template** (38 lines):
```python
class {{EntityName}}Create(BaseModel):
    pass

class {{EntityName}}Update(BaseModel):
    pass

class {{EntityName}}Public(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```

**Placeholders Used**:
- `{{EntityName}}` ✅ (defined)

**model.py.template** (13 lines):
```python
class {{EntityName}}(Base):
    __tablename__ = "{{table_name}}"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
```

**Placeholders Used**:
- `{{EntityName}}` ✅ (defined)
- `{{table_name}}` ❌ (NOT DEFINED)

#### Frontend Templates

**component.tsx.template** (27 lines):
```typescript
import { use{{EntityName}}s } from '../hooks/use-{{entity-name}}s'

export const {{EntityName}}List = () => {
  const { data: {{entity-name}}s, isLoading, error } = use{{EntityName}}s()

  {{{entity-name}}s?.map(({{entity-name}}) => (
    <li key={{{entity-name}}.id}>
      {{{entity-name}}.id}
```

**Placeholders Used**:
- `{{EntityName}}` ✅ (defined)
- `{{entity-name}}` ❌ (NOT DEFINED)
- `{{{entity-name}}` ❌ (MALFORMED - extra brace)

**api-hook.ts.template** (58 lines):
```typescript
import { api, {{EntityName}}, {{EntityName}}Create } from 'shared-types'

export function use{{EntityName}}s() {
  return useQuery({
    queryKey: ['{{entity-name-plural}}'],
    queryFn: async () => {
      const response = await api.get<{{EntityName}}[]>('/{{entity-name-plural}}')
```

**Placeholders Used**:
- `{{EntityName}}` ✅ (defined)
- `{{entity-name-plural}}` ❌ (NOT DEFINED)
- `{{{entity-name}}` ❌ (MALFORMED - appears in JSX)

#### Docker Templates

**docker-compose.service.yml.template** (14 lines):
```yaml
{{ServiceName}}:
  build:
    context: ./apps/{{service-path}}
    dockerfile: Dockerfile
  restart: always
  ports:
    - "{{port}}:{{port}}"
  volumes:
    - ./apps/{{service-path}}:/app
  command: {{command}}
```

**Placeholders Used**:
- `{{ServiceName}}` ✅ (defined)
- `{{service-path}}` ❌ (NOT DEFINED)
- `{{port}}` ❌ (NOT DEFINED)
- `{{command}}` ❌ (NOT DEFINED)

## Summary Table

### Used vs. Defined Placeholders

| Placeholder | Defined | Used In | Status |
|-------------|---------|---------|--------|
| `{{ProjectName}}` | ✅ Yes | (unused) | ❌ Unused |
| `{{FeatureName}}` | ✅ Yes | (unused) | ❌ Unused |
| `{{EntityName}}` | ✅ Yes | router.py, crud.py, schema.py, model.py, component.tsx, api-hook.ts | ✅ OK |
| `{{EntityNamePlural}}` | ✅ Yes | (conflicts with `{{entity_name_plural}}`) | ⚠️ Mismatch |
| `{{ServiceName}}` | ✅ Yes | docker-compose.service.yml | ✅ OK |
| `{{ApiBaseUrl}}` | ✅ Yes | (unused) | ❌ Unused |
| `{{entity_name}}` | ❌ No | router.py, crud.py | ❌ MISSING |
| `{{entity_name_plural}}` | ❌ No | router.py, crud.py | ❌ MISSING |
| `{{entity-name}}` | ❌ No | component.tsx, api-hook.ts | ❌ MISSING |
| `{{entity-name-plural}}` | ❌ No | api-hook.ts | ❌ MISSING |
| `{{table_name}}` | ❌ No | model.py | ❌ MISSING |
| `{{port}}` | ❌ No | docker-compose.service.yml | ❌ MISSING |
| `{{service-path}}` | ❌ No | docker-compose.service.yml | ❌ MISSING |
| `{{command}}` | ❌ No | docker-compose.service.yml | ❌ MISSING |

**Summary**:
- Defined: 6
- Used: 12
- Missing (used but not defined): 10
- Unused (defined but not used): 4

## Root Cause Analysis

### Issue 1: Inconsistent Placeholder Naming Across Languages

**Problem**: Different languages use different naming conventions

**Expected Behavior**:
```
Frontend (TypeScript):  {{entity-name}}, {{entity-name-plural}}   (kebab-case)
Backend (Python):       {{entity_name}}, {{entity_name_plural}}   (snake_case)
Manifest (Config):      {{EntityName}}, {{EntityNamePlural}}      (PascalCase)
```

**Actual**:
- Manifest only defines `{{EntityName}}` and `{{EntityNamePlural}}`
- No transformation rules documented
- No case-conversion mechanism in settings.json

### Issue 2: Missing Infrastructure Placeholders

**Problem**: Docker and database configuration requires additional placeholders

**Missing Infrastructure Placeholders**:
- `{{table_name}}` - Database table name (e.g., "users", "products")
- `{{port}}` - Docker service port (e.g., "3000", "8000")
- `{{service-path}}` - Service directory path (e.g., "frontend", "backend")
- `{{command}}` - Docker startup command (e.g., "npm run dev", "uvicorn ...")

**Why They're Missing**:
- Manifest was defined without considering Docker Compose use case
- Infrastructure templates were added later without updating manifest

### Issue 3: Malformed Placeholder Syntax

**Problem**: Some templates have extra braces

**Examples**:
```typescript
{{{entity-name}}s?.map(({{entity-name}}) => (  // Extra brace!
{{{entity-name}}.id}                           // Extra brace!
```

**Should Be**:
```typescript
{{{entity-name}s}?.map(({{entity-name}}) => (  // JSX expression
{{entity-name}}.id                             // Expression inside JSX
```

This is actually a JSX syntax issue, not a placeholder issue. The extra brace is part of JSX expression syntax `{...}`, but it's positioned awkwardly.

## Recommended Fix Strategy

### Option 1: Add Missing Placeholders (Recommended)

**Advantages**:
- Minimal manifest changes
- Each placeholder is explicit
- Clear patterns and examples for each
- Template rendering works correctly

**Implementation**:

```json
"entity_name": {
  "name": "{{entity_name}}",
  "description": "Entity name in snake_case for Python files and database",
  "required": true,
  "pattern": "^[a-z][a-z0-9_]*$",
  "example": "user"
},
"entity_name_plural": {
  "name": "{{entity_name_plural}}",
  "description": "Plural form of entity name in snake_case",
  "required": false,
  "pattern": "^[a-z][a-z0-9_]*$",
  "example": "users",
  "auto_generate": true,
  "auto_generate_from": "entity_name",
  "auto_generate_rule": "pluralize"
},
"entity_name_kebab": {
  "name": "{{entity-name}}",
  "description": "Entity name in kebab-case for TypeScript files",
  "required": true,
  "pattern": "^[a-z][a-z0-9-]*$",
  "example": "user",
  "auto_generate": true,
  "auto_generate_from": "entity_name",
  "auto_generate_rule": "to_kebab_case"
},
"entity_name_plural_kebab": {
  "name": "{{entity-name-plural}}",
  "description": "Plural entity name in kebab-case",
  "required": false,
  "pattern": "^[a-z][a-z0-9-]*$",
  "example": "users",
  "auto_generate": true,
  "auto_generate_from": "entity_name_plural",
  "auto_generate_rule": "to_kebab_case"
},
"table_name": {
  "name": "{{table_name}}",
  "description": "Database table name (snake_case, plural)",
  "required": false,
  "pattern": "^[a-z][a-z0-9_]*$",
  "example": "users",
  "auto_generate": true,
  "auto_generate_from": "entity_name_plural",
  "auto_generate_rule": "to_snake_case"
},
"port": {
  "name": "{{port}}",
  "description": "Port number for Docker service",
  "required": true,
  "pattern": "^[0-9]{4,5}$",
  "example": "3000"
},
"service_path": {
  "name": "{{service-path}}",
  "description": "Path to service directory (frontend or backend)",
  "required": true,
  "pattern": "^[a-z][a-z0-9-]*$",
  "example": "frontend"
},
"command": {
  "name": "{{command}}",
  "description": "Docker service startup command",
  "required": true,
  "example": "npm run dev"
}
```

**Estimated Changes**:
- Add 8 new placeholder objects
- Total JSON size: ~2 KB → ~3.5 KB
- Time to implement: 15 minutes

### Option 2: Add Case Transformation Rules

**Alternative Approach**: Instead of multiple placeholders, define transformation rules

**In settings.json**:
```json
"placeholder_transformations": {
  "EntityName": {
    "to_snake_case": "entity_name",
    "to_kebab_case": "entity-name",
    "to_plural_snake_case": "entity_name_plural",
    "to_plural_kebab_case": "entity-name-plural"
  }
}
```

**Challenges**:
- Template engine must support transformations
- More complex setup
- Less explicit

**Not Recommended** unless template engine has built-in support.

### Option 3: Rename All Placeholders

**Alternative Approach**: Use only PascalCase placeholders with auto-conversions

**Not Recommended** because:
- Requires changing all 7 template files
- Higher risk of introducing errors
- More effort (30+ minutes)

---

## Implementation Steps

### Step 1: Update manifest.json

Add 8 new placeholder definitions to the "placeholders" object.

**File**: `installer/global/templates/react-fastapi-monorepo/manifest.json`
**Lines to modify**: Add entries around line 80 (after existing placeholders)
**Estimated changes**: ~40 new lines

### Step 2: Verify Placeholder Coverage

After changes, verify:
```bash
# Check no unused placeholders in manifest
# Check no undefined placeholders in templates
# Ensure all patterns match actual usage
```

### Step 3: Test Template Rendering

Test that template engine can render all placeholders:
```bash
# Simulate: guardkit init react-fastapi-monorepo
# Verify: All 14 placeholders are prompted
# Verify: All template files render correctly
```

### Step 4: Update Documentation

Update CLAUDE.md with:
- List of all placeholders
- Case transformation rules
- Auto-generation examples

---

## Impact Assessment

### What Breaks Without This Fix

1. **Template Initialization**:
   ```bash
   $ guardkit init react-fastapi-monorepo
   # Users won't be prompted for {{entity_name}}, {{port}}, etc.
   # Generated code will have literal {{placeholder}} strings
   ```

2. **Code Generation**:
   ```python
   # Generated file apps/backend/app/models/{{entity_name}}.py
   class {{EntityName}}(Base):
       __tablename__ = "{{table_name}}"
       # ❌ Broken - placeholders not replaced
   ```

3. **Docker Compose Setup**:
   ```yaml
   # Generated docker-compose.yml service
   ports:
     - "{{port}}:{{port}}"  # ❌ Invalid YAML
   ```

### What Works After Fix

1. **Template Initialization** (works correctly):
   ```bash
   $ guardkit init react-fastapi-monorepo
   ? Enter project name: my-api
   ? Enter entity name: Product
   ? Enter database table name: products
   ? Enter service port: 8000
   # ✅ All placeholders prompted
   ```

2. **Code Generation** (works correctly):
   ```python
   # Generated file apps/backend/app/models/product.py
   class Product(Base):
       __tablename__ = "products"
       # ✅ Correct placeholder replacement
   ```

3. **Docker Compose Setup** (works correctly):
   ```yaml
   # Generated docker-compose.yml service
   ports:
     - "8000:8000"  # ✅ Valid YAML
   ```

---

## Time Estimates

| Task | Duration | Complexity |
|------|----------|-----------|
| Add placeholders to manifest.json | 10 min | Low |
| Verify no syntax errors | 2 min | Low |
| Test template rendering | 3 min | Low |
| Document changes | 5 min | Low |
| **Total** | **20 min** | **Low** |

---

## Conclusion

The placeholder inconsistency is a **critical issue** that prevents the template from functioning correctly. It is a **15-minute fix** with low complexity.

**Recommended Action**: Implement Option 1 (Add Missing Placeholders) immediately to enable template rendering and move to Phase 5 Code Review.

---

**Analysis Date**: 2025-11-09
**Severity**: HIGH
**Fix Priority**: CRITICAL PATH BLOCKER
**Estimated Resolution**: 15-20 minutes
