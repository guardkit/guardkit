# TASK-9037: Fix Build Artifact Exclusion in Codebase Analyzer

**Status**: backlog
**Priority**: critical
**Created**: 2025-11-12T00:00:00Z
**Updated**: 2025-11-12T01:00:00Z
**Tags**: #template-create #bugfix #codebase-analyzer #build-artifacts
**Complexity**: 3/10 (Simple - focused bug fix)

---

## Description

The codebase analyzer counts **all files** including build artifacts, causing incorrect language detection across **all technology stacks**. This is a universal bug affecting Java, C#, Python, JavaScript, and all other languages.

**Root Cause**: No build artifact exclusion in file counting logic.

---

## Current Behavior (BROKEN - All Stacks)

### Example 1: .NET MAUI Project
```bash
cd ~/Projects/DeCUK.Mobile.MyDrive
/template-create --validate --skip-qa
```

**Result:**
- ❌ Counts: 606 `.java` files (in `obj/Debug/` - auto-generated Android bindings)
- ❌ Counts: 373 `.cs` files (actual source code)
- ❌ Detects as: **Java** project (wrong!)
- ❌ Should be: **C#** project

---

## Expected Behavior (FIXED - All Stacks)

### Universal Exclusion Patterns

**Default exclusions (applies to ALL languages):**
- .NET: `obj/`, `bin/`, `*.user`, `*.suo`
- Java: `target/`, `*.class`, `*.jar`, `*.war`
- Node.js: `node_modules/`, lock files
- Python: `__pycache__/`, `*.pyc`, venvs
- Go: `vendor/`
- Rust: `target/`, `Cargo.lock`
- Generic: `build/`, `dist/`, `.git/`, `.vscode/`, `.idea/`

### After Fix

```bash
cd ~/Projects/DeCUK.Mobile.MyDrive
/template-create --validate --skip-qa

# Excludes: obj/, bin/
# Counts: 373 .cs files (source only)
# Detects: C# project ✅
```

---

## Acceptance Criteria

- [ ] Default exclusion patterns implemented (all stacks)
- [ ] File counting respects exclusions
- [ ] Language detection uses **only source files**
- [ ] Works with **any technology stack**
- [ ] Display excluded file count in output
- [ ] Test on .NET, Java, Node.js, Python projects

---

## Implementation Plan

### Phase 1: Create Exclusions Module (30 min)
- Create `installer/global/lib/template_creation/exclusions.py`
- Define `DEFAULT_EXCLUSIONS` list
- Implement `should_exclude_path()` function
- Implement `get_source_files()` function

### Phase 2: Integrate into Analyzer (30 min)
- Update `ai_analyzer.py` to use exclusions
- Replace `rglob("*")` with `get_source_files()`
- Test language detection accuracy

### Phase 3: Add Tests (1 hour)
- Unit tests for exclusion logic
- Test .NET, Node.js, Python exclusions
- Integration test on real .NET MAUI project

---

## Timeline

- **Total:** 2-3 hours (simple, focused bug fix)

---

## Related Tasks

- **TASK-9038:** Create /template-qa command
- **TASK-9039:** Remove Q&A from /template-create
- **TASK-9040:** Investigate template-create regression
