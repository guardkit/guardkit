# ADR 0003: Remove guardkit-python Template

**Date**: 2025-11-26
**Status**: Accepted
**Task**: TASK-G6D4

---

## Context

The `guardkit-python` template was created in TASK-066 to demonstrate GuardKit's architecture (Python CLI with orchestrator pattern). However, its existence created confusion and served no valid use case.

### Original Intent

- Created as a template for GuardKit development
- Intended to demonstrate GuardKit's own architecture (Python CLI with orchestrator pattern)
- Positioned as an "internal development" reference template
- Added as the 6th template (bringing total to 6)

### Problems Identified

During architectural review (TASK-D3A1) and post-implementation analysis, the following issues were discovered:

1. **GuardKit's `.claude/` directory is git-managed, not template-initialized**
   - GuardKit's configuration is checked into version control
   - Template initialization is never needed for GuardKit development
   - Creating a template implies template init is part of the development workflow (incorrect)

2. **Running `guardkit init guardkit-python` on GuardKit repo caused issues**
   - Led to agent deletion problems (TASK-BAA5)
   - Created confusion about when template initialization is appropriate
   - Suggested to developers they should run `guardkit init` on the GuardKit repository itself (wrong)

3. **No valid user use case**
   - Users needing Python CLI templates should use `fastapi-python` template
   - Users can create custom templates via `/template-create` from their proven code
   - Template did not serve external users' needs

4. **Maintenance burden**
   - One more template to keep updated with system changes
   - Required ongoing validation and documentation maintenance
   - Did not provide sufficient value to justify maintenance cost

5. **Conceptual confusion**
   - Blurred the line between GuardKit development and user projects
   - Unclear whether template was for learning GuardKit internals or building similar tools
   - Created ambiguity about git-managed vs template-initialized configurations

### Architectural Review Findings

**TASK-D3A1** architectural review concluded:
- Current approach (guardkit-python template): **3.5/10**
- Removal approach: **8.75/10**
- **Verdict**: "The guardkit-python template serves no real purpose"

---

## Decision

**Remove the `guardkit-python` template entirely.**

### Implementation

1. Delete `installer/global/templates/guardkit-python/` directory
2. Update template count from 6 to 5 in all documentation
3. Add explanation for removal in key documentation files
4. Create this ADR to document the decision and rationale

---

## Consequences

### Positive

- ✅ **Eliminates confusion** about GuardKit development vs user projects
- ✅ **Reduces template maintenance burden** (5 templates instead of 6)
- ✅ **Clarifies git-managed configuration** for GuardKit development
- ✅ **Simplifies documentation and onboarding** (one less template to explain)
- ✅ **Prevents incorrect usage** (running template init on GuardKit repo)
- ✅ **Focuses quality efforts** on templates with real user value

### Negative

- None identified - template had no valid use case
- Users wanting to understand GuardKit architecture can read the actual source code (more accurate than template)

### Neutral

- Template count reduced from 6 to 5
- Documentation requires updates (one-time cost)

---

## Alternatives Considered

### A) Keep template but document limitations

**Description**: Keep `guardkit-python` but add prominent warnings about when not to use it.

**Rejected because**:
- Doesn't solve the fundamental confusion
- Still requires ongoing maintenance
- Documentation burden increases (explaining why/when not to use)
- Complexity increases rather than decreases

### B) Repurpose for generic Python CLI projects

**Description**: Generalize the template for any Python CLI tool, removing GuardKit-specific patterns.

**Rejected because**:
- `fastapi-python` template already serves Python projects well
- Generic Python CLI templates are straightforward (don't need reference template)
- Users can create custom templates via `/template-create` from proven code
- Would require significant rework effort for minimal value

### C) Keep as "learning resource" only

**Description**: Mark template as "educational only" and document it's not for production use.

**Rejected because**:
- Learning GuardKit's architecture is better done by reading actual source code
- Templates imply they should be used to initialize projects
- "Educational only" creates confusion (what can you do with it?)
- Maintenance burden remains without clear value

---

## Guidance for Users

### For GuardKit Development

```bash
# Clone the repository
git clone https://github.com/your-org/guardkit.git
cd guardkit

# Configuration is in git - no template init needed
# The .claude/ directory is already configured
```

**Do NOT run**: `guardkit init guardkit-python`

### For Python CLI Projects

```bash
# Option 1: Use fastapi-python template as starting point
guardkit init fastapi-python

# Option 2: Create custom template from your proven project
cd your-proven-cli-project
/template-create --validate
```

### For Understanding GuardKit's Architecture

- **Read the source code** in `src/` (most accurate)
- **Review architectural documentation** in `docs/`
- **Study the implementation guides** in `docs/guides/`
- **Look at completed tasks** in `tasks/completed/`

Templates are not the right medium for understanding complex architectures - they're for **initializing new projects**.

---

## References

- **TASK-D3A1**: Architectural review validating removal decision
  - Score: 3.5/10 (current) → 8.75/10 (removal)
  - Conclusion: Template serves no real purpose
- **TASK-BAA5**: Original issue from running template init on GuardKit repo
  - Highlighted agent deletion problems
  - Demonstrated confusion about when to use template init
- **TASK-066**: Original task that created guardkit-python template
  - Intent was good (demonstrate patterns)
  - Execution created unintended confusion
- **Architectural Review**: `docs/reviews/TASK-D3A1-architectural-review.md`

---

## Related Decisions

- **ADR 0001**: Adopt Agentic Flow (establishes git-managed configuration)
- **Template Philosophy**: Focus on learning templates + `/template-create` for production
- **Quality Standards**: All templates must meet 8+/10 quality threshold

---

## Success Metrics

**Metrics for success** (achieved with this ADR):

- ✅ **No confusion** about GuardKit development vs user projects
- ✅ **Clear documentation**: GuardKit's `.claude/` is git-managed
- ✅ **Users directed** to appropriate templates (`fastapi-python`) or custom template creation
- ✅ **Reduced maintenance**: 5 high-quality templates instead of 6
- ✅ **Prevents mistakes**: No risk of running `guardkit init` on GuardKit repo

---

## Implementation Checklist

- [x] Delete `installer/global/templates/guardkit-python/` directory
- [x] Update `CLAUDE.md` template count (6 → 5)
- [x] Update `CLAUDE.md` Template Philosophy section
- [x] Add explanation for removal in `CLAUDE.md`
- [x] Update `docs/templates/TEMPLATE-OVERVIEW.md`
- [x] Update FAQ sections explaining removal
- [x] Create ADR 0003 (this document)
- [ ] Verify no broken references remain
- [ ] Commit changes with clear message
- [ ] Update related tasks (TASK-D3A1, TASK-BAA5) to reference this ADR

---

## Approval

**Approved by**: Architectural Review (TASK-D3A1)
**Date**: 2025-11-26
**Reviewers**: Architectural review team

**Decision**: Accepted - proceed with removal.
