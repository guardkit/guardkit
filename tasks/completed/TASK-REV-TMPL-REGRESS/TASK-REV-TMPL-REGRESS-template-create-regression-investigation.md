# TASK-REV-TMPL-REGRESS: Template Create Regression Investigation

## Metadata
```yaml
id: TASK-REV-TMPL-REGRESS
title: Investigate template-create regression between v0.97 and HEAD
status: review_complete
task_type: review
decision_required: true
created: 2025-12-01T20:00:00Z
updated: 2025-12-01T23:30:00Z
completed: 2025-12-01T23:30:00Z
priority: critical
tags: [architectural-review, regression, template-create, checkpoint-resume]
complexity: 8
review_mode: architectural
review_depth: comprehensive
estimated_duration: 4-6 hours
actual_duration: 4.5 hours
related_commits: [6c651a32, 09c3cc70, eb3f6ad6, f6343954, 0024640c, 483e9a6c]
baseline_commit: 6c651a32
review_results:
  score: 65
  findings_count: 3
  recommendations_count: 1
  decision: revert_and_selective_reapply
  report_path: .claude/reviews/TASK-REV-TMPL-REGRESS-review-report.md
```

## Problem Statement

Template creation workflow regressed between **v0.97 (6c651a32)** and **HEAD (483e9a6c)**. The v0.97 version works correctly with:
- ✅ Custom agent generation (8 agents for Svelte+Firebase)
- ✅ Readable agent request files
- ✅ Working checkpoint-resume flow
- ✅ Correct `/agent-enhance` instructions

The HEAD version exhibits multiple failures:
- ❌ Agent request file bloated to ~26k tokens (exceeds Claude Code 25k limit)
- ❌ Resume logic not working correctly (restarts from Phase 1)
- ❌ Phase 5 agent generation returns empty list (no custom agents)
- ❌ Cache pollution between Phase 1 and Phase 5 agent invocations

## Test Results

### v0.97 Test (✅ SUCCESS)
**Date**: 2025-12-01
**Branch**: `test-last-good-v0.97`
**Test Codebase**: kartlog (Svelte 5 + Firebase)

**Results**:
```
✅ Template created: javascript-standard-structure-template
✅ Custom agents: 8 agents generated
   - svelte-component-specialist
   - firebase-firestore-specialist
   - svelte-store-specialist
   - smui-form-specialist
   - realtime-listener-specialist
   - data-table-specialist
   - ai-chat-integration-specialist
   - crud-operations-specialist
✅ Agent request file: Readable size
✅ Checkpoint-resume: Worked correctly
✅ Instructions: /agent-enhance provided
```

**Minor Issues**:
- Missing `Any` import in `lib/codebase_analyzer/ai_analyzer.py` (line 17)
  - Fixed by adding `Any` to imports: `from typing import Optional, Dict, Any`
  - Non-blocking: Claude Code fixed it automatically

### HEAD Test (❌ MULTIPLE FAILURES)
**Date**: 2025-12-01
**Branch**: `main` (commit 483e9a6c)
**Test Codebase**: kartlog (Svelte 5 + Firebase)

**Results**:
```
❌ Agent request file: ~26,410 tokens (exceeds 25k Claude Code limit)
❌ Resume logic: Restarted from Phase 1 instead of continuing
❌ Phase 5 agents: Returned empty list (expected 8+ agents)
❌ Cache pollution: Phase 1 response cached, reused in Phase 5
❌ Template name: Auto-generated "javascript-standard-structure-template" (should be "svelte-firebase-pwa")
```

**Attempted Fixes** (introduced more issues):
- Added `clear_cache()` method to agent bridge
- Added cache clearing calls after Phase 1
- These changes are speculative and may cause more problems

## Commits Between v0.97 and HEAD

### Template-Create Related Commits
1. **09c3cc70** (Dec 1, 13:51) - "fixes for orchestrator for template-create"
   - Added orchestrator error messages (`orchestrator_error_messages.py`)
   - Added dependency install logic to installer
   - **Files changed**: 37 files, +10,032 lines

2. **eb3f6ad6** (Dec 1, 15:01) - "Further fix for template create orchestrator"
   - Path resolution fixes in `template-create.md`
   - **Files changed**: 7 files, +2,816 lines

3. **f6343954** (Dec 1, 16:38) - "Fixes for template create"
   - Modified `ai_analyzer.py` (4 lines)
   - Added diagnostic scripts
   - **Files changed**: 5 files, +769 lines

4. **0024640c** (Dec 1, 17:58) - "saving state in template create" ⚠️ **KEY COMMIT**
   - **Modified orchestrator**: 102 lines changed
   - Added Phase 1 checkpoint saving (`_save_checkpoint("before_phase1", phase=0)`)
   - Added `_run_from_phase_1()` method
   - Added unit tests for Phase 1 checkpoint
   - **Files changed**: 8 files, +2,408 lines

5. **483e9a6c** (Dec 1, 22:15) - "Complete TASK-FIX-AGENT-RESPONSE-FORMAT"
   - **OUR CHANGES** (attempting to fix perceived issues)
   - Added `clear_cache()` method to agent bridge
   - Added cache clearing calls after Phase 1
   - Modified response parser to accept `str | dict`
   - Modified agent bridge to serialize dict → string
   - **Files changed**: 8 files, +2,410 lines

## Investigation Scope

### Primary Questions

1. **Agent Request Bloat** (Critical)
   - Why is `.agent-request.json` now ~26k tokens vs smaller in v0.97?
   - What changed in prompt building between versions?
   - Is this related to Phase 1 checkpoint state including full analysis?

2. **Resume Logic Failure** (Critical)
   - Why does `--resume` restart from Phase 1 instead of continuing?
   - Is the state file being saved correctly?
   - Is the state file being loaded correctly?
   - What does commit 0024640c's Phase 1 checkpoint do differently?

3. **Phase 5 Agent Generation Failure** (Critical)
   - Why does Phase 5 return empty agent list on HEAD?
   - Is this actually cache pollution (our diagnosis) or something else?
   - Did the clear_cache() fix actually address a real problem?

4. **Architecture Understanding** (Foundational)
   - What is the complete checkpoint-resume flow?
   - How do agent invocations work (exit code 42 pattern)?
   - What is the agent bridge's role vs orchestrator's role?
   - How does state management work across invocations?

### Files to Review

**Core Orchestration**:
- `installer/global/commands/lib/template_create_orchestrator.py`
  - Current state (HEAD)
  - v0.97 state
  - Diff of commit 0024640c changes

**Agent Bridge**:
- `installer/global/lib/agent_bridge/invoker.py`
  - Agent invocation pattern
  - Response loading
  - Cache management (our changes)

**State Management**:
- `installer/global/lib/agent_bridge/state_manager.py`
  - State saving logic
  - State loading logic
  - Serialization format

**Phase 1 Analysis**:
- `installer/global/lib/codebase_analyzer/ai_analyzer.py`
  - How agent request is built
  - File sampling strategy
  - Prompt construction

**Phase 5 Agent Generation**:
- `installer/global/lib/agent_generator/agent_generator.py`
  - Agent identification logic
  - Agent invocation for recommendations

### Specific Investigation Tasks

#### Task 1: Document Checkpoint-Resume Architecture
- Trace complete flow from initial run through agent invocation to resume
- Document exit code 42 pattern
- Document state serialization/deserialization
- Create architecture diagram

#### Task 2: Compare Agent Request Generation
- Extract prompt building from v0.97
- Extract prompt building from HEAD
- Identify what causes size bloat
- Determine if bloat is legitimate or bug

#### Task 3: Trace Resume Logic Failure
- Check state file content when resume called
- Verify `config.resume` flag propagation
- Check `_resume_from_checkpoint()` execution
- Identify why Phase 1 restarts instead of continuing

#### Task 4: Analyze Phase 5 Agent Generation
- Determine if cache pollution is real issue
- Check if `clear_cache()` was needed
- Verify Phase 5 agent invocation on v0.97
- Compare Phase 5 behavior between versions

#### Task 5: Identify Root Cause
- Determine which commit introduced each regression
- Identify if regressions are related or independent
- Assess if our fixes (483e9a6c) made things worse

## Review Objectives

### Primary Objectives
1. **Understand the working system** (v0.97)
   - Document correct behavior
   - Document architecture
   - Establish baseline

2. **Identify regressions** (v0.97 → HEAD)
   - Pinpoint commit that broke each feature
   - Understand why changes were made
   - Assess if changes were necessary

3. **Recommend solution**
   - Revert problematic commits?
   - Fix forward with proper understanding?
   - Hybrid approach (revert + selective fixes)?

### Secondary Objectives
4. **Prevent future regressions**
   - Add integration tests for template-create
   - Document checkpoint-resume pattern
   - Add validation for agent request size

## Success Criteria

### Analysis Deliverables
- [ ] Complete architecture document for checkpoint-resume flow
- [ ] Root cause identified for agent request bloat
- [ ] Root cause identified for resume failure
- [ ] Root cause identified for Phase 5 empty agent list
- [ ] Assessment of our attempted fixes (483e9a6c)

### Recommendation Deliverables
- [ ] Clear recommendation: revert, fix forward, or hybrid
- [ ] If fix forward: detailed implementation plan
- [ ] If revert: identification of commits to revert
- [ ] Test strategy to verify fix
- [ ] Prevention strategy for future

## Decision Framework

### Option A: Full Revert to v0.97
**Approach**: Revert all commits from 09c3cc70 to 483e9a6c

**Pros**:
- ✅ Known working state
- ✅ Removes all speculative fixes
- ✅ Fast resolution

**Cons**:
- ⚠️ Loses any valid improvements in commits
- ⚠️ May lose important fixes (error messages, etc.)
- ⚠️ Doesn't understand what went wrong

### Option B: Selective Revert
**Approach**: Revert only problematic commits (e.g., 0024640c)

**Pros**:
- ✅ Keeps valid improvements
- ✅ Targeted fix
- ✅ Less disruptive

**Cons**:
- ⚠️ Requires identifying exact problematic commit
- ⚠️ May have dependencies between commits

### Option C: Fix Forward with Understanding
**Approach**: Understand root cause, then fix properly

**Pros**:
- ✅ Learns from mistakes
- ✅ Proper understanding for future
- ✅ Keeps valid improvements

**Cons**:
- ⚠️ Takes longer
- ⚠️ Risk of additional issues during fixing

### Option D: Hybrid (Revert + Targeted Fixes)
**Approach**: Revert to v0.97, then re-apply only necessary fixes

**Pros**:
- ✅ Returns to known good state
- ✅ Can selectively add improvements
- ✅ Controlled approach

**Cons**:
- ⚠️ Requires careful review of each commit
- ⚠️ Multiple steps

## Expected Outputs

### 1. Architecture Document
```markdown
# Template Create Checkpoint-Resume Architecture

## Overview
[Complete description of how checkpoint-resume works]

## Components
- Orchestrator
- Agent Bridge
- State Manager
- Agent Invoker

## Flow Diagrams
[Sequence diagrams showing normal flow and resume flow]

## State Lifecycle
[State creation, saving, loading, cleanup]

## Agent Invocation Pattern
[Exit code 42 pattern, request/response files, cache management]
```

### 2. Root Cause Analysis Report
```markdown
# Template Create Regression Analysis

## Regression 1: Agent Request Bloat
**Root Cause**: [Specific code change]
**Impact**: Claude Code cannot read request
**Fix**: [Specific solution]

## Regression 2: Resume Failure
**Root Cause**: [Specific code change]
**Impact**: Workflow restarts from beginning
**Fix**: [Specific solution]

## Regression 3: Phase 5 Empty Agents
**Root Cause**: [Specific code change or false alarm]
**Impact**: No custom agents generated
**Fix**: [Specific solution or revert speculative fix]
```

### 3. Recommendation Document
```markdown
# Template Create Fix Recommendation

## Recommended Approach: [Option A/B/C/D]

## Rationale
[Why this approach is best]

## Implementation Steps
1. [Step 1]
2. [Step 2]
...

## Testing Plan
1. [Test 1]
2. [Test 2]
...

## Rollback Plan
[If fix doesn't work]
```

## Execution Instructions

This task should be executed with:
```bash
/task-review TASK-REV-TMPL-REGRESS --mode=architectural --depth=comprehensive
```

**Expected Duration**: 4-6 hours
**Review Mode**: architectural (system design and flow analysis)
**Depth**: comprehensive (detailed investigation with architecture diagrams)

**Deliverables**:
1. Architecture document for checkpoint-resume system
2. Root cause analysis for each regression
3. Comparison of v0.97 vs HEAD behavior
4. Recommendation with implementation plan
5. Test strategy and prevention measures

**Decision Checkpoint**: Review will pause for human decision after presenting findings and recommendations.

## Notes

### Critical Observations

1. **v0.97 works completely** - This is our baseline
2. **Agent request size bloat** - User mentioned this early but we failed to acknowledge
3. **Speculative fixes may have worsened situation** - Our clear_cache() changes are untested
4. **Multiple commits changed orchestrator** - Need to review each carefully
5. **User's instinct was correct** - Should have reverted and documented before fixing

### Lessons Learned

1. **Always validate baseline before fixing** - Should have tested v0.97 first
2. **Don't pile fixes on fixes** - This trap was warned about
3. **Listen to user observations** - Agent request size bloat was mentioned but ignored
4. **Understand before changing** - Made changes without understanding architecture
5. **Test before committing** - Our fixes were not tested on actual template creation

---

**Status**: READY FOR REVIEW EXECUTION

**Next Step**: Execute `/task-review TASK-REV-TMPL-REGRESS --mode=architectural --depth=comprehensive`
