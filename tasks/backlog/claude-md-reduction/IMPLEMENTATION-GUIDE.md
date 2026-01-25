# Implementation Guide: CLAUDE.md Reduction

## Execution Strategy

### Wave 1 (Parallel - Can run simultaneously)

| Task | Action | Est. Time |
|------|--------|-----------|
| TASK-CMD1-001 | Create rules/autobuild.md | 15 min |
| TASK-CMD1-002 | Create rules/hash-based-ids.md | 10 min |
| TASK-CMD1-003 | Consolidate .claude/CLAUDE.md | 10 min |

**Conductor Execution**:
```bash
# Start 3 parallel workspaces
conductor spawn claude-md-reduction-wave1-1
conductor spawn claude-md-reduction-wave1-2
conductor spawn claude-md-reduction-wave1-3
```

### Wave 2 (Parallel - After Wave 1 completes)

| Task | Action | Est. Time |
|------|--------|-----------|
| TASK-CMD1-004 | Condense workflow sections | 15 min |
| TASK-CMD1-005 | Condense FAQ and examples | 10 min |

**Conductor Execution**:
```bash
conductor spawn claude-md-reduction-wave2-1
conductor spawn claude-md-reduction-wave2-2
```

### Wave 3 (Sequential - Final validation)

| Task | Action | Est. Time |
|------|--------|-----------|
| TASK-CMD1-006 | Validate character count | 20 min |

**Standard Execution**:
```bash
/task-work TASK-CMD1-006
```

## Expected Character Savings by Wave

| Wave | Savings | Cumulative |
|------|---------|------------|
| Wave 1 | ~17,200 chars | 17,200 |
| Wave 2 | ~7,500 chars | 24,700 |
| **Total** | **24,700 chars** | - |

## Post-Implementation State

### Before
- `/CLAUDE.md`: 55,546 chars
- `/.claude/CLAUDE.md`: 8,417 chars
- **Total**: 63,963 chars

### After
- `/CLAUDE.md`: ~30,850 chars (-44%)
- `/.claude/CLAUDE.md`: ~4,900 chars (-42%)
- **Total**: ~35,750 chars (**below 40k**)

## New Files Created

```
.claude/rules/
├── autobuild.md         (NEW - ~12,000 chars)
├── hash-based-ids.md    (NEW - ~3,500 chars)
├── clarifying-questions.md  (existing)
├── python-library.md        (existing)
├── task-workflow.md         (existing)
└── testing.md               (existing)
```

## Verification Checklist

- [ ] Root CLAUDE.md < 32,000 chars
- [ ] .claude/CLAUDE.md < 5,000 chars
- [ ] Total < 40,000 chars
- [ ] No broken links
- [ ] Performance warning gone
- [ ] `/task-status` works
- [ ] Rules load conditionally
