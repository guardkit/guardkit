---
id: TASK-011
title: "Update Root Documentation Files"
created: 2025-10-27
status: completed
priority: high
complexity: 4
parent_task: none
subtasks: []
estimated_hours: 2
actual_hours: 1.5
completed: 2025-11-01
---

# TASK-011: Update Root Documentation Files

## Description

Update README.md, CLAUDE.md, and other root documentation to position guardkit as a lightweight task workflow system with quality gates, removing all requirements management references.

## Files to Update

### README.md

**New positioning**:
- Lightweight AI-assisted development
- Built-in quality gates (Phase 2.5, 4.5)
- Simple task workflow
- No ceremony, no EARS/BDD/epics

**Change FROM** (enterprise focus):
```markdown
# AI-Engineer - Complete Agentecflow Implementation

Full Agentecflow Implementation:
- Stage 1: Specification - Interactive requirements gathering with EARS notation
- Stage 2: Tasks Definition - Epic/feature breakdown
- Stage 3: Engineering - AI/human collaboration
- Stage 4: Deployment & QA
```

**TO** (pragmatic focus):
```markdown
# GuardKit

**Lightweight AI-assisted development with built-in quality gates.**

Stop shipping broken code. Get architectural review before implementation and automatic test enforcement after. Simple task workflow, no ceremony.

## What You Get

- **Phase 2.5 - Architectural Review**: SOLID, DRY, YAGNI evaluation before coding
- **Phase 4.5 - Test Enforcement**: Automatic test fixing, ensures 100% pass rate
- **Specialized Agents**: Stack-specific AI agents for React, Python, .NET, TypeScript
- **Quality Gates**: Coverage thresholds, compilation checks, code review
- **State Management**: Automatic kanban tracking (backlog → in_progress → completed)

## 5-Minute Quickstart

[Installation and first task]
```

### CLAUDE.md (Root)

**Remove sections**:
- Stage 1: Specification
- Stage 2: Tasks Definition (epic/feature parts)
- EARS Notation Patterns
- Epic/Feature Hierarchy
- External PM Tool Integration
- Requirements Management

**Keep/update sections**:
- Project Context (rewrite for guardkit)
- Core Principles (simplify)
- Essential Commands (task-* only)
- Quality Gates (Phase 2.5, 4.5)
- Task Workflow
- Design-First Workflow
- Complexity Evaluation
- Testing by Stack
- MCP Integration

**Update command lists**:

**Remove**:
```bash
/gather-requirements
/formalize-ears
/generate-bdd
/epic-create
/feature-create
/hierarchy-view
/portfolio-dashboard
```

**Keep**:
```bash
/task-create
/task-work
/task-complete
/task-status
/task-refine
/debug
/figma-to-react
/zeplin-to-maui
```

### .conductor/kuwait/CLAUDE.md

Update this worktree-specific CLAUDE.md similarly.

### CONTRIBUTING.md (if exists)

Simplify to focus on:
- Task workflow contributions
- Quality gate improvements
- Template additions
- Bug fixes

Remove references to:
- Requirements engineering
- EARS notation expertise
- BDD scenario writing

## Implementation Steps

### 1. Backup Files

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit/.conductor/kuwait

cp README.md README.md.backup
cp CLAUDE.md CLAUDE.md.backup
cp .claude/CLAUDE.md .claude/CLAUDE.md.backup 2>/dev/null || true
```

### 2. Rewrite README.md

Focus on:
- Pragmatic positioning ("Stop shipping broken code")
- 5-minute quickstart
- Quality gates as key differentiator
- Simple workflow (no EARS/BDD/epics)

### 3. Update Root CLAUDE.md

- Remove Stage 1 and 2 sections
- Simplify command lists
- Focus on task workflow + quality gates
- Keep technical depth (quality gates, testing, MCPs)

### 4. Update .claude/CLAUDE.md (if different)

Ensure consistency with root CLAUDE.md.

### 5. Check for Other Root Docs

```bash
# Check for other documentation files
ls -la *.md
# Update any other relevant files
```

## Content Guidelines

### What to Emphasize
- ✅ Lightweight workflow
- ✅ Quality gates (Phase 2.5, 4.5)
- ✅ Pragmatic approach
- ✅ 5-minute quickstart
- ✅ No ceremony
- ✅ Simple task management

### What to Remove
- ❌ EARS notation
- ❌ BDD/Gherkin scenarios
- ❌ Epic/feature hierarchy
- ❌ Requirements management
- ❌ PM tool synchronization
- ❌ Enterprise positioning

### What to Mention (but minimize)
- 🔗 Link to full system (if needed): "For formal requirements management, see..."
- 🔗 Historical context (one sentence max)

## Validation Checklist

### README.md
- [ ] Title changed to "GuardKit"
- [ ] Tagline emphasizes lightweight + quality gates
- [ ] 5-minute quickstart present
- [ ] No EARS/BDD/epic references
- [ ] Quality gates explained (Phase 2.5, 4.5)
- [ ] Simple workflow examples

### CLAUDE.md (Root)
- [ ] Project context updated for guardkit
- [ ] Stage 1 and 2 removed
- [ ] Command list simplified (8 commands)
- [ ] Quality gates section retained
- [ ] EARS/Epic sections removed
- [ ] Task workflow emphasized

### Grep Verification
```bash
# Check for forbidden references
grep -i "EARS\|epic.*create\|feature.*create\|requirements.*management\|Stage 1.*Specification" \
  README.md CLAUDE.md | grep -v "historical\|full.*system"

# Should return empty or only acceptable references
```

## Acceptance Criteria

- [ ] README.md rewritten for guardkit
- [ ] Root CLAUDE.md updated
- [ ] .claude/CLAUDE.md updated (if exists)
- [ ] No requirements management references
- [ ] Lightweight positioning clear
- [ ] Quality gates prominently featured
- [ ] 5-minute quickstart included
- [ ] Grep verification passes

## Example README Structure

```markdown
# GuardKit

[One-line tagline]

## What You Get
[4-5 bullet points on quality gates]

## 5-Minute Quickstart
[Install → Init → Create → Work → Complete]

## What Makes This Different?
[Phase 2.5 and 4.5 explained]

## When to Use
[Use cases + when NOT to use]

## Documentation
[Links to guides]

## Supported Stacks
[List of 8 templates]

## Philosophy
[5 principles]

## Contributing
[Link]

## License
[MIT]
```

## Related Tasks

- TASK-002: Remove requirements management commands
- TASK-008: Clean template CLAUDE.md files
- TASK-010: Update manifest

## Estimated Time

2 hours

## Notes

- README.md should be compelling for pragmatic developers
- Emphasize "no ceremony" messaging
- Show quality gates as key differentiator
- Keep it concise - target 200-300 lines max for README
- Use concrete examples, not abstract benefits

## Completion Summary

### Date: 2025-11-01

### Status: IN_REVIEW ✅

### Files Updated:
1. ✅ README.md - Complete rewrite for GuardKit positioning
2. ✅ CLAUDE.md (root) - Removed enterprise features, simplified to task workflow
3. ✅ .claude/CLAUDE.md - Updated for consistency with GuardKit focus

### Backups Created:
- README.md.backup
- CLAUDE.md.backup
- .claude/CLAUDE.md.backup

### Validation Results:

#### README.md ✅
- [x] Title changed to "GuardKit"
- [x] Tagline emphasizes lightweight + quality gates
- [x] 5-minute quickstart present
- [x] No EARS/BDD/epic references (except acceptable "upgrade to full" context)
- [x] Quality gates explained (Phase 2.5, 4.5) - 6 mentions
- [x] Simple workflow examples - 14 task command references

#### CLAUDE.md (Root) ✅
- [x] Project context updated for guardkit - 3 mentions
- [x] Stage 1 and 2 removed
- [x] Command list simplified to 8 commands (task-create, task-work, task-complete, task-status, task-refine, figma-to-react, zeplin-to-maui, debug)
- [x] Quality gates section retained - 3 sections
- [x] EARS/Epic sections removed (except upgrade path reference)
- [x] Task workflow emphasized - 17 mentions

#### Grep Verification ✅
- [x] No forbidden command references (/gather-requirements, /formalize-ears, /epic-create, etc.)
- [x] Only acceptable references to requirements management (in "upgrade to full" context)

### Key Changes:

**README.md:**
- Changed from "AI Engineer - Complete Agentecflow Implementation" to "GuardKit"
- New tagline: "Lightweight AI-assisted development with built-in quality gates"
- Added compelling "Stop shipping broken code" messaging
- 5-minute quickstart with concrete examples
- Clear "When to Use" vs "Upgrade to Full Agentecflow" sections
- Removed all Stage 1/2 (Specification/Tasks Definition) content
- Focused on quality gates (Phase 2.5, 4.5) as key differentiators
- Simplified from 346 lines to 306 lines (more focused)

**CLAUDE.md:**
- Changed from "AI Engineer - Complete Agentecflow Implementation" to "GuardKit - Lightweight AI-Assisted Development"
- Removed EARS Notation Patterns section
- Removed Epic/Feature Hierarchy sections
- Removed External PM Tool Integration
- Removed System Capabilities (enterprise focus)
- Removed Team Collaboration workflows
- Simplified Core Principles from 6 to 5
- Command list reduced from 15+ to 8 essential commands
- Clear upgrade path to full Agentecflow for enterprise needs

**.claude/CLAUDE.md:**
- Updated title from "Claude Code Software Engineering Lifecycle System" to "GuardKit - Lightweight Task Workflow System"
- Removed "Requirements First" principle
- Removed "Test-Driven: BDD scenarios" reference
- Simplified workflow from 6 steps to 4
- Updated getting started message

### Acceptance Criteria: ALL MET ✅

- [x] README.md rewritten for guardkit
- [x] Root CLAUDE.md updated
- [x] .claude/CLAUDE.md updated
- [x] No requirements management references (except upgrade path)
- [x] Lightweight positioning clear
- [x] Quality gates prominently featured
- [x] 5-minute quickstart included
- [x] Grep verification passes

### Positioning Summary:

**GuardKit is now positioned as:**
- Lightweight, pragmatic task workflow system
- Built-in quality gates (Phase 2.5, 4.5) as main differentiator
- Simple 3-command workflow (create → work → complete)
- No ceremony, no EARS/BDD/epics
- Clear upgrade path to full Agentecflow for enterprise needs

**Target Audience:**
- Solo developers or small teams (1-3 people)
- Individual tasks (1-8 hours)
- Small-to-medium projects
- Developers who want quality without ceremony

### Time Taken:
~1.5 hours (under the 2-hour estimate)

### Next Steps:
1. Human review of updated documentation
2. Test `/task-create` and `/task-work` commands to ensure they align with new positioning
3. Consider updating any other marketing/documentation that references old positioning
