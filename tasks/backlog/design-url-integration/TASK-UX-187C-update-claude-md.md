---
id: TASK-UX-187C
title: Update CLAUDE.md documentation
status: backlog
created: 2025-11-11T11:45:00Z
updated: 2025-11-11T11:45:00Z
priority: high
tags: [ux-integration, documentation, claude-md]
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Update CLAUDE.md documentation

## Description

Update the main project documentation (`CLAUDE.md`) to reflect the new unified design-to-code workflow, deprecate old commands, and provide clear guidance on using the design URL integration feature.

This is part of Phase 6 of the Design URL Integration project (see [design-url-integration-implementation-guide.md](../../docs/proposals/design-url-integration-implementation-guide.md)).

## Acceptance Criteria

- [ ] Old commands marked as deprecated in CLAUDE.md
- [ ] New workflow documented with examples
- [ ] UX Design Integration section updated
- [ ] Command list updated (Essential Commands section)
- [ ] MCP Integration section updated
- [ ] Link to design-to-code user guide added
- [ ] Examples provided for common use cases
- [ ] Quick reference updated
- [ ] All technical details accurate

## Implementation Notes

### File to Update
- **File**: `CLAUDE.md` (project root)

### Key Sections to Update

**1. Essential Commands Section**

Update to show new workflow:

```markdown
### Core Workflow
```bash
/task-create "Title" [priority:high|medium|low] [design:URL]
/task-work TASK-XXX [--mode=standard|tdd]
/task-complete TASK-XXX
/task-status [TASK-XXX]
/task-refine TASK-XXX
```

### Design-to-Code Workflow
```bash
# Create task from design URL
/task-create "Component name" design:<figma-or-zeplin-url>

# Work on task (orchestrator handles extraction)
/task-work TASK-XXX

# Refine if needed (stays within design boundaries)
/task-refine TASK-XXX "Minor adjustment"
```

### Deprecated Commands
```bash
# [DEPRECATED] Use task-create with design: parameter instead
# /figma-to-react <file-key> [node-id]
# /zeplin-to-maui <project-id> <screen-id>
```
```

**2. UX Design Integration Section**

Replace existing section with updated workflow:

```markdown
## UX Design Integration

GuardKit provides a unified design-to-code workflow that converts Figma and Zeplin designs into production-ready components with **zero scope creep**.

### Unified Workflow

```bash
# Step 1: Create task with design URL
/task-create "Login Button" design:https://figma.com/design/abc123/...?node-id=2-2

# Step 2: Work on task
/task-work TASK-XXX
```

**That's it!** The system automatically:
1. Detects design source (Figma or Zeplin)
2. Routes to appropriate orchestrator (figma-orchestrator or zeplin-orchestrator)
3. Extracts design via MCP
4. Delegates to stack-specific UI specialist (react-ui-specialist, nextjs-ui-specialist, etc.)
5. Generates component matching design exactly
6. Runs visual regression tests (>95% fidelity)
7. Validates constraints (zero scope creep)

### Supported Design Sources

- **Figma**: via figma-dev-mode MCP
- **Zeplin**: via zeplin MCP

### Supported Stacks

- **React**: react-ui-specialist (in react-typescript template)
- **Next.js**: nextjs-ui-specialist (in nextjs-fullstack template)
- **MAUI**: maui-ui-specialist (create via /template-create)
- **Flutter**: flutter-ui-specialist (create via /template-create)
- **SwiftUI**: swiftui-ui-specialist (create via /template-create)

### Quality Gates

- **Visual Fidelity**: >95% similarity to design
- **Constraint Violations**: 0 (zero tolerance)
- **Compilation**: 100% success
- **Tests**: Pass all visual regression tests

### Constraint Boundaries

**Generated:**
- ✓ Component structure (HTML/XAML/JSX)
- ✓ Styling (Tailwind/XAML/CSS)
- ✓ Props/properties for visible elements
- ✓ Basic UI state (hover, focus)
- ✓ Visual tests

**NOT Generated:**
- ✗ Business logic
- ✗ API integration
- ✗ Database operations
- ✗ Authentication
- ✗ Global state management
- ✗ Routing
- ✗ Complex error handling
- ✗ Loading states

### Architecture

**Two-Tier System:**

**Tier 1: Orchestrators** (technology-agnostic, global)
- `figma-orchestrator`: Handles Figma designs
- `zeplin-orchestrator`: Handles Zeplin designs
- Execute 6-phase Saga pattern
- Enforce constraint validation

**Tier 2: UI Specialists** (stack-specific, template-based)
- `react-ui-specialist`: React components
- `nextjs-ui-specialist`: Next.js components
- `maui-ui-specialist`: .NET MAUI components (create via /template-create)
- `flutter-ui-specialist`: Flutter components (create via /template-create)
- Generate components in appropriate format
- Run visual regression tests

### Deprecated Commands

**⚠️ These commands are deprecated:**
- `/figma-to-react` - Use `/task-create` with `design:` parameter instead
- `/zeplin-to-maui` - Use `/task-create` with `design:` parameter instead

Commands will be removed in future version (2026-06-01).

**Migration:**
```bash
# Old way
/figma-to-react abc123 2-2

# New way
/task-create "Component name" design:https://figma.com/design/abc123/...?node-id=2-2
/task-work TASK-XXX
```

**See**: [Design-to-Code User Guide](docs/guides/design-to-code-user-guide.md) for comprehensive documentation.
```

**3. MCP Integration Best Practices Section**

Update to clarify when Design MCPs are used:

```markdown
## MCP Integration Best Practices

The system integrates with 4 MCP servers for enhanced capabilities. **All MCPs are optional** - the system works fine without them and falls back gracefully to training data.

### MCP Types

**Core MCPs** (used automatically during `/task-work`):
- **context7**: Library documentation (Phases 2, 3, 4 - automatic when task uses libraries)
- **design-patterns**: Pattern recommendations (Phase 2.5A - automatic during architectural review)

**Design MCPs** (ONLY used with design: parameter):
- **figma-dev-mode**: Figma design extraction (ONLY when task has design:figma-url)
- **zeplin**: Zeplin design extraction (ONLY when task has design:zeplin-url)

**Important**: Design MCPs are only used when you create a task with `design:` parameter. They are NOT used during regular `/task-work` execution without design URLs.

### Setup Guides

**Core MCPs** (recommended for all users):
- [Context7 MCP Setup](docs/guides/context7-mcp-setup.md) - Up-to-date library documentation
- [Design Patterns MCP Setup](docs/guides/design-patterns-mcp-setup.md) - Pattern recommendations

**Design MCPs** (only if using design-to-code workflow):
- [Figma MCP Setup](docs/mcp-setup/figma-mcp-setup.md) - For tasks with design:figma-url
- [Zeplin MCP Setup](docs/mcp-setup/zeplin-mcp-setup.md) - For tasks with design:zeplin-url

### When MCPs Are Used

```bash
# Core MCPs used automatically
/task-work TASK-XXX  # Uses context7 + design-patterns as needed

# Design MCPs used only with design: parameter
/task-create "Button" design:https://figma.com/...  # Requires figma-dev-mode MCP
/task-work TASK-XXX  # Uses figma-dev-mode to extract design
```
```

**4. Quick Reference Section**

Update to include design-to-code workflow:

```markdown
## Quick Reference

**Command Specifications:** `installer/global/commands/*.md`
**Agent Definitions:** `installer/global/agents/*.md`
**Workflow Guides:** `docs/guides/*.md` and `docs/workflows/*.md`
**Stack Templates:** `installer/global/templates/*/`
**Design-to-Code Guide:** `docs/guides/design-to-code-user-guide.md`
```

**5. Task Frontmatter Example**

Update to show design_url field:

```markdown
### Task Frontmatter

```yaml
---
id: TASK-001
title: Add user authentication
status: backlog
created: 2025-11-11T10:00:00Z
updated: 2025-11-11T10:00:00Z
priority: high
tags: [feature, backend]
complexity: 0
design_url: https://figma.com/design/abc123/...?node-id=2-2  # Optional
design_source: figma  # Auto-detected: figma | zeplin
design_metadata:  # Auto-populated
  file_key: abc123
  node_id: "2:2"
  extracted_at: 2025-11-11T10:05:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---
```
```

**6. Add Design-to-Code Examples**

Add new section with practical examples:

```markdown
## Design-to-Code Examples

### Figma to React

```bash
# Get Figma URL (with node-id)
# https://figma.com/design/abc123/MyDesign?node-id=2-2

# Create task
/task-create "Login Button" design:https://figma.com/design/abc123/MyDesign?node-id=2-2

# Work on task
/task-work TASK-XXX

# Output:
# - src/components/LoginButton.tsx
# - tests/LoginButton.visual.spec.ts
# - Visual fidelity: 97.3%
# - Constraint violations: 0
```

### Zeplin to Next.js

```bash
# Get Zeplin URL
# https://app.zeplin.io/project/proj123/screen/screen456

# Create task
/task-create "Hero Section" design:https://app.zeplin.io/project/proj123/screen/screen456

# Work on task
/task-work TASK-XXX

# Output:
# - src/components/HeroSection.tsx
# - tests/HeroSection.visual.spec.ts
# - Visual fidelity: 96.8%
# - Constraint violations: 0
```

### Zeplin to MAUI

```bash
# Get Zeplin URL
# https://app.zeplin.io/project/proj789/screen/screen101

# Create task
/task-create "Settings Screen" design:https://app.zeplin.io/project/proj789/screen/screen101

# Work on task
/task-work TASK-XXX

# Output:
# - Views/SettingsScreen.xaml
# - Views/SettingsScreen.xaml.cs
# - ViewModels/SettingsScreenViewModel.cs
# - Tests/SettingsScreenTests.cs
# - Platform correctness: 96.5%
# - Constraint violations: 0
```

**For full documentation**: [Design-to-Code User Guide](docs/guides/design-to-code-user-guide.md)
```

### Changes Summary

**Sections to Update:**
1. Essential Commands - Add design: parameter, mark old commands as deprecated
2. UX Design Integration - Replace with new unified workflow
3. MCP Integration Best Practices - Clarify when Design MCPs are used
4. Quick Reference - Add link to design-to-code guide
5. Task Frontmatter Example - Show design_url field
6. Add new section: Design-to-Code Examples

**Key Messages:**
- Unified workflow via task-create with design: parameter
- Technology-agnostic orchestrators
- Stack-specific UI specialists
- Zero scope creep enforcement
- Old commands deprecated (but still work)
- Design MCPs only used with design: parameter

### Testing Strategy

**Documentation Review**:
- Technical accuracy
- Consistency with implementation
- Clarity and readability
- All links valid

**User Testing**:
- Can users understand new workflow from CLAUDE.md?
- Are deprecation notices clear?
- Are examples helpful?

## Test Requirements

- [ ] Technical review: All technical details accurate
- [ ] Technical review: Consistent with implementation
- [ ] Technical review: Links valid (internal and external)
- [ ] User testing: New workflow clear
- [ ] User testing: Deprecation notices understood
- [ ] User testing: Examples can be followed
- [ ] Documentation standards: Formatting consistent
- [ ] Documentation standards: Grammar and spelling correct

## Dependencies

**Blockers** (must be completed first):
- TASK-UX-602E: Create design-to-code user guide (referenced in CLAUDE.md)
- All implementation tasks (UX-001 through UX-010) for accurate documentation

## Next Steps

After completing this task:
1. TASK-UX-013: Create pattern documentation for developers
2. Gather user feedback and iterate
3. Monitor adoption of new workflow

## References

- [Design URL Integration Proposal](../../docs/proposals/design-url-integration-proposal.md)
- [Implementation Guide](../../docs/proposals/design-url-integration-implementation-guide.md)
- [Design-to-Code User Guide](../../docs/guides/design-to-code-user-guide.md)
- [Existing CLAUDE.md](../../CLAUDE.md)

## Implementation Estimate

**Duration**: 3-4 hours

**Complexity**: 4/10 (Medium-Low)
- Update existing documentation
- Add new sections with examples
- Mark deprecated commands
- Ensure technical accuracy
- Maintain consistent style

## Test Execution Log

_Automatically populated by /task-work_
