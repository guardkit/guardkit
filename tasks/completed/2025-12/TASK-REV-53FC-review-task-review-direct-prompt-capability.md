---
id: TASK-REV-53FC
title: "Review: Can /task-review accept direct text prompts? Is /feature-plan over-complicated?"
status: backlog
created: 2025-12-05T08:20:00Z
updated: 2025-12-05T08:20:00Z
priority: high
tags: [review, workflow-simplification, task-review, feature-plan]
task_type: review
complexity: 3
---

# Review: /task-review Direct Prompt Capability

## Investigation Questions

1. **Can `/task-review` accept a direct text prompt without creating a task first?**
   - User observed they ran `/task-review` with a text prompt directly
   - Current documentation shows: `/task-review TASK-XXX [--mode=MODE]`
   - Is there undocumented direct prompt capability?

2. **If yes, has the user been over-complicating the workflow?**
   - Current documented workflow: `/task-create` → `/task-review TASK-XXX`
   - Potential simpler workflow: `/task-review "text prompt"` directly

3. **If direct prompts work, is `/feature-plan` over-engineered?**
   - `/feature-plan` was designed to combine `/task-create` + `/task-review`
   - If `/task-review` already accepts direct prompts, `/feature-plan` might be redundant
   - What unique value does `/feature-plan` provide beyond direct `/task-review`?

## Scope

- Review `/task-review` command documentation
- Test if direct text prompts work with `/task-review`
- Analyze if `/feature-plan` provides value beyond what `/task-review` offers
- Recommend workflow simplification if applicable

## Acceptance Criteria

- [ ] Clarify whether `/task-review` supports direct text prompts
- [ ] Document the supported usage patterns
- [ ] Assess whether `/feature-plan` is necessary or redundant
- [ ] Provide recommendation on workflow simplification

## Files to Review

- `installer/global/commands/task-review.md`
- `installer/global/commands/feature-plan.md`
- `CLAUDE.md` (workflow documentation)
