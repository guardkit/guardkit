# Proposal: Hybrid Template Creation Workflow

**Status**: Proposed
**Related Review**: [template-create-pivot-review.md](../reviews/template-create-pivot-review.md)
**Date**: 2025-11-20
**Decision**: MODIFY (Hybrid Approach)

---

## Problem Statement

The current `/template-create` implementation has **complexity issues** (agent bridge pattern, 2004 LOC orchestrator) but **works well** (4/4 completed tasks, 9+/10 quality, 88-94% time savings). The proposed pivot to a pure task-based workflow would **lose automation value** without solving the root complexity problem.

**Root Causes**:
1. ❌ Agent bridge pattern (exit code 42, checkpoint-resume) is over-engineered
2. ❌ Orchestrator has YAGNI violations (5/10 score)
3. ❌ 2004 LOC with high cyclomatic complexity
4. ✅ But generators work well (ManifestGenerator, TemplateGenerator, etc.)
5. ✅ And automation is valuable (1 command → complete template)

---

## Solution Overview

**Hybrid approach** that:
1. ✅ **Simplifies orchestrator** (remove agent bridge, reduce LOC 30-40%)
2. ✅ **Keeps automation** (`/template-create` for fast workflow)
3. ✅ **Adds guided option** (`/create-template-task` for oversight)

### Two Workflows

**Automation Mode** (default):
```bash
/template-create --validate --output-location=repo
# → 8 phases execute automatically
# → Complete template in <1 day
# → Quality: 9+/10
```

**Guided Mode** (optional):
```bash
/create-template-task "my-template" --source /path/to/codebase
# → Creates task with proven workflow steps
# → User runs: /task-work TASK-XXX
# → Quality gates from /task-work (Phase 2.5, 4.5, 5, 5.5)
# → Human oversight at each phase
```

---

## Architecture

### Simplified Orchestrator

**Current Architecture** (2004 LOC):
```
TemplateCreateOrchestrator
├── Phase 1-9.5 coordination
├── Agent bridge (exit code 42)
│   ├── .agent-request.json
│   ├── .agent-response.json
│   └── .template-create-state.json
├── Checkpoint-resume logic
│   ├── _run_from_phase_5()
│   ├── _run_from_phase_7()
│   └── _resume_from_checkpoint()
├── Serialization (6 methods)
│   ├── _serialize_analysis()
│   ├── _serialize_manifest()
│   ├── _serialize_settings()
│   ├── _serialize_templates()
│   ├── _serialize_agents()
│   └── _serialize_value() (cycle detection)
└── State persistence (StateManager)
```

**Proposed Architecture** (<1200 LOC):
```
TemplateCreateOrchestrator
├── Phase 1-9.5 coordination (streamlined)
├── Direct agent invocation
│   └── await task(subagent_type="...", prompt="...")
├── NO checkpoint-resume
├── NO state files
├── Pydantic serialization
│   └── model_dump(mode='json')
└── Linear execution (no resume branches)
```

**Complexity Reduction**:
- ❌ Remove agent bridge pattern (~400 LOC)
- ❌ Remove checkpoint-resume logic (~300 LOC)
- ❌ Remove custom serialization (~300 LOC)
- ❌ Remove infinite loop protection (~50 LOC)
- ✅ Keep phase coordination (~800 LOC)
- ✅ Keep error handling (~150 LOC)
- **Total**: 2004 LOC → <1200 LOC (40% reduction)

### New Command: `/create-template-task`

**Purpose**: Generate task for guided template creation

**Implementation**:
- Location: `installer/global/commands/create-template-task.md`
- Python: `installer/global/commands/lib/create_template_task.py`
- ~200 LOC (simple task generator)

**Usage**:
```bash
/create-template-task "react-admin" --source /path/to/codebase
```

**Generated Task** (markdown):
```markdown
# TASK-{ID}: Create Template from {Source}

## Objectives
Create template from {source} that achieves 9+/10 quality score.

## Workflow
1. Analyze source codebase
   - Read key files (components, hooks, API)
   - Identify patterns

2. Run /template-create
   - Execute: /template-create --validate --output-location=repo
   - Wait for completion

3. Run /template-validate
   - Execute: /template-validate installer/global/templates/{name}
   - Review quality report

4. IF score <9/10:
   - Analyze validation findings
   - Make improvements (Edit/Write tools)
   - Re-run /template-create
   - Re-validate
   - LOOP until 9+/10

5. WHEN score ≥9/10:
   - Complete task

## Acceptance Criteria
- Template validation score ≥9/10
- Zero critical issues
- All 16 sections score ≥8/10
```

**Integration with `/task-work`**:
- Task delegates to `/template-create` (automation)
- Quality gates from `/task-work` (Phase 2.5 architectural review, Phase 4.5 test enforcement)
- User has oversight at each iteration

---

## Implementation Plan

### Phase 1: Simplify Orchestrator (1-2 weeks)

**Week 1: Core Simplification**

**Task 1.1: Remove Agent Bridge Pattern** (3 days)
- Files: `template_create_orchestrator.py`, `template-create.md`
- Changes:
  - Replace `AgentBridgeInvoker` with direct `await task(...)` calls
  - Remove exit code 42 logic from command spec
  - Delete `.agent-request.json` / `.agent-response.json` handling
  - Remove `NEED_AGENT` exit code from orchestrator
  - Update `AIAgentGenerator` to use direct invocation

```python
# Before (agent bridge):
invoker = AgentBridgeInvoker(phase=WorkflowPhase.PHASE_6)
agents = generator.generate(analysis)  # May exit with code 42

# After (direct invocation):
agents = await generator.generate_async(analysis)  # Direct Task tool call
```

**Task 1.2: Remove Checkpoint-Resume Logic** (2 days)
- Files: `template_create_orchestrator.py`, `installer/global/lib/agent_bridge/state_manager.py`
- Changes:
  - Remove `_run_from_phase_5()`, `_run_from_phase_7()` methods
  - Remove `_resume_from_checkpoint()` method
  - Remove state file handling (`.template-create-state.json`)
  - Single execution path (no branching on phase number)
  - Remove `StateManager` usage

**Task 1.3: Simplify Serialization** (2 days)
- Files: `template_create_orchestrator.py`
- Changes:
  - Use Pydantic's `model_dump(mode='json')` for `CodebaseAnalysis`
  - Remove `_serialize_value()` method (300 lines with cycle detection)
  - Remove `_serialize_analysis/manifest/settings/templates/agents()` methods
  - Remove `_deserialize_*()` methods (no longer needed)
  - Direct JSON serialization for manifest/settings (already have `.to_dict()`)

**Task 1.4: Remove Infinite Loop Protection** (1 day)
- Files: `template-create.md` (command spec)
- Changes:
  - Remove `--max-iterations` flag
  - Remove iteration counter in orchestrator
  - Remove loop check logic
  - Rely on direct invocation (no loops possible)

**Week 2: Testing and Refinement**

**Task 1.5: Unit Tests** (2 days)
- Files: `tests/unit/test_template_create_orchestrator.py` (new)
- Tests:
  - Phase 1-9 execution
  - Direct agent invocation
  - Error handling per phase
  - Validation integration
  - Dry-run mode

**Task 1.6: Integration Tests** (2 days)
- Files: `tests/integration/test_template_create_workflow.py` (new)
- Tests:
  - Full workflow execution (Phase 1-9.5)
  - Regenerate existing templates (react-typescript, fastapi-python, nextjs-fullstack, react-fastapi-monorepo)
  - Verify quality scores ≥9/10
  - Performance testing (time to complete)

**Task 1.7: Refactor Cleanup** (1 day)
- Consolidate phase methods
- Extract common patterns
- Improve error messages
- Update documentation strings

**Success Criteria**:
- ✅ Orchestrator <1200 LOC (down from 2004)
- ✅ No exit code 42
- ✅ No state files
- ✅ All tests pass (80%+ coverage)
- ✅ Existing templates regenerate with same quality (9+/10)

### Phase 2: Add Guided Workflow (1 week)

**Task 2.1: Create `/create-template-task` Command** (3 days)
- Files:
  - `installer/global/commands/create-template-task.md` (command spec)
  - `installer/global/commands/lib/create_template_task.py` (implementation)
- Features:
  - Parse arguments (`--source`, `--name`, `--priority`)
  - Generate task markdown from template
  - Create task file in `tasks/backlog/`
  - Print next steps to user

```python
def create_template_task(
    template_name: str,
    source_path: Path,
    priority: str = "medium"
) -> Path:
    """
    Create task for guided template creation.

    Args:
        template_name: Template name (e.g., "react-admin")
        source_path: Path to source codebase
        priority: Task priority (high/medium/low)

    Returns:
        Path to created task file
    """
    # Generate task ID
    task_id = generate_task_id("TASK-TMPL")

    # Render task template
    task_content = render_task_template(
        task_id=task_id,
        template_name=template_name,
        source_path=source_path,
        priority=priority
    )

    # Write task file
    task_path = Path(f"tasks/backlog/{task_id}-create-{template_name}-template.md")
    task_path.write_text(task_content)

    return task_path
```

**Task 2.2: Task Template Content** (1 day)
- Files: `installer/global/commands/lib/task_templates/template_creation.md`
- Based on: TASK-057, TASK-058, TASK-059, TASK-062 (proven workflow)
- Sections:
  - Objectives
  - Context (source repository)
  - Workflow steps (1-5)
  - Acceptance criteria
  - Success metrics

**Task 2.3: Integration with `/task-work`** (2 days)
- Verify task works with `/task-work` command
- Quality gates applied (Phase 2.5, 4.5, 5, 5.5)
- Test iteration loop (score <9/10 → refine → re-validate)
- Ensure progress tracking works (task states)

**Task 2.4: Documentation** (1 day)
- Update CLAUDE.md with both workflows
- Add examples for automation and guided modes
- Decision guide: When to use each
- FAQ section

**Success Criteria**:
- ✅ `/create-template-task` command works
- ✅ Generated task replicates TASK-057 workflow
- ✅ Task integrates with `/task-work` quality gates
- ✅ Documentation explains both workflows clearly

### Phase 3: Testing and Rollout (1 week)

**Task 3.1: Comprehensive Integration Testing** (3 days)
- Test automation mode: `/template-create`
- Test guided mode: `/create-template-task` → `/task-work`
- Verify quality outcomes (9+/10 for both)
- Performance comparison (time to complete)
- Error scenario testing (missing files, invalid inputs, etc.)

**Task 3.2: Migration Testing** (1 day)
- Verify existing users unaffected
- Test backward compatibility (`--validate`, `--dry-run`, etc.)
- Ensure no breaking changes
- Test with existing templates

**Task 3.3: Documentation** (2 days)
- Migration guide for existing users
- Comparison table: Automation vs. Guided
- Update all template creation guides
- Add troubleshooting section
- FAQ expansion

**Task 3.4: Rollout** (1 day)
- Release notes
- Community announcement
- Monitor for issues
- Gather feedback

**Success Criteria**:
- ✅ All integration tests pass
- ✅ Documentation complete and clear
- ✅ No breaking changes for existing users
- ✅ Both workflows achieve 9+/10 quality
- ✅ User feedback positive

**Total Timeline**: 3-4 weeks

---

## Success Criteria

### Functional Requirements
- ✅ `/template-create` still works (automation mode)
- ✅ Orchestrator simplified (<1200 LOC, no agent bridge)
- ✅ `/create-template-task` works (guided mode)
- ✅ Both workflows achieve 9+/10 quality
- ✅ No breaking changes for existing users

### Quality Requirements
- ✅ Test coverage ≥80%
- ✅ All 4 existing templates regenerate successfully
- ✅ Code complexity reduced (cyclomatic complexity <10 per method)
- ✅ Documentation complete (both workflows explained)

### Performance Requirements
- ✅ Automation mode: Time to complete ≤1 day (unchanged)
- ✅ Guided mode: Time to complete ≤1.5 days (includes human oversight)
- ✅ No performance regression from agent bridge removal

### Usability Requirements
- ✅ Users understand when to use each workflow
- ✅ Error messages are clear and actionable
- ✅ Progress indicators work in both modes
- ✅ Debugging is simpler (no state files)

---

## Comparison: Automation vs. Guided Modes

| Aspect | Automation Mode | Guided Mode |
|--------|----------------|-------------|
| **Command** | `/template-create` | `/create-template-task` → `/task-work` |
| **Execution** | Fully automatic (8 phases) | Manual phase execution |
| **Oversight** | None (trust AI) | Human approval at each phase |
| **Time** | ~1 hour to 1 day | ~1-1.5 days (includes review) |
| **Quality** | 9+/10 (with `--validate`) | 9+/10 (with `/task-work` gates) |
| **Iteration** | Re-run command if needed | Built into workflow |
| **Use Case** | Simple templates, fast turnaround | Complex templates, high risk, learning |
| **Transparency** | Progress indicators | Task markdown, phase plans |
| **Debugging** | Direct execution (no state files) | Transparent state (task files) |

### When to Use Each

**Use Automation Mode** (`/template-create`):
- ✅ Simple template creation (familiar stack)
- ✅ Fast turnaround needed (<1 day)
- ✅ Trust AI to handle all phases
- ✅ Source codebase is well-structured
- ✅ Low risk (non-critical template)

**Use Guided Mode** (`/create-template-task`):
- ✅ Complex template (new stack, unusual patterns)
- ✅ High risk (production-critical template)
- ✅ Learning (want to understand each phase)
- ✅ Team collaboration (architect designs, dev implements)
- ✅ Need approval checkpoints

---

## Risks and Mitigation

### Risk 1: Agent Bridge Removal Breaks Existing Workflows
**Likelihood**: Low
**Impact**: High
**Mitigation**:
- Comprehensive testing with existing templates
- Rollback plan (keep agent bridge in separate branch)
- Gradual rollout (beta flag for simplified orchestrator)

### Risk 2: Direct Agent Invocation Timeouts
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**:
- Increase Task tool timeout (10 min → 30 min for template creation)
- Add retry logic for transient failures
- Provide fallback to synchronous execution

### Risk 3: Users Confused by Two Workflows
**Likelihood**: Medium
**Impact**: Low
**Mitigation**:
- Clear documentation with decision tree
- Examples for both workflows in CLAUDE.md
- FAQ section addressing common questions
- Default to automation (simpler)

### Risk 4: Migration Effort Exceeds Estimate
**Likelihood**: Low
**Impact**: Medium
**Mitigation**:
- Phased approach (can stop after Phase 1 if needed)
- Phase 1 provides value even without Phase 2
- Regular checkpoints with stakeholder

### Risk 5: Quality Regression from Simplification
**Likelihood**: Low
**Impact**: High
**Mitigation**:
- Regenerate all 4 existing templates as integration tests
- Quality scores must match or exceed current (9+/10)
- Extended validation (`--validate`) still available
- If regression detected, keep current implementation

---

## Backward Compatibility

### Preserved (No Breaking Changes)
- ✅ `/template-create` command syntax unchanged
- ✅ All flags work (`--validate`, `--dry-run`, `--output-location`, `--name`, etc.)
- ✅ Output format unchanged (manifest.json, settings.json, CLAUDE.md, templates/, agents/)
- ✅ Quality outcomes maintained (9+/10)
- ✅ Existing templates still valid

### Changed (Transparent to Users)
- ⚠️ Agent bridge removed (internal detail)
- ⚠️ Resume behavior removed (rarely needed, no user impact)
- ⚠️ State files removed (`.agent-request.json`, `.template-create-state.json`)
- ⚠️ Direct agent invocation (faster, simpler)

### Added (New Features)
- ✅ `/create-template-task` command (optional, new workflow)
- ✅ Simplified orchestrator (easier to maintain)
- ✅ Better error messages (no exit code 42 confusion)

### Migration Path
- **No action required** for current users
- `/template-create` continues to work exactly as before
- New users can discover `/create-template-task` via documentation
- No deprecation warnings (both workflows supported)

---

## Alternatives Considered

### Alternative 1: Keep Current Implementation
**Decision**: REJECT

**Pros**:
- ✅ No implementation cost
- ✅ No migration risk
- ✅ Users are familiar

**Cons**:
- ❌ Agent bridge complexity remains (YAGNI violation)
- ❌ Maintenance burden (2004 LOC orchestrator)
- ❌ Debugging challenges (exit code 42, state files)

**Why Rejected**:
- Agent bridge pattern doesn't justify its complexity
- Review identified YAGNI score of 5/10
- Simplification provides value without breaking changes

### Alternative 2: Full Pivot to Task-Based Workflow
**Decision**: REJECT

**Pros**:
- ✅ Eliminates orchestrator entirely
- ✅ Leverages `/task-work` infrastructure
- ✅ Human oversight at each phase

**Cons**:
- ❌ Loses automation value (single command → complete template)
- ❌ Doesn't solve root complexity (generators still complex)
- ❌ Breaking changes for existing users
- ❌ No evidence it's better (current approach works well)

**Why Rejected**:
- Completed tasks (TASK-057/058/059/062) show `/template-create` works and is fast
- Pivot trades automation for oversight (net negative)
- Migration risk not justified by benefits

### Alternative 3: Simplify Only (No Guided Workflow)
**Decision**: CONSIDERED

**Pros**:
- ✅ Simpler implementation (Phase 1 only)
- ✅ Reduces complexity
- ✅ No new commands

**Cons**:
- ⚠️ No guided option for complex cases
- ⚠️ Misses opportunity to add flexibility

**Why Not Recommended**:
- Phase 2 adds significant value (guided workflow)
- Implementation cost is low (1 week)
- Provides user choice without complexity

### Alternative 4: Hybrid Approach (RECOMMENDED)
**Decision**: RECOMMEND

**Pros**:
- ✅ Simplifies orchestrator (removes agent bridge)
- ✅ Preserves automation (`/template-create`)
- ✅ Adds guided option (`/create-template-task`)
- ✅ No breaking changes
- ✅ User choice (automation or oversight)

**Cons**:
- ⚠️ Implementation effort (3-4 weeks)
- ⚠️ Two workflows to maintain (but both simple)

**Why Recommended**:
- Best of both worlds
- Fixes YAGNI issues (agent bridge removal)
- Adds flexibility without losing automation
- Proven workflow from completed tasks

---

## Conclusion

The hybrid approach provides the best balance:
1. **Simplifies** the orchestrator (removes agent bridge, reduces LOC 30-40%)
2. **Preserves** automation value (`/template-create` for fast workflow)
3. **Adds** guided option (`/create-template-task` for oversight)
4. **No breaking changes** (backward compatible)

**Recommendation**: Approve hybrid approach and execute in 3 phases over 3-4 weeks.

---

## Next Steps

1. **Approval**: Review proposal with stakeholders
2. **Phase 1**: Simplify orchestrator (1-2 weeks)
   - Remove agent bridge pattern
   - Reduce LOC to <1200
   - Comprehensive testing
3. **Phase 2**: Add guided workflow (1 week)
   - Implement `/create-template-task`
   - Integrate with `/task-work`
   - Documentation
4. **Phase 3**: Testing and rollout (1 week)
   - Integration testing
   - Migration testing
   - Release

---

## References

**Review Document**: [template-create-pivot-review.md](../reviews/template-create-pivot-review.md)
**Completed Tasks**: TASK-057, TASK-058, TASK-059, TASK-062
**Current Implementation**: `installer/global/commands/lib/template_create_orchestrator.py`

---

**Document Status**: COMPLETE
**Proposal Status**: Proposed
**Implementation Status**: Awaiting Approval
**Created**: 2025-11-20
