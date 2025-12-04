# Shared Agents Refactoring - Lean Implementation Plan

**Based on**: TASK-ARCH-DC05 Architectural Review (Score: 82/100)
**Approach**: Minimal Viable Implementation - Ship fast, fix issues if they arise
**Total Tasks**: 6 tasks
**Estimated Duration**: 1-2 days

---

## Philosophy: Just Enough

The architectural review identified many potential risks and edge cases. However, we're choosing pragmatism over perfection:

- ✅ **Do**: Verify what we're migrating (don't break things)
- ✅ **Do**: Update both repos to use shared agents
- ✅ **Do**: Test that it works
- ❌ **Skip**: Elaborate test plans, rollback docs, checksums (handle if needed)

**Rationale**: This is a low-risk refactoring between two repos we control. We can iterate and fix issues as they arise.

---

## Task Breakdown

### TASK-SHA-001: Verify Agent Duplication

**Priority**: Critical (MUST DO FIRST)
**Effort**: 1 hour
**Why**: Ensures we only migrate agents that exist in both repos

**Acceptance Criteria**:
- [ ] Script compares agents in GuardKit vs RequireKit
- [ ] List of verified duplicates documented
- [ ] Only truly duplicated agents identified for migration

**Implementation**:
```bash
#!/bin/bash
# Simple duplication check
echo "Comparing GuardKit and RequireKit agents..."

GUARDKIT="installer/global/agents"
REQUIREKIT="../require-kit/.claude/agents"

echo "Agents in both repos:"
comm -12 <(ls $GUARDKIT/*.md | xargs basename -a | sort) \
         <(ls $REQUIREKIT/*.md | xargs basename -a | sort)

echo ""
echo "Save this list for migration."
```

---

### TASK-SHA-002: Create Shared Agents Repository

**Priority**: High
**Effort**: 2 hours
**Depends on**: TASK-SHA-001 (need verified list)

**Acceptance Criteria**:
- [ ] GitHub repo created: `guardkit/shared-agents`
- [ ] Verified agents copied to `agents/` directory
- [ ] Simple `manifest.json` listing agent files
- [ ] README with basic usage instructions
- [ ] v1.0.0 release created with tarball

**Implementation**:
```bash
# 1. Create repo
gh repo create guardkit/shared-agents --public

# 2. Copy verified agents (from TASK-SHA-001 list)
mkdir -p agents
cp guardkit/installer/global/agents/code-reviewer.md agents/
cp guardkit/installer/global/agents/test-orchestrator.md agents/
# ... copy other verified agents

# 3. Create simple manifest
cat > manifest.json <<EOF
{
  "version": "1.0.0",
  "agents": [
    "agents/code-reviewer.md",
    "agents/test-orchestrator.md"
  ]
}
EOF

# 4. Create release
tar -czf shared-agents.tar.gz agents/ manifest.json
gh release create v1.0.0 shared-agents.tar.gz --title "Initial Release"
```

---

### TASK-SHA-003: Update GuardKit Installer

**Priority**: High
**Effort**: 2 hours
**Depends on**: TASK-SHA-002 (need shared-agents v1.0.0)

**Acceptance Criteria**:
- [ ] Version pinning file created: `installer/shared-agents-version.txt`
- [ ] Installer downloads and extracts shared-agents
- [ ] Agents installed to `.claude/agents/universal/`
- [ ] Duplicate agents removed from `installer/global/agents/`

**Implementation**:
```bash
# installer/scripts/install.sh - Add this function

install_shared_agents() {
    local version=$(cat installer/shared-agents-version.txt)
    local url="https://github.com/guardkit/shared-agents/releases/download/$version/shared-agents.tar.gz"

    echo "Installing shared agents $version..."

    mkdir -p .claude/agents/universal
    curl -sL "$url" | tar -xz -C .claude/agents/universal --strip-components=1

    echo "Shared agents installed"
}

# Call during installation
install_shared_agents
```

---

### TASK-SHA-004: Update RequireKit Installer

**Priority**: High
**Effort**: 2 hours
**Depends on**: TASK-SHA-002 (need shared-agents v1.0.0)

**Acceptance Criteria**:
- [ ] Version pinning file created: `installer/shared-agents-version.txt`
- [ ] Installer downloads and extracts shared-agents
- [ ] Agents installed to `.claude/agents/universal/`
- [ ] Duplicate agents removed from `.claude/agents/`

**Implementation**:
Same as TASK-SHA-003, but in RequireKit repo.

---

### TASK-SHA-005: Test Both Tools

**Priority**: Critical
**Effort**: 1 hour
**Depends on**: TASK-SHA-003, TASK-SHA-004 (both installers updated)

**Acceptance Criteria**:
- [ ] GuardKit standalone: `/task-work` command works
- [ ] RequireKit standalone: `/formalize-ears` command works (if applicable)
- [ ] Both installed together: No conflicts
- [ ] Shared agents discovered correctly

**Implementation**:
```bash
# Test GuardKit
cd test-project-1
../guardkit/installer/scripts/install.sh
/task-create "Test task"
/task-work TASK-001  # Should use shared agents

# Test RequireKit
cd test-project-2
../require-kit/installer/scripts/install.sh
# Test RequireKit commands

# Test both together
cd test-project-3
../guardkit/installer/scripts/install.sh
../require-kit/installer/scripts/install.sh
ls .claude/agents/universal/  # Should have shared agents (not duplicated)
```

---

### TASK-SHA-006: Update Documentation

**Priority**: Medium
**Effort**: 1 hour
**Depends on**: TASK-SHA-005 (tests passing)

**Acceptance Criteria**:
- [ ] GuardKit CLAUDE.md mentions shared-agents
- [ ] RequireKit CLAUDE.md mentions shared-agents
- [ ] shared-agents README has usage instructions
- [ ] CHANGELOG updated in all three repos

**Implementation**:
```bash
# Update each README/CLAUDE.md with:
# - What changed (agents now shared)
# - How it works (downloaded at install time)
# - How to update (change version pinning file)
```

---

## Timeline

| Task | Effort | Can Parallelize |
|------|--------|-----------------|
| TASK-SHA-001: Verify duplication | 1h | No (must be first) |
| TASK-SHA-002: Create repo | 2h | No (needs verification) |
| TASK-SHA-003: Update GuardKit | 2h | Yes (after repo exists) |
| TASK-SHA-004: Update RequireKit | 2h | Yes (after repo exists) |
| TASK-SHA-005: Test | 1h | No (needs both updates) |
| TASK-SHA-006: Documentation | 1h | No (needs tests passing) |

**Sequential**: 9 hours (~1-2 days)
**Optimized**: 7 hours (parallel TASK-SHA-003 + 004)

---

## What We're Skipping (Intentionally)

### From Phase 0 (Over-Engineered Prerequisites)

❌ **Conflict detection**: If users have local customizations, installer will overwrite. We can add this later if it becomes a problem.

❌ **Elaborate test plan**: We'll test manually. If bugs slip through, we fix them.

❌ **Rollback procedures**: If something breaks, we can rollback manually using git.

❌ **Checksum validation**: GitHub is reliable. Corruption is rare. Not worth the complexity.

### From Phases 1-5 (Excessive Granularity)

❌ **Separate tasks for**:
- Creating manifest
- Setting up GitHub Actions (simple release workflow is enough)
- Creating fallback agents
- Agent discovery updates (existing discovery should work)
- Elaborate CI/CD testing

**Rationale**: These are all part of the core 6 tasks above. Breaking them into 38 micro-tasks adds overhead without value.

---

## Risk Acceptance

We're accepting these risks:

1. **Agent classification error**: Mitigated by TASK-SHA-001 (verification)
2. **User data loss**: Low probability (most users don't customize agents)
3. **Download failures**: GitHub is reliable; can handle edge cases if they occur
4. **Version conflicts**: Simple version pinning should suffice

**If these risks materialize**: We handle them reactively with hotfixes.

---

## Success Criteria

**Must achieve**:
- [ ] Verified agents migrated to shared-agents repo
- [ ] Both GuardKit and RequireKit use shared-agents
- [ ] No regression in functionality
- [ ] Zero duplication (DRY achieved)

**Nice to have** (can add later):
- Conflict detection for local customizations
- Checksums for download integrity
- Comprehensive test automation
- Elaborate rollback procedures

---

## Next Steps

1. Execute TASK-SHA-001 (verification) - **MUST BE FIRST**
2. Execute TASK-SHA-002 (create repo)
3. Execute TASK-SHA-003 + TASK-SHA-004 in parallel (update both installers)
4. Execute TASK-SHA-005 (test)
5. Execute TASK-SHA-006 (docs)
6. Ship it! 🚀

---

## Lessons from Architectural Review

**What we kept**:
- ✅ SOLID principles compliance (DIP especially)
- ✅ DRY elimination (core goal)
- ✅ Clear migration path (just simpler)

**What we simplified**:
- 38 tasks → 6 tasks
- 7-11 days → 1-2 days
- Enterprise-grade → Pragmatic

**Philosophy**: Perfect is the enemy of good. Ship fast, iterate based on real feedback.

---

**Last Updated**: 2025-11-28
**Approach**: Lean/MVP
**Status**: Ready for execution
