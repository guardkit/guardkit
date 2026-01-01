# Implementation Guide: Feature-Build CLI Native

## Wave Breakdown

### Wave 1: Core CLI Command (TASK-FBC-001)

**Tasks**: 1
**Parallel**: No (sequential)
**Estimated**: 8-12 hours

| Task | Title | Mode | Workspace |
|------|-------|------|-----------|
| TASK-FBC-001 | Add guardkit autobuild feature CLI command | task-work | fbc-wave1-1 |

**Deliverables**:
- `guardkit autobuild feature FEAT-XXX` command working
- Feature YAML loading and parsing
- Wave-based task execution
- Shared worktree per feature

**Exit Criteria**:
- Can execute all tasks in a feature
- No "CLI not available" fallback messages

---

### Wave 2: Reliability (TASK-FBC-002)

**Tasks**: 1
**Parallel**: No (depends on Wave 1)
**Estimated**: 4-6 hours

| Task | Title | Mode | Workspace |
|------|-------|------|-----------|
| TASK-FBC-002 | Add resume support for feature orchestration | task-work | fbc-wave2-1 |

**Deliverables**:
- State persistence in feature YAML
- `--resume` flag implementation
- `--fresh` flag for clean start
- Interrupted task recovery

**Exit Criteria**:
- Can resume interrupted feature builds
- State correctly persisted across restarts

---

### Wave 3: Polish (TASK-FBC-003, TASK-FBC-004)

**Tasks**: 2
**Parallel**: Yes (independent)
**Estimated**: 3-5 hours total

| Task | Title | Mode | Workspace |
|------|-------|------|-----------|
| TASK-FBC-003 | Enhance Player agent test execution | direct | fbc-wave3-1 |
| TASK-FBC-004 | Improve progress display for feature mode | direct | fbc-wave3-2 |

**Deliverables**:
- Player agents run tests before reporting
- Clear wave/task progress display
- Turn-by-turn status updates

**Exit Criteria**:
- Player reports include test results
- Progress display is informative and clear

---

## Execution Commands

### Wave 1

```bash
# Single task, use task-work directly
/task-work TASK-FBC-001
```

### Wave 2

```bash
# After Wave 1 complete
/task-work TASK-FBC-002
```

### Wave 3 (Parallel with Conductor)

```bash
# In Conductor workspace fbc-wave3-1
/task-work TASK-FBC-003

# In Conductor workspace fbc-wave3-2
/task-work TASK-FBC-004
```

Or execute sequentially:

```bash
/task-work TASK-FBC-003
/task-work TASK-FBC-004
```

---

## Total Estimates

| Wave | Tasks | Hours | Parallel |
|------|-------|-------|----------|
| 1 | 1 | 8-12h | No |
| 2 | 1 | 4-6h | No |
| 3 | 2 | 3-5h | Yes |
| **Total** | **4** | **15-23h** | |

---

## Success Metrics

After completion:

1. **No Fallback Messages**
   ```bash
   guardkit autobuild feature FEAT-XXX 2>&1 | grep -i "fallback\|not available"
   # Should return nothing
   ```

2. **Resume Works**
   ```bash
   # Interrupt mid-execution, then:
   guardkit autobuild feature FEAT-XXX --resume
   # Should continue from last completed task
   ```

3. **Progress Clear**
   - Wave headers visible
   - Task status updates in real-time
   - Final summary shows all results

---

## Source

Generated from TASK-REV-FB01 architectural review.
Report: `.claude/reviews/TASK-REV-FB01-cli-fallback-review-report.md`
