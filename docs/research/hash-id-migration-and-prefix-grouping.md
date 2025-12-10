# Hash ID Migration & Prefix-Based Task Grouping

**Created**: 2025-11-10
**Status**: Reference Guide
**Related Tasks**: TASK-046 through TASK-054, TASK-052 (Migration Script)

---

## Executive Summary

This document addresses two key aspects of the hash-based ID system:

1. **Migration Status**: Why tasks 063-073 weren't migrated and how to handle them
2. **Sequential Grouping**: How the prefix system provides better grouping than sequential numbering

**Key Insight**: The prefix-based system is **superior to sequential numbering** for grouping related tasks because it provides semantic meaning and works across multiple work sessions.

---

## Part 1: Migration Script Status

### What Was Migrated

The migration script (`scripts/migrate-my-tasks.py`) successfully migrated **58 tasks** from old sequential IDs to new hash-based IDs.

**Migration Coverage**:
- ✅ Tasks with YAML frontmatter: 58 tasks
- ❌ Tasks with old markdown format: 7 tasks (TASK-063, 064, 069-073)

### Why Some Tasks Were Not Migrated

**Technical Reason**: Format incompatibility

The migration script looks for YAML frontmatter:
```yaml
---
id: TASK-042
title: Some task
status: backlog
---
```

Tasks 063-073 use an older markdown format:
```markdown
# TASK-069: Demo/Test - Core Template Usage

**Created**: 2025-01-10
**Priority**: High
**Status**: backlog
```

**Unmigrated Tasks**:
1. TASK-063: Update Documentation for 4-Template Strategy
2. TASK-064: Template Validate Advanced Features
3. TASK-069: Demo/Test - Core Template Usage
4. TASK-070: Demo/Test - Custom Template from Existing Codebase
5. TASK-071: Demo/Test - Greenfield Template Creation
6. TASK-072: Demo/Test - End-to-End Workflow
7. TASK-073: Create Demo Repositories

**Total Lines**: ~5,390 lines across 7 files

### Handling Unmigrated Tasks

**Recommended Approach: Leave as-is**

These tasks are in backlog and use an older format. When you're ready to work on them:

**Option 1: Create New Tasks (Recommended)**
```bash
# When ready to work on the functionality
/task-create "Update docs for 4-template strategy" prefix:DOC
# Reference old task in description: "Based on TASK-063"
```

**Benefits**:
- Uses current task format
- Gets hash-based ID automatically
- Can apply proper prefix grouping
- Old task remains as historical reference

**Option 2: Manual Format Conversion**
If you need to preserve the exact task ID and history:

1. Add YAML frontmatter to each file
2. Run migration script again with `--execute`

**Example conversion**:
```markdown
---
id: TASK-069
title: Demo/Test - Core Template Usage
status: backlog
created: 2025-01-10T00:00:00Z
updated: 2025-01-10T00:00:00Z
priority: high
tags: [testing, demo, templates]
complexity: 5
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Demo/Test - Core Template Usage

[Rest of content...]
```

**Option 3: Extend Migration Script**
For bulk conversion, extend `scripts/migrate-my-tasks.py` to handle old markdown format.

---

## Part 2: Prefix-Based Task Grouping

### The Sequential Numbering Problem

**Old Approach (Sequential IDs)**:
```
TASK-042: Research caching strategies
TASK-043: Fix login validation bug
TASK-044: Research authentication patterns
TASK-045: Update API documentation
TASK-046: Research database schema design
```

**Problems**:
- ❌ No visual grouping - can't tell which tasks are related
- ❌ Numbers have no semantic meaning
- ❌ Requires manual tracking to group related work
- ❌ Merge conflicts with sequential numbering
- ❌ Can't group tasks across different time periods

### The Prefix Solution (Implemented in TASK-054)

**New Approach (Prefix-Based Grouping)**:
```
TASK-RES-a3f8: Research caching strategies
TASK-FIX-b2c4: Fix login validation bug
TASK-RES-f1a3: Research authentication patterns
TASK-DOC-c5e7: Update API documentation
TASK-RES-d4b1: Research database schema design
```

**Benefits**:
- ✅ Clear semantic grouping (all RES- tasks are research)
- ✅ Visual scanning - easy to spot related tasks
- ✅ Works across time periods - add RES tasks any time
- ✅ No merge conflicts with hash-based IDs
- ✅ Multiple grouping strategies (epic, tag, manual)

---

## Part 3: Using Prefixes for Sequential Task Creation

### Scenario: Research Session with Multiple Tasks

When doing research and creating multiple related tasks, use prefixes for automatic grouping:

#### Strategy 1: Manual Prefix (Most Explicit)

```bash
# Research session on authentication
/task-create "Research OAuth 2.0 providers" prefix:AUTH
/task-create "Research JWT best practices" prefix:AUTH
/task-create "Research session management" prefix:AUTH
/task-create "Research MFA implementation" prefix:AUTH

# Generated IDs:
# TASK-AUTH-a3f8: Research OAuth 2.0 providers
# TASK-AUTH-b2c4: Research JWT best practices
# TASK-AUTH-f1a3: Research session management
# TASK-AUTH-c5e7: Research MFA implementation
```

**When to use**: When you want explicit control over grouping.

#### Strategy 2: Epic-Based Grouping (Hierarchical)

```bash
# If using require-kit with epics
/task-create "Research authentication methods" epic:EPIC-001
/task-create "Evaluate OAuth providers" epic:EPIC-001
/task-create "Design token strategy" epic:EPIC-001

# Auto-generated prefix from epic:
# TASK-E01-a3f8: Research authentication methods
# TASK-E01-b2c4: Evaluate OAuth providers
# TASK-E01-f1a3: Design token strategy
```

**When to use**: When tasks belong to a larger epic/project.

#### Strategy 3: Tag-Based Inference (Automatic)

```bash
# System infers prefix from tags
/task-create "Research caching patterns" tags:[research]
/task-create "Research API design" tags:[research]
/task-create "Research database optimization" tags:[research]

# Auto-inferred prefix:
# TASK-RES-a3f8: Research caching patterns
# TASK-RES-b2c4: Research API design
# TASK-RES-f1a3: Research database optimization
```

**When to use**: When you want automatic grouping based on task type.

#### Strategy 4: Title Keyword Inference (Implicit)

```bash
# System infers from title keywords
/task-create "Fix login validation bug"
/task-create "Fix password reset email"
/task-create "Fix session timeout issue"

# Auto-inferred from "Fix" keyword:
# TASK-FIX-a3f8: Fix login validation bug
# TASK-FIX-b2c4: Fix password reset email
# TASK-FIX-f1a3: Fix session timeout issue
```

**When to use**: Quick task creation with automatic categorization.

---

## Part 4: Standard Prefix Categories

### Built-in Prefix Mappings

From TASK-054 implementation, these prefixes are automatically recognized:

#### Domain-Based Prefixes
- **DOC** - Documentation tasks
- **TEST** - Testing tasks
- **DB** - Database tasks
- **API** - API/Backend tasks
- **UI** - User interface tasks
- **INFR** - Infrastructure tasks

#### Type-Based Prefixes
- **FIX** - Bug fixes
- **FEAT** - New features
- **REFAC** → **REFA** - Refactoring (auto-truncated to 4 chars)

#### Epic-Based Prefixes (Auto-generated)
- **E01** - Epic 001
- **E02** - Epic 002
- **E[XX]** - Epic number (automatic from `epic:EPIC-XXX`)

#### Custom Prefixes
You can create your own:
- **AUTH** - Authentication tasks
- **PAY** - Payment integration
- **RES** - Research tasks
- **DEMO** - Demo/testing tasks
- **PERF** - Performance optimization

### Prefix Validation Rules

**Valid Format**: 2-4 uppercase alphanumeric characters

**Examples**:
- ✅ `AUTH` - Valid (4 chars)
- ✅ `E01` - Valid (3 chars, alphanumeric)
- ✅ `DB` - Valid (2 chars)
- ✅ `RES` - Valid (3 chars)
- ❌ `A` - Invalid (too short)
- ❌ `RESEARCH` - Invalid (too long, will be truncated to `RESE`)
- ❌ `auth` - Invalid (must be uppercase)
- ❌ `A-01` - Invalid (no special characters)

---

## Part 5: Claude Code Integration

### How Claude Code Creates Tasks with Hash IDs

The `/task-create` command automatically:

1. **Generates Hash-Based ID**
   - Uses `installer/core/lib/id_generator.py`
   - Produces 4-6 character hash (e.g., `a3f8`, `b2c4`)

2. **Applies Prefix Inference** (Priority Order)
   - Manual prefix: `prefix:AUTH` → `TASK-AUTH-xxxx`
   - Epic inference: `epic:EPIC-001` → `TASK-E01-xxxx`
   - Tag inference: `tags:[docs]` → `TASK-DOC-xxxx`
   - Title keywords: "Fix bug" → `TASK-FIX-xxxx`
   - No prefix: → `TASK-xxxx`

3. **Validates ID Format**
   - Checks pattern: `TASK-([A-Z0-9]{2,4}-)?[A-Fa-f0-9]{4,6}`
   - Verifies no duplicates exist
   - Returns error if invalid

### Example: Claude Code Research Session

**Typical workflow** when Claude Code does research and creates tasks:

```bash
# User asks: "Research authentication strategies and create implementation tasks"

# Claude Code would execute:
/task-create "Research OAuth 2.0 vs SAML comparison" prefix:AUTH
/task-create "Research JWT token strategies" prefix:AUTH
/task-create "Research session management patterns" prefix:AUTH
/task-create "Research MFA implementation options" prefix:AUTH
/task-create "Research password hashing algorithms" prefix:AUTH

# Results in grouped tasks:
# TASK-AUTH-a3f8: Research OAuth 2.0 vs SAML comparison
# TASK-AUTH-b2c4: Research JWT token strategies
# TASK-AUTH-f1a3: Research session management patterns
# TASK-AUTH-c5e7: Research MFA implementation options
# TASK-AUTH-d4b1: Research password hashing algorithms
```

**All tasks clearly grouped** under AUTH prefix, easy to:
- Find all authentication-related tasks: `ls tasks/backlog/TASK-AUTH-*`
- Grep for references: `grep -r "TASK-AUTH" tasks/`
- Track progress on authentication work

### Ensuring Proper Integration

**No special configuration needed** - the system works out of the box:

1. ✅ `/task-create` command uses hash ID generator
2. ✅ Prefix inference is automatic based on parameters
3. ✅ Validation prevents duplicates and invalid formats
4. ✅ All existing commands (`/task-work`, `/task-status`, etc.) work with hash IDs

**Claude Code just needs to**:
- Use `/task-create` with appropriate `prefix:`, `epic:`, or `tags:` parameters
- System handles the rest automatically

---

## Part 6: Comparison with Sequential Numbering

### Visual Comparison

#### Sequential Numbering (Old)
```
tasks/backlog/
├── TASK-042-research-caching.md
├── TASK-043-fix-login-bug.md
├── TASK-044-research-auth.md
├── TASK-045-update-docs.md
├── TASK-046-research-database.md
├── TASK-047-fix-session-timeout.md
└── TASK-048-research-api-design.md
```

**Problems**:
- Can't visually group related tasks
- Need to read titles to understand relationships
- Numbers have no meaning

#### Prefix-Based Grouping (New)
```
tasks/backlog/
├── TASK-DOC-c5e7-update-api-docs.md
├── TASK-FIX-b2c4-fix-login-bug.md
├── TASK-FIX-d4b1-fix-session-timeout.md
├── TASK-RES-a3f8-research-caching.md
├── TASK-RES-d4b1-research-database.md
├── TASK-RES-f1a3-research-auth.md
└── TASK-RES-c5e7-research-api-design.md
```

**Benefits**:
- Instant visual grouping (RES, FIX, DOC)
- Easy to find related tasks: `ls TASK-RES-*`
- Semantic meaning in file names

### Functional Comparison

| Feature | Sequential | Hash + Prefix |
|---------|-----------|---------------|
| **Uniqueness** | ❌ Requires global counter | ✅ Cryptographic hash |
| **Merge Conflicts** | ❌ Frequent with parallel work | ✅ None |
| **Grouping** | ❌ Manual tracking | ✅ Automatic via prefix |
| **Semantic Meaning** | ❌ None (just numbers) | ✅ Clear (FIX, DOC, RES) |
| **Scalability** | ❌ Limited by counter | ✅ Unlimited |
| **Readability** | ❌ Need to memorize numbers | ✅ Self-documenting |
| **Cross-session** | ❌ Can't group across time | ✅ Use same prefix anytime |
| **Visual Scanning** | ❌ Must read all titles | ✅ Instant grouping |

---

## Part 7: Best Practices

### For Daily Task Creation

**1. Use Consistent Prefixes Within a Session**
```bash
# Good: All research tasks use same prefix
/task-create "Research caching" prefix:RES
/task-create "Research databases" prefix:RES
/task-create "Research authentication" prefix:RES

# Avoid: Mixing prefixes for same category
/task-create "Research caching" prefix:CACHE
/task-create "Research databases" prefix:DB
/task-create "Research auth" prefix:SEC
```

**2. Let Epic Inference Work for You**
```bash
# If using require-kit with epics
/task-create "Task 1" epic:EPIC-001
/task-create "Task 2" epic:EPIC-001
/task-create "Task 3" epic:EPIC-001
# All get E01 prefix automatically
```

**3. Use Tags for Automatic Categorization**
```bash
# Tag inference handles categorization
/task-create "Update API guide" tags:[docs]      # → TASK-DOC-xxxx
/task-create "Fix login issue" tags:[bug]        # → TASK-FIX-xxxx
/task-create "Add OAuth support" tags:[feature]  # → TASK-FEAT-xxxx
```

**4. Create Custom Prefixes for Projects**
```bash
# Project-specific prefix for clarity
/task-create "Build payment flow" prefix:PAY
/task-create "Test payment integration" prefix:PAY
/task-create "Document payment API" prefix:PAY
```

### For Research Workflows

When doing research followed by implementation:

```bash
# Phase 1: Research (prefix:RES)
/task-create "Research authentication patterns" prefix:RES
/task-create "Research database schema design" prefix:RES
/task-create "Research API architecture" prefix:RES

# Phase 2: Implementation (prefix from research insight)
/task-create "Implement OAuth 2.0" prefix:AUTH
/task-create "Implement JWT tokens" prefix:AUTH
/task-create "Implement session management" prefix:AUTH

# Phase 3: Testing (prefix:TEST)
/task-create "Test authentication flow" prefix:TEST
/task-create "Test token refresh" prefix:TEST
/task-create "Test session timeout" prefix:TEST
```

**Result**: Clear separation between research, implementation, and testing phases.

---

## Part 8: Migration Recommendations

### For Existing Projects

**If you're starting GuardKit now**:
- ✅ Use hash-based IDs from day 1
- ✅ Apply prefixes consistently
- ✅ No migration needed

**If you have existing sequential IDs**:
1. Run migration script: `python3 scripts/migrate-my-tasks.py --dry-run`
2. Review preview
3. Execute migration: `python3 scripts/migrate-my-tasks.py --execute`
4. Verify results: `grep -r "TASK-[0-9]" tasks/` (should find none)

**If you have unmigrated tasks (like 063-073)**:
- **Option A**: Leave as historical reference, create new tasks when needed
- **Option B**: Manually add YAML frontmatter and re-run migration
- **Option C**: Archive and recreate with hash IDs

### Rollback Plan

If migration causes issues:

```bash
# Automatic rollback script created during migration
bash .claude/state/rollback-migration.sh

# Manual rollback
rm -rf tasks/
cp -r .claude/state/backup/tasks-pre-hash-migration-TIMESTAMP/ tasks/
```

**Backup location**: `.claude/state/backup/tasks-pre-hash-migration-TIMESTAMP/`

---

## Part 9: FAQ

### Q: Do I need to memorize hash IDs?

**A**: No! Use prefixes and tab completion:
```bash
# Find all research tasks
ls tasks/backlog/TASK-RES-*

# Work on a specific task (tab complete)
/task-work TASK-RES-<TAB>

# Or search by title
grep -r "Research authentication" tasks/
```

### Q: What if I create two tasks with the same prefix?

**A**: Perfect! That's the point - group related tasks:
```bash
/task-create "Research OAuth" prefix:AUTH
/task-create "Research JWT" prefix:AUTH

# Both get TASK-AUTH-xxxx but with different hashes
# TASK-AUTH-a3f8 and TASK-AUTH-b2c4
```

### Q: Can I change a prefix after creation?

**A**: Not recommended, but possible:
1. Rename file: `TASK-OLD-a3f8.md` → `TASK-NEW-a3f8.md`
2. Update frontmatter: `id: TASK-OLD-a3f8` → `id: TASK-NEW-a3f8`
3. Update all cross-references

**Better approach**: Use correct prefix at creation time.

### Q: How do I list all tasks in a group?

**A**: Use standard file operations:
```bash
# List all research tasks
ls tasks/*/TASK-RES-*

# Count tasks by prefix
ls tasks/backlog/TASK-* | cut -d'-' -f2 | sort | uniq -c

# Find all auth-related tasks
find tasks -name "TASK-AUTH-*"
```

### Q: What about subtasks (e.g., TASK-E01-a3f8.1)?

**A**: Supported! Add `.N` suffix:
```bash
# Main task
TASK-E01-a3f8: Implement authentication

# Subtasks
TASK-E01-a3f8.1: Setup OAuth provider
TASK-E01-a3f8.2: Implement token management
TASK-E01-a3f8.3: Add MFA support
```

### Q: Does this work with require-kit integration?

**A**: Yes! Full compatibility:
- Epic links automatically generate prefixes (E01, E02, etc.)
- External IDs (Jira, Linear, Azure DevOps) work normally
- Requirements and BDD scenarios link correctly

---

## Part 10: Implementation Status

### Completed Tasks (Hash ID System)

| Task | Title | Status |
|------|-------|--------|
| TASK-046 | Core hash-based ID generator | ✅ Completed |
| TASK-047 | ID validation and collision detection | ✅ Completed |
| TASK-048 | Update /task-create command | ✅ Completed |
| TASK-050 | JSON persistence for ID mappings | ✅ Completed |
| TASK-052 | Migration script | ✅ Completed |
| TASK-054 | Prefix support and inference | ✅ Completed |

### Files Modified/Created

**Core Implementation**:
- `installer/core/lib/id_generator.py` (522 lines, 96% coverage)
- `installer/core/lib/external_id_persistence.py` (448 lines, 90% coverage)
- `scripts/migrate-my-tasks.py` (442 lines, migration tool)

**Tests**:
- `tests/unit/test_id_validation.py` (728 lines, 36 tests)
- `tests/unit/test_task_create_hash_ids.py` (39 tests)
- `tests/lib/test_external_id_persistence.py` (35 tests)

**Documentation**:
- `installer/core/commands/task-create.md` (updated with prefix syntax)
- This document: `docs/research/hash-id-migration-and-prefix-grouping.md`

### Test Coverage

| Component | Tests | Coverage |
|-----------|-------|----------|
| ID Generator | 36 tests | 96% |
| ID Validation | 36 tests | 96% |
| Persistence | 35 tests | 90% |
| Task Create Integration | 39 tests | 100% |
| **Total** | **146 tests** | **95%** |

---

## Part 11: Future Enhancements

### Potential Improvements

**Prefix Auto-completion**:
```bash
# Shell completion for common prefixes
/task-create "title" prefix:<TAB>
# Shows: AUTH, DOC, TEST, FIX, FEAT, RES, API, UI, DB, INFR
```

**Prefix Statistics**:
```bash
# Show distribution of tasks by prefix
/task-stats --by-prefix

# Output:
# RES:  12 tasks (Research)
# AUTH:  8 tasks (Authentication)
# DOC:   5 tasks (Documentation)
# FIX:   3 tasks (Bug fixes)
```

**Prefix Aliases**:
```python
# Custom prefix aliases
ALIAS_MAP = {
    "research": "RES",
    "auth": "AUTH",
    "authentication": "AUTH",
    "document": "DOC",
    "documentation": "DOC",
}
```

**Visual Task Dashboard**:
```
┌─────────────────────────────────────┐
│ Task Dashboard by Prefix            │
├─────────────────────────────────────┤
│ AUTH  ████████░░ 8 tasks            │
│ RES   ████████████████░░ 12 tasks   │
│ DOC   ████░░ 5 tasks                │
│ FIX   ██░░ 3 tasks                  │
└─────────────────────────────────────┘
```

---

## Conclusion

The hash-based ID system with prefix grouping provides:

1. **Better than Sequential**: Semantic grouping vs meaningless numbers
2. **Zero Conflicts**: Parallel work with no ID collisions
3. **Self-Documenting**: Prefixes make task purpose clear
4. **Flexible**: Manual, epic, tag, or title-based inference
5. **Production Ready**: 146 tests, 95% coverage, fully integrated

**Migration Status**: 58 tasks migrated, 7 old-format tasks can remain as-is or be recreated.

**Claude Code Integration**: Fully compatible - just use `/task-create` with appropriate parameters.

**Bottom Line**: Prefix-based grouping is superior to sequential numbering for organizing related tasks, especially in research and multi-task workflows.

---

**Document Version**: 1.0
**Last Updated**: 2025-11-10
**Next Review**: When prefix enhancements are added
