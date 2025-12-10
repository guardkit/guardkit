# TASK-ENF3: Add Prominent Invocation Messages - Implementation Plan

**Documentation Level**: minimal
**Complexity**: 3/10
**Phases**: 2-4
**Estimated Duration**: 2-4 hours

---

## File Structure

| File | Type | Changes |
|------|------|---------|
| `installer/core/commands/task-work.md` | Modify | Add pre/post invocation messages to Phases 2, 2.5B, 3, 4, 5 |
| `.claude/task-plans/TASK-ENF3-implementation-plan.md` | Create | This plan (reference) |

---

## Implementation Phases

### Phase 2: Add Messages to Phase 2 (Implementation Planning)

**Location**: `installer/core/commands/task-work.md` line ~997

**Change**: Insert 2 message blocks around existing Phase 2 INVOKE

**Before INVOKE** (new):
```
**DISPLAY PRE-INVOCATION MESSAGE**:

═══════════════════════════════════════════════════════
🤖 INVOKING AGENT: {selected_planning_agent_from_table}
═══════════════════════════════════════════════════════
Phase: 2 (Implementation Planning)
Model: {selected_model_for_agent}
Stack: {detected_stack}
Specialization:
  - {capability_1}
  - {capability_2}
  - {capability_3}

Starting agent execution...
═══════════════════════════════════════════════════════
```

**After INVOKE / WAIT** (new):
```
**DISPLAY POST-COMPLETION MESSAGE**:

═══════════════════════════════════════════════════════
✅ AGENT COMPLETED: {selected_planning_agent_from_table}
═══════════════════════════════════════════════════════
Duration: {time_elapsed} seconds
Status: Implementation plan generated

Proceeding to Phase 2.5A (Pattern Suggestion)...
═══════════════════════════════════════════════════════
```

---

### Phase 3: Add Messages to Phase 2.5B (Architectural Review)

**Location**: `installer/core/commands/task-work.md` line ~1074

**Change**: Insert 2 message blocks around existing Phase 2.5B INVOKE

**Before INVOKE** (new):
```
**DISPLAY PRE-INVOCATION MESSAGE**:

═══════════════════════════════════════════════════════
🤖 INVOKING AGENT: architectural-reviewer
═══════════════════════════════════════════════════════
Phase: 2.5B (Architectural Review)
Model: Sonnet (deep reasoning for architecture assessment)
Stack: {detected_stack}
Specialization:
  - SOLID principles evaluation
  - DRY principle verification
  - YAGNI principle assessment

Starting agent execution...
═══════════════════════════════════════════════════════
```

**After INVOKE / WAIT** (new):
```
**DISPLAY POST-COMPLETION MESSAGE**:

═══════════════════════════════════════════════════════
✅ AGENT COMPLETED: architectural-reviewer
═══════════════════════════════════════════════════════
Duration: {time_elapsed} seconds
Architectural Review Score: {score}/100
Status: Architecture review complete

Proceeding to Phase 2.7 (Complexity Evaluation)...
═══════════════════════════════════════════════════════
```

---

### Phase 4: Add Messages to Phase 3 (Implementation)

**Location**: `installer/core/commands/task-work.md` line ~1788

**Change**: Insert 2 message blocks around existing Phase 3 INVOKE

**Before INVOKE** (new):
```
**DISPLAY PRE-INVOCATION MESSAGE**:

═══════════════════════════════════════════════════════
🤖 INVOKING AGENT: {selected_implementation_agent_from_table}
═══════════════════════════════════════════════════════
Phase: 3 (Implementation)
Model: Haiku (4-5x faster, 80% cheaper than Sonnet)
Stack: {detected_stack}
Specialization:
  - {capability_1}
  - {capability_2}
  - {capability_3}

Starting agent execution...
═══════════════════════════════════════════════════════
```

**After INVOKE / WAIT** (new):
```
**DISPLAY POST-COMPLETION MESSAGE**:

═══════════════════════════════════════════════════════
✅ AGENT COMPLETED: {selected_implementation_agent_from_table}
═══════════════════════════════════════════════════════
Duration: {time_elapsed} seconds
Files created/modified: {file_count}
{if file_count > 0: "Modified files:"}
{if file_count > 0: list up to 5 files}
Status: Implementation complete

Proceeding to Phase 4 (Testing)...
═══════════════════════════════════════════════════════
```

---

### Phase 5: Add Messages to Phase 4 (Testing)

**Location**: `installer/core/commands/task-work.md` line ~1803

**Change**: Insert 2 message blocks around existing Phase 4 INVOKE

**Before INVOKE** (new):
```
**DISPLAY PRE-INVOCATION MESSAGE**:

═══════════════════════════════════════════════════════
🤖 INVOKING AGENT: {selected_testing_agent_from_table}
═══════════════════════════════════════════════════════
Phase: 4 (Testing)
Model: {selected_model_for_agent}
Stack: {detected_stack}
Specialization:
  - Comprehensive test suite creation
  - {framework_specific_testing}
  - Coverage metrics validation

Starting agent execution...
═══════════════════════════════════════════════════════
```

**After INVOKE / WAIT** (new):
```
**DISPLAY POST-COMPLETION MESSAGE**:

═══════════════════════════════════════════════════════
✅ AGENT COMPLETED: {selected_testing_agent_from_table}
═══════════════════════════════════════════════════════
Duration: {time_elapsed} seconds
Test Results: {passed}/{total} passed
Coverage: {line_coverage}% line, {branch_coverage}% branch
Status: Tests {status}

{if status == "PASSED": "Proceeding to Phase 4.5 (Fix Loop)..."}
{if status == "FAILED": "Running Phase 4.5 (Auto-fix Loop)..."}
═══════════════════════════════════════════════════════
```

---

### Phase 6: Add Messages to Phase 5 (Code Review)

**Location**: `installer/core/commands/task-work.md` line ~1974

**Change**: Insert 2 message blocks around existing Phase 5 INVOKE

**Before INVOKE** (new):
```
**DISPLAY PRE-INVOCATION MESSAGE**:

═══════════════════════════════════════════════════════
🤖 INVOKING AGENT: code-reviewer
═══════════════════════════════════════════════════════
Phase: 5 (Code Review)
Model: Sonnet (quality-focused code assessment)
Stack: {detected_stack}
Specialization:
  - Code quality assessment
  - Pattern compliance verification
  - Best practices validation

Starting agent execution...
═══════════════════════════════════════════════════════
```

**After INVOKE / WAIT** (new):
```
**DISPLAY POST-COMPLETION MESSAGE**:

═══════════════════════════════════════════════════════
✅ AGENT COMPLETED: code-reviewer
═══════════════════════════════════════════════════════
Duration: {time_elapsed} seconds
Review Status: {APPROVED|APPROVED_WITH_NOTES|NEEDS_REVISION}
Issues Found: {count}
Status: Code review complete

Proceeding to Phase 5.5 (Plan Audit)...
═══════════════════════════════════════════════════════
```

---

## Message Templates

### Pre-Invocation Template
```
═══════════════════════════════════════════════════════
🤖 INVOKING AGENT: {agent_name}
═══════════════════════════════════════════════════════
Phase: {phase_number} ({phase_name})
Model: {model} ({model_justification})
Stack: {detected_stack}
Specialization:
  - {capability_1}
  - {capability_2}
  - {capability_3}

Starting agent execution...
═══════════════════════════════════════════════════════
```

**Variable Mapping**:
- `{agent_name}`: From Phase tables (e.g., `python-api-specialist`)
- `{phase_number}`: Phase being executed (2, 2.5B, 3, 4, 5)
- `{phase_name}`: Human-readable phase name
- `{model}`: Haiku, Sonnet, or Opus
- `{model_justification}`: Speed/cost or quality rationale
- `{detected_stack}`: Python, React, TypeScript, .NET, etc.
- `{capability_1/2/3}`: Top 3 capabilities from agent metadata

### Post-Completion Template
```
═══════════════════════════════════════════════════════
✅ AGENT COMPLETED: {agent_name}
═══════════════════════════════════════════════════════
Duration: {time_elapsed} seconds
{phase_specific_metrics}
Status: {status}

Proceeding to Phase {next_phase}...
═══════════════════════════════════════════════════════
```

**Phase-Specific Metrics**:
- Phase 2: "Implementation plan generated"
- Phase 2.5B: "Architectural Review Score: {score}/100"
- Phase 3: "Files created/modified: {count}" + file list
- Phase 4: "Test Results: {passed}/{total}" + coverage %
- Phase 5: "Review Status: {status}" + issues count

---

## Integration Points

### 1. Agent Name Resolution
- Use `{selected_planning_agent_from_table}` from Phase 2
- Use `architectural-reviewer` (hardcoded for Phase 2.5B)
- Use `{selected_implementation_agent_from_table}` from Phase 3
- Use `{selected_testing_agent_from_table}` from Phase 4
- Use `code-reviewer` (hardcoded for Phase 5)

### 2. Model Selection
- Phase 2: From planning table (typically Sonnet)
- Phase 2.5B: Sonnet (architecture decisions)
- Phase 3: From implementation table (typically Haiku)
- Phase 4: From testing table (typically Haiku)
- Phase 5: Sonnet (code quality assessment)

### 3. Capability Display
- Extract top 3 capabilities from agent metadata (frontmatter)
- Fallback to generic specialization if metadata missing
- Keep to 50 chars max per capability for formatting

### 4. Timing Calculation
- Record timestamp at invocation start
- Calculate elapsed time after WAIT completes
- Format as "{seconds} seconds" (e.g., "45 seconds")

### 5. File Tracking
- Count files created/modified during implementation
- List up to 5 most recent files
- Format: "  - {filename}" with relative paths from project root

### 6. Test Metrics
- Extract from test agent output (passed/total, coverage %)
- Display line coverage and branch coverage separately
- Format: "85% line, 72% branch"

---

## No Code Changes Required

**Important**: This is a documentation-only update. The messages are displayed as markdown text in the task-work.md command specification. These are **instructions for Claude to follow**, not Python code to execute.

**Rationale**:
- GuardKit commands are specifications, not executable scripts
- Claude reads the messages in task-work.md and displays them during execution
- No separate Python/helper module needed (unlike architectural review or testing)
- Messages are part of the orchestration workflow documentation

---

## Acceptance Criteria Mapping

| Requirement | Implementation | File | Location |
|-------------|-----------------|------|----------|
| R1: Pre-invocation messages | 5x message blocks | task-work.md | Phases 2, 2.5B, 3, 4, 5 |
| R2: Post-completion messages | 5x message blocks | task-work.md | Phases 2, 2.5B, 3, 4, 5 |
| R3: Model selection display | Template variables | task-work.md | All messages |
| R4: Specialization display | Capability templates | task-work.md | All messages |
| R5: Integration with all phases | 10x total messages | task-work.md | All 5 phases |

---

## Testing Strategy

**Validation** (manual during Phase 4.5 execution):
1. Run `/task-work TASK-TEST` on Python API task
2. Verify Phase 2 message displays with planning agent name
3. Verify Phase 2.5B message displays "architectural-reviewer"
4. Verify Phase 3 message displays implementation agent and Haiku model
5. Verify Phase 4 message displays test results and coverage
6. Verify Phase 5 message displays review status
7. Confirm all messages use consistent formatting with ═══ and emoji
8. Verify next phase announcements are correct

**Edge Cases**:
- No files modified (Phase 3 message shows "0 files")
- Test failures (Phase 4 message shows FAILED status)
- Missing capabilities (specialization shows generic message)
- Long file lists (Phase 3 shows "... and 5 more" if >5 files)

---

## Effort Estimate

| Phase | Task | Estimate |
|-------|------|----------|
| 2 | Phase 2 messages | 15 min |
| 3 | Phase 2.5B messages | 10 min |
| 4 | Phase 3 messages | 15 min |
| 5 | Phase 4 messages | 15 min |
| 6 | Phase 5 messages | 10 min |
| Test | Manual validation | 30-45 min |
| **Total** | | **1.5-2.5 hours** |

---

## Implementation Checklist

- [ ] Add Phase 2 pre-invocation message
- [ ] Add Phase 2 post-completion message
- [ ] Add Phase 2.5B pre-invocation message
- [ ] Add Phase 2.5B post-completion message
- [ ] Add Phase 3 pre-invocation message
- [ ] Add Phase 3 post-completion message
- [ ] Add Phase 4 pre-invocation message
- [ ] Add Phase 4 post-completion message
- [ ] Add Phase 5 pre-invocation message
- [ ] Add Phase 5 post-completion message
- [ ] Verify message formatting (═══, emoji, indentation)
- [ ] Validate variable naming consistency
- [ ] Test on actual task execution
- [ ] Update task status to IN_REVIEW

---

## Success Metrics

- Agent invocations immediately visible (before task runs)
- Model selection transparent (Haiku vs Sonnet rationale visible)
- Completion status clearly confirmed with timing info
- User can identify which agent handled which phase
- All 5 phases show consistent message format
- No code changes required (documentation-only)

