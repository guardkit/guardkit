---
id: TASK-UX-602E
title: Create design-to-code user guide
status: backlog
created: 2025-11-11T11:40:00Z
updated: 2025-11-11T11:40:00Z
priority: high
tags: [ux-integration, documentation, user-guide]
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Create design-to-code user guide

## Description

Create a comprehensive user guide that documents the design-to-code workflow, including setup, usage, troubleshooting, and best practices for converting Figma and Zeplin designs into code using the unified task workflow.

This is part of Phase 6 of the Design URL Integration project (see [design-url-integration-implementation-guide.md](../../docs/proposals/design-url-integration-implementation-guide.md)).

## Acceptance Criteria

- [ ] User guide created at `docs/guides/design-to-code-user-guide.md`
- [ ] Setup instructions included (MCP configuration)
- [ ] Usage examples provided for each design source (Figma, Zeplin)
- [ ] Stack-specific examples (React, Next.js, MAUI, etc.)
- [ ] Troubleshooting section included
- [ ] Best practices documented
- [ ] Architecture explanation (orchestrators + UI specialists)
- [ ] Constraint boundaries explained
- [ ] Screenshots and diagrams included (where appropriate)
- [ ] Guide linked from CLAUDE.md and README

## Implementation Notes

### Target File
- **File**: `docs/guides/design-to-code-user-guide.md`

### Document Structure

```markdown
# Design-to-Code User Guide

Comprehensive guide for converting Figma and Zeplin designs into code using GuardKit's unified design workflow.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Setup](#setup)
   - [Figma Setup](#figma-setup)
   - [Zeplin Setup](#zeplin-setup)
4. [Quick Start](#quick-start)
5. [How It Works](#how-it-works)
   - [Architecture](#architecture)
   - [6-Phase Saga Pattern](#6-phase-saga-pattern)
   - [Constraint Boundaries](#constraint-boundaries)
6. [Usage by Design Source](#usage-by-design-source)
   - [Figma to Code](#figma-to-code)
   - [Zeplin to Code](#zeplin-to-code)
7. [Stack-Specific Examples](#stack-specific-examples)
   - [React](#react-example)
   - [Next.js](#nextjs-example)
   - [.NET MAUI](#maui-example)
   - [Other Stacks](#other-stacks)
8. [Refinement and Iteration](#refinement-and-iteration)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)
11. [FAQ](#faq)
12. [Migration from Old Commands](#migration-from-old-commands)

## Overview

GuardKit's design-to-code workflow converts design system files (Figma, Zeplin) into production-ready components with **zero scope creep**.

**Key Features:**
- ✓ Technology-agnostic (works with any stack)
- ✓ Integrated with task workflow
- ✓ >95% visual fidelity
- ✓ Zero constraint violations
- ✓ Automatic testing and validation
- ✓ Full traceability

**Supported Design Sources:**
- Figma (via figma-dev-mode MCP)
- Zeplin (via zeplin MCP)

**Supported Stacks:**
- React, Next.js, Vue (via react-ui-specialist, nextjs-ui-specialist)
- .NET MAUI (via maui-ui-specialist - create via /template-create)
- Flutter, SwiftUI (create UI specialists via /template-create)

## Prerequisites

1. **GuardKit Installed**: Follow installation guide
2. **Design Tool Access**: Figma or Zeplin account with design access
3. **MCP Server**: Install appropriate MCP server (Figma or Zeplin)
4. **Project Initialized**: Use `guardkit init <template>` for your stack

## Setup

### Figma Setup

1. **Install Figma MCP Server**:
   ```bash
   npm install -g @figma/mcp-server
   ```

2. **Configure MCP Server**:
   Follow: [Figma MCP Setup Guide](../mcp-setup/figma-mcp-setup.md)

3. **Get Figma Access Token**:
   - Go to Figma → Settings → Personal Access Tokens
   - Generate new token with read access
   - Add token to MCP configuration

4. **Verify Installation**:
   ```bash
   # Check if MCP is configured
   cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

### Zeplin Setup

1. **Install Zeplin MCP Server**:
   ```bash
   npm install -g @zeplin/mcp-server
   ```

2. **Configure MCP Server**:
   Follow: [Zeplin MCP Setup Guide](../mcp-setup/zeplin-mcp-setup.md)

3. **Get Zeplin API Token**:
   - Go to Zeplin → Profile → Personal Access Tokens
   - Generate new token
   - Add token to MCP configuration

4. **Verify Installation**:
   ```bash
   # Check if MCP is configured
   cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

## Quick Start

**Step 1: Get Design URL**

**Figma**:
- Open design in Figma
- Select component/frame
- Click "Share" → Copy link
- Example: `https://figma.com/design/abc123/MyDesign?node-id=2-2`

**Zeplin**:
- Open screen in Zeplin
- Copy URL from browser
- Example: `https://app.zeplin.io/project/proj123/screen/screen456`

**Step 2: Create Task with Design URL**

```bash
/task-create "Login Button Component" design:https://figma.com/design/abc123/...?node-id=2-2
```

**Step 3: Work on Task**

```bash
/task-work TASK-XXX
```

**That's it!** The system will:
1. Extract design from Figma/Zeplin
2. Generate component matching design exactly
3. Run visual regression tests
4. Validate constraints (zero scope creep)
5. Return production-ready code

## How It Works

### Architecture

Two-tier architecture:

```
                    ┌─────────────────────────┐
                    │   task-work (Phase 3)   │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼────────────┐
                    │    Detect Design URL   │
                    │   + Detect Stack       │
                    └───────────┬────────────┘
                                │
                    ┌───────────▼────────────┐
     ┌──────────────┤   Route to Orchestrator ├──────────────┐
     │              └────────────────────────┘               │
     │                                                        │
┌────▼──────────┐                                   ┌────────▼────────┐
│   figma-      │                                   │  zeplin-        │
│   orchestrator│                                   │  orchestrator   │
└────┬──────────┘                                   └────────┬────────┘
     │                                                        │
     │  (6-phase Saga: extract, document, delegate,          │
     │                 test, validate)                       │
     │                                                        │
     └────────────────────┬──────────────────────────────────┘
                          │
          ┌───────────────▼────────────────┐
          │   Delegate to UI Specialist    │
          └───────────────┬────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
┌───────▼────────┐                  ┌───────▼────────┐
│ react-ui-      │                  │ nextjs-ui-     │
│ specialist     │                  │ specialist     │
└────────────────┘                  └────────────────┘
```

**Orchestrators** (technology-agnostic):
- Handle MCP calls (Figma/Zeplin)
- Extract design elements
- Document constraint boundaries
- Delegate to UI specialists
- Validate results

**UI Specialists** (stack-specific):
- Generate components in appropriate format
- Run visual regression tests
- Return results to orchestrator

### 6-Phase Saga Pattern

Each orchestrator executes these phases:

**Phase 0: MCP Verification**
- Check if required MCP server is available
- Validate design URL format
- Error if MCP not configured

**Phase 1: Design Extraction**
- Call Figma/Zeplin MCP to extract design
- Parse design elements (layout, colors, fonts, spacing)
- Download visual reference image
- Convert icon codes (if applicable)

**Phase 2: Boundary Documentation**
- Generate prohibition checklist (12 categories)
- Document what's NOT allowed:
  - ✗ No business logic
  - ✗ No API integration
  - ✗ No database operations
  - ✗ No authentication
  - ✗ No state management (beyond UI state)
  - ✗ No routing
  - ✗ No error handling (beyond UI feedback)
  - ✗ No loading states
  - ✗ No data validation
  - ✗ No internationalization
  - ✗ No analytics
  - ✗ No testing infrastructure

**Phase 3: Component Generation** (delegated to UI specialist)
- Pass design elements + constraints to UI specialist
- UI specialist generates component in stack-appropriate format
- UI specialist applies styling (Tailwind, XAML, etc.)
- UI specialist returns generated files

**Phase 4: Visual Regression Testing** (delegated to UI specialist)
- UI specialist generates Playwright test
- Compare rendered component to visual reference
- Calculate visual fidelity score (0.0-1.0)
- Require >95% similarity

**Phase 5: Constraint Validation** (orchestrator)
- Scan generated code for prohibited patterns
- Validate against prohibition checklist
- Zero tolerance for violations
- Fail task if violations detected

### Constraint Boundaries

**What's Generated:**
- ✓ Component structure (HTML/XAML/JSX)
- ✓ Styling (Tailwind/XAML/CSS)
- ✓ Props/properties for visible design elements
- ✓ Basic UI state (hover, focus, disabled)
- ✓ Visual tests

**What's NOT Generated:**
- ✗ Business logic
- ✗ API calls
- ✗ Database queries
- ✗ Authentication logic
- ✗ Global state management
- ✗ Routing
- ✗ Complex error handling
- ✗ Loading states
- ✗ Data validation
- ✗ Internationalization
- ✗ Analytics

**Why These Boundaries?**

Design files show **what users see**, not **what the system does**. By enforcing strict boundaries, we ensure:
1. Components match design exactly (no extra features)
2. Visual fidelity >95% (pixel-perfect)
3. Zero scope creep
4. Clear separation of concerns

## Usage by Design Source

### Figma to Code

**1. Get Figma URL**

Open Figma design and select component:
```
https://figma.com/design/{file_key}/{design_name}?node-id={node_id}
```

Example:
```
https://figma.com/design/abc123/MyDesign?node-id=2-2
```

**2. Create Task**

```bash
/task-create "Login Button" design:https://figma.com/design/abc123/MyDesign?node-id=2-2
```

**3. Work on Task**

```bash
/task-work TASK-XXX
```

**Output** (React example):
```
📁 Generated Files
- src/components/LoginButton.tsx (85 lines)
- tests/LoginButton.visual.spec.ts (42 lines)

📊 Results
- Visual Fidelity: 97.3%
- Constraint Violations: 0
- Tests: 1 passed
```

### Zeplin to Code

**1. Get Zeplin URL**

Open Zeplin screen:
```
https://app.zeplin.io/project/{project_id}/screen/{screen_id}
```

Or Zeplin component:
```
https://app.zeplin.io/project/{project_id}/styleguide/components?coid={component_id}
```

Example:
```
https://app.zeplin.io/project/proj123/screen/screen456
```

**2. Create Task**

```bash
/task-create "Dashboard Screen" design:https://app.zeplin.io/project/proj123/screen/screen456
```

**3. Work on Task**

```bash
/task-work TASK-XXX
```

**Output** (MAUI example):
```
📁 Generated Files
- Views/DashboardScreen.xaml (185 lines)
- Views/DashboardScreen.xaml.cs (42 lines)
- ViewModels/DashboardScreenViewModel.cs (68 lines)
- Tests/DashboardScreenTests.cs (95 lines)

📊 Results
- Platform Correctness: 96.8%
- Constraint Violations: 0
- Tests: 3 passed (iOS, Android, Windows)
```

## Stack-Specific Examples

### React Example

**Create Task:**
```bash
/task-create "Profile Card" design:https://figma.com/design/abc123/...?node-id=5-10
```

**Generated Files:**
```typescript
// src/components/ProfileCard.tsx
import { cn } from '@/lib/utils';

interface ProfileCardProps {
  name: string;
  title: string;
  avatarUrl: string;
  onClick?: () => void;
}

export function ProfileCard({ name, title, avatarUrl, onClick }: ProfileCardProps) {
  return (
    <div
      className="flex items-center gap-4 p-6 bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow"
      onClick={onClick}
    >
      <img src={avatarUrl} alt={name} className="w-16 h-16 rounded-full" />
      <div>
        <h3 className="text-lg font-semibold text-gray-900">{name}</h3>
        <p className="text-sm text-gray-600">{title}</p>
      </div>
    </div>
  );
}
```

```typescript
// tests/ProfileCard.visual.spec.ts
import { test, expect } from '@playwright/test';

test('ProfileCard matches design specification', async ({ page }) => {
  await page.goto('/component-preview/ProfileCard');
  await page.waitForSelector('[data-testid="profile-card"]');

  const screenshot = await page.screenshot();
  const similarity = await compareToDesign(screenshot, 'ProfileCard');

  expect(similarity).toBeGreaterThan(0.95);
});
```

### Next.js Example

**Create Task:**
```bash
/task-create "Hero Section" design:https://figma.com/design/def456/...?node-id=8-15
```

**Generated Files:**
```typescript
// src/components/HeroSection.tsx
import Image from 'next/image';
import Link from 'next/link';

interface HeroSectionProps {
  title: string;
  subtitle: string;
  ctaText: string;
  ctaHref: string;
  backgroundImage: string;
}

export function HeroSection({
  title,
  subtitle,
  ctaText,
  ctaHref,
  backgroundImage,
}: HeroSectionProps) {
  return (
    <section className="relative h-screen flex items-center justify-center">
      <Image
        src={backgroundImage}
        alt="Hero background"
        fill
        className="object-cover"
        priority
      />
      <div className="relative z-10 text-center text-white">
        <h1 className="text-6xl font-bold mb-4">{title}</h1>
        <p className="text-xl mb-8">{subtitle}</p>
        <Link
          href={ctaHref}
          className="inline-block px-8 py-4 bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
        >
          {ctaText}
        </Link>
      </div>
    </section>
  );
}
```

### MAUI Example

**Create Task:**
```bash
/task-create "Settings Screen" design:https://app.zeplin.io/project/proj789/screen/screen101
```

**Generated Files:**
```xml
<!-- Views/SettingsScreen.xaml -->
<?xml version="1.0" encoding="utf-8" ?>
<ContentPage xmlns="http://schemas.microsoft.com/dotnet/2021/maui"
             xmlns:x="http://schemas.microsoft.com/winfx/2009/xaml"
             x:Class="MyApp.Views.SettingsScreen"
             Title="Settings">
    <ScrollView>
        <VerticalStackLayout Padding="20" Spacing="16">
            <Label Text="Account Settings"
                   FontSize="24"
                   FontAttributes="Bold"
                   TextColor="#1A1A1A" />

            <Frame BorderColor="#E0E0E0"
                   CornerRadius="8"
                   Padding="16"
                   HasShadow="False">
                <VerticalStackLayout Spacing="12">
                    <Label Text="Email Notifications"
                           FontSize="16"
                           TextColor="#333333" />
                    <Switch IsToggled="{Binding EmailNotificationsEnabled}" />
                </VerticalStackLayout>
            </Frame>

            <!-- More settings... -->
        </VerticalStackLayout>
    </ScrollView>
</ContentPage>
```

### Other Stacks

For stacks not yet supported (Flutter, SwiftUI, etc.):

1. **Create UI Specialist via /template-create**:
   ```bash
   /template-create
   # Follow prompts to create Flutter/SwiftUI template with UI specialist
   ```

2. **Use Same Workflow**:
   ```bash
   /task-create "Component name" design:<design-url>
   /task-work TASK-XXX
   ```

The orchestrator will automatically detect your stack and delegate to the appropriate UI specialist.

## Refinement and Iteration

After initial generation, you can refine the component:

```bash
/task-refine TASK-XXX "Update button hover color to blue-700"
```

**Design-Aware Refinement:**
- System detects task has design context
- Enforces constraint boundaries
- Warns if refinement violates constraints
- Re-validates after changes

**Constraint Violations:**
```bash
/task-refine TASK-XXX "Add API call to fetch user data"

❌ Error: Refinement violates design constraints
  ✗ API integration detected (prohibited)

Suggested Actions:
  1. Create new task for API integration
  2. Update design in Figma/Zeplin first
```

## Troubleshooting

### MCP Server Not Available

**Error:**
```
✗ Required MCP server 'figma-dev-mode' is not available.
```

**Solution:**
1. Install MCP server: `npm install -g @figma/mcp-server`
2. Configure in claude_desktop_config.json
3. Restart Claude Desktop
4. Re-run task

See: [Figma MCP Setup Guide](../mcp-setup/figma-mcp-setup.md)

### Invalid Design URL

**Error:**
```
✗ Invalid Design URL: Could not parse Figma URL
```

**Solution:**
1. Check URL format matches expected pattern
2. Ensure node-id parameter is present (Figma)
3. Copy URL directly from Figma/Zeplin (don't manually construct)

**Valid Formats:**
- Figma: `https://figma.com/design/{file_key}/...?node-id={node_id}`
- Zeplin: `https://app.zeplin.io/project/{project_id}/screen/{screen_id}`

### Visual Fidelity <95%

**Error:**
```
✗ Visual fidelity below threshold: 89.3% (requires >95%)
```

**Solution:**
1. Check design complexity (very complex designs may need manual adjustment)
2. Verify design reference image loaded correctly
3. Review generated styling for accuracy
4. May need to refine component manually

### UI Specialist Not Found

**Error:**
```
✗ UI specialist 'flutter-ui-specialist' not found for stack 'flutter'.
```

**Solution:**
1. Create UI specialist via `/template-create`
2. Or use existing template that includes UI specialist
3. Ensure template is initialized: `guardkit init flutter-template`

## Best Practices

1. **Start with Simple Components**
   - Begin with buttons, cards, form fields
   - Build confidence before tackling complex screens

2. **Use Node Selection (Figma)**
   - Select specific component/frame in Figma
   - Include node-id in URL for precise extraction
   - Avoids extracting entire page

3. **Check Visual Reference**
   - Review extracted visual reference before proceeding
   - Ensure it matches expected component
   - Cancel and adjust if needed

4. **Respect Constraint Boundaries**
   - Don't add logic beyond what's visible
   - Create separate tasks for business logic
   - Use design-to-code only for UI components

5. **Iterate in Design Tool First**
   - Update designs in Figma/Zeplin
   - Re-run task to regenerate component
   - Don't manually add features not in design

6. **Use Refinement Sparingly**
   - For minor tweaks only (colors, spacing)
   - Major changes should go through design tool
   - Avoid violating constraint boundaries

## FAQ

**Q: Can I use this for entire pages/screens?**
A: Yes, but start with individual components first. Large screens may have lower visual fidelity scores and require more manual refinement.

**Q: What if I need business logic?**
A: Create a separate task for business logic. The design-to-code workflow generates UI only. Implement logic in parent components or services.

**Q: Can I customize generated code?**
A: Yes, but use /task-refine to stay within constraint boundaries. For major changes, update the design first.

**Q: Does this work with design systems?**
A: Yes! Extract design system components and generate them as reusable components in your codebase.

**Q: What if my stack isn't supported?**
A: Create a UI specialist via /template-create. Follow the pattern from existing specialists (react-ui-specialist, nextjs-ui-specialist).

**Q: How accurate is the visual fidelity?**
A: Typically >95% for well-structured designs. Complex designs or custom fonts may require manual adjustment.

**Q: Can I skip MCP setup?**
A: No, MCP servers are required for design extraction. They provide the bridge between Figma/Zeplin and GuardKit.

## Migration from Old Commands

**Old Commands (Deprecated):**
- `/figma-to-react`
- `/zeplin-to-maui`

**New Workflow:**
```bash
# Old way
/figma-to-react abc123 2-2

# New way
/task-create "Component name" design:https://figma.com/design/abc123/...?node-id=2-2
/task-work TASK-XXX
```

**Benefits:**
- ✓ Technology-agnostic
- ✓ Integrated with task workflow
- ✓ Better planning and review
- ✓ Automatic testing
- ✓ Full traceability

See: [Deprecation Notice](../../installer/core/commands/figma-to-react.md)

---

## Need Help?

- **Issues**: Report at https://github.com/anthropics/guardkit/issues
- **Discussions**: https://github.com/anthropics/guardkit/discussions
- **Documentation**: https://github.com/anthropics/guardkit/docs
```

### Key Sections to Include

1. **Overview**: What the feature does, key benefits
2. **Setup**: Step-by-step MCP installation and configuration
3. **Quick Start**: Minimal example to get started
4. **How It Works**: Architecture explanation, Saga pattern
5. **Usage by Design Source**: Figma and Zeplin specific instructions
6. **Stack-Specific Examples**: Real code examples for each stack
7. **Refinement**: How to iterate on generated code
8. **Troubleshooting**: Common errors and solutions
9. **Best Practices**: Tips for success
10. **FAQ**: Common questions
11. **Migration**: How to migrate from old commands

### Testing Strategy

**Documentation Review**:
- Technical accuracy
- Completeness
- Clarity and readability
- Examples correctness

**User Testing**:
- Have users follow guide step-by-step
- Collect feedback on clarity
- Identify gaps or confusion points

**Link Validation**:
- Verify all internal links work
- Verify external links are valid

## Test Requirements

- [ ] Technical review: Architecture explanation accurate
- [ ] Technical review: Code examples correct
- [ ] Technical review: All links valid
- [ ] User testing: Setup instructions clear
- [ ] User testing: Quick start works
- [ ] User testing: Examples can be followed
- [ ] Documentation standards: Formatting consistent
- [ ] Documentation standards: Grammar and spelling correct

## Dependencies

**Blockers** (must be completed first):
- All previous UX tasks (UX-001 through UX-010) for accurate documentation

**Related**:
- TASK-UX-012: Update CLAUDE.md (will reference this guide)

## Next Steps

After completing this task:
1. TASK-UX-012: Update CLAUDE.md to reference this guide
2. TASK-UX-013: Create pattern documentation for developers
3. Gather user feedback and iterate

## References

- [Design URL Integration Proposal](../../docs/proposals/design-url-integration-proposal.md)
- [Implementation Guide](../../docs/proposals/design-url-integration-implementation-guide.md)
- [Figma MCP Setup](../mcp-setup/figma-mcp-setup.md)
- [Zeplin MCP Setup](../mcp-setup/zeplin-mcp-setup.md)
- [UX Design Integration Workflow](../workflows/ux-design-integration-workflow.md)

## Implementation Estimate

**Duration**: 6-8 hours

**Complexity**: 5/10 (Medium)
- Comprehensive documentation
- Multiple examples for each stack
- Troubleshooting scenarios
- Clear explanations of complex concepts
- User-friendly language

## Test Execution Log

_Automatically populated by /task-work_
