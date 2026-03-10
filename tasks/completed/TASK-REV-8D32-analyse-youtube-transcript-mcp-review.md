---
id: TASK-REV-8D32
title: Analyse youtube-transcript-mcp autobuild review findings
status: completed
created: 2026-03-10T00:00:00Z
updated: 2026-03-10T12:00:00Z
review_results:
  mode: architectural
  depth: standard
  score: 82
  findings_count: 11
  recommendations_count: 6
  decision: implement
  report_path: .claude/reviews/TASK-REV-8D32-review-report.md
  completed_at: 2026-03-10T12:00:00Z
priority: high
tags: [review, autobuild, youtube-transcript-mcp, quality-gates, infrastructure]
complexity: 6
task_type: review
source_review: /Users/richardwoollcott/Projects/appmilla_github/youtube-transcript-mcp/.claude/reviews/TASK-REV-7D5B-review-report.md
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyse youtube-transcript-mcp autobuild review findings

## Description

Analyse the review report from TASK-REV-7D5B (youtube-transcript-mcp autobuild review, scored 82/100) to investigate the recommendations and create implementation tasks to fix the identified issues. The review covers 5 features, 23 tasks, and 37 orchestrator turns across the autobuild of a YouTube transcript MCP server.

## Source Review Summary

**Overall Score: 82/100**

| Dimension | Score |
|-----------|-------|
| Code Quality | 85/100 |
| Feature Completeness | 90/100 |
| Test Quality | 88/100 |
| Review Document Quality | 45/100 |
| Autobuild Process Effectiveness | 78/100 |

## Key Findings to Investigate

### High Priority (GuardKit SDK improvements)

1. **CancelledError bug in GuardKit SDK** - Async generator cancellation errors in SDK layer affect all runs, caused 1 complete failure (FEAT-2AAA run 1). Single biggest reliability issue.
2. **Quality gate task inefficiency** - 4 quality gate tasks (17% of all tasks) consumed 41% of total turns (15/37) while producing zero production code. Root cause: implementation tasks don't include lint compliance in ACs.
3. **Auto-fix lint errors before Coach review** - Add pre-verification step running `ruff check --fix` automatically so Coach only sees unfixable issues.

### Medium Priority (youtube-transcript-mcp codebase)

4. **Review document quality** (45/100) - Raw autobuild logs, not human-readable review documents. Need structured summaries.
5. **Test file consolidation** - Overlapping test coverage between root `tests/` and `tests/unit/` directories.
6. **Add conftest.py** - Extract duplicated mock helpers into shared fixtures.
7. **Register custom pytest marks** - Add `seam` and `integration_contract` to pyproject.toml.

### Investigation (Cross-cutting)

11. **Graphiti effectiveness for job-specific context retrieval** - Investigate how well Graphiti knowledge capture is working for retrieving job-specific context during autobuild runs. Assess whether captured knowledge is being surfaced at the right time, improving task quality, and reducing redundant work. Determine if Graphiti is providing meaningful benefit or needs tuning/restructuring.

### Low Priority (youtube-transcript-mcp codebase)

8. **Fix 13 remaining ruff errors** - 8 auto-fixable, 5 manual.
9. **Increase parallelism** - Configure more parallel waves for independent tasks.
10. **Add protocol/ and e2e/ tests** - Empty test directories suggest planned but unimplemented test categories.

## Acceptance Criteria

- [x] Each recommendation from the review is triaged as GuardKit-scope or youtube-transcript-mcp-scope
- [x] High priority GuardKit improvements have implementation tasks created
- [x] Medium/low priority youtube-transcript-mcp fixes have implementation tasks created
- [x] Projected impact of fixes is quantified (turn reduction, time savings)
- [x] Recommendations are prioritised with clear implementation order
- [x] Graphiti context retrieval effectiveness is assessed with findings documented

## Implementation Notes

The review identified two distinct categories of work:

1. **GuardKit SDK improvements** (recommendations 1-3): These affect all autobuild runs across all projects and should be addressed in the guardkit repo.
2. **youtube-transcript-mcp fixes** (recommendations 4-10): These are specific to the youtube-transcript-mcp codebase and should be addressed there.

Key metric: fixing quality gate inefficiency + CancelledError could achieve **50%+ reduction** in total orchestrator turns.
