---
id: TASK-BRF-004
title: Document Honesty Context in Coach Prompt
status: backlog
task_type: implementation
created: 2026-01-24T16:30:00Z
updated: 2026-01-24T16:30:00Z
priority: medium
tags: [autobuild, documentation, honesty-verification, coach-agent]
complexity: 2
parent_review: TASK-REV-BLOC
feature_id: FEAT-BRF
wave: 2
implementation_mode: direct
conductor_workspace: block-research-fidelity-wave2-2
dependencies: []
---

# Task: Document Honesty Context in Coach Prompt

## Description

Enhance the Coach agent definition to more explicitly reference the pre-validated honesty context that it receives from the CoachVerifier.

**Problem**: The Coach agent definition mentions honesty verification but could be more explicit about how to use the pre-validated context in decision-making.

**Solution**: Add clearer documentation and examples showing how Coach should factor honesty verification into its decisions.

## Acceptance Criteria

- [ ] AC-001: Add "How to Use Honesty Verification" section to autobuild-coach.md
- [ ] AC-002: Include example prompts showing honesty context usage
- [ ] AC-003: Document the relationship between CoachVerifier and Coach agent
- [ ] AC-004: Add decision tree for honesty-aware approval/feedback

## Technical Approach

### Update `.claude/agents/autobuild-coach.md`

Add new section after the existing Honesty Verification section:

```markdown
## Using Honesty Verification in Decisions

The honesty verification context you receive has already been validated by `CoachVerifier`. Here's how to use it:

### Decision Tree

```
IF honesty_score < 0.5:
  → MUST provide feedback (critical honesty failure)
  → Include honesty discrepancies in issues

ELIF honesty_score < 0.8 AND critical_discrepancies > 0:
  → Strongly consider feedback
  → Verify claims independently before approving

ELIF honesty_score >= 0.8:
  → Proceed with normal validation
  → Honesty is not a blocking concern
```

### Example: Low Honesty Score Response

When you see low honesty (< 0.8), your decision should reference it:

```json
{
  "decision": "feedback",
  "issues": [
    {
      "severity": "must_fix",
      "category": "honesty_discrepancy",
      "description": "Player claimed tests passed but independent verification shows 2 failures",
      "honesty_score": 0.67
    }
  ],
  "rationale": "Cannot approve due to honesty discrepancies. Player must address test failures."
}
```

### Relationship to CoachVerifier

```
Player Report → CoachVerifier → Honesty Context → You (Coach)
                    ↓
              Runs tests
              Checks files
              Calculates score
```

You receive the verification RESULTS. You don't need to re-verify, but you should factor the results into your decision.
```

## Related Files

- `.claude/agents/autobuild-coach.md` - Primary update
- `installer/core/agents/autobuild-coach.md` - Sync update

## Notes

Documentation-only change. Improves Coach agent's understanding of honesty context usage.
