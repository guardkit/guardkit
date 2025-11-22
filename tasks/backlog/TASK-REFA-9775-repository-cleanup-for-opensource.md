# TASK-REFA-9775: Repository Root Cleanup for Open Source Release

**Task ID**: TASK-REFA-9775
**Priority**: HIGH
**Status**: BACKLOG
**Created**: 2025-11-22T19:15:00Z
**Updated**: 2025-11-22T19:15:00Z
**Tags**: [cleanup, opensource, repository-hygiene, documentation]
**Complexity**: 3/10 (Simple - file organization and cleanup)
**Related**: None

---

## Overview

Review and clean up the repository root directory to prepare Taskwright for open source release. Remove temporary files, debug logs, backup directories, and ensure only production-ready files remain in the root.

**Current State**:
- ⚠️ 95+ files/directories in repository root (excessive)
- ⚠️ Multiple debug/log files (agent-enhancement-debug.log, DEBUG_AGENT_ENHANCEMENT.md)
- ⚠️ Backup directories (.claude.backup.20251011)
- ⚠️ Coverage report JSON files (multiple, large)
- ⚠️ Temporary Python scripts (add_frontmatter_to_agents.py, complexity_evaluation_51B2E.py)
- ⚠️ Implementation guides that should be in docs/ (AGENT-DISCOVERY-IMPLEMENTATION-GUIDE.md)
- ⚠️ Assessment findings in root (assessment-findings.md)
- ⚠️ macOS system files (.DS_Store)
- ⚠️ Session state files (.template-create-state.json, .template-init-session.json)

**Target State**:
- ✅ Clean root directory with <20 essential files
- ✅ All documentation in appropriate directories (docs/, installer/global/)
- ✅ Debug/log files removed or moved to appropriate locations
- ✅ Backup directories removed
- ✅ .gitignore updated to prevent future clutter
- ✅ Only production-ready files in root
- ✅ Professional appearance for open source project

**Impact**:
- **First Impressions**: Clean repository shows professionalism
- **Discoverability**: Essential files easy to find
- **Maintenance**: Reduced clutter improves maintainability
- **Onboarding**: New contributors can navigate easily

---

## Acceptance Criteria

### AC1: Debug and Log File Cleanup
- [ ] **AC1.1**: Remove or move agent-enhancement-debug.log
- [ ] **AC1.2**: Remove or move DEBUG_AGENT_ENHANCEMENT.md to docs/debugging/ if needed
- [ ] **AC1.3**: Remove temporary Python scripts (add_frontmatter_to_agents.py, complexity_evaluation_51B2E.py)
- [ ] **AC1.4**: Update .gitignore to exclude *.log files from root
- [ ] **AC1.5**: Update .gitignore to exclude debug files

### AC2: Coverage Report Cleanup
- [ ] **AC2.1**: Remove all coverage*.json files from root (8+ files, 3+ MB total)
- [ ] **AC2.2**: Move .coverage to coverage/ directory or remove
- [ ] **AC2.3**: Ensure coverage/ directory is in .gitignore
- [ ] **AC2.4**: Update .gitignore to exclude coverage*.json files
- [ ] **AC2.5**: Document coverage report generation in docs/development/

### AC3: Backup Directory Cleanup
- [ ] **AC3.1**: Remove .claude.backup.20251011 directory
- [ ] **AC3.2**: Update .gitignore to exclude .claude.backup.* directories
- [ ] **AC3.3**: Document backup procedures in docs/development/ if needed
- [ ] **AC3.4**: Verify no other backup directories exist

### AC4: Documentation Organization
- [ ] **AC4.1**: Move AGENT-DISCOVERY-IMPLEMENTATION-GUIDE.md to docs/guides/ or docs/implementation/
- [ ] **AC4.2**: Move assessment-findings.md to appropriate location (docs/analysis/ or archive)
- [ ] **AC4.3**: Review CLAUDE.md for completeness (keep in root as main user guide)
- [ ] **AC4.4**: Review CHANGELOG.md for completeness (keep in root)
- [ ] **AC4.5**: Ensure all guides are referenced from appropriate indexes

### AC5: System and Session File Cleanup
- [ ] **AC5.1**: Remove .DS_Store files
- [ ] **AC5.2**: Update .gitignore to exclude .DS_Store
- [ ] **AC5.3**: Evaluate .template-create-state.json (move to .claude/state/ or make ephemeral)
- [ ] **AC5.4**: Evaluate .template-init-session.json (move to .claude/state/ or make ephemeral)
- [ ] **AC5.5**: Update .gitignore for session state files if needed

### AC6: Essential Files Verification
- [ ] **AC6.1**: Verify README.md exists and is comprehensive
- [ ] **AC6.2**: Verify LICENSE file exists (add if missing)
- [ ] **AC6.3**: Verify CONTRIBUTING.md exists (add if missing)
- [ ] **AC6.4**: Verify .gitignore is comprehensive
- [ ] **AC6.5**: Verify installer/ directory is organized and documented

### AC7: .gitignore Comprehensiveness
- [ ] **AC7.1**: Exclude Python cache files (__pycache__/, *.pyc)
- [ ] **AC7.2**: Exclude coverage reports (coverage/, .coverage, coverage*.json)
- [ ] **AC7.3**: Exclude OS files (.DS_Store, Thumbs.db)
- [ ] **AC7.4**: Exclude IDE files (.vscode/, .idea/)
- [ ] **AC7.5**: Exclude log and debug files (*.log, *debug*.md)
- [ ] **AC7.6**: Exclude backup directories (*.backup.*)
- [ ] **AC7.7**: Exclude session state files (.template-*-state.json, .template-*-session.json)

### AC8: Final Verification
- [ ] **AC8.1**: Root directory has <20 files/directories (excluding .git)
- [ ] **AC8.2**: All remaining files are production-ready
- [ ] **AC8.3**: No debug/temp files remain in root
- [ ] **AC8.4**: Documentation is discoverable and well-organized
- [ ] **AC8.5**: Repository passes first-impression test

---

## Implementation Plan

### Summary

**Phase 1**: Audit and Categorize (30 minutes)
- Inventory all files in root directory
- Categorize by type (debug, coverage, docs, config, backup)
- Identify essential vs removable files

**Phase 2**: Move Documentation (20 minutes)
- Move implementation guides to docs/
- Move assessment findings to docs/analysis/
- Update cross-references

**Phase 3**: Remove Temporary Files (20 minutes)
- Remove debug logs and scripts
- Remove coverage reports
- Remove backup directories
- Remove system files

**Phase 4**: Update .gitignore (15 minutes)
- Add comprehensive exclusion rules
- Test .gitignore effectiveness
- Document gitignore patterns

**Phase 5**: Verification (15 minutes)
- Count remaining files
- Verify essential files present
- Test repository appearance

**Total Effort**: 1.67 hours (~2 hours with buffer)
**Risk**: Low (file operations only, no code changes)

### Detailed Steps

#### Phase 1: Audit and Categorize (30 minutes)

**Step 1.1: Inventory Current Files (15 minutes)**

```bash
# List all files in root
ls -la /Users/richardwoollcott/Projects/appmilla_github/taskwright/ > root-files-inventory.txt

# Categorize files
echo "=== DEBUG/LOG FILES ===" >> categorized-inventory.txt
ls -la | grep -E "(debug|\.log)" >> categorized-inventory.txt

echo "=== COVERAGE FILES ===" >> categorized-inventory.txt
ls -la | grep -E "(coverage|\.coverage)" >> categorized-inventory.txt

echo "=== BACKUP DIRECTORIES ===" >> categorized-inventory.txt
ls -la | grep backup >> categorized-inventory.txt

echo "=== DOCUMENTATION ===" >> categorized-inventory.txt
ls -la | grep -E "\.(md|MD)" >> categorized-inventory.txt

echo "=== PYTHON SCRIPTS ===" >> categorized-inventory.txt
ls -la | grep "\.py$" >> categorized-inventory.txt

echo "=== SESSION/STATE FILES ===" >> categorized-inventory.txt
ls -la | grep -E "(session|state)" >> categorized-inventory.txt
```

**Step 1.2: Identify Essential Files (15 minutes)**

**Essential Files to Keep in Root**:
- CLAUDE.md (main user guide)
- CHANGELOG.md (version history)
- README.md (if exists)
- LICENSE (if exists, add if missing)
- CONTRIBUTING.md (if exists, add if missing)
- .gitignore
- conftest.py (pytest configuration)
- pyproject.toml or setup.py (if exists)

**Files to Remove**:
- Debug logs: agent-enhancement-debug.log, DEBUG_AGENT_ENHANCEMENT.md
- Temp scripts: add_frontmatter_to_agents.py, complexity_evaluation_51B2E.py
- Coverage: coverage*.json, .coverage
- Backups: .claude.backup.20251011/
- System: .DS_Store
- Assessment: assessment-findings.md

**Files to Move**:
- AGENT-DISCOVERY-IMPLEMENTATION-GUIDE.md → docs/implementation/
- assessment-findings.md → docs/analysis/ or archive/

---

#### Phase 2: Move Documentation (20 minutes)

**Step 2.1: Move Implementation Guides (10 minutes)**

```bash
# Create docs/implementation/ if doesn't exist
mkdir -p docs/implementation/

# Move implementation guide
mv AGENT-DISCOVERY-IMPLEMENTATION-GUIDE.md docs/implementation/agent-discovery-implementation-guide.md

# Update cross-references (if any)
grep -r "AGENT-DISCOVERY-IMPLEMENTATION-GUIDE.md" . --exclude-dir=.git
# Update any references found
```

**Step 2.2: Move Assessment Findings (10 minutes)**

```bash
# Create docs/analysis/ if doesn't exist
mkdir -p docs/analysis/

# Move or archive assessment findings
mv assessment-findings.md docs/analysis/assessment-findings-20251122.md

# Or if outdated:
# mkdir -p archive/
# mv assessment-findings.md archive/assessment-findings-20251122.md
```

**Acceptance Criteria**: AC4.1, AC4.2

---

#### Phase 3: Remove Temporary Files (20 minutes)

**Step 3.1: Remove Debug and Log Files (5 minutes)**

```bash
# Remove debug logs
rm -f agent-enhancement-debug.log
rm -f DEBUG_AGENT_ENHANCEMENT.md

# Remove temporary Python scripts
rm -f add_frontmatter_to_agents.py
rm -f complexity_evaluation_51B2E.py
```

**Acceptance Criteria**: AC1.1, AC1.2, AC1.3

**Step 3.2: Remove Coverage Files (5 minutes)**

```bash
# Remove coverage JSON files
rm -f coverage*.json
rm -f .coverage

# Ensure coverage/ directory is preserved (if needed)
# and .gitignore excludes it
```

**Acceptance Criteria**: AC2.1, AC2.2

**Step 3.3: Remove Backup Directories (5 minutes)**

```bash
# Remove backup directory
rm -rf .claude.backup.20251011/

# Check for other backup directories
ls -la | grep backup
```

**Acceptance Criteria**: AC3.1

**Step 3.4: Remove System Files (5 minutes)**

```bash
# Remove macOS system files
find . -name ".DS_Store" -type f -delete

# Verify removal
find . -name ".DS_Store" -type f
```

**Acceptance Criteria**: AC5.1

---

#### Phase 4: Update .gitignore (15 minutes)

**Step 4.1: Add Comprehensive Exclusions (10 minutes)**

**File**: `.gitignore`

**Add or verify these patterns**:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Testing / Coverage
.coverage
coverage/
coverage*.json
htmlcov/
.tox/
.pytest_cache/
.hypothesis/

# OS Files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.project
.pydevproject

# Logs and Debug
*.log
*debug*.log
*DEBUG*.md
debug-*.md

# Backup Directories
*.backup/
*.backup.*
.*.backup.*

# Session/State Files (unless needed for functionality)
.template-create-state.json
.template-init-session.json
*.session.json
*.state.json

# Temporary Files
*.tmp
*.temp
temp/
tmp/
*.pyc
*.pyo

# Environment
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/
```

**Acceptance Criteria**: AC7.1-AC7.7, AC1.4, AC1.5, AC2.4, AC3.2, AC5.2, AC5.5

**Step 4.2: Test .gitignore (5 minutes)**

```bash
# Check what would be committed
git status

# Verify excluded files don't appear
git status --ignored

# Test by creating a temp file
touch test-debug.log
git status  # Should not show test-debug.log
rm test-debug.log
```

**Acceptance Criteria**: AC7.1-AC7.7

---

#### Phase 5: Verification (15 minutes)

**Step 5.1: Count Remaining Files (5 minutes)**

```bash
# Count files/directories in root (excluding .git)
ls -la | grep -v "^d.*\.git$" | wc -l

# Should be <20 for professional appearance
```

**Acceptance Criteria**: AC8.1

**Step 5.2: Verify Essential Files Present (5 minutes)**

```bash
# Check essential files
ls -la README.md CLAUDE.md CHANGELOG.md LICENSE CONTRIBUTING.md .gitignore conftest.py

# Note which are missing and need to be created
```

**Acceptance Criteria**: AC6.1-AC6.5, AC8.2

**Step 5.3: Final Appearance Check (5 minutes)**

```bash
# List root directory in clean format
ls -la

# Verify:
# - No debug files
# - No coverage files
# - No backup directories
# - No temporary scripts
# - Only production-ready files
```

**Acceptance Criteria**: AC8.3, AC8.4, AC8.5

---

## Files to Remove (Summary)

**Debug/Log Files**:
- `agent-enhancement-debug.log`
- `DEBUG_AGENT_ENHANCEMENT.md`

**Temporary Python Scripts**:
- `add_frontmatter_to_agents.py`
- `complexity_evaluation_51B2E.py`

**Coverage Files** (8+ files, ~3MB):
- `coverage.json`
- `coverage-comprehensive-task-review.json`
- `coverage-id-generator.json`
- `coverage-task-utils.json`
- `coverage_settings_generator.json`
- `coverage_task007.json`
- `.coverage`

**Backup Directories**:
- `.claude.backup.20251011/`

**System Files**:
- `.DS_Store` (all instances)

**Session/State Files** (evaluate - may need to move to .claude/state/):
- `.template-create-state.json`
- `.template-init-session.json`

---

## Files to Move

**Implementation Guides**:
- `AGENT-DISCOVERY-IMPLEMENTATION-GUIDE.md` → `docs/implementation/agent-discovery-implementation-guide.md`

**Assessment Findings**:
- `assessment-findings.md` → `docs/analysis/assessment-findings-20251122.md` or `archive/`

---

## Files to Keep in Root

**Documentation** (Essential):
- `CLAUDE.md` (main user guide - 28KB, keep)
- `CHANGELOG.md` (version history - 4KB, keep)
- `README.md` (if exists, verify completeness)
- `LICENSE` (if exists, add if missing)
- `CONTRIBUTING.md` (if exists, add if missing)

**Configuration**:
- `.gitignore` (update comprehensively)
- `conftest.py` (pytest configuration)

**Directories** (Keep):
- `.claude/` (configuration and state)
- `.conductor/` (conductor integration)
- `.git/` (version control)
- `.pytest_cache/` (gitignore will exclude)
- `docs/` (documentation)
- `installer/` (installation scripts and resources)
- `tasks/` (task management)
- `tests/` (if exists)
- `coverage/` (if exists, gitignore will exclude)

---

## Testing Strategy

### Test 1: File Count Verification

**Objective**: Verify root directory has <20 files/directories

**Method**:
```bash
# Count non-git files/directories
ls -la | grep -v "total" | grep -v "^d.*\.git$" | tail -n +2 | wc -l
```

**Success Criteria**:
- File/directory count <20 (excluding .git)
- Only production-ready files remain
- No temporary or debug files

**Acceptance Criteria**: AC8.1

### Test 2: .gitignore Effectiveness

**Objective**: Verify .gitignore prevents future clutter

**Method**:
```bash
# Create test files
touch test-debug.log
touch .DS_Store
mkdir test.backup
touch coverage-test.json
touch test-session.json

# Check git status
git status

# Clean up test files
rm test-debug.log .DS_Store coverage-test.json test-session.json
rmdir test.backup
```

**Success Criteria**:
- `git status` does not show test files
- All patterns in .gitignore are effective
- No warnings or errors

**Acceptance Criteria**: AC7.1-AC7.7

### Test 3: Documentation Discoverability

**Objective**: Verify documentation is well-organized and findable

**Method**:
1. Check docs/ directory structure
2. Verify implementation guides are in docs/implementation/
3. Verify analysis documents are in docs/analysis/
4. Check for broken cross-references

**Success Criteria**:
- All moved documentation is in appropriate directories
- No broken links
- Documentation index (if exists) is updated
- README.md references key documentation

**Acceptance Criteria**: AC4.1, AC4.2, AC4.5, AC8.4

### Test 4: Essential Files Presence

**Objective**: Verify all essential open source files are present

**Method**:
```bash
# Check for essential files
for file in README.md LICENSE CONTRIBUTING.md CLAUDE.md CHANGELOG.md .gitignore; do
  if [ -f "$file" ]; then
    echo "✓ $file exists"
  else
    echo "✗ $file missing"
  fi
done
```

**Success Criteria**:
- README.md exists and is comprehensive
- LICENSE exists (add if missing)
- CONTRIBUTING.md exists (add if missing)
- CLAUDE.md exists (verified)
- CHANGELOG.md exists (verified)
- .gitignore exists and is comprehensive

**Acceptance Criteria**: AC6.1-AC6.5

### Test 5: Professional Appearance

**Objective**: Verify repository makes good first impression

**Method**:
1. List root directory: `ls -la`
2. Review for clutter
3. Check GitHub preview (if available)
4. Get second opinion from team member

**Success Criteria**:
- Root directory looks clean and professional
- No debug/temp files visible
- Documentation is prominent
- Project structure is clear

**Acceptance Criteria**: AC8.5

---

## Design Decisions & Rationale

### Decision 1: Remove vs Archive Coverage Files

**Chosen**: Remove coverage*.json files entirely
**Alternative**: Move to coverage/ directory or archive/

**Rationale**:
- ✅ Coverage reports are regenerated on each test run
- ✅ JSON reports are not human-readable (use HTML reports instead)
- ✅ Reduces repository size by ~3MB
- ✅ Prevents confusion about which report is current
- ⚠️ HTML coverage reports (if needed) should be in coverage/ and gitignored

### Decision 2: Keep vs Move Session State Files

**Chosen**: Evaluate during implementation (may move to .claude/state/)
**Alternative**: Remove entirely

**Rationale**:
- ⚠️ Need to verify if .template-create-state.json is needed for functionality
- ⚠️ Need to verify if .template-init-session.json is needed
- ✅ If needed, should be in .claude/state/ not root
- ✅ If ephemeral, should be gitignored

### Decision 3: Move vs Archive Assessment Findings

**Chosen**: Move to docs/analysis/ with timestamp
**Alternative**: Archive or remove

**Rationale**:
- ✅ Assessment findings may have historical value
- ✅ Timestamping prevents confusion
- ✅ docs/analysis/ is appropriate location
- ⚠️ Can be archived later if outdated

### Decision 4: .gitignore Comprehensiveness Level

**Chosen**: Comprehensive patterns covering all common cases
**Alternative**: Minimal patterns

**Rationale**:
- ✅ Prevents future clutter from debug files, logs, coverage
- ✅ Standard patterns for Python projects
- ✅ Covers OS-specific files (macOS, Windows, Linux)
- ✅ Includes IDE patterns for common editors
- ✅ Better to be comprehensive than permissive for open source

---

## Success Metrics

### Quantitative

- **Root file count**: <20 files/directories (excluding .git)
- **Debug files removed**: 4+ files (logs, scripts, debug docs)
- **Coverage files removed**: 8+ files (~3MB)
- **Backup directories removed**: 1+ directories
- **Documentation moved**: 2+ files to appropriate locations
- **.gitignore patterns added**: 30+ comprehensive patterns
- **Time to complete**: ≤2 hours

### Qualitative

- **Professional appearance**: Repository looks ready for open source
- **Discoverability**: Documentation is easy to find
- **Maintainability**: Reduced clutter improves maintenance
- **Onboarding**: New contributors can navigate easily
- **First impression**: Clean, organized, well-maintained

### Validation

**Before Completion**:
- [ ] All 8 AC groups completed (40 total sub-criteria)
- [ ] Root directory has <20 files (AC8.1)
- [ ] No debug/temp files remain (AC8.3)
- [ ] .gitignore is comprehensive (AC7.1-AC7.7)
- [ ] Documentation is organized (AC4.1-AC4.5)
- [ ] Essential files present (AC6.1-AC6.5)
- [ ] All 5 tests pass
- [ ] Changes committed

**After Deployment** (1 week):
- [ ] No new clutter accumulates in root
- [ ] .gitignore prevents unintended commits
- [ ] Contributors can find documentation easily
- [ ] No complaints about repository organization

---

## Risk Assessment

### Risk 1: Removing Needed Files

**Likelihood**: Low (careful categorization and backup)
**Impact**: Medium (could require restoration)

**Mitigation**:
- Create backup branch before cleanup: `git checkout -b cleanup-backup`
- Review each file before removal
- Test functionality after cleanup
- Git history preserves deleted files if needed

### Risk 2: Breaking Cross-References

**Likelihood**: Low (limited cross-references to root files)
**Impact**: Low (easy to fix with search/replace)

**Mitigation**:
- Search for references before moving files: `grep -r "FILENAME" .`
- Update all references when moving files
- Test documentation links after moves
- Use relative paths for future-proofing

### Risk 3: .gitignore Too Aggressive

**Likelihood**: Very Low (standard patterns tested)
**Impact**: Low (can adjust .gitignore)

**Mitigation**:
- Use standard Python project .gitignore patterns
- Test .gitignore with dummy files before commit
- Review `git status --ignored` to verify
- Can whitelist specific files if needed with `!filename`

---

## Rollout Plan

### Phase 1: Audit (30 minutes)
- Inventory all root files
- Categorize by type
- Identify essential vs removable
- **Checkpoint**: Categorized inventory complete

### Phase 2: Move Documentation (20 minutes)
- Move implementation guides
- Move assessment findings
- Update cross-references
- **Checkpoint**: Documentation organized

### Phase 3: Remove Temporary Files (20 minutes)
- Remove debug logs and scripts
- Remove coverage reports
- Remove backup directories
- Remove system files
- **Checkpoint**: Temporary files removed

### Phase 4: Update .gitignore (15 minutes)
- Add comprehensive patterns
- Test .gitignore effectiveness
- **Checkpoint**: .gitignore comprehensive

### Phase 5: Verification (15 minutes)
- Count remaining files (<20)
- Verify essential files present
- Test repository appearance
- **Checkpoint**: All tests pass

**Total Estimated Time**: 1.67 hours (2 hours with buffer)

---

## Dependencies

**Blocks**: Open source release
**Blocked By**: None
**Related**:
- Future task: Add/update README.md
- Future task: Add LICENSE file
- Future task: Add CONTRIBUTING.md

---

## Completion Checklist

Before marking this task complete:

- [ ] **AC1**: Debug and Log File Cleanup (5 sub-criteria)
  - [ ] AC1.1: agent-enhancement-debug.log removed
  - [ ] AC1.2: DEBUG_AGENT_ENHANCEMENT.md removed/moved
  - [ ] AC1.3: Temporary Python scripts removed
  - [ ] AC1.4: .gitignore excludes *.log
  - [ ] AC1.5: .gitignore excludes debug files

- [ ] **AC2**: Coverage Report Cleanup (5 sub-criteria)
  - [ ] AC2.1: All coverage*.json removed
  - [ ] AC2.2: .coverage moved/removed
  - [ ] AC2.3: coverage/ in .gitignore
  - [ ] AC2.4: .gitignore excludes coverage*.json
  - [ ] AC2.5: Coverage generation documented

- [ ] **AC3**: Backup Directory Cleanup (4 sub-criteria)
  - [ ] AC3.1: .claude.backup.20251011/ removed
  - [ ] AC3.2: .gitignore excludes .claude.backup.*
  - [ ] AC3.3: Backup procedures documented
  - [ ] AC3.4: No other backup directories

- [ ] **AC4**: Documentation Organization (5 sub-criteria)
  - [ ] AC4.1: AGENT-DISCOVERY-IMPLEMENTATION-GUIDE.md moved
  - [ ] AC4.2: assessment-findings.md moved
  - [ ] AC4.3: CLAUDE.md reviewed
  - [ ] AC4.4: CHANGELOG.md reviewed
  - [ ] AC4.5: Guides referenced from indexes

- [ ] **AC5**: System and Session File Cleanup (5 sub-criteria)
  - [ ] AC5.1: .DS_Store removed
  - [ ] AC5.2: .gitignore excludes .DS_Store
  - [ ] AC5.3: .template-create-state.json evaluated
  - [ ] AC5.4: .template-init-session.json evaluated
  - [ ] AC5.5: .gitignore updated for session files

- [ ] **AC6**: Essential Files Verification (5 sub-criteria)
  - [ ] AC6.1: README.md exists and complete
  - [ ] AC6.2: LICENSE exists
  - [ ] AC6.3: CONTRIBUTING.md exists
  - [ ] AC6.4: .gitignore comprehensive
  - [ ] AC6.5: installer/ organized

- [ ] **AC7**: .gitignore Comprehensiveness (7 sub-criteria)
  - [ ] AC7.1: Python cache excluded
  - [ ] AC7.2: Coverage reports excluded
  - [ ] AC7.3: OS files excluded
  - [ ] AC7.4: IDE files excluded
  - [ ] AC7.5: Log and debug files excluded
  - [ ] AC7.6: Backup directories excluded
  - [ ] AC7.7: Session state files excluded

- [ ] **AC8**: Final Verification (5 sub-criteria)
  - [ ] AC8.1: <20 files in root
  - [ ] AC8.2: All files production-ready
  - [ ] AC8.3: No debug/temp files
  - [ ] AC8.4: Documentation discoverable
  - [ ] AC8.5: Professional appearance

- [ ] All 5 phases complete (2 hours total)
- [ ] All 5 tests pass
- [ ] Changes committed to git
- [ ] Task marked complete

---

**Created**: 2025-11-22T19:15:00Z
**Updated**: 2025-11-22T19:15:00Z
**Status**: BACKLOG
**Ready for Implementation**: YES
**Complexity**: 3/10 (Simple - file organization and cleanup)
**Estimated Effort**: 2 hours

---

## Related Documents

- **Project Guide**: [CLAUDE.md](../../CLAUDE.md)
- **Changelog**: [CHANGELOG.md](../../CHANGELOG.md)
- **Git Configuration**: [.gitignore](../../.gitignore)
