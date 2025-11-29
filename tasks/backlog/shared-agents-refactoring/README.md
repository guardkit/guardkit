# Shared Agents Refactoring - Lean Implementation

**Approach**: Minimal Viable Implementation
**Total Tasks**: 6 tasks
**Estimated Duration**: 1-2 days
**Philosophy**: Ship fast, fix issues if they arise

---

## Quick Start

Execute tasks in order:

```bash
# 1. Verify what we're migrating (MUST BE FIRST)
/task-work TASK-SHA-001

# 2. Create shared-agents repo with verified agents
/task-work TASK-SHA-002

# 3 & 4. Update both installers (can run in parallel)
/task-work TASK-SHA-003  # TaskWright
/task-work TASK-SHA-004  # RequireKit

# 5. Test everything works
/task-work TASK-SHA-005

# 6. Update docs and ship
/task-work TASK-SHA-006
```

**Total time**: ~9 hours (1-2 days)

---

## The 6 Tasks

### TASK-SHA-001: Verify Agent Duplication ⭐ CRITICAL
**Effort**: 1 hour
**Why**: Ensures we only migrate agents that exist in both repos

**Quick version**:
```bash
# Compare agent files
comm -12 <(ls taskwright/installer/global/agents/*.md | xargs basename -a | sort) \
         <(ls ../require-kit/.claude/agents/*.md | xargs basename -a | sort)
```

### TASK-SHA-002: Create Shared Agents Repository
**Effort**: 2 hours
**Depends on**: TASK-SHA-001

1. Create `taskwright-dev/shared-agents` repo
2. Copy verified agents
3. Create simple manifest.json
4. Release v1.0.0

### TASK-SHA-003: Update TaskWright Installer
**Effort**: 2 hours
**Depends on**: TASK-SHA-002

1. Add version pinning file
2. Add install function (curl + tar)
3. Remove duplicate agents
4. Test

### TASK-SHA-004: Update RequireKit Installer
**Effort**: 2 hours
**Depends on**: TASK-SHA-002
**Can parallelize**: With TASK-SHA-003

Same as TASK-SHA-003, but for RequireKit.

### TASK-SHA-005: Test Both Tools
**Effort**: 1 hour
**Depends on**: TASK-SHA-003 + TASK-SHA-004

1. Test TaskWright alone
2. Test RequireKit alone
3. Test both together
4. Verify no duplication

### TASK-SHA-006: Update Documentation
**Effort**: 1 hour
**Depends on**: TASK-SHA-005

Update READMEs and CHANGELOGs in all three repos.

---

## What We're NOT Doing

Intentionally skipping these (from the over-engineered approach):

❌ Conflict detection for local customizations
❌ Elaborate test plans
❌ Detailed rollback procedures
❌ Checksum validation
❌ Offline fallback mechanisms
❌ Extensive CI/CD workflows
❌ Comprehensive error handling

**Rationale**: These are "nice to haves" that add complexity. We can add them later if needed.

---

## Success Criteria

**Must achieve**:
- ✅ Agents moved to shared-agents repo
- ✅ Both tools use shared-agents
- ✅ No duplication (DRY achieved)
- ✅ No regression in functionality

**That's it!** Simple and effective.

---

## Risk Acceptance

We're accepting these small risks:

1. **User customizations**: May be overwritten (low probability - most users don't customize agents)
2. **Download failures**: GitHub is reliable, but if it fails, user re-runs installer
3. **Version conflicts**: Simple version pinning should suffice

**If issues arise**: We handle them with quick hotfixes.

---

## Timeline

| Phase | Tasks | Duration |
|-------|-------|----------|
| Preparation | TASK-SHA-001 | 1 hour |
| Setup | TASK-SHA-002 | 2 hours |
| Integration | TASK-SHA-003 + 004 (parallel) | 2 hours |
| Validation | TASK-SHA-005 | 1 hour |
| Documentation | TASK-SHA-006 | 1 hour |
| **Total** | **6 tasks** | **7-9 hours** |

**Calendar time**: 1-2 days (with breaks and context switching)

---

## Documents

- **[IMPLEMENTATION-PLAN-LEAN.md](./IMPLEMENTATION-PLAN-LEAN.md)** - Detailed task breakdown
- **[TASK-SHA-001](./TASK-SHA-001-verify-duplication.md)** - Verification
- **[TASK-SHA-002](./TASK-SHA-002-create-shared-repo.md)** - Create repo
- **[TASK-SHA-003](./TASK-SHA-003-update-taskwright.md)** - Update TaskWright
- **[TASK-SHA-004](./TASK-SHA-004-update-requirekit.md)** - Update RequireKit
- **[TASK-SHA-005](./TASK-SHA-005-test-both-tools.md)** - Testing
- **[TASK-SHA-006](./TASK-SHA-006-update-documentation.md)** - Documentation

**Archived** (over-engineered approach):
- `archive/` - Contains the original 38-task plan for reference

---

## Philosophy

> Perfect is the enemy of good. Ship fast, iterate based on real feedback.

This lean approach gets us 90% of the value with 10% of the effort. We can always enhance later if needed.

---

**Ready to start?** Run `/task-work TASK-SHA-001` 🚀
