# Bidirectional Optional Integration Architecture

## Overview

taskwright and require-kit implement a **bidirectional optional integration model** where both packages work independently with optional mutual enhancement when installed together.

## Architecture Principles

### 1. Independence
- **taskwright** works standalone: Task execution, quality gates, architectural review, test enforcement
- **require-kit** works standalone: Requirements engineering (EARS), BDD generation, epic/feature hierarchy
- Neither package hard-depends on the other

### 2. Mutual Discovery
- Both packages detect each other via marker files in `~/.agentecflow/`
- Feature detection library (`lib/feature_detection.py`) provides graceful degradation
- Commands adapt based on available features

### 3. Progressive Enhancement
- Core functionality available in standalone mode
- Enhanced features unlock when both packages installed
- No breaking changes when transitioning standalone → integrated

## Installation Scenarios

### Scenario 1: taskwright Only

**Installation:**
```bash
cd taskwright && ./installer/scripts/install.sh
```

**Capabilities:**
- ✅ Task management workflow (`/task-create`, `/task-work`, `/task-complete`)
- ✅ Quality gates (compilation, tests, coverage)
- ✅ Architectural review (SOLID/DRY/YAGNI)
- ✅ Test enforcement (Phase 4.5 auto-fix loop)
- ✅ Stack templates (react, python, .NET MAUI, etc.)
- ✅ Design-first workflow flags
- ❌ EARS requirements (install require-kit for this)
- ❌ Epic/Feature hierarchy (install require-kit for this)
- ❌ BDD scenario generation (install require-kit for this)
- ❌ PM tool synchronization (install require-kit for this)

**Use Case:** Lean startup, individual developers, rapid prototyping

### Scenario 2: require-kit Only

**Installation:**
```bash
cd require-kit && ./installer/scripts/install.sh
```

**Capabilities:**
- ✅ Requirements engineering (EARS notation)
- ✅ Epic/Feature hierarchy management
- ✅ BDD/Gherkin scenario generation
- ✅ PM tool export (Jira, Linear, GitHub, Azure DevOps)
- ✅ Requirements validation and traceability
- ❌ Task execution workflow (install taskwright for this)
- ❌ Architectural review (install taskwright for this)
- ❌ Quality gates and testing (install taskwright for this)

**Use Case:** Business analysts, product managers, requirements specification teams

### Scenario 3: Both Installed (Full Agentecflow)

**Installation:**
```bash
cd taskwright && ./installer/scripts/install.sh
cd require-kit && ./installer/scripts/install.sh
```

**Capabilities:**
- ✅ **Complete Agentecflow**: Stage 1 (Specification) → Stage 2 (Tasks) → Stage 3 (Engineering) → Stage 4 (Deployment)
- ✅ Full requirements traceability (EARS → BDD → Tasks → Implementation)
- ✅ Integrated reporting (requirements coverage, spec drift detection)
- ✅ Epic → Feature → Task hierarchy with automatic progress rollup
- ✅ PM tool synchronization with bidirectional updates
- ✅ All standalone features from both packages

**Use Case:** Enterprise teams, regulated industries, complete SDLC automation

## Technical Implementation

### Marker Files

Both packages create marker files in `~/.agentecflow/` upon installation:

**taskwright.marker.json:**
```json
{
  "package": "taskwright",
  "version": "1.0.0",
  "provides": ["task_management", "quality_gates", "architectural_review"],
  "optional_integration": ["require-kit"],
  "integration_model": "bidirectional_optional"
}
```

**require-kit.marker.json:**
```json
{
  "package": "require-kit",
  "version": "1.0.0",
  "provides": ["requirements_engineering", "epic_management", "bdd_generation"],
  "optional_integration": ["taskwright"],
  "integration_model": "bidirectional_optional"
}
```

### Feature Detection

**Library:** `installer/global/lib/feature_detection.py` (duplicated in both repos)

**Usage in taskwright commands:**
```python
from installer.global.lib.feature_detection import supports_requirements

if supports_requirements():
    # Full requirements integration
    requirements = load_requirements_from_docs()
    epic = load_epic_context()
else:
    # Graceful degradation
    requirements = []
    epic = None
```

**Key Functions:**
- `supports_requirements()` → Check if require-kit installed
- `supports_epics()` → Check if epic management available
- `supports_features()` → Check if feature management available
- `supports_bdd()` → Check if BDD generation available

### Graceful Degradation Examples

#### Example 1: task-create Command

**With require-kit:**
```bash
/task-create "User login" epic:EPIC-001 requirements:[REQ-001,REQ-002]
# ✅ Creates task with full epic/requirements linking
```

**Without require-kit:**
```bash
/task-create "User login" epic:EPIC-001 requirements:[REQ-001,REQ-002]
# ⚠️  Warning: epic/requirements features require require-kit
# ✅ Creates task with core fields only (title, priority, tags)
```

#### Example 2: task-work Phase 1

**With require-kit:**
```
📋 Task Context Loaded

ID: TASK-042
Title: User login implementation
Requirements: 2 linked (REQ-001, REQ-002)
Epic: EPIC-001 (User Management)
```

**Without require-kit:**
```
📋 Task Context Loaded

ID: TASK-042
Title: User login implementation
(Requirements features available with require-kit)
```

#### Example 3: Phase 5 Spec Drift Detection

**With require-kit:**
```
📋 REQUIREMENTS COVERAGE
✅ REQ-001: User shall authenticate within 1 second
   └─ src/auth/AuthService.ts
❌ REQ-002: Session tokens shall expire after 24 hours
   └─ NOT IMPLEMENTED
```

**Without require-kit:**
```
📋 REQUIREMENTS COVERAGE
ℹ️  Requirements traceability unavailable
   Install require-kit for EARS requirements tracking
```

## Migration Paths

### Path 1: Monolithic to Modular

**Starting point:** Current taskwright with all features bundled

**Steps:**
1. Split into taskwright (tasks) + require-kit (requirements)
2. Both packages install to `~/.agentecflow/`
3. Install scripts create marker files
4. Commands detect features and adapt

**Result:** Existing users see no breaking changes (both installed)

### Path 2: Adding Capabilities

**Scenario A: Start with taskwright, add requirements later**
```bash
# Day 1: Rapid development with tasks only
cd taskwright && ./installer/scripts/install.sh
/task-create "Feature X" && /task-work TASK-001

# Day 30: Add requirements management when team scales
cd require-kit && ./installer/scripts/install.sh
/epic-create "User Management" && /feature-create "Authentication" epic:EPIC-001
/task-create "User login" epic:EPIC-001 requirements:[REQ-001]
```

**Scenario B: Start with requirements, add execution later**
```bash
# Day 1: Requirements specification phase
cd require-kit && ./installer/scripts/install.sh
/gather-requirements && /formalize-ears && /epic-create "Platform"

# Day 15: Begin implementation
cd taskwright && ./installer/scripts/install.sh
/task-work TASK-001  # Now has full requirements context
```

## Benefits

### For Users
1. **Flexibility**: Install only what you need
2. **No Lock-In**: Switch between standalone and integrated seamlessly
3. **Progressive Enhancement**: Start simple, add capabilities over time
4. **Reduced Complexity**: Smaller surface area in standalone mode

### For Maintenance
1. **Clear Separation**: Each package has single responsibility
2. **Independent Versioning**: Update taskwright without touching require-kit
3. **Easier Testing**: Test standalone mode and integrated mode separately
4. **Reduced Coupling**: Changes in one package don't break the other

### For Teams
1. **Role-Based Access**: BAs use require-kit, devs use taskwright, or both
2. **Scalable**: Start with 1 developer (taskwright only), scale to enterprise (both)
3. **No Training Overhead**: Learn features incrementally
4. **Organizational Fit**: Adapt to team structure and workflow

## Anti-Patterns Avoided

### ❌ Hard Dependency
```
require-kit ──[requires]──> taskwright
```
**Problem:** Can't use require-kit without taskwright (unnecessary coupling)

### ❌ Monolithic Bundle
```
agentecflow-complete (contains everything)
```
**Problem:** Users forced to install features they don't need

### ❌ Fragile Integration
```
if require_kit_exists:
    call_require_kit_api()
else:
    raise Error("require-kit required")
```
**Problem:** Crashes instead of degrading gracefully

## Implementation Checklist

### taskwright ✅
- [x] `lib/feature_detection.py` - Detection library
- [x] `spec_drift_detector.py` - Graceful degradation for requirements
- [x] `task-work.md` Phase 1 - Conditional requirements display
- [x] `task-work.md` Step 3 - Conditional agent selection
- [x] `task-create.md` - Help text shows integration options separately
- [x] `templates/taskwright.marker.json` - Marker file template
- [x] `docs/architecture/bidirectional-integration.md` - This document

### require-kit ✅ (Already Implemented)
- [x] `lib/feature_detection.py` - Detection library
- [x] Commands adapted for standalone operation
- [x] `templates/require-kit.marker.json` - Marker file template
- [x] `docs/architecture/bidirectional-integration.md` - Integration guide

## Next Steps

1. **Update Installation Scripts**: Ensure marker files are created correctly
2. **Test Matrix**: Verify all 3 scenarios (taskwright only, require-kit only, both)
3. **Documentation**: Update README files for both packages
4. **User Communication**: Announce bidirectional integration model
5. **Migration Guide**: Help existing users understand the new architecture

## References

- **TASK-012**: Original shared installation strategy specification
- **REQ-003**: Shared installer requirements (require-kit)
- **REQ-003A**: require-kit installer implementation
- **require-kit commit 42d7871**: Feature detection implementation
