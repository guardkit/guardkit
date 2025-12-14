---
id: TASK-TR-10E0
title: Add Phase 1.5 Codebase Exploration to /task-review command
status: backlog
created: 2025-12-14T11:05:00Z
updated: 2025-12-14T11:05:00Z
priority: medium
tags: [task-review, explore-agent, codebase-context, enhancement]
complexity: 3
related_to: TASK-REV-2658
review_source: .claude/reviews/TASK-REV-2658-review-report.md
---

# Task: Add Phase 1.5 Codebase Exploration to /task-review command

## Description

Implement the recommendation from TASK-REV-2658 review: Add explicit Explore agent invocation to `/task-review` for comprehensive depth reviews only.

When users run `/task-review TASK-XXX --depth=comprehensive`, the command should first invoke the Explore agent to gather broad codebase context before executing the review analysis. This improves review quality by 10-20% for comprehensive reviews with negligible time overhead (<0.5%).

## Background

From TASK-REV-2658 analysis:
- Explore agent produces high-quality codebase understanding (24 tool uses, 67k tokens, 1.5 min)
- Cost/benefit is excellent for comprehensive reviews (+35% tokens, <0.5% time overhead)
- Cost/benefit is poor for quick reviews (+233% tokens)
- Solution: Gate exploration on `--depth=comprehensive` only

## Acceptance Criteria

- [ ] Add Phase 1.5: Codebase Exploration section to task-review.md
- [ ] Phase 1.5 only executes when `--depth=comprehensive`
- [ ] Explore agent invoked with `subagent_type: "Explore"`
- [ ] Exploration prompt includes review mode context
- [ ] Exploration context stored for use in Phase 2
- [ ] Display exploration progress and completion message
- [ ] Quick and standard depth reviews unchanged (no exploration)
- [ ] Update command documentation to explain when exploration occurs

## Implementation Details

### Location

File: `installer/core/commands/task-review.md`

Insert between:
- Phase 1: Load Review Context (line ~607)
- Phase 2: Execute Review Analysis (line ~612)

### New Section to Add

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
  **SKIP** to Phase 2
```

### Update Phase 2 to Use Exploration Context

In Phase 2: Execute Review Analysis, add:

```markdown
{if exploration_context:}
**CODEBASE CONTEXT** (from exploration):
  {exploration_context.summary}

  Key findings:
  {exploration_context.findings}
{endif}
```

### Expected Behavior Matrix

| Command | Exploration |
|---------|-------------|
| `/task-review TASK-XXX` (defaults to standard) | No |
| `/task-review TASK-XXX --depth=quick` | No |
| `/task-review TASK-XXX --depth=standard` | No |
| `/task-review TASK-XXX --depth=comprehensive` | Yes |
| `/task-review TASK-XXX --mode=security --depth=comprehensive` | Yes |
| `/task-review TASK-XXX --mode=architectural --depth=comprehensive` | Yes |

## Testing

1. Run `/task-review` with `--depth=comprehensive` and verify Explore agent is invoked
2. Run `/task-review` with `--depth=standard` and verify no exploration occurs
3. Run `/task-review` with `--depth=quick` and verify no exploration occurs
4. Verify exploration context is used in Phase 2 analysis
5. Verify progress messages display correctly

## Future Enhancements (Out of Scope)

These were identified in TASK-REV-2658 but deferred:
- Add `--explore` flag for explicit override (Option 3)
- Extend to Mode + Depth gating (Option 4) - e.g., architectural+standard
- Add exploration for security mode at all depths

## Related Files

- [task-review.md](../../installer/core/commands/task-review.md) - Main file to modify
- [TASK-REV-2658-review-report.md](../../.claude/reviews/TASK-REV-2658-review-report.md) - Source analysis

## Notes

- Explore agent uses Haiku model (cost-efficient)
- Typical exploration: 24 tool uses, 67k tokens, 1.5 minutes
- This is a documentation-only change (no code changes needed)
