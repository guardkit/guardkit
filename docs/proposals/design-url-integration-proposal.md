# Design URL Integration Proposal

## Problem Statement

Current implementation of `/figma-to-react` and `/zeplin-to-maui` commands:
- ❌ Stack-specific commands (not technology-agnostic)
- ❌ Separate from core task workflow
- ❌ Doesn't leverage template architecture
- ❌ Requires new command for each stack/design-tool combination

## User's Original Vision

> "I want to create a task for implementing UI, provide a Figma/Zeplin URL, and have the stack-specific agents handle the implementation."

## Proposed Architecture

### 1. Task Creation with Design URLs

```bash
# Instead of:
/figma-to-react https://figma.com/design/abc?node-id=2-2

# Do this:
/task-create "Implement login form" design:https://figma.com/design/abc?node-id=2-2
/task-work TASK-001  # Auto-detects design URL, invokes appropriate specialist
```

### 2. Task Frontmatter Extension

```yaml
---
id: TASK-001
title: Implement login form
status: backlog
design_url: https://figma.com/design/abc?node-id=2-2
design_source: figma  # Auto-detected: figma | zeplin | sketch
design_metadata:
  file_key: abc123
  node_id: "2:2"
  extracted_at: null
---
```

### 3. Technology-Agnostic Orchestrators + Stack-Specific UI Specialists

**Global Orchestrators** (handle design extraction, delegate to UI specialists):

```
installer/global/agents/
├── figma-orchestrator.md       # Figma MCP extraction → delegates to UI specialists
└── zeplin-orchestrator.md      # Zeplin MCP extraction → delegates to UI specialists
```

**Stack-Specific UI Specialists** (extend existing agents to handle design contexts):

```
installer/global/templates/
├── react-typescript/
│   └── agents/
│       └── react-ui-specialist.md       # Extended to handle design contexts from orchestrators
├── nextjs-fullstack/
│   └── agents/
│       └── nextjs-ui-specialist.md      # Extended to handle design contexts from orchestrators
```

**Future UI Specialists** (created via `/template-create`, not manually):
- MAUI UI specialist (created when user runs `/template-create` for MAUI projects)
- Flutter UI specialist (created when user runs `/template-create` for Flutter projects)
- SwiftUI UI specialist (created when user runs `/template-create` for SwiftUI projects)

### 4. Workflow Integration

**Phase 1: Task Context Loading**
- Detect `design_url` in task frontmatter
- Parse design source (Figma, Zeplin, etc.)
- Load MCP tools based on design source

**Phase 2: Implementation Planning**
- UX specialist generates design-aware plan
- Documents design constraints (zero scope creep)
- Creates prohibition checklist

**Phase 3: Implementation**
- Task manager detects design URL and design source
- Invokes appropriate orchestrator (figma-orchestrator or zeplin-orchestrator)
- Orchestrator executes 6-phase Saga:
  - Phase 0: MCP Verification (design tool MCP available)
  - Phase 1: Design Extraction (via Figma/Zeplin MCP)
  - Phase 2: Boundary Documentation (prohibition checklist)
  - Phase 3: Component Generation (delegates to stack-specific UI specialist)
  - Phase 4: Visual Regression Testing (delegates to stack-specific UI specialist)
  - Phase 5: Constraint Validation (orchestrator validates against prohibitions)

**Phase 4: Testing**
- Includes visual regression tests from Phase 4 of Saga
- Standard test enforcement loop

**Phase 5: Code Review**
- Reviews generated components
- Validates zero scope creep

## Technology-Agnostic Design

### Design Source Detection

```python
def detect_design_source(url: str) -> str:
    """Auto-detect design tool from URL."""
    if "figma.com" in url:
        return "figma"
    elif "zeplin.io" in url or "app.zeplin.io" in url:
        return "zeplin"
    elif "sketch.com" in url:
        return "sketch"
    else:
        raise ValueError(f"Unsupported design tool: {url}")
```

### Stack Detection

Stack detection already works - task-work detects stack from project files:
- `.csproj` → .NET MAUI
- `package.json` + React → react-typescript
- `pubspec.yaml` → Flutter

### Orchestrator Selection Matrix

| Design Tool | Orchestrator | MCP Server | Delegates To |
|-------------|--------------|------------|--------------|
| Figma | figma-orchestrator | figma-dev-mode | Stack-specific UI specialist (react-ui-specialist, nextjs-ui-specialist, etc.) |
| Zeplin | zeplin-orchestrator | zeplin | Stack-specific UI specialist (maui-ui-specialist, react-native-ui-specialist, etc.) |

**Routing Logic**:
```python
if task.design_url:
    design_source = task.design_source  # "figma" | "zeplin"
    stack = detect_stack()  # react-typescript, maui, flutter, etc.

    # Select orchestrator based on design source
    if design_source == "figma":
        orchestrator = "figma-orchestrator"
    elif design_source == "zeplin":
        orchestrator = "zeplin-orchestrator"

    # Orchestrator handles MCP extraction, then delegates to UI specialist
    invoke_orchestrator(orchestrator, task, target_specialist=f"{stack}-ui-specialist")
else:
    # Standard implementation without design extraction
    invoke_standard_implementation(task)
```

## Agent Architecture

### Two-Tier Architecture: Orchestrators + UI Specialists

**Tier 1: Technology-Agnostic Orchestrators**
- Handle MCP calls (Figma/Zeplin)
- Extract design elements, styles, metadata
- Generate prohibition checklists (zero scope creep)
- Validate constraints after implementation
- Delegate component generation to UI specialists

**Tier 2: Stack-Specific UI Specialists**
- Receive design context from orchestrator
- Generate components in stack-appropriate format
- Run stack-appropriate visual regression tests
- Return results to orchestrator for validation

### Orchestrator Pattern (Technology-Agnostic)

```markdown
---
name: figma-orchestrator
description: Orchestrates Figma design extraction and delegates to UI specialists
tools: Read, Write, Grep, mcp__figma-dev-mode__*
mcp_dependencies:
  - figma-dev-mode (required)
---

# Figma Orchestrator

## Mission
Extract Figma designs and coordinate with UI specialists for implementation.

## Execution Pattern (6-Phase Saga)
1. MCP Verification (figma-dev-mode available)
2. Design Extraction (via Figma MCP)
3. Boundary Documentation (prohibition checklist)
4. Component Generation (delegate to UI specialist)
5. Visual Regression Testing (delegate to UI specialist)
6. Constraint Validation (verify zero scope creep)

## Delegation
Passes to UI specialist:
- designElements: Extracted elements from Figma
- designConstraints: Prohibition checklist
- designMetadata: File key, node ID, visual reference

Receives from UI specialist:
- generated_files: List of file paths
- visual_fidelity: Similarity score (0.0-1.0)
- constraint_violations: List of violations (must be empty)
```

### UI Specialist Pattern (Stack-Specific)

UI specialists are extended to handle design contexts:

```markdown
# In react-ui-specialist.md (extended)

## Design Context Handling

if task.design_context:
    # Received from figma-orchestrator or zeplin-orchestrator
    designElements = task.design_context.elements
    prohibitions = task.design_context.prohibitions
    visualReference = task.design_context.visualReference

    # Generate component matching design exactly
    generate_component(designElements, prohibitions)

    # Run visual regression tests
    visual_fidelity = run_visual_tests(visualReference)

    # Return to orchestrator for validation
    return {
        generated_files: [...]
        visual_fidelity: 0.97
        constraint_violations: []
    }
else:
    # Standard UI implementation without design extraction
    implement_standard_ui(task)
```

### Stack-Specific Customization

Each UI specialist customizes:
- **Component format**: React (JSX/TSX), MAUI (XAML), Flutter (Dart), SwiftUI (Swift)
- **Styling approach**: Tailwind, CSS-in-JS, XAML styling, Flutter themes
- **Testing strategy**: Playwright, xUnit, Flutter widget tests, XCTest
- **Visual comparison**: Screenshot diff, XAML validation, widget golden tests

## Migration Path

### Phase 1: Add Design URL Support to task-create
```bash
/task-create "Implement login" design:https://figma.com/design/abc?node-id=2-2
```

### Phase 2: Refactor Orchestrators (Technology-Agnostic)
- Refactor `figma-react-orchestrator.md` → `figma-orchestrator.md` (remove React-specific naming)
- Refactor `zeplin-maui-orchestrator.md` → `zeplin-orchestrator.md` (remove MAUI-specific naming)
- Update orchestrators to delegate to any stack's UI specialist

### Phase 3: Extend UI Specialists (Stack-Specific)
- Extend `react-ui-specialist` to handle design contexts from orchestrators
- Extend `nextjs-ui-specialist` to handle design contexts from orchestrators
- Future specialists (MAUI, Flutter, SwiftUI) created via `/template-create`

### Phase 4: Update task-work Phase 3
- Detect design_url in task frontmatter
- Route to appropriate orchestrator based on design source
- Orchestrator delegates to stack-specific UI specialist

### Phase 5: Deprecate Standalone Commands
- Keep `/figma-to-react` and `/zeplin-to-maui` for backward compatibility
- Add deprecation warnings
- Update docs to use task workflow

### Phase 6: Remove Standalone Commands (Future)
- Remove deprecated commands after migration period
- Orchestrators become the only design-to-code entry point

## Benefits

✅ **Technology-Agnostic**: Works with any stack that has a UX specialist
✅ **Unified Workflow**: Single task workflow for all development
✅ **Template-Driven**: Each stack handles design-to-code its own way
✅ **Extensible**: Add new stacks by adding template agents
✅ **Consistent Quality**: All tasks go through same gates
✅ **Zero Scope Creep**: Same constraints apply regardless of stack
✅ **MCP Integration**: Leverage existing MCPs without standalone commands

## Example Usage

### React Project
```bash
cd my-react-project
/task-create "Login form" design:https://figma.com/design/abc?node-id=2-2
/task-work TASK-001
# → Detects React stack
# → Detects Figma design URL
# → Invokes figma-orchestrator
# → Orchestrator extracts design via Figma MCP
# → Orchestrator delegates to react-ui-specialist
# → Generates TypeScript React + Tailwind
# → Runs Playwright visual tests
# → Orchestrator validates constraints
```

### .NET MAUI Project
```bash
cd my-maui-app
/task-create "User profile" design:https://app.zeplin.io/project/abc/screen/def
/task-work TASK-002
# → Detects .NET MAUI stack
# → Detects Zeplin design URL
# → Invokes zeplin-orchestrator
# → Orchestrator extracts design via Zeplin MCP
# → Orchestrator delegates to maui-ui-specialist
# → Generates XAML + C#
# → Runs xUnit platform tests
# → Orchestrator validates constraints
```

### Flutter Project (Future)
```bash
cd my-flutter-app
/task-create "Dashboard" design:https://figma.com/design/xyz?node-id=5-10
/task-work TASK-003
# → Detects Flutter stack
# → Detects Figma design URL
# → Invokes figma-orchestrator
# → Orchestrator extracts design via Figma MCP
# → Orchestrator delegates to flutter-ui-specialist (created via /template-create)
# → Generates Dart widgets
# → Runs widget golden tests
# → Orchestrator validates constraints
```

## Design Decisions

### 1. Multiple designs per task?
**Decision**: ✅ One design URL per task (keep it simple)

**Rationale**:
- Maintains clear task scope
- Easier to track design changes
- Reduces complexity in constraint validation
- If multiple components needed, create multiple tasks

**Example**:
```bash
# Instead of:
/task-create "Login flow" design:[url1, url2, url3]  # ❌ Not supported

# Do this:
/task-create "Login form" design:url1     # ✅ TASK-001
/task-create "Password reset" design:url2 # ✅ TASK-002
/task-create "Success screen" design:url3 # ✅ TASK-003
```

### 2. Design updates after implementation?
**Decision**: ✅ Use `/task-refine` with updated design URL

**Rationale**:
- Design changes are common in iterative development
- `/task-refine` already supports lightweight updates
- Allows re-extraction and visual regression testing
- Maintains task history and traceability

**Workflow**:
```bash
# Initial implementation
/task-create "Login form" design:https://figma.com/.../v1
/task-work TASK-001
/task-complete TASK-001

# Design updated in Figma (v2)
/task-refine TASK-001 design:https://figma.com/.../v2
# → Re-extracts design
# → Regenerates component
# → Re-runs visual tests
# → Updates only what changed
```

**Version tracking**:
- Task frontmatter stores design URL history
- Each refinement appends to `design_history` array
- Visual regression compares against latest design

### 3. Mixed design sources?
**Decision**: ✅ One design source per task (Figma OR Zeplin, not both)

**Rationale**:
- Simplifies MCP tool selection
- Avoids confusion about which design is canonical
- Reduces validation complexity
- Clear constraint boundaries

**Validation**:
```python
# task-create validates at creation time
if task has design_url:
    design_source = detect_design_source(design_url)
    # Store single source: "figma" | "zeplin" | "sketch"
    # Reject if multiple sources detected
```

### 4. Partial implementation?
**Decision**: ✅ UX specialist gracefully skips if no design URL

**Rationale**:
- Not all tasks require design extraction
- UX specialist should be optional enhancement
- Tasks without design URL follow standard workflow
- Allows mixed task types in same project

**Behavior**:
```python
# In task-work Phase 3
if task.design_url:
    # Invoke UX specialist for design-driven implementation
    invoke_ux_specialist(task, design_url)
else:
    # Standard implementation without design extraction
    invoke_standard_implementation(task)
```

**UX specialist pattern**:
```markdown
# In UX specialist agent
if not design_url:
    log("No design URL provided, skipping design extraction")
    return None  # Task manager continues with standard workflow
```

### 5. Design validation?
**Decision**: ✅ Validate design URL accessibility at task creation time

**Rationale**:
- Fail fast - catch invalid URLs before work begins
- Better user experience (immediate feedback)
- Prevents wasted time in task-work Phase 3
- Validates MCP server availability early

**Validation steps** (during `/task-create`):
1. **URL format validation**: Check URL matches known design tool patterns
2. **MCP availability**: Verify required MCP server is installed
3. **Accessibility check**: Attempt to fetch design metadata (lightweight call)
4. **Authentication check**: Validate access token has required permissions

**Example validation**:
```python
def validate_design_url(url: str) -> ValidationResult:
    # 1. Detect design source
    design_source = detect_design_source(url)  # "figma" | "zeplin"

    # 2. Check MCP server availability
    if design_source == "figma" and not mcp_available("figma-dev-mode"):
        return ValidationResult(
            valid=False,
            error="Figma MCP server not installed",
            help="Run: npm install -g @figma/mcp-server"
        )

    # 3. Lightweight accessibility check
    try:
        metadata = fetch_design_metadata(url, design_source)
        return ValidationResult(valid=True, metadata=metadata)
    except AuthError:
        return ValidationResult(
            valid=False,
            error="Design URL not accessible - authentication failed",
            help="Check FIGMA_ACCESS_TOKEN in .env"
        )
    except NotFoundError:
        return ValidationResult(
            valid=False,
            error="Design URL not found",
            help="Verify URL is correct and design exists"
        )
```

**Task creation flow**:
```bash
/task-create "Login form" design:https://figma.com/design/invalid

# Validation fails immediately:
❌ Design URL validation failed

Error: Design not found
URL: https://figma.com/design/invalid

Possible causes:
- URL is incorrect or malformed
- Design was deleted or moved
- Access token doesn't have permission to this file

Suggestions:
1. Verify URL in Figma
2. Check FIGMA_ACCESS_TOKEN has 'file:read' scope
3. Ensure design is shared with you

Task creation aborted.
```

## Next Steps

1. ✅ Document proposal (this file)
2. ⏳ Review with user
3. ⏳ Refine based on feedback
4. ⏳ Create implementation task
5. ⏳ Implement Phase 1 (task-create enhancement)
6. ⏳ Implement Phase 2 (template UX specialists)
7. ⏳ Implement Phase 3 (task-work integration)
8. ⏳ Test with real projects
9. ⏳ Deprecate standalone commands
10. ⏳ Update documentation

## Decision Record

**Date**: 2025-11-11
**Status**: ✅ Approved
**Approved by**: User
**Implementation Priority**: High

### Key Decisions
1. ✅ One design URL per task (simple, clear scope)
2. ✅ Design updates via `/task-refine` (iterative design changes)
3. ✅ Single design source per task (no mixing Figma + Zeplin)
4. ✅ UX specialist optional (graceful skip if no design URL)
5. ✅ Validate design URL at creation time (fail fast)

### Architecture Summary
- **Approach**: Template-based UX specialists, unified workflow
- **Integration**: Add `design:URL` parameter to `/task-create`
- **Routing**: Automatic based on stack detection + design source detection
- **Quality**: Same zero-scope-creep constraints for all stacks
- **Migration**: Deprecate standalone commands, move to templates

### Next Actions
1. ✅ Create implementation tasks (TASK-UX-7F1E, TASK-UX-C3A3)
2. ⏳ Implement Phase 1: task-create design URL support
3. ⏳ Implement Phase 2: Refactor orchestrators to be technology-agnostic
4. ⏳ Implement Phase 3: Extend UI specialists to handle design contexts
5. ⏳ Implement Phase 4: Update task-work integration
6. ⏳ Test with real projects
7. ⏳ Deprecate `/figma-to-react` and `/zeplin-to-maui`
8. ⏳ Update documentation
