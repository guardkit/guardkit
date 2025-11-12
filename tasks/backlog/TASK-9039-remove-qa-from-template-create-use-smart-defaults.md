# TASK-9039: Remove Q&A from /template-create, Use Smart Defaults

**Status**: backlog
**Priority**: high
**Created**: 2025-11-12T01:00:00Z
**Updated**: 2025-11-12T01:00:00Z
**Tags**: #template-create #refactor #smart-defaults #non-interactive
**Complexity**: 5/10 (Moderate - refactoring existing command)
**Depends On**: TASK-9038 (optional Q&A command must exist first)

---

## Description

Refactor `/template-create` to work **non-interactively** using smart defaults. Remove the blocking Q&A session that hangs in CI/CD environments.

**Key Change**: No more interactive prompts by default - just smart detection.

---

## Current Behavior (BROKEN)

```bash
/template-create --skip-qa

# Hangs waiting for input
# Makes wrong assumptions when --skip-qa used
# Doesn't work in CI/CD
```

---

## Expected Behavior (FIXED)

```bash
/template-create

# No prompts - just works ✅
# Smart detection:
#   - Detects language from project files
#   - Excludes build artifacts (TASK-9037)
#   - Works in CI/CD
```

---

## Acceptance Criteria

### Core Functionality
- [ ] No interactive prompts by default
- [ ] Smart detection of language/framework
- [ ] Reads config file if provided (`--config`)
- [ ] Works in CI/CD (non-interactive)
- [ ] Backward compatible (`--skip-qa` deprecated but works)

### Smart Defaults
- [ ] Detect language from project files (`.csproj`, `package.json`, `requirements.txt`, etc.)
- [ ] Detect frameworks from dependencies
- [ ] Use default exclusions from TASK-9037
- [ ] Infer common architecture patterns

### Config File Support
- [ ] `--config <file>` flag to use saved config
- [ ] Priority: config file > smart defaults
- [ ] Clear error if config file invalid

---

## Implementation Plan

### Phase 1: Add Smart Detection (2 hours)
- Implement language detection from project files
- Implement framework detection from dependencies
- Test detection accuracy

### Phase 2: Refactor Orchestrator (2 hours)
- Remove blocking Q&A calls
- Add `--config` flag support
- Fallback to smart defaults if no config

### Phase 3: Testing (1 hour)
- Test without config (smart defaults)
- Test with config file
- Test in CI/CD environment

---

## Timeline

- **Total:** 4-5 hours

---

## Related Tasks

- **TASK-9037:** Build artifact exclusion (prerequisite)
- **TASK-9038:** /template-qa command (prerequisite)
- **TASK-9040:** Investigate regression
