# Implementation Plan - TASK-024

## Task Overview
**Title:** Audit core user guides - Remove RequireKit features
**Task ID:** TASK-024
**Technology Stack:** Default (Documentation)
**Complexity Score:** 6/10 (Medium)
**Estimated Duration:** 6.3 hours (380 minutes)

## Architecture & Strategy

### Three-Tier Documentation Structure
1. **GETTING-STARTED.md** - Focus on basic 5-minute quickstart
2. **QUICK_REFERENCE.md** - Essential commands and syntax only
3. **guardkit-workflow.md** - Core workflow states and phases

This separation ensures:
- New users get simple, clear onboarding
- Reference material is uncluttered
- Workflow documentation is accurate

## Files to Modify

### 1. docs/guides/GETTING-STARTED.md
**Purpose:** Focus on 5-minute quickstart with GuardKit-only features
**Estimated Lines:** 650

**Changes Required:**
- Remove RequireKit-specific workflow references
- Remove EARS notation examples
- Remove BDD scenario generation examples
- Show simple task creation → work → complete flow
- Add RequireKit callout at end of "Next Steps" section

**Implementation Notes:**
- Keep command examples very simple
- Use `/task-create "Title"` basic syntax only
- Focus on 3 commands: task-create, task-work, task-complete

---

### 2. docs/guides/QUICK_REFERENCE.md
**Purpose:** Remove RequireKit command parameters, keep GuardKit-only syntax
**Estimated Lines:** 700

**Changes Required:**
- Remove `epic:`, `feature:`, `requirements:`, `bdd:` parameters from syntax tables
- Keep simple parameter examples only: `priority:`, `tags:`
- Create "Extended Features" section pointing to RequireKit
- Update all command examples to use GuardKit-only syntax
- Remove PM tool synchronization references

**Implementation Notes:**
- Update command syntax table to remove RequireKit columns
- Create callout box: "Need advanced features? See RequireKit integration"
- Verify all parameter examples are valid GuardKit syntax

---

### 3. docs/guides/guardkit-workflow.md
**Purpose:** Update workflow diagrams and remove Requirements Analysis phase
**Estimated Lines:** 650

**Changes Required:**
- Update workflow diagrams to show GuardKit-only states
- Remove References Analysis phase (Phase 1) documentation
- Keep quality gates and test enforcement sections intact
- Fix GitHub repository URLs to correct repositories
- Ensure workflow diagrams accurately reflect GuardKit flow

**Implementation Notes:**
- Workflow states: BACKLOG → IN_PROGRESS → IN_REVIEW → COMPLETED
- Add design-first workflow (--design-only / --implement-only)
- Add micro-task workflow (--micro flag)
- Verify all state transitions are accurate

---

## Key Changes Summary

### Content to Remove
- BDD mode workflow references
- EARS notation examples and explanations
- Epic/feature hierarchy examples and workflows
- PM tool synchronization instructions
- Requirements traceability examples
- References Analysis phase (Phase 1)

### Content to Keep/Add
- Simple task creation syntax: `/task-create "Title" priority:high`
- Core commands: `/task-work`, `/task-complete`, `/task-status`, `/task-refine`
- Quality gates workflow
- Complexity evaluation process
- Design-first workflow (--design-only, --implement-only)
- Micro-task workflow (--micro flag)
- Template-based initialization
- Integration callouts with RequireKit links

### RequireKit Integration Callouts
Add in these sections:
- After basic task creation examples
- In "Advanced Workflows" sections
- When discussing requirements or specifications
- In workflow decision trees

**Callout Format:**
```markdown
> **Need Formal Requirements?**
> RequireKit adds EARS notation, BDD scenarios, and epic/feature hierarchy.
> See: https://github.com/requirekit/require-kit
```

---

## Implementation Phases

### Phase 1: Audit GETTING-STARTED.md (90 minutes)
1. Find all RequireKit references using grep
2. Identify BDD, EARS, epic/feature mentions
3. Create focused 5-minute quickstart section
4. Add RequireKit callout in "Next Steps"
5. Review for clarity and completeness

### Phase 2: Audit QUICK_REFERENCE.md (80 minutes)
1. Extract current command syntax tables
2. Remove epic, feature, requirements, bdd parameters
3. Create "Extended Features" section with RequireKit link
4. Update all command examples
5. Review parameter list against GuardKit spec

### Phase 3: Audit guardkit-workflow.md (110 minutes)
1. Update workflow diagrams (Markdown/Mermaid format)
2. Remove Requirements Analysis phase references
3. Add design-first workflow documentation
4. Add micro-task workflow documentation
5. Fix GitHub repository URLs
6. Verify all state transitions match current implementation

### Phase 4: Validation & Testing (100 minutes)
1. Follow each guide step-by-step without RequireKit installed
2. Verify all command examples execute successfully
3. Check all links (internal and external)
4. Validate code block syntax highlighting
5. Ensure workflow diagrams render correctly

---

## Risks & Mitigations

### Risk 1: Content Accuracy (MEDIUM)
**Description:** Extensive RequireKit contamination across guides; risk of removing too much content or breaking references

**Mitigation:**
- Follow acceptance criteria exactly
- Use grep to find all RequireKit mentions before editing
- Keep backup of original files in git
- Review each change against acceptance criteria

---

### Risk 2: Broken References (MEDIUM)
**Description:** Cross-references between guides may break if not updated consistently

**Mitigation:**
- Test each guide step-by-step after modifications
- Verify all internal links (links between guides)
- Use automated link checker if available
- Review cross-file references

---

### Risk 3: GitHub URL Changes (LOW)
**Description:** Need to verify correct repository URLs for external links

**Mitigation:**
- Confirm correct GitHub repository URLs before finalizing
- Test that all repository links are valid
- Verify repository names match current configuration

---

## Quality Gates

| Gate | Type | Validation |
|------|------|-----------|
| Content Accuracy | Required | Manual review against acceptance criteria |
| Functional Verification | Required | Walk through each guide step-by-step |
| Link Verification | Required | Check all internal and external links |
| Syntax Validation | Required | Verify code block syntax highlighting |

---

## Test Strategy

**Manual Documentation Validation:**
1. Clone fresh repository (without local modifications)
2. Follow each guide exactly as written
3. Verify all command examples work
4. Validate all links are correct
5. Check that workflow diagrams are accurate

**Acceptance Criteria Checklist:**
- [ ] Remove BDD mode workflow references (RequireKit feature)
- [ ] Remove EARS notation examples and explanations (RequireKit feature)
- [ ] Remove epic/feature hierarchy examples (RequireKit feature)
- [ ] Remove PM tool synchronization instructions (RequireKit feature)
- [ ] Remove requirements traceability examples (RequireKit feature)
- [ ] Update command examples to use GuardKit-only syntax
- [ ] Fix GitHub URLs to correct repositories
- [ ] Add "Need requirements management?" callout boxes with RequireKit links
- [ ] Ensure workflow diagrams show GuardKit-only flow
- [ ] Verify all command examples work without RequireKit installed

---

## Dependencies

**External Packages:** None (documentation task)
**Internal Dependencies:** None
**Tools Required:** Markdown editor, grep, link checker (optional)

---

## Summary

This task removes RequireKit feature references from three critical user-facing guides while adding integration callouts that direct users to RequireKit when they need advanced requirements management.

The three-tier documentation structure ensures:
- **GETTING-STARTED.md** remains a simple 5-minute onboarding guide
- **QUICK_REFERENCE.md** provides quick lookup without cognitive overload
- **guardkit-workflow.md** documents accurate GuardKit workflow states

Total effort: ~6.3 hours of careful documentation audit and validation.
