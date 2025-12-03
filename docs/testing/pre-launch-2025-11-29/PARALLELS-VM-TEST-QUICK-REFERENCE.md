# TaskWright VM Testing - Quick Reference Card

**Print this page for easy reference during testing**

---

## Setup (5 min)

```bash
# 1. Create VM snapshot
# Name: "Pre-TaskWright-Install"

# 2. Install prerequisites
xcode-select --install
brew install python@3.11
```

---

## Phase 1: Installation (45 min)

### Install TaskWright
```bash
mkdir -p ~/Projects
cd ~/Projects
git clone https://github.com/guardkit/guardkit.git
cd guardkit
chmod +x installer/scripts/install.sh
./installer/scripts/install.sh
guardkit --version  # Verify
```

### Install RequireKit
```bash
cd ~/Projects
git clone https://github.com/requirekit/require-kit.git
cd require-kit
chmod +x installer/scripts/install.sh
./installer/scripts/install.sh
ls ~/.agentecflow/require-kit.marker  # Verify
```

### Initialize Project
```bash
mkdir -p ~/Projects/test-api-service
cd ~/Projects/test-api-service
git init
git config user.name "Test User"
git config user.email "test@example.com"
guardkit init fastapi-python
```

**Q&A Answers**:
- Purpose: **User management API**
- Auth: **JWT**
- Database: **PostgreSQL**
- Async: **Yes**
- Testing: **pytest**
- Celery: **No**
- Docker: **Yes**
- Project name: **test-api-service**

---

## Phase 2: Task Workflow (45 min)

### Create Tasks
```bash
cd ~/Projects/test-api-service

/task-create "Add health check endpoint"
# Expected: TASK-XXXX

/task-create "Fix auth bug" prefix:FIX
# Expected: TASK-FIX-XXXX

/task-status  # Verify all tasks
```

### Work on Task
```bash
/task-work TASK-XXXX

# Watch for:
# - Stack detection: Python/FastAPI
# - Agent selection: python-api-specialist
# - Phase 2.5: Architectural review (if complex)
# - Phase 4.5: Test enforcement
```

### Complete Task
```bash
/task-complete TASK-XXXX
ls tasks/completed/TASK-XXXX/  # Verify
```

---

## Phase 3: BDD Integration (45 min)

### Create Requirement (RequireKit)
```bash
cd ~/Projects/require-kit

/req-create "User Authentication System" type:epic
# Expected: REQ-001

/req-create "Login Functionality" parent:REQ-001 type:requirement
# Expected: REQ-002

/formalize-ears REQ-002
```

**EARS Template**:
```
WHEN user submits login form with email and password,
WHERE account status is active,
SYSTEM SHALL authenticate credentials,
AND system SHALL return JWT token with 24-hour expiration.
```

### Generate BDD Scenarios
```bash
/generate-bdd REQ-002
# Expected: BDD-001 created with 3 scenarios
```

### Run BDD Mode (TaskWright)
```bash
cd ~/Projects/test-api-service

/task-create "Implement login endpoint" task_type:implementation
# Edit frontmatter: Add 'bdd_scenarios: [BDD-001]'

/task-work TASK-XXXX --mode=bdd

# Watch for:
# - RequireKit detection
# - Scenario loading
# - bdd-generator agent invocation
# - Step definition generation
# - BDD tests execution
```

---

## Phase 4: KartLog Demo (30 min, BONUS)

### Clone and Setup
```bash
cd ~/Projects
git clone https://github.com/ColinEberhardt/kartlog.git
cd kartlog
npm install
npm run dev  # Should start on http://localhost:5173
```

### Two Claude Instances

**Instance 1** (Interrogator):
```bash
cd ~/Projects/test-api-service
/task-create "Add weather conditions tracking to KartLog"
/gather-requirements TASK-XXXX
```

**Instance 2** (Answerer):
```bash
cd ~/Projects/kartlog
# Answer questions by reading source:
cat src/lib/types.ts
cat src/components/SessionForm.svelte
cat src/lib/firebase.ts
grep -r "validation" src/
```

### Implement Feature
```bash
# Back to Instance 1
/task-work TASK-XXXX --mode=standard

# Watch for:
# - Implementation matches Svelte patterns
# - Uses existing KartLog code style
# - Firestore integration correct
```

---

## Screenshots Checklist

- [ ] TaskWright installation success
- [ ] RequireKit installation success
- [ ] Template init Q&A session
- [ ] Project file structure
- [ ] Hash-based task IDs
- [ ] Subagent discovery output
- [ ] Architectural review scores
- [ ] Test enforcement with fix loop
- [ ] Completion report
- [ ] EARS formalization
- [ ] Generated Gherkin scenarios
- [ ] BDD mode execution
- [ ] BDD tests passing
- [ ] KartLog weather feature (optional)

---

## Success Indicators

**✅ Installation Phase**:
- Commands available globally
- Marker file exists for RequireKit
- Template files copied to project

**✅ Task Workflow Phase**:
- Hash IDs generated correctly
- Correct subagent selected
- Quality gates trigger appropriately
- Tests pass before completion

**✅ BDD Integration Phase**:
- RequireKit detected
- Scenarios load correctly
- Step definitions generated
- All BDD tests pass

---

## Quick Troubleshooting

**Command not found**:
```bash
export PATH="$HOME/.agentecflow/bin:$PATH"
source ~/.zshrc
```

**RequireKit not detected**:
```bash
ls ~/.agentecflow/require-kit.marker
# If missing, re-run RequireKit installer
```

**Tests failing**:
```bash
# This is expected! Watch for fix loop (up to 3 attempts)
# If all attempts fail, task should block
```

---

## Time Tracking

| Phase | Start | End | Duration | Status |
|-------|-------|-----|----------|--------|
| Setup | ___ | ___ | ___ min | [ ] |
| Phase 1 | ___ | ___ | ___ min | [ ] |
| Phase 2 | ___ | ___ | ___ min | [ ] |
| Phase 3 | ___ | ___ | ___ min | [ ] |
| Phase 4 | ___ | ___ | ___ min | [ ] |
| **Total** | | | ___ min | |

**Target**: 2-3 hours total

---

## Post-Test Actions

1. [ ] Complete PARALLELS-VM-TEST-RESULTS.md
2. [ ] Upload all screenshots
3. [ ] Create fix tasks if issues found
4. [ ] Update baseline documentation
5. [ ] Proceed to shared agents Phase 0

---

**Good luck testing! 🚀**
