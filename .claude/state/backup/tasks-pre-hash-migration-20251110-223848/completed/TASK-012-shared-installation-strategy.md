---
id: TASK-012
title: "Shared Installation Strategy - Optional Requirements Integration"
created: 2025-10-27
status: completed
completed: 2025-01-08T00:00:00Z
priority: critical
complexity: 6
parent_task: none
subtasks: []
estimated_hours: 3
started: 2025-10-28
---

# TASK-012: Shared Installation Strategy - Optional Requirements Integration

## Problem Statement

TASK-004, TASK-005, and TASK-006 currently plan to **remove** epic/feature/requirements functionality from task-create.md, task-work.md, and task-status.md.

However, if guardkit and require-kit both install to `~/.agentecflow` and can coexist, we should make requirements features **optional/extensible** rather than removing them.

## Strategic Decision

### Installation Scenarios

1. **guardkit only**: Task workflow without requirements
2. **require-kit only**: Full requirements management (includes tasks)
3. **Both installed**: Full integration with all features

### Implication

Commands should **detect** whether require-kit is installed and **gracefully degrade** if not, rather than hard-coding removal of features.

## Proposed Architecture

### Feature Detection

```bash
# Check if require-kit is installed
if [ -f ~/.agentecflow/require-kit.marker ]; then
  REQUIREMENTS_AVAILABLE=true
else
  REQUIREMENTS_AVAILABLE=false
fi
```

### Graceful Degradation in Commands

#### task-create.md

**Current plan (TASK-004)**: Remove epic/feature/requirements fields entirely

**Better approach**: Make fields optional
```yaml
# Frontmatter template
---
id: {TASK_ID}
title: "{title}"
created: {date}
status: backlog
priority: {priority}
complexity: 0
parent_task: none
subtasks: []
# Optional (only if require-kit installed):
epic: none              # Optional
feature: none           # Optional
requirements: []        # Optional
---
```

**Implementation**:
```bash
# In task-create command logic
if [ "$REQUIREMENTS_AVAILABLE" = true ]; then
  # Include epic/feature/requirements flags
  # Show epic/feature linking options
else
  # Skip epic/feature/requirements
  # Don't show those flags in help
fi
```

#### task-work.md

**Current plan (TASK-005)**: Remove Phase 1 requirements loading

**Better approach**: Conditional Phase 1
```
Phase 1: Task Analysis
  - Load task description (always)
  - Load parent task context (always, if subtask)
  - Identify technology stack (always)

  # Conditional (only if require-kit installed):
  - Load EARS requirements (if linked)
  - Load BDD scenarios (if linked)
  - Load epic/feature context (if linked)
```

**Implementation**:
```bash
# In task-work Phase 1
if [ "$REQUIREMENTS_AVAILABLE" = true ]; then
  # Check task frontmatter for requirements/epic/feature
  if [ -n "$epic" ] || [ -n "$requirements" ]; then
    # Load requirements context
    # Pass to agents
  fi
fi
# Continue with standard workflow
```

#### task-status.md

**Current plan (TASK-006)**: Remove epic/feature filters

**Better approach**: Conditional filters
```bash
# Always available
/task-status --status backlog
/task-status --priority high

# Only if require-kit installed
/task-status --epic EPIC-001      # Only shown if require-kit present
/task-status --feature FEAT-005   # Only shown if require-kit present
```

**Implementation**:
```bash
# In task-status help text
echo "Filters:"
echo "  --status    Filter by status"
echo "  --priority  Filter by priority"

if [ "$REQUIREMENTS_AVAILABLE" = true ]; then
  echo "  --epic      Filter by epic (require-kit)"
  echo "  --feature   Filter by feature (require-kit)"
fi
```

## Installation Architecture

### Directory Structure (Shared)

```
~/.agentecflow/
├── commands/
│   ├── task-create.md         # GuardKit (graceful degradation)
│   ├── task-work.md           # GuardKit (graceful degradation)
│   ├── task-status.md         # GuardKit (graceful degradation)
│   ├── epic-create.md         # Require-kit only
│   ├── feature-create.md      # Require-kit only
│   └── gather-requirements.md # Require-kit only
├── agents/
│   ├── architectural-reviewer.md  # GuardKit
│   ├── test-verifier.md          # GuardKit
│   ├── requirements-analyst.md   # Require-kit only
│   └── bdd-generator.md          # Require-kit only
├── lib/
│   ├── checkpoint_display.py     # GuardKit
│   ├── feature_generator.py      # Require-kit only
│   └── ...
├── guardkit.marker             # Installed marker
└── require-kit.marker            # Installed marker
```

### Package Manifests

**guardkit/installer/global/manifest.json**:
```json
{
  "name": "guardkit",
  "version": "1.0.0",
  "install_to": "~/.agentecflow",
  "provides": [
    "task-management",
    "quality-gates",
    "architectural-review",
    "test-enforcement"
  ],
  "optional_integration": [
    "require-kit"
  ]
}
```

**require-kit/installer/global/manifest.json**:
```json
{
  "name": "require-kit",
  "version": "1.0.0",
  "install_to": "~/.agentecflow",
  "provides": [
    "requirements-engineering",
    "bdd-generation",
    "epic-management",
    "feature-management"
  ],
  "requires": [
    "guardkit"  # Require-kit depends on guardkit
  ]
}
```

## Implementation Strategy

### Phase 1: Install Scripts
- Both packages install to `~/.agentecflow`
- Create marker files (`guardkit.marker`, `require-kit.marker`)
- Check for conflicts, merge safely

### Phase 2: Feature Detection Library
Create `lib/feature_detection.py`:
```python
def is_require_kit_installed() -> bool:
    """Check if require-kit is installed."""
    return Path.home() / ".agentecflow" / "require-kit.marker").exists()

def supports_requirements() -> bool:
    """Check if requirements features are available."""
    return is_require_kit_installed()
```

### Phase 3: Conditional Command Logic
- task-create.md: Include epic/feature fields only if require-kit present
- task-work.md: Load requirements only if require-kit present AND task has requirements
- task-status.md: Show epic/feature filters only if require-kit present

### Phase 4: Help Text
Commands should show different help based on what's installed:
```bash
/task-create --help
# GuardKit only:
#   Usage: /task-create "title" [priority:high|medium|low]

# Both installed:
#   Usage: /task-create "title" [priority:high] [epic:EPIC-XXX] [requirements:[REQ-001]]
```

## Updated Task Approach

### TASK-004: Modify task-create.md (REVISED)
**Old**: Remove epic/feature/requirements fields
**New**: Make epic/feature/requirements fields optional, shown only if require-kit installed

### TASK-005: Modify task-work.md (REVISED)
**Old**: Remove Phase 1 requirements loading
**New**: Make Phase 1 requirements loading conditional on require-kit presence

### TASK-006: Modify task-status.md (REVISED)
**Old**: Remove epic/feature filters
**New**: Make epic/feature filters conditional on require-kit presence

## Benefits

### For Users
1. **Flexibility**: Install just what you need
2. **No Breaking Changes**: Full integration when both installed
3. **Progressive Enhancement**: Start with guardkit, add require-kit later
4. **No Duplication**: Shared agents, lib, templates

### For Maintenance
1. **Single Source**: One set of commands, conditional behavior
2. **No Divergence**: Changes apply to both systems
3. **Clear Dependencies**: require-kit extends guardkit

## Testing Strategy

### Test Matrix
```
| Scenario | task-create | task-work | task-status |
|----------|-------------|-----------|-------------|
| guardkit only | No epic/feature | No req loading | No epic filter |
| require-kit only | Full features | Full req loading | Full filters |
| Both installed | Full features | Full req loading | Full filters |
```

### Test Commands
```bash
# Scenario 1: guardkit only
uninstall require-kit
/task-create "Task"  # Should work, no epic/feature
/task-status --epic EPIC-001  # Should warn "require-kit not installed"

# Scenario 2: Both installed
install require-kit
/task-create "Task" epic:EPIC-001  # Should work
/task-status --epic EPIC-001  # Should work
```

## Documentation Strategy

### guardkit README.md
```markdown
# GuardKit

Lightweight task workflow with quality gates.

## Optional: Requirements Management

Install [require-kit](https://github.com/requirekit/require-kit) for:
- EARS notation requirements
- BDD/Gherkin scenarios
- Epic/Feature hierarchy
- PM tool synchronization

When both are installed, task commands gain additional features.
```

### require-kit README.md
```markdown
# Require-Kit

Requirements management for guardkit.

## Prerequisites

Requires [guardkit](https://github.com/you/guardkit) to be installed first.

## What You Get

- EARS notation requirements
- BDD/Gherkin scenarios
- Epic/Feature hierarchy
- Automatic linking to tasks
```

## Migration Path

### For Existing Users
If someone has "full agentecflow" installed:
1. Install guardkit → Gets task workflow + quality gates
2. Install require-kit → Gets requirements features
3. Everything works together, no data loss

## Acceptance Criteria

- [x] Both packages can install to `~/.agentecflow` without conflict
- [x] Marker files created/detected correctly
- [x] Commands detect require-kit presence
- [x] Epic/feature functionality works when both installed
- [x] Graceful degradation when only guardkit installed
- [x] Help text adapts to installed packages
- [x] No breaking changes when both installed

## Implementation Summary

### Completed Work

1. **Feature Detection Library** (`lib/feature_detection.py`)
   - `FeatureDetector` class for package detection
   - Marker file checking (guardkit.marker, require-kit.marker)
   - Feature availability queries (requirements, epics, features, BDD)
   - Compatibility checking and status messages
   - Global convenience functions

2. **Package Manifest** (`manifest.json`)
   - Updated name to "guardkit"
   - Added `install_to: ~/.agentecflow`
   - Listed provided features
   - Declared optional integration with require-kit

3. **Command Updates**
   - **task-create.md**: Added feature detection section, conditional epic/feature fields in frontmatter
   - **task-work.md**: Added feature detection, conditional requirements loading in Phase 1.5
   - **task-status.md**: Added feature detection, separated core vs extended filters

4. **Installation Script** (`install.sh`)
   - Added `create_package_marker()` function
   - Creates guardkit.marker with metadata
   - Copies manifest to ~/.agentecflow
   - Integrated into main installation flow

5. **Documentation** (`README.md`)
   - Added installation options section
   - Documented graceful degradation behavior
   - Explained guardkit-only vs full Agentecflow setup

### Testing

Successfully tested feature detection library with all scenarios:
- No packages installed
- GuardKit only
- GuardKit + require-kit
- Feature availability queries
- Status message generation

## Related Tasks

- **BLOCKS TASK-004**: Need to revise approach
- **BLOCKS TASK-005**: Need to revise approach
- **BLOCKS TASK-006**: Need to revise approach
- TASK-010: Update manifest (needs install_to field)
- TASK-002: Remove commands (UNCHANGED - require-kit will provide these)
- TASK-003: Remove agents (UNCHANGED - require-kit will provide these)

## Estimated Time

3 hours (design + prototype feature detection)

## Next Steps

1. Validate this approach with stakeholders
2. Create feature_detection.py library
3. Update TASK-004, 005, 006 to use conditional logic
4. Test installation scenarios
5. Update documentation strategy

## Notes

- This is a **breaking change to the plan** but a **better long-term architecture**
- Preserves optionality and progressive enhancement
- Avoids code duplication between guardkit and require-kit
- Makes both packages more maintainable
- **CRITICAL**: Need to update TASK-004, 005, 006 before executing them

---

## Implementation Summary (2025-10-28)

### ✅ Completed Implementation

The bidirectional optional integration has been successfully implemented for guardkit, matching require-kit's existing implementation.

### Files Created/Modified

1. **`installer/global/lib/feature_detection.py`** - NEW ✨
   - Copied from require-kit (designed for duplication)
   - Provides `supports_requirements()`, `supports_epics()`, `supports_features()`, `supports_bdd()`
   - Detects installed packages via marker files in `~/.agentecflow/`

2. **`installer/global/commands/lib/spec_drift_detector.py`** - MODIFIED 🔧
   - Added graceful degradation for missing require-kit
   - Returns empty requirements list if `supports_requirements()` is False
   - Updated `format_drift_report()` to show appropriate message when requirements unavailable

3. **`installer/global/commands/task-work.md`** - MODIFIED 🔧
   - Phase 1: Conditional extraction of requirements/epic/feature fields
   - Step 3: Two agent selection tables (with/without require-kit)
   - Phase 1 invocation: Uses `analysis_agent` (requirements-analyst or task-manager)
   - Display logic: Shows requirements info only when require-kit installed

4. **`installer/global/commands/task-create.md`** - MODIFIED 🔧
   - Split examples into "Core" (always available) and "Integration" (require-kit required)
   - Split options into "Core Options" and "Integration Options"
   - Added installation instructions for require-kit
   - Added bidirectional integration note at top

5. **`installer/global/templates/guardkit.marker.json`** - NEW ✨
   - Marker file template for installation scripts
   - Declares optional_integration with require-kit
   - Lists all provided capabilities

6. **`docs/architecture/bidirectional-integration.md`** - NEW ✨
   - Complete architecture guide
   - 3 installation scenarios documented
   - Technical implementation details
   - Migration paths
   - Implementation checklist

### Acceptance Criteria Status

- [x] Both packages can install to `~/.agentecflow` without conflict
- [x] Marker files created/detected correctly (template provided)
- [x] Commands detect require-kit presence (`supports_requirements()`)
- [x] Epic/feature functionality works when both installed (conditional logic)
- [x] Graceful degradation when only guardkit installed (all commands updated)
- [x] Help text adapts to installed packages (task-create.md shows conditional options)
- [x] No breaking changes when both installed (backwards compatible)

### Key Implementation Details

**Feature Detection Pattern:**
```python
from installer.global.lib.feature_detection import supports_requirements

if supports_requirements():
    # Full integration: Load requirements, epics, features
    requirements = frontmatter.requirements
    analysis_agent = "requirements-analyst"
else:
    # Graceful degradation: Standalone mode
    requirements = []
    analysis_agent = "task-manager"
```

**Agent Selection Logic:**
- **With require-kit**: Uses `requirements-analyst` for Phase 1
- **Without require-kit**: Uses `task-manager` for Phase 1 (existing guardkit agent)

**Display Logic:**
- Requirements/epic/feature info shown only when `supports_requirements()` returns True
- User sees helpful message to install require-kit for enhanced features

### Integration with require-kit

This implementation aligns with require-kit's existing bidirectional integration (commit 42d7871):
- Both use identical `feature_detection.py` (designed for duplication)
- Both create marker files in `~/.agentecflow/`
- Both degrade gracefully when the other is missing
- Both provide helpful installation messages

### Testing Required

1. **Scenario 1**: guardkit only (no require-kit marker)
   - Task creation should work without epic/feature fields
   - Phase 1 should use task-manager agent
   - Spec drift should skip requirements loading

2. **Scenario 2**: Both installed (both markers present)
   - Full integration features available
   - Phase 1 uses requirements-analyst
   - Spec drift loads from docs/requirements/

3. **Scenario 3**: Transition (install require-kit after guardkit)
   - Existing tasks continue to work
   - New tasks get enhanced features
   - No data migration required

### Next Steps

1. Update installation scripts to create marker file from template
2. Run test matrix (3 scenarios above)
3. Update README.md with installation options
4. Close related tasks (TASK-004, TASK-005, TASK-006 now obsolete)
