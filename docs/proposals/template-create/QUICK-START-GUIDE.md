# Template-Create Redesign: Quick Action Guide

**Date**: 2025-11-18  
**Context**: Solo developer preparing for open source release  
**Strategy**: Rename existing to legacy, build clean main command

---

## ✅ Key Decision Made

**Approach**: Rename `template-create` → `template-create-legacy`, build fixed version as main `template-create`

**Why this is perfect for your situation:**
- ✅ Clean for new open source users (only see `/template-create`)
- ✅ Safe fallback available if you need it
- ✅ No "v1 vs v2" confusion
- ✅ Professional first impression
- ✅ Legacy can be removed once proven stable

---

## 🚀 Implementation Path

### Week 1: Foundation (6-9 hours)

**Phase 1**: TASK-ARTIFACT-FILTER (2-3 hours)
- Fix: Build artifacts excluded (obj/, bin/, node_modules/)
- Result: Correct language detection

**Phase 2**: TASK-AGENT-BRIDGE-COMPLETE (4-6 hours)
- Fix: Agent invocation working with checkpoint-resume
- Result: 90%+ confidence scores

### Week 2: Checkpoint-Resume (7-10 hours)

**Phase 3**: TASK-PHASE-1-CHECKPOINT (2-3 hours)
- Enable AI analysis in Phase 1
- Result: 68% → 90%+ confidence

**Phase 4**: TASK-PHASE-5-CHECKPOINT (2-3 hours)
- Enable AI agent recommendation
- Result: 1 agent → 7-9 agents

**Phase 5**: TASK-PHASE-7-5-CHECKPOINT (3-4 hours)
- Enable agent enhancement
- Result: 34 lines → 150-250 lines

### Week 3: Integration (3-5 hours)

**Phase 6**: TASK-REMOVE-DETECTOR (1-2 hours)
- Delete 1,045 LOC of hard-coded detection
- Result: AI-first architecture restored

**Phase 7**: TASK-RENAME-LEGACY-BUILD-NEW (2-3 hours)
- Rename existing files to `-legacy`
- Build clean new `template-create`
- Result: Clean main command ready

### Week 4: Open Source Prep (2-3 hours)

**Phase 8**: TASK-OPEN-SOURCE-DOCUMENTATION (2-3 hours)
- User guide (beginner-friendly)
- Architecture docs (for contributors)
- Troubleshooting guide
- Result: Ready for public release

---

## 📋 Day-by-Day Checklist

### Day 1-2: Build Artifact Filtering

```bash
# Create branch
git checkout -b feature/artifact-filter

# Implement (see TASK-ARTIFACT-FILTER.md)
# - Create exclusion_patterns.py
# - Modify stratified_sampler.py
# - Write tests

# Test
pytest tests/unit/test_exclusion_patterns.py -v

# Verify on .NET project
cd ~/Projects/DeCUK.Mobile.MyDrive
/template-create --validate --name test-filter
# Should detect as C#, not Java!

# Commit
git add . && git commit -m "feat: exclude build artifacts (TASK-ARTIFACT-FILTER)"
git push origin feature/artifact-filter
```

### Day 3-5: Agent Bridge Completion

```bash
# Create branch
git checkout main && git pull
git checkout -b feature/agent-bridge

# Implement (see TASK-AGENT-BRIDGE-COMPLETE.md)
# - Create checkpoint_manager.py
# - Create response_parser.py
# - Complete agent_invoker.py

# Test
pytest tests/unit/test_checkpoint_manager.py -v
pytest tests/integration/test_agent_workflow.py -v

# Manual test checkpoint cycle
cd /tmp/test && /template-create --validate
# Should exit with code 42, write .agent-request.json

# Commit
git add . && git commit -m "feat: complete agent bridge (TASK-AGENT-BRIDGE-COMPLETE)"
git push origin feature/agent-bridge
```

### Day 6-10: Checkpoint-Resume (3 tasks)

Follow same pattern for:
- TASK-PHASE-1-CHECKPOINT
- TASK-PHASE-5-CHECKPOINT
- TASK-PHASE-7-5-CHECKPOINT (already exists!)

### Day 11-13: Integration

**Remove Detector:**
```bash
git checkout main && git pull
git checkout -b feature/remove-detector

rm installer/core/commands/lib/smart_defaults_detector.py
rm tests/unit/test_smart_defaults_detector.py

# Remove references in orchestrator
# Run tests to verify
pytest tests/ -v

git add . && git commit -m "refactor: remove hard-coded detector"
git push origin feature/remove-detector
```

**Rename Legacy & Build New:**
```bash
git checkout main && git pull
git checkout -b feature/rename-legacy

# Rename existing files
mv installer/core/commands/template-create.md \
   installer/core/commands/template-create-legacy.md

mv installer/core/commands/lib/template_create_orchestrator.py \
   installer/core/commands/lib/template_create_legacy_orchestrator.py

# Build new clean template-create
# (Apply all fixes from Phases 1-6)

# Test
/template-create --validate --name test-new
/template-create-legacy --validate --name test-legacy

git add . && git commit -m "feat: rename legacy and build clean main command"
git push origin feature/rename-legacy
```

### Day 14-16: Documentation

```bash
git checkout main && git pull
git checkout -b docs/open-source-prep

# Create user guide
cat > docs/guides/template-creation-guide.md << EOF
# Template Creation Guide
...user-friendly guide...
EOF

# Update CLAUDE.md
# Update README.md

git add . && git commit -m "docs: prepare for open source release"
git push origin docs/open-source-prep
```

---

## 🎯 Success Criteria

### Before Open Source Release

- [ ] `/template-create` works perfectly
- [ ] All 4 reference projects create successfully
- [ ] Test coverage ≥95%
- [ ] Documentation complete
- [ ] No references to "legacy" in user-facing docs
- [ ] Professional first impression

### Quality Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Confidence | 68% | 90%+ |
| Agents | 1 (14%) | 7-9 (78-100%) |
| Agent Size | 34 lines | 150-250 lines |
| Language Accuracy | 70% | 95%+ |

---

## 🧪 Testing Strategy

### Quick Test (After Each Phase)

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests  
pytest tests/integration/ -v

# Quick manual test
cd /tmp/test-project
/template-create --validate --name quick-test
```

### Full Validation (Before Open Source)

Test on all 4 reference projects:

```bash
# .NET MAUI
cd ~/Projects/DeCUK.Mobile.MyDrive
/template-create --validate --name net9-maui-mydrive

# React TypeScript
cd ~/Projects/bulletproof-react
/template-create --validate --name react-typescript

# FastAPI Python
cd ~/Projects/fastapi-best-practices
/template-create --validate --name fastapi-python

# Next.js
cd ~/Projects/nextjs-boilerplate
/template-create --validate --name nextjs-fullstack
```

**All must pass:**
- ✅ Correct language detected
- ✅ Confidence ≥90%
- ✅ 7-9 agents detected
- ✅ Agent files 150-250 lines
- ✅ Templates complete without errors

---

## 🎁 Quick Wins (Can Do Now)

### 1. Test Current State (15 min)

```bash
cd ~/Projects/appmilla_github/guardkit

# Document current behavior
/template-create --validate --name baseline > baseline.log 2>&1

# Save for comparison
cat baseline.log
```

### 2. Read Task Files (30 min)

```bash
# Read the two starter tasks
cat tasks/backlog/TASK-ARTIFACT-FILTER.md
cat tasks/backlog/TASK-AGENT-BRIDGE-COMPLETE.md

# These are ready to implement!
```

### 3. Set Up Test Environment (15 min)

```bash
# Create test workspace
mkdir -p ~/Projects/template-test-workspace
cd ~/Projects/template-test-workspace

# Copy a test project
cp -r ~/Projects/DeCUK.Mobile.MyDrive ./test-maui
```

---

## 📚 Documentation Reference

**Main Design**: [TEMPLATE-CREATE-REDESIGN-PROPOSAL.md](./TEMPLATE-CREATE-REDESIGN-PROPOSAL.md)
- Complete problem analysis
- Technical designs
- Architecture decisions

**Task Files**:
- [TASK-ARTIFACT-FILTER.md](./tasks/backlog/TASK-ARTIFACT-FILTER.md) - Phase 1
- [TASK-AGENT-BRIDGE-COMPLETE.md](./tasks/backlog/TASK-AGENT-BRIDGE-COMPLETE.md) - Phase 2

**Investigation Docs** (for context):
- [SESSION-SUMMARY-PHASE-7-5-SILENT-FAILURE.md](./SESSION-SUMMARY-PHASE-7-5-SILENT-FAILURE.md)
- [docs/research/template-create-architectural-review.md](./docs/research/template-create-architectural-review.md)

---

## 🚨 Common Issues

**Issue**: Tests failing after changes
```bash
# Clear cache
pytest --cache-clear
pip install -e .
pytest tests/ -v
```

**Issue**: Import errors
```bash
# Set PYTHONPATH
export PYTHONPATH="/path/to/guardkit:/path/to/guardkit/installer/core"
```

**Issue**: Checkpoint not working
```bash
# Check exit code
echo $?  # Should be 42

# Check files
ls -la .agent-request.json .agent-response.json
```

---

## 💡 Pro Tips

1. **Work in small branches** - One task per branch
2. **Test frequently** - After every change
3. **Commit often** - Easy to rollback if needed
4. **Keep legacy as fallback** - Don't delete until new version proven
5. **Document as you go** - Update docs with each task

---

## ✨ Ready to Start?

**Your first step:**

```bash
cd ~/Projects/appmilla_github/guardkit

# Read the design
cat TEMPLATE-CREATE-REDESIGN-PROPOSAL.md

# Read first task
cat tasks/backlog/TASK-ARTIFACT-FILTER.md

# Create branch and begin!
git checkout -b feature/artifact-filter
```

---

**Timeline**: ~4 weeks (6-8 hours/week)  
**Outcome**: Clean, professional template-create ready for open source  
**Risk**: Low (legacy fallback available)

Good luck! 🚀
