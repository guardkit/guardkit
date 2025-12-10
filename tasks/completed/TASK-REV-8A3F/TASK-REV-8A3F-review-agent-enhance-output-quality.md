---
id: TASK-REV-8A3F
title: Review agent-enhance command output quality - empty/missing extended files
status: completed
created: 2025-12-07T17:30:00Z
updated: 2025-12-07T19:15:00Z
completed: 2025-12-07T19:15:00Z
completed_location: tasks/completed/TASK-REV-8A3F/
priority: high
tags: [review, agent-enhance, progressive-disclosure, quality-assurance, template-create]
complexity: 5
task_type: review
decision_required: false
related_tasks: [TASK-REV-7C49, TASK-EXT-C7C1]
review_report: .claude/reviews/TASK-REV-8A3F-review-report.md
recommendation: revise
revision_reason: Initial analysis made incorrect assumptions. Need deeper investigation before recommending changes to complex template-create/agent-enhance commands.
review_results:
  mode: code-quality
  depth: standard
  score: null
  findings_count: 4
  recommendations_count: 3
  decision: revise
  report_path: .claude/reviews/TASK-REV-8A3F-review-report.md
  completed_at: 2025-12-07T19:15:00Z
organized_files:
  - TASK-REV-8A3F-review-agent-enhance-output-quality.md
---

# Task: Review Agent-Enhance Command Output Quality

## Description

The `/agent-enhance` and `/template-create` commands are producing empty or missing extended files (`*-ext.md`). This was discovered during TASK-REV-7C49 which incorrectly assumed comprehensive agent content existed when it was actually stub files.

**Core Problem**: The agent-enhance workflow should:
1. AI analyzes the **actual codebase** being templated
2. Extracts **real code patterns, examples, and best practices** from that codebase
3. Generates agent content **specific to that codebase's architecture**
4. Creates both core and extended files with **codebase-specific content**

**What's Happening Instead**:
- Extended files are empty (0 bytes) - see `docs/reviews/progressive-disclosure/agent-ehance-output/`
- Agent files remain as stubs (~30 lines) instead of comprehensive (~500+ lines)
- TASK-EXT-C7C1 was created based on false assumption that comprehensive content existed

## Review Scope

### Files to Analyze

**Agent-Enhance Command**:
- `installer/core/commands/agent-enhance.md` - Command specification
- Related Python scripts in `installer/core/commands/lib/`

**Template-Create Command**:
- `installer/core/commands/template-create.md` - Command specification
- Phase 6-8 agent generation logic

**Evidence of Problem**:
- `docs/reviews/progressive-disclosure/agent-ehance-output/` - All files are 0-1 bytes
- `~/.agentecflow/templates/javascript-standard-structure-template/agents/` - Stub files only
- `tasks/completed/TASK-REV-7C49/review-report.md` - Review assumed content existed

**Reference (Working Examples)**:
- `installer/core/agents/devops-specialist.md` (~111 lines core)
- `installer/core/agents/devops-specialist-ext.md` (~2327 lines extended)
- These show what properly enhanced agents should look like

## Acceptance Criteria

### Root Cause Analysis
- [ ] Identify why agent-enhance produces empty output files
- [ ] Identify why template-create Phase 6-8 doesn't generate comprehensive content
- [ ] Determine if AI codebase analysis is being invoked correctly
- [ ] Check if there are error handling gaps hiding failures

### Quality Standards Definition
- [ ] Define what "comprehensive agent content" means (line counts, sections)
- [ ] Define minimum quality thresholds for core vs extended files
- [ ] Document expected content for codebase-analyzed agents vs generic templates

### Process Improvement
- [ ] Recommend fixes to agent-enhance command
- [ ] Recommend fixes to template-create Phase 6-8
- [ ] Suggest validation gates to prevent empty file creation
- [ ] Propose error reporting improvements

## Analysis Focus Areas

1. **AI Codebase Analysis**
   - Is the AI actually reading and analyzing the source codebase?
   - Are code examples being extracted from the actual project files?
   - Is the analysis happening during agent-enhance or being skipped?

2. **Content Generation Pipeline**
   - What prompts are used for agent content generation?
   - Is there a failure mode that produces empty files silently?
   - Are there timeouts or token limits causing truncation?

3. **File Writing**
   - Are files being written correctly or failing silently?
   - Is there a race condition or async issue?
   - Are permissions or path issues involved?

4. **Validation Gaps**
   - Why wasn't empty output detected during template-create validation?
   - Why did TASK-REV-7C49 pass with score 8.2/10 when files were empty?
   - What validation should be added?

## Related Context

**TASK-REV-7C49 Review Report** stated:
- Line 64-65: `pwa-vite-specialist` and `openai-function-calling-specialist` have "no ext file"
- Line 74: Described as "(core, no extended)" suggesting this was expected
- But the task description for TASK-EXT-C7C1 assumed 518/736 line files existed

**TASK-EXT-C7C1** (now blocked):
- Created to "split" files that don't actually have content to split
- Should be closed/cancelled after this review determines root cause

## Decision Options

After review, recommend one of:
- **[I]mplement** - Create implementation tasks to fix agent-enhance/template-create
- **[R]evise** - Need deeper analysis before recommending fixes
- **[C]ancel** - If issue is user error, not system bug

## Implementation Notes

This review will inform fixes to:
- `/agent-enhance` command - ensure AI codebase analysis runs
- `/template-create` Phase 6-8 - ensure agent content is generated
- Validation logic - prevent empty files from being accepted
- Error handling - surface failures instead of silent empty output

After this review, TASK-EXT-C7C1 should be either:
- Cancelled (if the fix is to agent-enhance command)
- Revised (if manual content creation is still needed)
