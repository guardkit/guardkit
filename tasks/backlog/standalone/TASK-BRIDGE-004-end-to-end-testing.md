# TASK-BRIDGE-004: End-to-End Bridge Testing and Validation

**Status**: backlog
**Priority**: high
**Estimated Duration**: 1 hour
**Tags**: #bridge #ai-integration #testing #validation

---

## Description

Perform comprehensive end-to-end testing of the Python↔Claude agent bridge with real codebases, validate that agent generation now works correctly, and verify that the user's original issue (zero agents created) is resolved.

**Part of**: Python↔Claude Agent Invocation Bridge (Critical Feature)
**See**: `docs/proposals/python-claude-bridge-technical-spec.md`

**Depends on**:
- TASK-BRIDGE-001 (Agent Bridge Infrastructure)
- TASK-BRIDGE-002 (Orchestrator Integration)
- TASK-BRIDGE-003 (Command Integration)

---

## Context

This task validates the complete bridge implementation by testing with the user's actual `dotnet-maui-clean-mvvm` codebase that originally revealed the bug (zero agents created). Success means 7-9 agents are now generated.

---

## Acceptance Criteria

### Critical Success Metric
- [ ] **User's dotnet-maui-clean-mvvm codebase generates 7-9 agents** (vs 0 before)

### Functional Testing
- [ ] Bridge successfully requests agent invocation
- [ ] Claude invokes architectural-reviewer agent
- [ ] Agent returns valid JSON response
- [ ] Orchestrator parses response and creates agents
- [ ] All agents written to `~/.agentecflow/templates/{name}/agents/`
- [ ] Template creation completes successfully
- [ ] Temporary files cleaned up

### Error Handling
- [ ] Graceful fallback if agent invocation fails
- [ ] Graceful fallback if agent returns invalid JSON
- [ ] Graceful fallback if agent times out
- [ ] Hard-coded detection still works as fallback

### Performance
- [ ] Checkpoint-resume overhead < 1 second
- [ ] Total template creation time acceptable (~3-8 minutes)
- [ ] No noticeable performance degradation

### Documentation
- [ ] Success metrics documented
- [ ] Before/after comparison recorded
- [ ] Any issues or bugs logged

---

## Test Plan

### Test 1: User's Dotnet MAUI Codebase (PRIMARY)

**Objective**: Validate that the original bug is fixed

**Steps**:
1. Navigate to user's dotnet-maui-clean-mvvm codebase
2. Run `/template-create`
3. Observe checkpoint-resume flow:
   - Phase 6 triggers exit code 42
   - Agent request written
   - architectural-reviewer invoked
   - Agent response written
   - Orchestrator resumes
   - Agents generated
4. Verify agents directory:
   ```bash
   ls -la ~/.agentecflow/templates/dotnet-maui-clean-mvvm/agents/
   ```
5. Count agents (should be 7-9)
6. Inspect agent files for quality

**Expected Results**:
- ✅ 7-9 agent files created
- ✅ Agents include: mvvm-viewmodel-specialist, navigation-specialist, domain-operations-specialist, repository-pattern-specialist, etc.
- ✅ Each agent has proper markdown format
- ✅ Agent definitions reference correct example files

**Regression Check**:
- Before: 0 agents
- After: 7-9 agents
- **Improvement: ∞ (from 0 to 7-9)**

---

### Test 2: React TypeScript Codebase

**Objective**: Validate bridge works for different technology stack

**Steps**:
1. Use a React TypeScript codebase
2. Run `/template-create`
3. Verify agents generated

**Expected Results**:
- ✅ 5-7 agents created
- ✅ Agents include: react-component-specialist, hooks-specialist, api-integration-specialist, etc.

---

### Test 3: FastAPI Python Codebase

**Objective**: Validate bridge works for Python stack

**Steps**:
1. Use a FastAPI Python codebase
2. Run `/template-create`
3. Verify agents generated

**Expected Results**:
- ✅ 6-8 agents created
- ✅ Agents include: fastapi-endpoint-specialist, domain-service-specialist, repository-specialist, etc.

---

### Test 4: Error Scenarios

**Objective**: Validate error handling and fallback

#### Test 4a: Agent Timeout
1. Modify timeout to 1 second
2. Run `/template-create` on large codebase
3. Verify fallback to hard-coded detection
4. Verify template still created (with fewer agents)

#### Test 4b: Agent Returns Invalid JSON
1. Mock agent to return non-JSON response
2. Run `/template-create`
3. Verify fallback to hard-coded detection

#### Test 4c: Agent Request File Corrupted
1. Manually corrupt `.agent-request.json` during execution
2. Verify error handling

---

### Test 5: Performance Testing

**Objective**: Validate no significant performance degradation

1. Measure total execution time for template creation
2. Measure checkpoint-resume overhead
3. Compare with estimated overhead (~250-620ms)

**Expected Results**:
- ✅ Overhead < 1 second
- ✅ Total time: 3-8 minutes (same as before)

---

### Test 6: Multiple Agent Invocations

**Objective**: Validate support for multiple agent requests

**Note**: Currently only Phase 6 uses agents, but architecture supports multiple phases needing agents.

1. (Future) If multiple phases need agents, verify loop handles multiple iterations

---

## Test Execution Checklist

**Before Testing**:
- [ ] All TASK-BRIDGE-001, 002, 003 complete
- [ ] Code merged to main branch
- [ ] `install.sh` run to deploy changes
- [ ] User's codebase available

**During Testing**:
- [ ] Record all outputs
- [ ] Capture any errors or warnings
- [ ] Note performance metrics
- [ ] Screenshot agent files

**After Testing**:
- [ ] Document results
- [ ] Update success metrics
- [ ] Log any issues
- [ ] Verify cleanup

---

## Success Criteria Validation

Record actual results in this table:

| Metric | Before (TASK-TMPL-4E89) | After (Bridge Complete) | Target | Status |
|--------|------------------------|------------------------|--------|--------|
| Agents created (dotnet-maui) | 0 | **?** | 7-9 | ⏳ |
| Detection method | Hard-coded | **?** | AI-powered | ⏳ |
| Detection coverage | 14-30% | **?** | 78-100% | ⏳ |
| Agent quality | N/A | **?** | High | ⏳ |
| Fallback works | N/A | **?** | Yes | ⏳ |
| Checkpoint overhead | N/A | **?** | <1s | ⏳ |
| Total execution time | ~5min | **?** | 3-8min | ⏳ |

---

## Issue Reporting

If any issues found during testing, create new tasks with this template:

```markdown
## Bug: [Description]

**Severity**: Critical | High | Medium | Low
**Component**: Bridge Infrastructure | Orchestrator | Command
**Found During**: End-to-end testing (TASK-BRIDGE-004)

**Steps to Reproduce**:
1. ...

**Expected Behavior**:
...

**Actual Behavior**:
...

**Workaround**:
...

**Fix Priority**: Immediate | High | Normal
```

---

## Documentation Updates

After successful testing, update:

- [ ] `docs/proposals/python-claude-bridge-architecture.md` - Add "IMPLEMENTED" status
- [ ] `docs/proposals/python-claude-bridge-technical-spec.md` - Add test results
- [ ] `CLAUDE.md` - Document that AI-powered agent generation is live
- [ ] User communication - Inform user that issue is resolved

---

## Definition of Done

- [ ] All test scenarios executed
- [ ] Success criteria validated
- [ ] **User's codebase generates 7-9 agents** (PRIMARY SUCCESS METRIC)
- [ ] Error handling verified
- [ ] Performance acceptable
- [ ] All issues logged
- [ ] Documentation updated
- [ ] User notified of fix

---

## Related Tasks

- TASK-BRIDGE-001: Agent Bridge Infrastructure (PREREQUISITE)
- TASK-BRIDGE-002: Orchestrator Integration (PREREQUISITE)
- TASK-BRIDGE-003: Command Integration (PREREQUISITE)
- TASK-TMPL-4E89: Original implementation (context)

---

## References

- [Architecture Proposal](../../docs/proposals/python-claude-bridge-architecture.md)
- [Technical Specification](../../docs/proposals/python-claude-bridge-technical-spec.md)
- [User Bug Report](../../tasks/in_review/TASK-TMPL-4E89-fix-ai-agent-generation-in-template-create.md)
