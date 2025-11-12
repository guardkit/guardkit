# TASK-9038: Create /template-qa Command for Optional Customization

**Status**: backlog
**Priority**: medium
**Created**: 2025-11-12T01:00:00Z
**Updated**: 2025-11-12T01:00:00Z
**Tags**: #template-create #command #customization #qa
**Complexity**: 4/10 (Moderate - new command creation)
**Depends On**: None (independent)

---

## Description

Create a **new optional command** `/template-qa` that runs an interactive Q&A session to customize template generation. This is for advanced users who need to override defaults.

**Key Point**: This is **optional** - most users will just run `/template-create` with smart defaults.

---

## Use Cases

### 90% of Users (Don't Need This)
```bash
# Just works with smart defaults
cd ~/Projects/my-project
/template-create
```

### 10% of Users (Need Customization)
```bash
# Run Q&A for customization
/template-qa
# Saves config to .template-create-config.json

# Use saved config
/template-create --config .template-create-config.json
```

---

## Acceptance Criteria

### Core Functionality
- [ ] New command: `/template-qa`
- [ ] Interactive Q&A session (prompts for answers)
- [ ] Saves answers to `.template-create-config.json`
- [ ] Validates all answers before saving
- [ ] Clear, helpful prompts (not confusing)

### Resume Support
- [ ] `--resume` flag to edit existing config
- [ ] Loads current answers and allows editing
- [ ] Preserves unchanged answers

### Config File Format
- [ ] JSON format (human-readable)
- [ ] Schema validation
- [ ] Example config in documentation

---

## Implementation Plan

### Phase 1: Create Q&A Orchestrator (2 hours)
- Extract Q&A logic from `template_create_orchestrator.py`
- Create `template_qa_orchestrator.py`
- Implement config save/load

### Phase 2: Create Command File (1 hour)
- Create `/template-qa.md` command
- Document usage and examples
- Add to command index

### Phase 3: Testing (1 hour)
- Test Q&A flow
- Test config save/resume
- Test validation logic

---

## Timeline

- **Total:** 3-4 hours

---

## Related Tasks

- **TASK-9037:** Fix build artifact exclusion (independent)
- **TASK-9039:** Remove Q&A from /template-create (depends on this)
