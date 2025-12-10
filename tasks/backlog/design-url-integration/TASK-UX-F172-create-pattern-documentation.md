---
id: TASK-UX-F172
title: Create pattern documentation for developers
status: backlog
created: 2025-11-11T11:50:00Z
updated: 2025-11-11T11:50:00Z
priority: medium
tags: [ux-integration, documentation, architecture, patterns]
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Create pattern documentation for developers

## Description

Create comprehensive technical documentation that explains the architecture, design patterns, and extension points of the design-to-code system. This documentation is aimed at developers who want to understand the internals or extend the system (e.g., create new UI specialists for other stacks).

This is part of Phase 6 of the Design URL Integration project (see [design-url-integration-implementation-guide.md](../../docs/proposals/design-url-integration-implementation-guide.md)).

## Acceptance Criteria

- [ ] Architecture documentation created at `docs/patterns/design-to-code-architecture.md`
- [ ] Design patterns explained (Saga, Orchestrator, Delegation)
- [ ] Component interaction diagrams included
- [ ] Extension points documented
- [ ] UI specialist creation guide included
- [ ] Testing strategies documented
- [ ] Code examples provided
- [ ] Integration patterns explained
- [ ] Referenced from CLAUDE.md

## Implementation Notes

### Target File
- **File**: `docs/patterns/design-to-code-architecture.md`

### Document Structure

```markdown
# Design-to-Code Architecture

Technical documentation for the design-to-code system architecture, patterns, and extension points.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
   - [Two-Tier System](#two-tier-system)
   - [Component Diagram](#component-diagram)
   - [Sequence Diagrams](#sequence-diagrams)
3. [Design Patterns](#design-patterns)
   - [Saga Pattern](#saga-pattern)
   - [Orchestrator Pattern](#orchestrator-pattern)
   - [Delegation Pattern](#delegation-pattern)
   - [Constraint Validation Pattern](#constraint-validation-pattern)
4. [Orchestrators](#orchestrators)
   - [Orchestrator Responsibilities](#orchestrator-responsibilities)
   - [6-Phase Saga Implementation](#6-phase-saga-implementation)
   - [MCP Integration](#mcp-integration)
5. [UI Specialists](#ui-specialists)
   - [UI Specialist Responsibilities](#ui-specialist-responsibilities)
   - [Design Context Interface](#design-context-interface)
   - [Component Generation](#component-generation)
   - [Visual Regression Testing](#visual-regression-testing)
6. [Extension Points](#extension-points)
   - [Creating New UI Specialists](#creating-new-ui-specialists)
   - [Creating New Orchestrators](#creating-new-orchestrators)
   - [Adding Design Sources](#adding-design-sources)
7. [Integration Patterns](#integration-patterns)
   - [Task-Work Integration](#task-work-integration)
   - [MCP Server Integration](#mcp-server-integration)
   - [Stack Detection](#stack-detection)
8. [Testing Strategies](#testing-strategies)
   - [Unit Testing](#unit-testing)
   - [Integration Testing](#integration-testing)
   - [Visual Regression Testing](#visual-regression-testing-1)
9. [Code Examples](#code-examples)
   - [Creating a UI Specialist](#creating-a-ui-specialist-example)
   - [Implementing Design Context Detection](#implementing-design-context-detection)
   - [Constraint Validation](#constraint-validation-example)
10. [Best Practices](#best-practices)
11. [Performance Considerations](#performance-considerations)
12. [Security Considerations](#security-considerations)

## Overview

The design-to-code system converts Figma and Zeplin designs into production-ready components with zero scope creep using a two-tier architecture: technology-agnostic orchestrators and stack-specific UI specialists.

**Key Principles:**
- **Separation of Concerns**: Orchestrators handle design extraction, UI specialists handle code generation
- **Technology Agnostic**: One orchestrator works with any stack via delegation
- **Constraint Enforcement**: Zero tolerance for scope creep via prohibition checklists
- **Visual Fidelity**: >95% similarity to design via regression testing
- **Extensibility**: Easy to add new stacks and design sources

## Architecture

### Two-Tier System

```
┌─────────────────────────────────────────────────────────────┐
│                    Task-Work Command                        │
│  (Phase 1: Load design_url, Phase 3: Route to orchestrator) │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────▼─────────────────┐
        │   Detect Design Source + Stack   │
        └───────────────┬─────────────────┘
                        │
        ┌───────────────▼─────────────────┐
        │   Route to Orchestrator          │
        │   (figma | zeplin)               │
        └───────────────┬─────────────────┘
                        │
    ┌───────────────────┴────────────────────┐
    │                                         │
┌───▼──────────────┐               ┌─────────▼───────────┐
│   Figma          │               │   Zeplin            │
│   Orchestrator   │               │   Orchestrator      │
│                  │               │                     │
│ - MCP: figma-    │               │ - MCP: zeplin       │
│   dev-mode       │               │                     │
│ - 6-phase Saga   │               │ - 6-phase Saga      │
│ - Constraint     │               │ - Constraint        │
│   validation     │               │   validation        │
└───┬──────────────┘               └─────────┬───────────┘
    │                                         │
    │  (Delegate to UI Specialist)           │
    │                                         │
    └────────────────┬────────────────────────┘
                     │
        ┌────────────▼─────────────────┐
        │   Detect Stack               │
        │   (react, nextjs, maui, etc.) │
        └────────────┬─────────────────┘
                     │
    ┌────────────────┴─────────────────────────┐
    │                                           │
┌───▼──────────┐     ┌────────────┐     ┌─────▼──────┐
│  React UI    │     │  Next.js   │     │  MAUI UI   │
│  Specialist  │     │  UI        │     │  Specialist │
│              │     │  Specialist │     │             │
│ - Generate   │     │            │     │ - Generate  │
│   TSX        │     │ - Generate │     │   XAML      │
│ - Tailwind   │     │   TSX      │     │ - C# code-  │
│   CSS        │     │ - Server/  │     │   behind    │
│ - Playwright │     │   Client   │     │ - Platform  │
│   tests      │     │   detection│     │   tests     │
└──────────────┘     │ - Playwright    │ └────────────┘
                     │   tests    │
                     └────────────┘
```

**Tier 1: Orchestrators** (Global, Technology-Agnostic)
- Location: `installer/core/agents/`
- Purpose: Handle design extraction, constraint validation
- Examples: `figma-orchestrator.md`, `zeplin-orchestrator.md`
- Tools: MCP servers (figma-dev-mode, zeplin)

**Tier 2: UI Specialists** (Template-Specific, Stack-Aware)
- Location: `installer/core/templates/{stack}/agents/`
- Purpose: Generate code in stack-appropriate format
- Examples: `react-ui-specialist.md`, `nextjs-ui-specialist.md`
- Tools: Code generation, visual regression testing

### Component Diagram

```
┌────────────────────────────────────────────────────────┐
│                    User Interface                      │
│  /task-create "Button" design:https://figma.com/...   │
└───────────────────────┬────────────────────────────────┘
                        │
┌───────────────────────▼────────────────────────────────┐
│             Task Management Layer                      │
│  - Task creation (with design_url)                     │
│  - Task metadata storage                               │
│  - State management                                    │
└───────────────────────┬────────────────────────────────┘
                        │
┌───────────────────────▼────────────────────────────────┐
│            Orchestration Layer                         │
│  - Design source detection                             │
│  - Stack detection                                     │
│  - Orchestrator selection                              │
│  - Routing logic                                       │
└─────────┬──────────────────────────────────┬───────────┘
          │                                  │
┌─────────▼──────────┐           ┌──────────▼──────────┐
│  Figma Orchestrator │           │  Zeplin Orchestrator │
│                     │           │                      │
│ Phase 0: MCP Verify │           │ Phase 0: MCP Verify  │
│ Phase 1: Extract    │           │ Phase 1: Extract     │
│ Phase 2: Boundaries │           │ Phase 2: Boundaries  │
│ Phase 3: Delegate   │───────────│ Phase 3: Delegate    │
│ Phase 4: Test       │           │ Phase 4: Test        │
│ Phase 5: Validate   │           │ Phase 5: Validate    │
└─────────┬──────────┘           └──────────┬───────────┘
          │                                  │
          └──────────────┬───────────────────┘
                         │
┌────────────────────────▼───────────────────────────────┐
│              UI Specialist Layer                       │
│  - Component generation                                │
│  - Visual regression testing                           │
│  - Stack-specific patterns                             │
└────────────────────────────────────────────────────────┘
```

### Sequence Diagrams

**Successful Design-to-Code Flow:**

```
User          Task-Work     Orchestrator    MCP Server    UI Specialist
 │                │              │              │               │
 │ task-create   │              │              │               │
 │ design:url    │              │              │               │
 ├──────────────>│              │              │               │
 │                │              │              │               │
 │ task-work     │              │              │               │
 │ TASK-XXX      │              │              │               │
 ├──────────────>│              │              │               │
 │                │              │              │               │
 │                │ Phase 1:     │              │               │
 │                │ Load design_url             │               │
 │                │─────────────>│              │               │
 │                │              │              │               │
 │                │ Phase 3:     │              │               │
 │                │ Route to     │              │               │
 │                │ orchestrator │              │               │
 │                │─────────────>│              │               │
 │                │              │              │               │
 │                │              │ Phase 0:     │               │
 │                │              │ Verify MCP   │               │
 │                │              ├─────────────>│               │
 │                │              │<─────────────┤               │
 │                │              │  MCP OK      │               │
 │                │              │              │               │
 │                │              │ Phase 1:     │               │
 │                │              │ Extract      │               │
 │                │              │ design       │               │
 │                │              ├─────────────>│               │
 │                │              │<─────────────┤               │
 │                │              │ Design data  │               │
 │                │              │              │               │
 │                │              │ Phase 2:     │               │
 │                │              │ Document     │               │
 │                │              │ boundaries   │               │
 │                │              │              │               │
 │                │              │ Phase 3:     │               │
 │                │              │ Delegate     │               │
 │                │              ├──────────────┼──────────────>│
 │                │              │              │  Generate     │
 │                │              │              │  component    │
 │                │              │              │               │
 │                │              │              │  Phase 4:     │
 │                │              │              │  Run tests    │
 │                │              │<─────────────┼───────────────┤
 │                │              │ Component result              │
 │                │              │              │               │
 │                │              │ Phase 5:     │               │
 │                │              │ Validate     │               │
 │                │              │ constraints  │               │
 │                │              │              │               │
 │                │<─────────────┤              │               │
 │                │ Success      │              │               │
 │<───────────────┤              │              │               │
 │ Component      │              │              │               │
 │ generated      │              │               │              │
```

## Design Patterns

### Saga Pattern

The **Saga Pattern** coordinates a sequence of related operations with compensation logic.

**Implementation in Orchestrators:**

Each orchestrator executes a 6-phase saga:
1. **Phase 0**: MCP Verification (abort if MCP unavailable)
2. **Phase 1**: Design Extraction (abort if extraction fails)
3. **Phase 2**: Boundary Documentation (document prohibitions)
4. **Phase 3**: Component Generation (delegate to UI specialist)
5. **Phase 4**: Visual Regression Testing (delegate to UI specialist)
6. **Phase 5**: Constraint Validation (abort if violations detected)

**Compensation:**
- If Phase 0 fails: Guide user to install MCP
- If Phase 1 fails: Validate design URL, check permissions
- If Phase 3 fails: UI specialist returns error details
- If Phase 5 fails: Rollback generated files, report violations

**Benefits:**
- Clear error handling at each phase
- Easy to understand workflow
- Audit trail of what happened
- Graceful failure handling

### Orchestrator Pattern

The **Orchestrator Pattern** coordinates multiple services without them knowing about each other.

**Implementation:**

Orchestrators coordinate MCP servers and UI specialists:
- Orchestrator calls MCP to extract design
- Orchestrator prepares design context
- Orchestrator delegates to UI specialist
- Orchestrator validates results
- UI specialist never knows about MCP server
- MCP server never knows about UI specialist

**Benefits:**
- Loose coupling between components
- Easy to add new design sources
- Easy to add new stacks
- Clear responsibilities

### Delegation Pattern

The **Delegation Pattern** transfers responsibility for a task to another component.

**Implementation:**

Orchestrators delegate component generation to UI specialists:

```typescript
// Orchestrator delegates to UI specialist
const componentResult = await invokeAgent({
  agent: `${stack}-ui-specialist`,
  input: {
    designElements: extractedElements,
    designConstraints: prohibitionChecklist,
    designMetadata: metadata
  }
});
```

UI specialist generates component and returns result:

```typescript
// UI specialist returns result to orchestrator
return {
  generated_files: ['Button.tsx', 'Button.test.ts'],
  visual_fidelity: 0.973,
  constraint_violations: []
};
```

**Benefits:**
- UI specialist focused on code generation only
- Orchestrator focused on workflow only
- Clear interface between layers
- Technology-agnostic orchestration

### Constraint Validation Pattern

The **Constraint Validation Pattern** enforces boundaries via prohibition checklists.

**Implementation:**

Orchestrator generates prohibition checklist (Phase 2):

```typescript
const prohibitionChecklist = {
  no_business_logic: true,
  no_api_integration: true,
  no_database_operations: true,
  no_authentication: true,
  no_state_management: true,
  no_routing: true,
  no_error_handling: true,
  no_loading_states: true,
  no_data_validation: true,
  no_internationalization: true,
  no_analytics: true,
  no_testing_infrastructure: true
};
```

Orchestrator validates generated code (Phase 5):

```typescript
function validateConstraints(code: string, checklist: ProhibitionChecklist): string[] {
  const violations = [];

  if (checklist.no_api_integration && (code.includes('fetch(') || code.includes('axios'))) {
    violations.push("API integration detected");
  }

  if (checklist.no_state_management && (code.includes('useState') || code.includes('useReducer'))) {
    violations.push("State management detected");
  }

  // More checks...

  return violations;
}
```

**Benefits:**
- Zero tolerance for scope creep
- Clear boundaries documented upfront
- Automated validation
- Predictable behavior

## Orchestrators

### Orchestrator Responsibilities

1. **MCP Verification**: Check if required MCP server is available
2. **Design Extraction**: Call MCP to extract design elements
3. **Boundary Documentation**: Generate prohibition checklist
4. **Delegation**: Invoke appropriate UI specialist
5. **Constraint Validation**: Validate generated code against prohibitions

### 6-Phase Saga Implementation

**Example: Figma Orchestrator**

```markdown
---
name: figma-orchestrator
description: Orchestrates Figma design extraction and delegates to UI specialists
tools: Read, Write, Grep, mcp__figma-dev-mode__*
mcp_dependencies:
  - figma-dev-mode (required)
---

# Mission

Execute a 6-phase Saga pattern workflow that extracts Figma designs, delegates component generation to stack-specific UI specialists, and validates visual fidelity while enforcing strict constraint adherence (zero scope creep).

## Phase 0: MCP Verification

Check if figma-dev-mode MCP server is available:

```typescript
if (!isMCPAvailable('figma-dev-mode')) {
  throw new Error("Figma MCP server not available. Please install: npm install -g @figma/mcp-server");
}
```

## Phase 1: Design Extraction

Extract design from Figma via MCP:

```typescript
const designData = await mcp__figma_dev_mode__get_figma_data({
  fileKey: designMetadata.file_key,
  nodeId: designMetadata.node_id
});

const visualReference = await mcp__figma_dev_mode__download_figma_images({
  fileKey: designMetadata.file_key,
  nodes: [{ nodeId: designMetadata.node_id, fileName: 'reference.png' }],
  localPath: '.temp/design-references/'
});
```

## Phase 2: Boundary Documentation

Generate prohibition checklist:

```typescript
const prohibitionChecklist = {
  no_business_logic: true,
  no_api_integration: true,
  // ... all 12 prohibitions
};
```

## Phase 3: Component Generation (Delegated)

Delegate to UI specialist:

```typescript
const componentResult = await invokeAgent({
  agent: `${stack}-ui-specialist`,
  input: {
    designElements: extractedElements,
    designConstraints: prohibitionChecklist,
    designMetadata: {
      source: 'figma',
      fileKey: designMetadata.file_key,
      nodeId: designMetadata.node_id,
      extractedAt: new Date().toISOString(),
      visualReference: visualReference.path
    }
  }
});
```

## Phase 4: Visual Regression Testing (Delegated)

UI specialist runs Playwright tests and returns visual fidelity score.

## Phase 5: Constraint Validation

Validate generated code:

```typescript
const violations = validateConstraints(
  componentResult.generated_files,
  prohibitionChecklist
);

if (violations.length > 0) {
  throw new Error(`Constraint violations detected: ${violations.join(', ')}`);
}

if (componentResult.visual_fidelity < 0.95) {
  throw new Error(`Visual fidelity below threshold: ${componentResult.visual_fidelity}`);
}
```
```

### MCP Integration

Orchestrators use MCP servers for design extraction:

**Figma MCP Tools:**
- `mcp__figma-dev-mode__get_figma_data`: Extract design data
- `mcp__figma-dev-mode__download_figma_images`: Download images
- `mcp__figma-dev-mode__get_variable_defs`: Get design variables

**Zeplin MCP Tools:**
- `mcp__zeplin__get_project`: Get project details
- `mcp__zeplin__get_screen`: Get screen details
- `mcp__zeplin__get_component`: Get component details
- `mcp__zeplin__get_styleguide`: Get style guide
- `mcp__zeplin__get_colors`: Get color palette
- `mcp__zeplin__get_text_styles`: Get text styles

## UI Specialists

### UI Specialist Responsibilities

1. **Design Context Detection**: Detect if design context is present
2. **Component Generation**: Generate code in stack-appropriate format
3. **Visual Regression Testing**: Run Playwright tests against visual reference
4. **Result Reporting**: Return generated files, visual fidelity, and violations

### Design Context Interface

UI specialists receive design context from orchestrators:

```typescript
interface DesignContext {
  designElements: ExtractedElement[];
  designConstraints: ProhibitionChecklist;
  designMetadata: {
    source: "figma" | "zeplin";
    fileKey?: string;
    nodeId?: string;
    projectId?: string;
    screenId?: string;
    extractedAt: string;
    visualReference: string;
  };
}
```

### Component Generation

**Example: React UI Specialist**

```markdown
## Design-Driven Implementation Mode

When design context is present:

**Step 1: Detect Design Context**

```typescript
const hasDesignContext = input?.designContext !== undefined;

if (!hasDesignContext) {
  // Standard UI implementation mode
  // ...
  return;
}
```

**Step 2: Generate Component**

```typescript
// Extract design elements
const { designElements, designConstraints, designMetadata } = input.designContext;

// Generate TypeScript React component matching design exactly
// Apply Tailwind CSS classes for styling (match design specs pixel-perfect)
// Implement ONLY props for visible design elements
// NO loading states, error states, or API integrations
```

**Step 3: Generate Visual Regression Test**

```typescript
// Generate Playwright test
// Compare rendered component to visual reference
// Return visual fidelity score
```

**Step 4: Return Results**

```typescript
return {
  generated_files: ['Button.tsx', 'Button.test.ts'],
  visual_fidelity: 0.973,
  constraint_violations: []
};
```
```

### Visual Regression Testing

UI specialists generate Playwright tests for visual validation:

```typescript
// tests/Button.visual.spec.ts
import { test, expect } from '@playwright/test';

test('Button matches design specification', async ({ page }) => {
  await page.goto('/component-preview/Button');
  await page.waitForSelector('[data-testid="button"]');

  const screenshot = await page.screenshot();
  const designReference = await loadDesignReference('Button');
  const similarity = await compareImages(screenshot, designReference);

  expect(similarity).toBeGreaterThan(0.95);
});
```

## Extension Points

### Creating New UI Specialists

To add support for a new stack (e.g., Flutter):

**Step 1: Create UI Specialist File**

Location: `installer/core/templates/flutter-*/agents/flutter-ui-specialist.md`

**Step 2: Implement Design Context Detection**

```markdown
## Design-Driven Implementation Mode

When design context is present, generate Flutter widget matching design exactly.
```

**Step 3: Implement Component Generation**

```markdown
**Generate Dart Widget:**
- Extract design elements from context
- Generate Flutter widget code
- Apply styling from design
- Return generated files
```

**Step 4: Implement Visual Regression Testing**

```markdown
**Run Visual Tests:**
- Use Flutter integration testing
- Compare screenshots to design reference
- Return visual fidelity score
```

**Step 5: Update Stack Detection**

Add Flutter detection to task-work Phase 3:

```python
# Check for Flutter
pubspec_yaml = cwd / "pubspec.yaml"
if pubspec_yaml.exists():
    return 'flutter'
```

### Creating New Orchestrators

To add support for a new design source (e.g., Sketch):

**Step 1: Create Orchestrator File**

Location: `installer/core/agents/sketch-orchestrator.md`

**Step 2: Implement 6-Phase Saga**

Follow the same pattern as figma-orchestrator and zeplin-orchestrator.

**Step 3: Add MCP Integration**

Create or use existing MCP server for Sketch.

**Step 4: Update Design Source Detection**

Add Sketch detection to task-work Phase 1:

```python
def detect_design_source(design_url: str) -> str:
    if 'sketch.cloud' in design_url:
        return 'sketch'
    # ...
```

### Adding Design Sources

To add a new design source:

1. **Create MCP Server**: Develop MCP server for design tool
2. **Create Orchestrator**: Implement 6-phase saga
3. **Update Detection**: Add URL pattern detection
4. **Update Validation**: Add URL format validation
5. **Test**: Create integration tests

## Integration Patterns

### Task-Work Integration

**Phase 1: Load Design URL**

```python
# Phase 1: Requirements Analysis
design_url = task.frontmatter.get('design_url')

if design_url:
    design_source = detect_design_source(design_url)
    design_metadata = parse_design_url(design_url, design_source)

    # Store in task state
    task.state['design_context'] = {
        'design_url': design_url,
        'design_source': design_source,
        'design_metadata': design_metadata
    }
```

**Phase 3: Route to Orchestrator**

```python
# Phase 3: Implementation
design_context = task.state.get('design_context')

if design_context:
    orchestrator_name = get_orchestrator_for_source(design_context['design_source'])
    stack = detect_project_stack()

    invoke_orchestrator(
        orchestrator_name=orchestrator_name,
        task=task,
        design_context=design_context,
        target_stack=stack
    )
```

### MCP Server Integration

Orchestrators call MCP servers via tool invocation:

```typescript
// Figma MCP call
const designData = await tools.mcp__figma_dev_mode__get_figma_data({
  fileKey: 'abc123',
  nodeId: '2:2'
});

// Zeplin MCP call
const screenData = await tools.mcp__zeplin__get_screen({
  projectId: 'proj123',
  screenId: 'screen456'
});
```

### Stack Detection

Detect project stack from project files:

```python
def detect_project_stack() -> str:
    cwd = Path.cwd()

    # Check for Next.js
    package_json = cwd / "package.json"
    if package_json.exists():
        with open(package_json) as f:
            package_data = json.load(f)
            dependencies = {**package_data.get('dependencies', {}), **package_data.get('devDependencies', {})}

            if 'next' in dependencies:
                return 'nextjs'
            elif 'react' in dependencies:
                return 'react'

    # Check for .NET MAUI
    for csproj_file in cwd.rglob("*.csproj"):
        with open(csproj_file) as f:
            if '<UseMaui>true</UseMaui>' in f.read():
                return 'maui'

    # Check for Flutter
    if (cwd / "pubspec.yaml").exists():
        return 'flutter'

    return 'unknown'
```

## Testing Strategies

### Unit Testing

Test individual components in isolation:

```python
def test_detect_design_source_figma():
    url = "https://figma.com/design/abc123/MyDesign?node-id=2-2"
    assert detect_design_source(url) == 'figma'

def test_detect_design_source_zeplin():
    url = "https://app.zeplin.io/project/proj123/screen/screen456"
    assert detect_design_source(url) == 'zeplin'

def test_parse_figma_url():
    url = "https://figma.com/design/abc123/MyDesign?node-id=2-2"
    metadata = parse_design_url(url, 'figma')
    assert metadata['file_key'] == 'abc123'
    assert metadata['node_id'] == '2:2'
```

### Integration Testing

Test full workflow with mocked components:

```python
@pytest.mark.integration
def test_design_to_code_workflow_figma(mock_mcp_server, mock_ui_specialist):
    # Create task with Figma design URL
    task = create_task("Button", design_url="https://figma.com/design/abc123/?node-id=2-2")

    # Work on task
    result = task_work(task.id)

    # Assert orchestrator was invoked
    assert result.orchestrator == 'figma-orchestrator'

    # Assert UI specialist was invoked
    assert result.ui_specialist == 'react-ui-specialist'

    # Assert component generated
    assert len(result.generated_files) > 0
```

### Visual Regression Testing

Test visual fidelity with Playwright:

```typescript
test('Generated component matches design', async ({ page }) => {
  await page.goto('/component-preview/Button');
  await page.waitForSelector('[data-testid="button"]');

  const screenshot = await page.screenshot();
  const designReference = fs.readFileSync('.temp/design-references/Button.png');
  const similarity = await compareImages(screenshot, designReference);

  expect(similarity).toBeGreaterThan(0.95);
});
```

## Code Examples

### Creating a UI Specialist Example

**File: `installer/core/templates/flutter-ui-specialist/agents/flutter-ui-specialist.md`**

```markdown
---
name: flutter-ui-specialist
description: Flutter widget specialist with design context support
tools: Read, Write, Edit, Bash, Grep, Glob
capabilities:
  - standard_ui_implementation
  - design_driven_implementation
  - visual_regression_testing
design_sources:
  - figma
  - zeplin
---

# Mission

Generate Flutter widgets with optional design context support.

## Design Context Detection

```dart
// Detect if design context is present
final hasDesignContext = input?.designContext != null;

if (hasDesignContext) {
  // Design-driven mode
  final designElements = input.designContext.designElements;
  final designConstraints = input.designContext.designConstraints;
  final designMetadata = input.designContext.designMetadata;

  // Generate Flutter widget matching design exactly
  // ...
} else {
  // Standard Flutter widget generation
  // ...
}
```

## Component Generation

When design context is present:

**Step 1: Analyze Design Elements**

Extract Flutter-specific properties from design elements.

**Step 2: Generate Widget**

```dart
import 'package:flutter/material.dart';

class ButtonWidget extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;

  const ButtonWidget({
    Key? key,
    required this.label,
    this.onPressed,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return ElevatedButton(
      onPressed: onPressed,
      style: ElevatedButton.styleFrom(
        backgroundColor: Color(0xFF2563EB),
        padding: EdgeInsets.symmetric(horizontal: 24, vertical: 12),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w600,
          color: Colors.white,
        ),
      ),
    );
  }
}
```

**Step 3: Generate Visual Regression Test**

```dart
// test/button_widget_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';
import 'package:my_app/widgets/button_widget.dart';

void main() {
  testWidgets('ButtonWidget matches design specification', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ButtonWidget(label: 'Click me', onPressed: () {}),
        ),
      ),
    );

    await expectLater(
      find.byType(ButtonWidget),
      matchesGoldenFile('goldens/button_widget.png'),
    );
  });
}
```

**Step 4: Return Results**

```dart
return ComponentResult(
  generatedFiles: [
    'lib/widgets/button_widget.dart',
    'test/button_widget_test.dart',
  ],
  visualFidelity: 0.973,
  constraintViolations: [],
);
```
```

### Implementing Design Context Detection

```typescript
// In UI specialist agent
const hasDesignContext = input?.designContext !== undefined;

if (hasDesignContext) {
  console.log("Design-driven implementation mode activated");

  const { designElements, designConstraints, designMetadata } = input.designContext;

  // Extract relevant information
  const designSource = designMetadata.source; // "figma" or "zeplin"
  const visualReference = designMetadata.visualReference;

  // Proceed with design-driven generation
  generateComponentFromDesign(designElements, designConstraints);
} else {
  console.log("Standard implementation mode");

  // Proceed with standard generation
  generateComponentFromRequirements(taskDescription);
}
```

### Constraint Validation Example

```typescript
function validateConstraints(
  generatedCode: string,
  constraints: ProhibitionChecklist
): string[] {
  const violations: string[] = [];

  // Check for API integration
  if (constraints.prohibitions.no_api_integration) {
    if (generatedCode.includes('fetch(') || generatedCode.includes('axios')) {
      violations.push("API integration detected (prohibited)");
    }
  }

  // Check for state management
  if (constraints.prohibitions.no_state_management) {
    const stateHookCount = (generatedCode.match(/useState|useReducer/g) || []).length;
    if (stateHookCount > 3) { // Arbitrary threshold for complex state management
      violations.push("Complex state management detected (may exceed design boundaries)");
    }
  }

  // Check for routing
  if (constraints.prohibitions.no_routing) {
    if (generatedCode.includes('useRouter') || generatedCode.includes('redirect')) {
      violations.push("Routing logic detected (prohibited)");
    }
  }

  // Add more checks for other prohibitions...

  return violations;
}
```

## Best Practices

1. **Keep Orchestrators Technology-Agnostic**
   - Don't add stack-specific logic to orchestrators
   - Use delegation for all code generation
   - Orchestrators should only coordinate

2. **Make UI Specialists Stack-Specific**
   - Each UI specialist should be an expert in its stack
   - Generate idiomatic code for the stack
   - Follow stack-specific best practices

3. **Enforce Constraint Boundaries**
   - Always validate generated code against prohibitions
   - Zero tolerance for violations
   - Fail fast if scope creep detected

4. **Test Visual Fidelity**
   - Always require >95% similarity
   - Use visual regression testing
   - Compare to design reference image

5. **Provide Clear Error Messages**
   - Guide users to resolution
   - Include help text for MCP installation
   - Suggest alternatives when constraints violated

6. **Document Extension Points**
   - Make it easy to add new stacks
   - Provide clear examples
   - Follow existing patterns

## Performance Considerations

1. **MCP Calls**: Cache design data to avoid repeated MCP calls
2. **Image Comparison**: Use efficient image comparison algorithms
3. **Stack Detection**: Cache stack detection results
4. **File Generation**: Generate files in parallel when possible

## Security Considerations

1. **MCP Tokens**: Store tokens securely in MCP configuration
2. **Design URLs**: Validate URL formats to prevent injection
3. **Generated Code**: Scan for security vulnerabilities (XSS, SQL injection)
4. **File Paths**: Validate file paths to prevent directory traversal

---

## See Also

- [Design-to-Code User Guide](../guides/design-to-code-user-guide.md)
- [Design URL Integration Proposal](../proposals/design-url-integration-proposal.md)
- [Implementation Guide](../proposals/design-url-integration-implementation-guide.md)
- [UX Design Integration Workflow](../workflows/ux-design-integration-workflow.md)
```

### Key Sections

1. **Architecture**: High-level overview with diagrams
2. **Design Patterns**: Saga, Orchestrator, Delegation, Constraint Validation
3. **Orchestrators**: Responsibilities, 6-phase saga, MCP integration
4. **UI Specialists**: Responsibilities, design context, component generation
5. **Extension Points**: How to create new UI specialists and orchestrators
6. **Integration Patterns**: Task-work integration, MCP integration, stack detection
7. **Testing Strategies**: Unit, integration, visual regression testing
8. **Code Examples**: Real implementations of key patterns
9. **Best Practices**: Guidelines for extending the system
10. **Performance & Security**: Considerations for production use

### Testing Strategy

**Documentation Review**:
- Technical accuracy
- Code examples correctness
- Diagrams clear and accurate
- Extension guide completeness

**Developer Testing**:
- Can developers follow extension guide?
- Are patterns clear and understandable?
- Can developers create new UI specialists successfully?

## Test Requirements

- [ ] Technical review: Architecture diagrams accurate
- [ ] Technical review: Code examples correct and runnable
- [ ] Technical review: Patterns explained clearly
- [ ] Developer testing: Extension guide can be followed
- [ ] Developer testing: New UI specialist can be created
- [ ] Documentation standards: Formatting consistent
- [ ] Documentation standards: Cross-references valid

## Dependencies

**Blockers** (must be completed first):
- All implementation tasks (UX-001 through UX-010) for accurate technical documentation

**Related**:
- TASK-UX-602E: Create design-to-code user guide (complements this doc)
- TASK-UX-187C: Update CLAUDE.md (references this doc)

## Next Steps

After completing this task:
1. Link from CLAUDE.md
2. Gather developer feedback
3. Create video tutorials if needed
4. Update based on community contributions

## References

- [Design URL Integration Proposal](../../docs/proposals/design-url-integration-proposal.md)
- [Implementation Guide](../../docs/proposals/design-url-integration-implementation-guide.md)
- [Design-to-Code User Guide](../../docs/guides/design-to-code-user-guide.md)
- [Figma Orchestrator](../../installer/core/agents/figma-orchestrator.md)
- [Zeplin Orchestrator](../../installer/core/agents/zeplin-orchestrator.md)
- [React UI Specialist](../../installer/core/templates/react-typescript/agents/react-ui-specialist.md)
- [Next.js UI Specialist](../../installer/core/templates/nextjs-fullstack/agents/nextjs-ui-specialist.md)

## Implementation Estimate

**Duration**: 8-10 hours

**Complexity**: 7/10 (High)
- Comprehensive technical documentation
- Architecture diagrams
- Detailed code examples
- Extension guides
- Testing strategies
- Best practices

## Test Execution Log

_Automatically populated by /task-work_
