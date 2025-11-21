---
id: TASK-UX-92BF
title: Extend nextjs-ui-specialist to handle design contexts
status: backlog
created: 2025-11-11T11:15:00Z
updated: 2025-11-11T11:15:00Z
priority: high
tags: [ux-integration, ui-specialist, nextjs]
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Extend nextjs-ui-specialist to handle design contexts

## Description

Extend the existing `nextjs-ui-specialist.md` agent in the nextjs-fullstack template to handle design contexts passed from orchestrators (figma-orchestrator, zeplin-orchestrator).

The agent should detect when a design context is present and switch to design-driven implementation mode, generating Next.js components that match design specifications exactly while maintaining visual fidelity.

This is part of Phase 3 of the Design URL Integration project (see [design-url-integration-implementation-guide.md](../../docs/proposals/design-url-integration-implementation-guide.md)).

## Acceptance Criteria

- [ ] Agent detects design context from orchestrator input
- [ ] Design-driven implementation mode activated when context present
- [ ] Next.js components generated match design specifications exactly
- [ ] Appropriate use of Client Components ('use client') for interactive elements
- [ ] Visual regression tests run automatically (Playwright)
- [ ] Results returned to orchestrator in expected format
- [ ] Graceful fallback to standard UI implementation when no design context
- [ ] Zero scope creep enforcement (only implement visible design elements)
- [ ] Agent updated in nextjs-fullstack template directory
- [ ] Tests updated to cover design context scenarios

## Implementation Notes

### Source File
- **File**: `installer/global/templates/nextjs-fullstack/agents/nextjs-ui-specialist.md`

### Key Changes Required

**1. Add Design Context Detection**

Add detection logic at the beginning of the agent prompt:

```typescript
// Detect if this is a design-driven implementation
const hasDesignContext = input?.designContext !== undefined;

if (hasDesignContext) {
  // Design-driven mode
  const { designElements, designConstraints, designMetadata } = input.designContext;

  // Extract design source
  const designSource = designMetadata.source; // "figma" or "zeplin"

  // Proceed with design-driven implementation
  // ...
} else {
  // Standard UI implementation mode (existing behavior)
  // ...
}
```

**2. Update Agent Metadata**

Add capabilities section to frontmatter:

```markdown
---
name: nextjs-ui-specialist
description: Next.js component specialist with design context support
tools: Read, Write, Edit, Bash, Grep, Glob
capabilities:
  - standard_ui_implementation
  - design_driven_implementation
  - visual_regression_testing
  - constraint_validation
  - server_component_optimization
  - client_component_generation
design_sources:
  - figma
  - zeplin
---
```

**3. Add Design-Driven Implementation Mode**

```typescript
### Design-Driven Implementation Mode

When design context is present:

**Step 1: Analyze Design Elements**
- Review extracted design elements from orchestrator
- Identify component structure (hierarchy, layout)
- Extract styling requirements (colors, fonts, spacing)
- Note interactive elements (buttons, inputs, links)
- Determine if Client Component is needed ('use client' directive)

**Step 2: Generate Next.js Component**
- Create TypeScript Next.js component matching design exactly
- Add 'use client' directive if component has interactivity (onClick, onChange, useState, etc.)
- Use Server Component by default for static design elements
- Apply Tailwind CSS classes for styling (match design specs pixel-perfect)
- Implement ONLY props for visible design elements
- NO loading states, error states, or API integrations
- NO logic beyond what's visible in the design
- Follow Next.js 14+ App Router conventions

**Step 3: Apply Design Constraints**
- Review prohibition checklist from orchestrator
- Enforce zero scope creep (no extra features)
- Validate against constraint violations

**Step 4: Run Visual Regression Tests**
- Generate Playwright visual regression test
- Compare rendered component to design visual reference
- Calculate visual fidelity score (0.0-1.0)
- Require >95% similarity for approval

**Step 5: Return Results to Orchestrator**
```typescript
interface ComponentResult {
  generated_files: string[];
  visual_fidelity: number;  // 0.0-1.0
  constraint_violations: string[];
}
```

Example return:
```typescript
{
  generated_files: [
    "src/components/LoginButton.tsx",
    "tests/LoginButton.visual.spec.ts"
  ],
  visual_fidelity: 0.97,
  constraint_violations: []
}
```

**4. Update Existing Behavior (Standard Mode)**

Keep existing behavior when no design context present:

```typescript
### Standard UI Implementation Mode

When NO design context is present (default behavior):

1. Analyze user requirements from task description
2. Generate Next.js component (Server or Client as appropriate)
3. Apply Tailwind CSS styling
4. Write unit tests (Vitest or Jest)
5. Follow Next.js best practices (App Router)
6. Return generated files list
```

**5. Design Elements Interface**

The orchestrator will pass design context in this format:

```typescript
interface DesignContext {
  designElements: ExtractedElement[];
  designConstraints: ProhibitionChecklist;
  designMetadata: {
    source: "figma" | "zeplin";
    nodeId?: string;        // Figma
    fileKey?: string;       // Figma
    projectId?: string;     // Zeplin
    screenId?: string;      // Zeplin
    componentId?: string;   // Zeplin
    extractedAt: string;
    visualReference: string; // Base64 image or URL
  };
}

interface ExtractedElement {
  id: string;
  type: "frame" | "text" | "button" | "image" | "icon" | "input";
  name: string;
  properties: {
    position: { x: number; y: number; width: number; height: number };
    style: {
      backgroundColor?: string;
      color?: string;
      fontSize?: string;
      fontWeight?: string;
      fontFamily?: string;
      borderRadius?: string;
      padding?: string;
      margin?: string;
      border?: string;
      icon?: string;
    };
    content?: string; // For text elements
    placeholder?: string; // For input elements
  };
  children?: ExtractedElement[];
}

interface ProhibitionChecklist {
  prohibitions: {
    no_business_logic: boolean;
    no_api_integration: boolean;
    no_database_operations: boolean;
    no_authentication: boolean;
    no_state_management: boolean;
    no_routing: boolean;
    no_error_handling: boolean;
    no_loading_states: boolean;
    no_data_validation: boolean;
    no_internationalization: boolean;
    no_analytics: boolean;
    no_testing_infrastructure: boolean;
  };
}
```

**6. Client vs Server Component Decision**

```typescript
/**
 * Determine if component needs 'use client' directive
 */
function needsClientComponent(designElements: ExtractedElement[]): boolean {
  // Check for interactive elements
  const hasInteractivity = designElements.some(element =>
    element.type === 'button' ||
    element.type === 'input' ||
    element.properties.onClick !== undefined
  );

  // Client Component required if any interactivity detected
  return hasInteractivity;
}

// Example generated component
'use client'; // Only if needsClientComponent() returns true

import { cn } from '@/lib/utils';

interface LoginButtonProps {
  label: string;
  onClick?: () => void;
}

export function LoginButton({ label, onClick }: LoginButtonProps) {
  return (
    <button
      onClick={onClick}
      className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
    >
      {label}
    </button>
  );
}
```

**7. Visual Regression Testing with Playwright**

Generate Playwright test for visual regression:

```typescript
// tests/LoginButton.visual.spec.ts
import { test, expect } from '@playwright/test';

test('LoginButton matches design specification', async ({ page }) => {
  // Render component in Next.js app
  await page.goto('/component-preview/LoginButton');

  // Wait for component to render
  await page.waitForSelector('[data-testid="login-button"]');

  // Take screenshot
  const screenshot = await page.screenshot();

  // Compare to design reference (provided by orchestrator)
  const designReference = await loadDesignReference('LoginButton');
  const similarity = await compareImages(screenshot, designReference);

  // Assert visual fidelity >95%
  expect(similarity).toBeGreaterThan(0.95);
});
```

**8. Error Handling**

Handle cases where design context is invalid:

```typescript
if (hasDesignContext) {
  // Validate design context structure
  if (!input.designContext.designElements || input.designContext.designElements.length === 0) {
    throw new Error("Invalid design context: no design elements provided");
  }

  if (!input.designContext.designMetadata.visualReference) {
    throw new Error("Invalid design context: no visual reference provided");
  }

  // Proceed with design-driven implementation
  // ...
}
```

**9. Constraint Validation**

Before returning results, validate against constraints:

```typescript
function validateConstraints(
  generatedCode: string,
  constraints: ProhibitionChecklist
): string[] {
  const violations: string[] = [];

  // Check for prohibited patterns
  if (constraints.prohibitions.no_api_integration && (generatedCode.includes('fetch(') || generatedCode.includes('axios'))) {
    violations.push("API integration detected (prohibited)");
  }

  if (constraints.prohibitions.no_state_management && (generatedCode.includes('useState') || generatedCode.includes('useReducer'))) {
    violations.push("State management detected beyond what's visible (prohibited)");
  }

  if (constraints.prohibitions.no_loading_states && generatedCode.includes('isLoading')) {
    violations.push("Loading state detected (prohibited)");
  }

  if (constraints.prohibitions.no_routing && (generatedCode.includes('useRouter') || generatedCode.includes('redirect'))) {
    violations.push("Routing logic detected (prohibited)");
  }

  // Add more checks for other prohibitions...

  return violations;
}
```

**10. Next.js Specific Patterns**

Ensure generated components follow Next.js best practices:

```typescript
// Use Next.js Image component for images (when appropriate)
import Image from 'next/image';

// Use Next.js Link component for navigation (when appropriate)
import Link from 'next/link';

// Use Server Components by default, Client Components only when needed
// Server Component (default - no 'use client')
export function StaticDesignElement() {
  return <div>Static content</div>;
}

// Client Component (only for interactivity)
'use client';
export function InteractiveDesignElement() {
  const [state, setState] = useState();
  return <button onClick={() => setState(...)}>Click me</button>;
}
```

### Testing Strategy

**Unit Tests**:
- Test design context detection (with/without context)
- Test mode switching (design-driven vs standard)
- Test design element parsing
- Test Client vs Server Component decision logic
- Test constraint validation logic
- Test result format

**Integration Tests**:
- Full flow with mock design context from orchestrator
- Verify component generation matches design specs
- Verify correct 'use client' directive usage
- Verify Playwright visual regression test generation
- Verify result format returned to orchestrator

**Manual Testing**:
- Test with figma-orchestrator (after UX-003 is complete)
- Test with zeplin-orchestrator (after UX-004 is complete)
- Verify visual fidelity >95% with real designs
- Test Server Component rendering
- Test Client Component interactivity

## Test Requirements

- [ ] Unit test: Design context detection (present)
- [ ] Unit test: Design context detection (absent)
- [ ] Unit test: Mode switching (design-driven vs standard)
- [ ] Unit test: Design element parsing
- [ ] Unit test: Client vs Server Component decision logic
- [ ] Unit test: Constraint validation logic
- [ ] Unit test: Result format validation
- [ ] Integration test: Full design-driven flow with mock context
- [ ] Integration test: Component generation matches design specs
- [ ] Integration test: Correct 'use client' directive usage
- [ ] Integration test: Playwright test generation
- [ ] Integration test: Result returned to orchestrator
- [ ] Edge case test: Invalid design context
- [ ] Edge case test: Missing visual reference
- [ ] Edge case test: Empty design elements array
- [ ] Edge case test: Constraint violation detected
- [ ] Edge case test: Complex nested design elements

## Dependencies

**Blockers** (must be completed first):
- TASK-UX-2A61: Refactor figma-react-orchestrator to figma-orchestrator
- TASK-UX-EFC3: Refactor zeplin-maui-orchestrator to zeplin-orchestrator

**Parallel Development**: Can be developed in parallel with TASK-UX-71BD (react-ui-specialist) using Conductor + git worktrees.

## Parallel Development

This task is marked for parallel development:

```bash
# Terminal 1
conductor start ux-react-ui-specialist main
cd .conductor/ux-react-ui-specialist
/task-work TASK-UX-71BD

# Terminal 2 (simultaneously)
conductor start ux-nextjs-ui-specialist main
cd .conductor/ux-nextjs-ui-specialist
/task-work TASK-UX-92BF
```

## Next Steps

After completing this task:
1. TASK-UX-007: Update task-work Phase 1 to load design URL
2. TASK-UX-008: Update task-work Phase 3 to route to orchestrators
3. TASK-UX-009: Update task-refine for design context awareness

## References

- [Design URL Integration Proposal](../../docs/proposals/design-url-integration-proposal.md)
- [Implementation Guide - Phase 3](../../docs/proposals/design-url-integration-implementation-guide.md#phase-3-extend-ui-specialists-parallel)
- [Existing Next.js UI Specialist](../../installer/global/templates/nextjs-fullstack/agents/nextjs-ui-specialist.md)
- [Figma Orchestrator](../../installer/global/agents/figma-orchestrator.md) (after UX-003)
- [Zeplin Orchestrator](../../installer/global/agents/zeplin-orchestrator.md) (after UX-004)
- [Next.js App Router Documentation](https://nextjs.org/docs/app)
- [Next.js Server and Client Components](https://nextjs.org/docs/app/building-your-application/rendering/server-components)

## Implementation Estimate

**Duration**: 4-6 hours

**Complexity**: 6/10 (Medium-High)
- Extend existing agent with design context detection
- Add design-driven implementation mode
- Handle Next.js specific patterns (Server/Client Components)
- Generate Playwright visual regression tests
- Implement constraint validation
- Maintain backward compatibility (standard mode)
- Integration with orchestrators

## Test Execution Log

_Automatically populated by /task-work_
