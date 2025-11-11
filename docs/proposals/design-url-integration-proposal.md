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

### 3. Template-Based UX Specialists

Each template provides its own UX specialist agent:

```
installer/global/templates/
├── react-typescript/
│   └── agents/
│       └── react-ux-specialist.md       # Handles Figma → React
├── nextjs-fullstack/
│   └── agents/
│       └── nextjs-ux-specialist.md      # Handles Figma → Next.js
├── default/  # .NET MAUI, Flutter, SwiftUI
│   └── agents/
│       └── maui-ux-specialist.md        # Handles Zeplin → MAUI
│       └── flutter-ux-specialist.md     # Handles Figma → Flutter
│       └── swiftui-ux-specialist.md     # Handles Figma → SwiftUI
```

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
- Task manager detects design URL
- Invokes stack-specific UX specialist
- UX specialist executes 6-phase Saga:
  - Phase 0: MCP Verification
  - Phase 1: Design Extraction
  - Phase 2: Boundary Documentation
  - Phase 3: Component Generation
  - Phase 4: Visual Regression Testing
  - Phase 5: Constraint Validation

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
- `.csproj` → .NET (uses maui-ux-specialist for Zeplin)
- `package.json` + React → react-typescript (uses react-ux-specialist for Figma)
- `pubspec.yaml` → Flutter (uses flutter-ux-specialist for Figma)

### MCP Selection Matrix

| Stack | Design Tool | MCP Server | Agent |
|-------|-------------|------------|-------|
| React/TypeScript | Figma | figma-dev-mode | react-ux-specialist |
| Next.js | Figma | figma-dev-mode | nextjs-ux-specialist |
| .NET MAUI | Zeplin | zeplin | maui-ux-specialist |
| Flutter | Figma | figma-dev-mode | flutter-ux-specialist |
| SwiftUI | Figma | figma-dev-mode | swiftui-ux-specialist |
| React Native | Figma/Zeplin | figma-dev-mode/zeplin | react-native-ux-specialist |

## Agent Architecture

### Shared Design-to-Code Pattern

All UX specialists implement the same interface:

```markdown
---
name: react-ux-specialist
description: React component generation from Figma designs
tools: Read, Write, Grep, mcp__figma-dev-mode__*
mcp_dependencies:
  - figma-dev-mode (required)
design_sources: [figma]
---

# React UX Specialist

## Mission
Generate pixel-perfect React components from Figma designs with zero scope creep.

## Input Contract
Receives from task manager:
- design_url: Figma URL
- design_source: "figma"
- task_context: Full task details

## Execution Pattern
1. MCP Verification (figma-dev-mode available)
2. Design Extraction (via MCP)
3. Boundary Documentation (zero scope creep)
4. Component Generation (TypeScript React + Tailwind)
5. Visual Regression Testing (Playwright)
6. Constraint Validation

## Output Contract
Returns to task manager:
- generated_files: List of file paths
- visual_fidelity: Similarity score (0.0-1.0)
- constraint_violations: List of violations (must be empty)
- test_results: Test execution results
```

### Stack-Specific Customization

Each agent customizes:
- **Component format**: React (JSX/TSX), MAUI (XAML), Flutter (Dart), SwiftUI (Swift)
- **Styling approach**: Tailwind, CSS-in-JS, XAML styling, Flutter themes
- **Testing strategy**: Playwright, xUnit, Flutter widget tests, XCTest
- **Visual comparison**: Screenshot diff, XAML validation, widget golden tests

## Migration Path

### Phase 1: Add Design URL Support to task-create
```bash
/task-create "Implement login" design:https://figma.com/design/abc?node-id=2-2
```

### Phase 2: Create Template UX Specialists
- react-ux-specialist.md (Figma → React)
- maui-ux-specialist.md (Zeplin → MAUI)
- (others as templates are added)

### Phase 3: Update task-work Phase 3
- Detect design_url in task frontmatter
- Route to appropriate UX specialist based on stack + design source

### Phase 4: Deprecate Standalone Commands
- Keep `/figma-to-react` and `/zeplin-to-maui` for backward compatibility
- Add deprecation warnings
- Update docs to use task workflow

### Phase 5: Remove Standalone Commands (Future)
- Remove deprecated commands after migration period
- Archive orchestrator agents or move to templates

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
# → Invokes react-ux-specialist
# → Generates TypeScript React + Tailwind
# → Runs Playwright visual tests
```

### .NET MAUI Project
```bash
cd my-maui-app
/task-create "User profile" design:https://app.zeplin.io/project/abc/screen/def
/task-work TASK-002
# → Detects .NET MAUI stack
# → Detects Zeplin design URL
# → Invokes maui-ux-specialist
# → Generates XAML + C#
# → Runs xUnit platform tests
```

### Flutter Project
```bash
cd my-flutter-app
/task-create "Dashboard" design:https://figma.com/design/xyz?node-id=5-10
/task-work TASK-003
# → Detects Flutter stack
# → Detects Figma design URL
# → Invokes flutter-ux-specialist
# → Generates Dart widgets
# → Runs widget golden tests
```

## Open Questions

1. **Multiple designs per task?**
   - Support `design:[url1, url2, url3]` for multi-component tasks?
   - Or enforce one design URL per task?

2. **Design updates after implementation?**
   - How to handle design changes?
   - `/task-refine` with updated design URL?
   - Versioning of design URLs?

3. **Mixed design sources?**
   - Task with both Figma and Zeplin URLs?
   - Probably reject - one design source per task

4. **Partial implementation?**
   - What if design URL is optional?
   - Specialist should gracefully skip if no design URL

5. **Design validation?**
   - Validate design URL is accessible before task creation?
   - Or defer until task-work Phase 3?

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
**Status**: Proposed
**Decision**: TBD after user review
