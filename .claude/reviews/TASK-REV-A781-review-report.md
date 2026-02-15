# Review Report: TASK-REV-A781

## Executive Summary

The task-work session preamble consuming ~1800 seconds (30 minutes) is caused by **three compounding factors**, not a single root cause. The primary driver is **massive context injection** (~1.7MB+ of rules, commands, and agent definitions) that the Claude Agent SDK loads into the session before the first model turn. This is amplified by **serial subagent invocation** during Phases 1.6-2.8, and **redundant SDK session initialization** when task-work delegates back through the SDK.

The fix is architecturally straightforward: reduce context payload, skip unnecessary phases for autobuild tasks, and eliminate double-session overhead.

## Review Details

- **Mode**: Architectural Review (deep)
- **Task**: TASK-REV-A781
- **Source**: `docs/reviews/feature-build/gap_analysis.md` (Minor Observations)
- **Related Tasks**: TASK-ASF-001 (direct mode workaround), TASK-ASF-008 (timeout increase)

---

## Finding 1: Massive Context Injection (~60% of overhead)

**Severity**: Critical
**Estimated Time Consumed**: ~1080 seconds (18 minutes)

### Evidence

When the SDK creates a session with `setting_sources=["user", "project"]`, it loads:

| Source | Size | Description |
|--------|------|-------------|
| User commands (`~/.claude/commands/*.md`) | **839 KB** | 26 command specifications |
| Project commands (`.claude/commands/*.md`) | **161 KB** | 16 project-level commands |
| Project rules (`.claude/rules/**/*.md`) | **63 KB** | 14 rule/pattern files |
| Project CLAUDE.md files | **~15 KB** | Root + .claude/CLAUDE.md |
| **Total injected context** | **~1,078 KB** | Before first model turn |

The task-work command spec alone (`installer/core/commands/task-work.md`) is **165 KB / 4,844 lines** - roughly **45,000 tokens**. This is loaded as a skill definition before the model even begins processing.

Additionally, when the pre-loop design phase executes `/task-work --design-only` via SDK, it creates **a second Claude session** that loads the same context again. The implementation path shows:

```
AutoBuild Orchestrator
  └─→ PreLoopQualityGates.execute()
      └─→ TaskWorkInterface.execute_design_phase()
          └─→ SDK query("/task-work TASK-XXX --design-only")  ← Second session, reloads ALL context
              └─→ Claude processes /task-work skill (165KB)
                  └─→ Phase 1.5-2.8 with subagent invocations
```

### Root Cause

The Claude Agent SDK loads **all** commands and rules as system context regardless of which command will actually be invoked. There is no lazy loading or selective inclusion - every session gets the full ~1MB payload.

### Impact on Model Processing

At ~1MB of context, the first model turn must process roughly **250,000-300,000 tokens** of system context before generating its first response. This alone accounts for significant latency:
- Input token processing: ~200K-300K tokens at model inference speed
- First-turn reasoning over massive context to identify the task-work command
- Skill expansion (the `/task-work` prompt gets expanded with the full spec)

---

## Finding 2: Serial Subagent Invocations During Design Phase (~25% of overhead)

**Severity**: High
**Estimated Time Consumed**: ~450 seconds (7.5 minutes)

### Evidence

The `--design-only` path executes Phases 1.6 through 2.8 sequentially, each potentially spawning subagents:

| Phase | Operation | Subagents | Estimated Time |
|-------|-----------|-----------|----------------|
| 1.6 | Clarifying Questions | `clarification-questioner` | 60-90s |
| 2 | Implementation Planning | (inline, large prompt) | 90-120s |
| 2.1 | Library Context | Context7 MCP calls | 30-60s |
| 2.5A | Pattern Suggestions | `pattern-advisor` (if MCP available) | 30-60s |
| 2.5B | Architectural Review | `architectural-reviewer` | 60-90s |
| 2.7 | Complexity Evaluation | `complexity-evaluator` | 30-60s |
| 2.8 | Human Checkpoint | (blocking wait or auto-approve) | 10-30s |
| **Total** | | | **310-510s** |

Each subagent invocation via the `Task` tool creates its own context, runs inference, and returns results. These are executed **serially** - no parallelization of independent phases.

### Root Cause

The task-work command specification defines a strictly sequential phase pipeline. Phases like 2.5A (Pattern Suggestions) and 2.5B (Architectural Review) could theoretically run in parallel, but the specification mandates sequential execution.

---

## Finding 3: Double SDK Session Initialization (~15% of overhead)

**Severity**: High
**Estimated Time Consumed**: ~270 seconds (4.5 minutes)

### Evidence

The autobuild flow creates **two SDK sessions** before any implementation work begins:

**Session 1: Pre-Loop Quality Gates**
```python
# task_work_interface.py:352-361
options = ClaudeAgentOptions(
    cwd=str(self.worktree_path),
    allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Task", "Skill"],
    permission_mode="acceptEdits",
    max_turns=50,
    setting_sources=["user", "project"],  # Loads ALL context
)
```

**Session 2: Player Turn 1 (via task-work --implement-only)**
```python
# agent_invoker.py:2504-2515
options = ClaudeAgentOptions(
    cwd=str(self.worktree_path),
    allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Task", "Skill"],
    permission_mode="acceptEdits",
    max_turns=TASK_WORK_SDK_MAX_TURNS,  # 50
    setting_sources=["user", "project"],  # Loads ALL context AGAIN
)
```

Each session initialization involves:
1. SDK process startup (Node.js/CLI)
2. Loading all setting sources (~1MB)
3. First-turn context processing (~250K tokens)
4. Skill expansion and command parsing

The double initialization essentially doubles the context loading overhead.

### Root Cause

The architecture delegates from Python (AutoBuild orchestrator) → SDK (Claude session) → Skill expansion → Claude processes phases. This creates an inherent double-session pattern: one for design, one for implementation.

---

## Finding 4: Direct Mode Comparison

**Severity**: Informational

### What Direct Mode Skips

Direct mode (`_invoke_player_direct()` in `agent_invoker.py:2036`) avoids the preamble overhead by:

1. **No pre-loop quality gates**: Skips the entire `PreLoopQualityGates.execute()` call
2. **No skill invocation**: Sends a custom prompt directly, not `/task-work --implement-only`
3. **Simpler setting_sources**: Uses `["project"]` only (no user commands), saving ~839KB
4. **No Phase 1.6-2.8**: No clarification, planning, architectural review, or complexity evaluation
5. **Single session**: One SDK invocation instead of two

```python
# agent_invoker.py:1354 (direct mode)
setting_sources=["project"]  # Only project CLAUDE.md + rules (~78KB)

# agent_invoker.py:2514 (task-work mode)
setting_sources=["user", "project"]  # Full user + project commands (~1,078KB)
```

### Quantified Difference

| Metric | Direct Mode | Task-Work Mode | Delta |
|--------|-------------|----------------|-------|
| SDK sessions | 1 | 2 | +1 session |
| Context loaded | ~78 KB | ~1,078 KB per session | +1,000 KB |
| Design phases | 0 | 7 phases (1.6-2.8) | +7 phases |
| Subagent calls | 0 | 3-5 | +3-5 agents |
| Estimated preamble | ~60-120s | ~1,800s | +1,680s |

---

## Impact Assessment for Wave 2 Tasks

### Will Wave 2 Tasks Hit This Problem?

**Yes.** Wave 2 tasks (complexity 4-6) are defined as requiring `task-work` mode. Per the autobuild rules:

- `guardkit autobuild task` has **Pre-Loop Default: On** with a 7,200s timeout
- Wave 2 tasks specifically cannot use `implementation_mode: direct` (that's a workaround for simple tasks)
- The intensity auto-detection for feature subtasks maps complexity 4-6 to LIGHT or STANDARD intensity, both of which include the full Phase 1.6-2.8 pipeline

**Expected overhead per Wave 2 task**: 1,200-1,800 seconds preamble before implementation starts.

**For a typical Wave 2 with 4 tasks**: 4,800-7,200 seconds (1.3-2 hours) of pure preamble overhead.

### Risk Level

**HIGH** - The current 7,200s total timeout for `guardkit autobuild task` means:
- Preamble: ~1,800s
- Remaining for implementation: ~5,400s (90 minutes)
- For complexity 5-6 tasks, this may be insufficient for multi-turn Player-Coach loops

---

## Recommendations

### Recommendation 1: Reduce Context Payload (HIGH IMPACT, MEDIUM EFFORT)

**Estimated Complexity**: 5/10
**Expected Savings**: ~600-900 seconds (50-60% of overhead)

**Approach**: Create a lightweight `setting_sources` mode for autobuild SDK sessions:

1. **Selective command loading**: Only load the commands actually needed (`task-work`, `task-complete`) rather than all 26 user commands and 16 project commands
2. **Slim task-work spec**: The 165KB task-work spec could be split into a core spec (~20KB) and extended reference. The execution protocol section alone would suffice for the SDK session
3. **Direct mode setting_sources for pre-loop**: Use `["project"]` instead of `["user", "project"]` for the design phase session, since the skill is invoked via prompt not user commands

**Implementation sketch**:
```python
# For pre-loop design phase, don't load user skills - use direct prompt
options = ClaudeAgentOptions(
    setting_sources=["project"],  # 78KB vs 1,078KB
    # Include task-work execution protocol inline in prompt
)
```

### Recommendation 2: Eliminate Double Session (HIGH IMPACT, HIGH EFFORT)

**Estimated Complexity**: 7/10
**Expected Savings**: ~270-450 seconds (15-25% of overhead)

**Approach**: Merge pre-loop and first Player turn into a single SDK session:

1. Instead of two separate sessions (design-only → implement-only), create one session that runs the full task-work pipeline
2. The pre-loop result (plan, complexity, architectural score) gets embedded in the Player's turn context rather than requiring a separate SDK invocation
3. This halves the session initialization overhead

**Risk**: This changes the architectural boundary between design and implementation. The current two-session model provides clean separation. A single-session approach would need careful prompt engineering to maintain quality gate enforcement.

### Recommendation 3: Skip Unnecessary Phases for AutoBuild (MEDIUM IMPACT, LOW EFFORT)

**Estimated Complexity**: 3/10
**Expected Savings**: ~180-300 seconds (10-15% of overhead)

**Approach**: When autobuild invokes task-work, pass flags to skip phases irrelevant in autonomous mode:

1. **Skip Phase 1.6 (Clarification)**: No human present during autobuild. Already done with `--no-questions`, but verify it's consistently applied
2. **Skip Phase 2.5A (Pattern MCP)**: Pattern suggestions add latency with limited value in autonomous mode
3. **Reduce Phase 2.5B (Architectural Review)**: For complexity ≤5, use lightweight review or skip entirely (`--skip-arch-review`)
4. **Auto-approve Phase 2.8**: Already implemented with `--auto-approve-checkpoint`, verify it works without delay

**Implementation**: Add an `--autobuild-mode` flag that bundles these optimizations:
```
/task-work TASK-XXX --design-only --autobuild-mode
# Equivalent to: --no-questions --skip-arch-review --auto-approve-checkpoint --docs=minimal
```

### Recommendation 4: Expand Direct Mode Coverage (LOW IMPACT, LOW EFFORT)

**Estimated Complexity**: 2/10
**Expected Savings**: Avoids the problem entirely for eligible tasks

**Approach**: Expand the criteria for tasks that can use `implementation_mode: direct`:

1. Current: Only tasks explicitly marked `implementation_mode: direct`
2. Proposed: Auto-detect eligible tasks based on complexity (≤3) and risk (no high-risk keywords)
3. This won't help Wave 2 (complexity 4-6) but reduces the blast radius for simpler tasks

### Recommendation 5: Implement Prompt Caching / Session Reuse (HIGHEST IMPACT, HIGHEST EFFORT)

**Estimated Complexity**: 8/10
**Expected Savings**: ~1,200-1,500 seconds (70-80% of overhead)

**Approach**: If the Claude Agent SDK supports prompt caching or session reuse:

1. Cache the system prompt (CLAUDE.md + rules + commands) across multiple SDK sessions
2. Reuse a warm session for consecutive task-work invocations within the same autobuild run
3. This would nearly eliminate the context loading overhead for turns 2+

**Dependency**: This requires SDK-level support for prompt caching. May not be feasible with current SDK architecture.

---

## Decision Matrix

| Recommendation | Impact | Effort | Risk | Priority |
|----------------|--------|--------|------|----------|
| R1: Reduce context payload | High | Medium (5/10) | Low | **1st** |
| R3: Skip unnecessary phases | Medium | Low (3/10) | Very Low | **2nd** |
| R2: Eliminate double session | High | High (7/10) | Medium | **3rd** |
| R4: Expand direct mode | Low | Low (2/10) | Low | **4th** |
| R5: Prompt caching | Highest | Highest (8/10) | High | **5th** (future) |

### Recommended Approach

**Phase 1** (Quick wins, ~30 min implementation): R3 + R4
- Add `--autobuild-mode` flag to task-work (bundles optimizations)
- Expand direct mode criteria for complexity ≤3

**Phase 2** (Major reduction, ~4 hours): R1
- Split task-work spec into core + extended
- Use `["project"]` setting_sources for pre-loop session
- Selective command loading

**Phase 3** (Architecture improvement, ~8 hours): R2
- Merge pre-loop and first Player turn into single session
- Requires careful design to maintain quality gate integrity

**Phase 4** (Future optimization): R5
- Investigate SDK prompt caching capabilities
- Implement session reuse for multi-turn autobuild runs

### Expected Combined Savings

| Phase | Cumulative Savings | Preamble Duration |
|-------|-------------------|-------------------|
| Current | 0 | ~1,800s |
| After Phase 1 | ~300s | ~1,500s |
| After Phase 2 | ~900s | ~900s |
| After Phase 3 | ~1,200s | ~600s |
| After Phase 4 | ~1,500s | ~300s |

---

## Revised Implementation Strategy (Post-Review Revision)

Based on revision feedback, the implementation plan is reframed with more aggressive R1 treatment and deferred R2:

### Phase 1: Quick Wins (R3 + R4, ~1 hour)
- Add `--autobuild-mode` composite flag to task-work
- Expand direct mode auto-detection for complexity ≤3
- Savings: ~300s immediately

### Phase 2: Main Fix (R1 Aggressive, ~4 hours)
- Switch pre-loop session to `setting_sources=["project"]`
- Inline slim task-work execution protocol (~15-20KB) directly in prompt instead of relying on `/task-work` skill expansion (which requires loading all 839KB of user commands)
- Key insight: `_build_design_prompt()` sends `/task-work TASK-XXX --design-only` which **requires** `"user"` in setting_sources to find the skill. By inlining the protocol, we eliminate this dependency entirely
- Same approach for `_invoke_task_work_implement()`: inline the `--implement-only` execution protocol
- Savings: ~800-1,000s (from ~1,800s to ~600-800s)

### Deferred: R2 (Merge Sessions)
- High effort (7/10), medium savings (~270s)
- Risk of breaking design/implement boundary
- Not worth it when R1+R3 gets us to ~600s

### Deferred: R5 (Prompt Caching)
- Depends on SDK capabilities outside our control
- Investigate when SDK supports it

---

## Appendix: Complete Preamble Timeline

```
T=0s      AutoBuild orchestrator starts
T=5s      Git worktree created
T=10s     PreLoopQualityGates.execute() begins
T=15s     SDK Session 1 starting (task-work --design-only)
T=15s     ├── SDK loads setting_sources ["user", "project"] (~1MB)
T=60s     ├── First model turn processes ~250K tokens of context
T=120s    ├── Skill /task-work expanded (~165KB → tokens)
T=180s    ├── Phase 1.5: Load task context
T=210s    ├── Phase 1.6: Clarification (if not skipped)
T=300s    ├── Phase 2: Implementation planning (large prompt generation)
T=420s    ├── Phase 2.1: Library context (Context7 MCP)
T=480s    ├── Phase 2.5A: Pattern suggestions
T=540s    ├── Phase 2.5B: Architectural review (subagent)
T=630s    ├── Phase 2.7: Complexity evaluation (subagent)
T=660s    ├── Phase 2.8: Checkpoint (auto-approve)
T=660s    └── SDK Session 1 completes
T=660s    PreLoopQualityGates.execute() completes
T=670s    Player Turn 1 begins
T=675s    SDK Session 2 starting (task-work --implement-only)
T=675s    ├── SDK loads setting_sources ["user", "project"] (~1MB) AGAIN
T=735s    ├── First model turn processes ~250K tokens of context AGAIN
T=800s    ├── Skill /task-work expanded AGAIN
T=900s    └── Phase 3: Implementation finally begins
          (... but with task-work delegation, may spawn more subagents)
T=~1800s  First meaningful code output
```

**Key insight**: Of the ~1,800 seconds, approximately:
- **1,080s** (60%) is context loading and model processing of bloated system prompts
- **450s** (25%) is serial subagent execution during design phases
- **270s** (15%) is duplicated session initialization overhead
