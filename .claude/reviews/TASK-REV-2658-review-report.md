# Review Report: TASK-REV-2658

## Executive Summary

**Status**: Analysis Complete - Decision Required
**Review Mode**: Decision Analysis
**Review Depth**: Standard
**Completed**: 2025-12-14

**Question**: Should `/task-review` explicitly invoke the Explore agent to gather codebase context before executing review analysis?

**Recommendation**: **Option 2 - Depth-Gated Auto-Invocation** (Comprehensive depth only)

This approach provides the exploration benefits for complex reviews where they matter most, while avoiding unnecessary overhead for quick/standard reviews.

---

## Current State Analysis

### How `/task-review` Currently Gathers Context

The current `/task-review` workflow (Phase 1: Load Review Context) does the following:

1. **Reads task file** - Parses frontmatter metadata
2. **Invokes clarification-questioner** (optional) - Asks about review focus, depth, trade-offs
3. **Loads relevant codebase files** - Described as "Load relevant codebase files/modules"
4. **Loads design documents and ADRs** - Related documentation

**Key Finding**: The current Phase 1 description is vague about HOW codebase files are loaded. It says "Load relevant codebase files/modules" but doesn't specify a mechanism. In practice, Claude Code uses its own judgment to read files as needed during Phase 2 analysis.

### How the Explore Agent Was Used (Observed Behavior)

From the `feature-plan-test.md` example, when Claude Code was NOT following the command file instructions, it naturally:

1. Launched an `Explore` Task agent with `subagent_type='Explore'`
2. Used Haiku 4.5 model (cost-efficient)
3. Made 24 tool uses in 1m 38s
4. Consumed 67.1k tokens
5. Produced comprehensive understanding of codebase structure

The agent's prompt was: "Explore current project infrastructure"

**Result**: Claude stated "Now I have a clear picture of the current state" and proceeded to produce high-quality, contextually-aware analysis.

### Comparison: Explore Agent vs Current Approach

| Aspect | Current (Ad-hoc) | With Explore Agent |
|--------|------------------|-------------------|
| Context gathering | As-needed during analysis | Upfront, systematic |
| Codebase understanding | Partial, task-focused | Comprehensive, structural |
| Token cost | Variable, often lower | Fixed overhead (50-70k) |
| Time cost | Variable | Fixed (1-2 min) |
| Quality of analysis | Good for focused reviews | Better for broad/architectural reviews |
| Risk of missing context | Higher | Lower |

---

## Benefits Assessment

### When Explore Would Help Most

1. **Architectural Reviews** (`--mode=architectural`)
   - Need to understand overall system structure
   - Pattern identification requires broad context
   - SOLID/DRY/YAGNI assessment needs full picture

2. **Technical Debt Reviews** (`--mode=technical-debt`)
   - Debt is often distributed across codebase
   - Need to find all occurrences of problematic patterns
   - Prioritization requires understanding dependencies

3. **Security Reviews** (`--mode=security`)
   - Attack surface requires comprehensive scan
   - Vulnerabilities often span multiple files
   - Need to trace data flows across system

4. **Comprehensive Depth** (`--depth=comprehensive`)
   - Already commits to thorough analysis
   - Time investment (4-6 hours) makes exploration worthwhile
   - User expects exhaustive coverage

### When Explore Would Be Overkill

1. **Quick Reviews** (`--depth=quick`)
   - 15-30 minute timeframe doesn't justify 1.5 min exploration
   - Surface-level review doesn't need deep context
   - Cost/benefit ratio poor

2. **Code Quality Reviews** (`--mode=code-quality`)
   - Often focused on specific files
   - Metrics are objective, not context-dependent
   - Local analysis usually sufficient

3. **Decision Mode** (`--mode=decision`)
   - Often about specific technical choices
   - Context provided in task description
   - Exploration may not add value

### Quality Impact Analysis

**Reduces hallucination risk by**:
- Ensuring agent has actual file structure, not assumptions
- Providing real code patterns to reference
- Revealing dependencies that might be missed

**Improves recommendations by**:
- Understanding existing patterns to extend
- Identifying integration points correctly
- Ensuring suggestions are codebase-compatible

**Estimated quality improvement**: 10-20% for comprehensive/architectural reviews, minimal for quick/focused reviews.

---

## Cost/Tradeoff Analysis

### Token Cost

| Scenario | Without Explore | With Explore | Delta |
|----------|----------------|--------------|-------|
| Quick review | ~30k | ~100k | +233% |
| Standard review | ~80k | ~150k | +88% |
| Comprehensive review | ~200k | ~270k | +35% |

**Insight**: For comprehensive reviews, the relative overhead is much smaller.

### Time Cost

| Scenario | Exploration Time | Total Review Time | Overhead % |
|----------|-----------------|-------------------|------------|
| Quick (15-30 min) | 1.5 min | 16.5-31.5 min | 5-10% |
| Standard (1-2 hours) | 1.5 min | 61.5-121.5 min | 1-2.5% |
| Comprehensive (4-6 hours) | 1.5 min | 241.5-361.5 min | <0.5% |

**Insight**: Time overhead is negligible for standard/comprehensive reviews.

### When Investment Is Worthwhile

**High ROI scenarios**:
- Comprehensive depth (always)
- Architectural mode + standard/comprehensive depth
- Security mode (any depth)
- Technical debt mode + standard/comprehensive depth
- Unknown/new codebase

**Low ROI scenarios**:
- Quick depth (any mode)
- Code quality mode with specific file focus
- Well-known codebase with narrow scope

---

## Implementation Options

### Option 1: Always Invoke (Full Integration)

**Description**: Add Explore agent invocation as Phase 0.5, before all reviews.

```markdown
### Phase 0.5: Codebase Exploration (NEW)

**INVOKE** Task tool:
  subagent_type: "Explore"
  description: "Explore codebase for review context"
  prompt: "Explore the codebase focusing on {review_mode} concerns.
           Thoroughness level: {depth}"
```

**Pros**:
- Consistent behavior
- Simple to implement
- Always-on quality benefit

**Cons**:
- Adds overhead to quick reviews (poor ROI)
- Increases cost for all reviews
- May delay simple reviews unnecessarily

**Effort**: Low (add single phase)
**Risk**: Low (additive change)

### Option 2: Depth-Gated Auto-Invocation (RECOMMENDED)

**Description**: Auto-invoke Explore for comprehensive depth, skip for quick/standard.

```markdown
### Phase 0.5: Codebase Exploration (Comprehensive Only)

**IF** depth == "comprehensive":
  **INVOKE** Task tool:
    subagent_type: "Explore"
    description: "Comprehensive codebase exploration"
    prompt: "Thoroughly explore codebase for {review_mode} review..."
```

**Pros**:
- Optimal cost/benefit balance
- Aligns with user's time commitment
- No overhead for quick reviews

**Cons**:
- Standard depth misses some benefit
- Slightly more complex logic

**Effort**: Low (conditional invocation)
**Risk**: Low

### Option 3: Optional via `--explore` Flag

**Description**: User explicitly requests exploration with a flag.

```bash
/task-review TASK-XXX --explore
/task-review TASK-XXX --explore=quick|thorough
```

**Pros**:
- Full user control
- No unwanted overhead
- Explicit opt-in

**Cons**:
- Users may not know when to use it
- Requires learning new flag
- May be underutilized

**Effort**: Low (add flag)
**Risk**: Low

### Option 4: Mode + Depth Gating

**Description**: Auto-invoke based on both mode AND depth combinations.

```markdown
**IF** (mode in [architectural, security, technical-debt] AND depth != quick) OR depth == comprehensive:
  INVOKE Explore
```

**Pros**:
- Fine-grained optimization
- Maximum ROI
- Tailored to review type

**Cons**:
- Complex logic
- Harder to predict behavior
- More edge cases

**Effort**: Medium
**Risk**: Low-Medium (complexity)

### Option 5: Complexity-Gated

**Description**: Use task complexity score to decide.

```markdown
**IF** complexity >= 6:
  INVOKE Explore
```

**Pros**:
- Reuses existing complexity scoring
- Scales with task difficulty
- Consistent with other gating

**Cons**:
- Complexity may not correlate with need for exploration
- Some high-complexity tasks are narrow in scope

**Effort**: Low
**Risk**: Low

---

## Comparison with Other Commands

### `/feature-plan` (Currently)

The fixed `/feature-plan` command explicitly PROHIBITS using Explore:

> ❌ **DO NOT** use Explore or other agents for the review - the `/task-review` command handles analysis

This was added because the command should delegate to `/task-review` rather than doing its own exploration. The prohibition is about command orchestration, not about whether exploration is valuable.

### `/task-work` (Currently)

Does NOT use Explore agent. Context gathering happens during:
- Phase 1: Task file reading
- Phase 2: Implementation planning (agent reads relevant files)
- Phase 3: Implementation (agent explores as needed)

### Consistency Consideration

If `/task-review` adds Explore:
- Creates asymmetry with `/task-work`
- But `/task-review` is about ANALYSIS (broader context needed)
- `/task-work` is about IMPLEMENTATION (focused context sufficient)

**Conclusion**: Asymmetry is acceptable because the commands have different purposes.

---

## Recommendation

### Primary Recommendation: Option 2 - Depth-Gated Auto-Invocation

**Rationale**:

1. **Comprehensive depth already commits to thorough analysis** - Users choosing `--depth=comprehensive` expect exhaustive review and accept longer duration (4-6 hours). Adding 1.5 minutes of exploration is negligible overhead.

2. **Highest ROI scenario** - Comprehensive reviews benefit most from broad context, and the relative cost overhead is smallest (<0.5% time increase).

3. **No impact on quick reviews** - Quick reviews remain fast, preserving the tool's versatility.

4. **Simple implementation** - Single conditional check, minimal complexity.

### Secondary Recommendation: Consider Option 4 for Future Enhancement

If Option 2 proves valuable, expand to Mode + Depth gating in a future iteration. This would add exploration for:
- Architectural reviews (standard + comprehensive)
- Security reviews (all depths)
- Technical debt reviews (standard + comprehensive)

This could be implemented as a follow-up task after validating Option 2.

### Implementation Approach

**Phase 1: Minimal Implementation** (Option 2)
1. Add Phase 0.5 to `/task-review` command specification
2. Condition: `--depth=comprehensive` only
3. Use Explore agent with thoroughness='very thorough'
4. Pass review mode to focus exploration

**Phase 2: Validation** (Future)
1. Track quality improvements in comprehensive reviews
2. Gather user feedback on exploration value
3. Measure token/time overhead

**Phase 3: Expansion** (Future, if validated)
1. Extend to Mode + Depth gating (Option 4)
2. Add `--explore` flag for explicit override (Option 3)
3. Document when exploration adds value

---

## Implementation Specification (If Approved)

### Changes to task-review.md

Add between current Phase 1 (Load Review Context) and Phase 2 (Execute Review Analysis):

```markdown
### Phase 1.5: Codebase Exploration (Comprehensive Depth Only)

**IF** depth == "comprehensive":

  **DISPLAY**: "Phase 1.5: Exploring codebase for comprehensive review..."

  **INVOKE** Task tool:
    ```
    subagent_type: "Explore"
    description: "Comprehensive codebase exploration for {review_mode} review"
    prompt: "Explore the codebase thoroughly to support a {review_mode} review.

    CONTEXT:
      Task ID: {task_id}
      Review Mode: {review_mode}
      Review Scope: {task_description}

    FOCUS AREAS based on review mode:
      - architectural: Project structure, patterns, dependencies, layers
      - code-quality: Code organization, naming, complexity, duplication
      - technical-debt: Legacy code, workarounds, TODOs, deprecated patterns
      - security: Auth flows, data handling, input validation, secrets
      - decision: Relevant components, integration points, constraints

    Thoroughness level: very thorough

    Return structured summary of findings for review analysis."
    ```

  **WAIT** for agent completion

  **STORE** exploration_context for Phase 2

  **DISPLAY**: "✓ Codebase exploration complete ({duration}s, {tool_uses} tool uses)"

**ELSE**:
  **SET** exploration_context = None
```

### Expected Behavior

| Command | Exploration |
|---------|-------------|
| `/task-review TASK-XXX --depth=quick` | No |
| `/task-review TASK-XXX --depth=standard` | No |
| `/task-review TASK-XXX --depth=comprehensive` | Yes |
| `/task-review TASK-XXX --mode=security --depth=comprehensive` | Yes |

### Optional Future Flag

```markdown
### Flag: --explore

**Purpose**: Override automatic exploration behavior

**Values**:
- `--explore` or `--explore=auto` - Use automatic depth-gated behavior (default)
- `--explore=always` - Force exploration regardless of depth
- `--explore=never` - Skip exploration regardless of depth
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Exploration takes too long | Low | Medium | Set timeout, use Haiku model |
| Token cost concerns | Low | Low | Only applies to comprehensive reviews |
| Exploration doesn't add value | Low | Low | Easy to remove if not beneficial |
| Inconsistency with other commands | Medium | Low | Document reasoning, asymmetry is justified |

---

## Summary

**Question**: Should `/task-review` add Explore agent for codebase context?

**Answer**: Yes, but only for comprehensive depth reviews.

**Rationale**:
- Exploration adds most value for thorough reviews
- Cost/benefit ratio is best for comprehensive depth
- Time overhead is negligible for long reviews
- No impact on quick/standard reviews

**Recommended Option**: Option 2 - Depth-Gated Auto-Invocation

**Implementation Effort**: Low (1-2 hours)
**Risk Level**: Low
**Expected Benefit**: 10-20% quality improvement for comprehensive reviews

---

## Appendix: Observed Explore Usage

From `docs/reviews/clarifying-questions/feature-plan-test.md`:

```
Explore(Explore current project infrastructure) Haiku 4.5
  Done (24 tool uses · 67.1k tokens · 1m 38s)
```

This shows:
- Model: Haiku 4.5 (cost-efficient)
- Tool uses: 24 (thorough exploration)
- Tokens: 67.1k (moderate)
- Duration: 1m 38s (fast)
- Thoroughness: High (24 tool uses indicates deep exploration)
