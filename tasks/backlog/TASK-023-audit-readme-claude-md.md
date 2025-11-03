---
id: TASK-023
title: Audit and fix README.md and CLAUDE.md - Remove RequireKit features
status: backlog
created: 2025-11-03T20:30:00Z
updated: 2025-11-03T20:30:00Z
priority: high
tags: [documentation, audit, requirekit-separation]
complexity: 5
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Audit and fix README.md and CLAUDE.md - Remove RequireKit features

## Description

Review and update the main entry point documentation files (README.md and CLAUDE.md) to ensure they only document Taskwright features. Remove references to RequireKit features while adding appropriate links to RequireKit where integration makes sense.

## Scope

**Files to audit:**
- README.md (~300 lines)
- CLAUDE.md (~400 lines)

**Total: ~700 lines**

## Acceptance Criteria

- [ ] Remove BDD mode references (this is a RequireKit feature)
- [ ] Remove EARS notation mentions (RequireKit feature)
- [ ] Remove epic/feature hierarchy references (RequireKit feature)
- [ ] Remove portfolio management mentions (RequireKit feature)
- [ ] Fix GitHub repository URLs to use correct orgs:
  - Taskwright: `https://github.com/taskwright-dev/taskwright`
  - RequireKit: `https://github.com/requirekit/require-kit`
- [ ] Add appropriate "Need requirements management?" sections with links to RequireKit
- [ ] Ensure all features described actually exist in Taskwright
- [ ] Verify command examples work with Taskwright-only features
- [ ] Update "When to Use" section to clarify Taskwright vs RequireKit use cases

## RequireKit Features to Remove/Link

**Remove these features** (they belong in RequireKit):
- EARS requirements notation
- BDD/Gherkin scenario generation
- Epic and feature hierarchy management
- Portfolio management
- PM tool synchronization (Jira, Linear, Azure DevOps, GitHub)
- Requirements traceability matrices

**Keep these features** (they are Taskwright):
- Task creation and workflow (backlog → in_progress → in_review → completed)
- Quality gates (Phase 2.5 architectural review, Phase 4.5 test enforcement)
- Complexity evaluation (Phase 2.7)
- Design-first workflow (--design-only, --implement-only)
- Stack-specific templates and agents
- MCP integration (Context7, design-patterns, Figma, Zeplin)
- Conductor.build integration

## Where to Add RequireKit Links

Add references to RequireKit in these contexts:
- When discussing requirements management
- When mentioning formal specifications (EARS, BDD)
- In "When NOT to Use Taskwright" section
- In "Need More?" or "Advanced Features" sections

## Implementation Notes

Use this pattern for RequireKit references:
```markdown
## Need Requirements Management?

For formal requirements (EARS notation, BDD scenarios, epic/feature hierarchy, PM tool sync), see [RequireKit](https://github.com/requirekit/require-kit) which integrates seamlessly with Taskwright.
```

## Test Requirements

- [ ] Verify all links work (no 404s)
- [ ] Ensure code examples can be run with Taskwright installation only
- [ ] Check that feature claims match actual implementation
- [ ] Validate command syntax against actual command specs
