# TaskWright VM Testing - FOCUSED Quick Reference

**Print this for 1.5-2 hour focused test (recent changes only)**

---

## What We're Testing

✅ **BDD Mode Restoration** (TASK-BDD-001 to BDD-005)
✅ **Template Init Q&A** (if recently changed)
✅ **Subagent Discovery** (if recently changed)
✅ **Conductor Integration** (if recently changed)

❌ **NOT Testing**: Hash IDs (stable), Quality Gates (not changed), Basic workflow (stable)

---

## Installation (20 min)

```bash
# Prerequisites
xcode-select --install
brew install python@3.11

# Install TaskWright
mkdir -p ~/Projects && cd ~/Projects
git clone https://github.com/taskwright-dev/taskwright.git
cd taskwright
chmod +x installer/scripts/install.sh && ./installer/scripts/install.sh
taskwright --version  # Verify

# Install RequireKit
cd ~/Projects
git clone https://github.com/requirekit/require-kit.git
cd require-kit
chmod +x installer/scripts/install.sh && ./installer/scripts/install.sh
ls ~/.agentecflow/require-kit.marker  # Verify
```

---

## Template Init Q&A (20 min)

```bash
mkdir -p ~/Projects/test-api-service && cd ~/Projects/test-api-service
git init
git config user.name "Test User"
git config user.email "test@example.com"

taskwright init fastapi-python
# Watch for Q&A session - document questions asked
```

**Validate**:
- [ ] Q&A session appears (not silent)
- [ ] Questions relevant and clear
- [ ] Generated files match answers
- [ ] `.claude/agents/` populated

---

## BDD Mode (40 min)

### Test WITHOUT RequireKit (5 min)

```bash
# Hide marker
mv ~/.agentecflow/require-kit.marker ~/.agentecflow/require-kit.marker.backup

cd ~/Projects/test-api-service
/task-create "Test BDD error"
/task-work TASK-XXXX --mode=bdd

# Expected: Clear error with installation instructions

# Restore marker
mv ~/.agentecflow/require-kit.marker.backup ~/.agentecflow/require-kit.marker
```

### Create EARS Requirement (10 min)

```bash
cd ~/Projects/require-kit

/req-create "User Authentication" type:epic
/req-create "Login with JWT" parent:REQ-001 type:requirement
/formalize-ears REQ-002

# EARS example:
# WHEN user submits login credentials,
# WHERE account is active,
# SYSTEM SHALL authenticate user,
# AND system SHALL return JWT token valid for 24 hours.
```

### Generate Gherkin (5 min)

```bash
/generate-bdd REQ-002
# Note the BDD-XXX ID
```

### Run BDD Mode (20 min)

```bash
cd ~/Projects/test-api-service

/task-create "Implement JWT login" task_type:implementation
# Edit frontmatter: Add 'bdd_scenarios: [BDD-001]'

/task-work TASK-XXXX --mode=bdd

# Watch for:
# - RequireKit detection ✅
# - Scenarios loaded from RequireKit
# - bdd-generator agent invoked
# - Step definitions generated (pytest-bdd)
# - BDD tests execute and pass
```

**Validate**:
- [ ] RequireKit detected
- [ ] Scenarios load correctly
- [ ] bdd-generator agent used (not local)
- [ ] Step definitions created
- [ ] All scenarios pass

---

## Subagent Discovery (15 min)

```bash
cd ~/Projects/test-api-service

/task-create "Add health check endpoint"
/task-work TASK-XXXX --mode=standard

# Watch Phase 3 agent selection:
# Expected: python-api-specialist
# Source: global
# Stack: python
```

**Validate**:
- [ ] Stack detected (Python/FastAPI)
- [ ] Correct agent selected
- [ ] Discovery feedback shown

---

## Conductor (15 min, optional)

```bash
cd ~/Projects/taskwright

/task-create "Test conductor 1"
/task-create "Test conductor 2"

conductor create-workspace test-wt1 TASK-XXXX
conductor create-workspace test-wt2 TASK-YYYY

# In worktree 1
cd ../test-wt1
/task-work TASK-XXXX && /task-complete TASK-XXXX

# In worktree 2
cd ../test-wt2
/task-work TASK-YYYY && /task-complete TASK-YYYY

# Back to main
cd ~/Projects/taskwright
ls tasks/completed/  # Both should be here
git status  # Should be clean
```

---

## Quick Results Checklist

### BDD Mode
- [ ] Works WITH RequireKit
- [ ] Errors WITHOUT RequireKit (clear message)
- [ ] Scenarios load
- [ ] Step definitions generated
- [ ] Tests execute

### Template Init
- [ ] Q&A appears
- [ ] Questions relevant
- [ ] Config generated
- [ ] Structure correct

### Subagent Discovery
- [ ] Stack detected
- [ ] Correct agent
- [ ] Feedback clear

### Conductor
- [ ] State synced
- [ ] No conflicts

---

## Critical Issues? (Block Launch)

- BDD mode broken: **YES / NO**
- Installation fails: **YES / NO**
- RequireKit detection broken: **YES / NO**

**If YES to any**: Create fix tasks immediately

**If NO to all**: ✅ Ready for launch!

---

## Time Tracking

| Phase | Start | End | Duration |
|-------|-------|-----|----------|
| Install | ___ | ___ | ___ min |
| Template Q&A | ___ | ___ | ___ min |
| BDD Mode | ___ | ___ | ___ min |
| Subagent | ___ | ___ | ___ min |
| Conductor | ___ | ___ | ___ min |
| **Total** | | | ___ min |

**Target**: 1.5-2 hours

---

**Focus on recent changes only - you got this! 🚀**
