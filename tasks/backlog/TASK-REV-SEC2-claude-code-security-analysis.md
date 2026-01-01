---
id: TASK-REV-SEC2
title: Analyze Claude Code Security Plugin Techniques
status: review_complete
created: 2025-12-31T15:15:00Z
updated: 2025-12-31T16:00:00Z
priority: high
task_type: review
tags: [security, research, claude-code, coach-agent, autobuild]
complexity: 4
decision_required: true
related_tasks:
  - TASK-REV-SEC1
  - TASK-SEC-001
  - TASK-SEC-002
  - TASK-SEC-003
  - TASK-SEC-004
related_feature: tasks/backlog/coach-security-integration/
review_results:
  mode: research
  depth: standard
  sources_analyzed: 2
  findings_count: 12
  recommendations_count: 15
  report_path: .claude/reviews/TASK-REV-SEC2-review-report.md
  completed_at: 2025-12-31T16:00:00Z
  key_findings:
    - Claude Code uses substring matching (not regex) for quick checks
    - security-review tool uses 10-category vulnerability taxonomy
    - Confidence scoring (>80%) reduces false positives
    - Hard exclusion rules filter DOS, rate limiting, resource management
    - Path-based filtering limits checks to relevant file types
  applicable_techniques: 15
  directly_reusable: 8
  needs_adaptation: 7
  decision: update
  decision_timestamp: 2025-12-31T16:30:00Z
  tasks_updated:
    - TASK-SEC-001
    - TASK-SEC-002
    - TASK-SEC-003
    - TASK-SEC-004
    - TASK-SEC-005
    - TASK-SEC-006
---

# Review Task: Analyze Claude Code Security Plugin Techniques

## Description

Analyze the Claude Code security-guidance plugin to identify techniques, patterns, and approaches that could be adopted or adapted for the Coach agent security integration feature (TASK-REV-SEC1 implementation tasks).

## Reference Material

**Source Repository**: https://github.com/anthropics/claude-code/tree/main/plugins/security-guidance

This is Claude Code's official security review plugin that provides automated security analysis. Understanding its implementation could inform our Coach agent security integration.

## Review Scope

### Primary Questions to Answer

1. **Detection Patterns**: What security detection patterns does Claude Code use?
   - Regex patterns for vulnerability detection
   - AST-based analysis approaches
   - Language-specific security rules

2. **Severity Classification**: How does Claude Code classify security findings?
   - Severity levels (critical, high, medium, low, info)
   - Confidence scoring
   - False positive handling

3. **Architecture**: What is the plugin's architecture?
   - How is the security review invoked?
   - How are findings reported?
   - How does it integrate with the main workflow?

4. **Reusable Components**: What can we directly adopt?
   - Security check patterns
   - Finding report formats
   - Configuration schemas

5. **Gaps and Differences**: What does our Coach context require differently?
   - Integration with Player-Coach loop
   - Task-aware security (auth-tagged vs general)
   - Performance considerations for autonomous loop

### Applicability to Coach Security Integration

For each technique identified, assess applicability to:

| Task | Potential Benefit |
|------|-------------------|
| TASK-SEC-001 (Quick Checks) | Regex patterns, detection rules |
| TASK-SEC-002 (Config Schema) | Configuration structure |
| TASK-SEC-003 (Full Review) | Review invocation patterns |
| TASK-SEC-004 (Tag Detection) | Security keyword lists |
| TASK-SEC-005 (Tests) | Test patterns for security checks |
| TASK-SEC-006 (Docs) | Documentation structure |

## Acceptance Criteria

### For the Review

- [x] Fetch and analyze Claude Code security-guidance plugin source
- [x] Document detection patterns and rules
- [x] Document severity classification approach
- [x] Document plugin architecture and integration points
- [x] Identify directly reusable components
- [x] Identify patterns that need adaptation
- [x] Assess performance characteristics
- [x] Create recommendations for each TASK-SEC-* task
- [x] Note any licensing considerations

### Deliverables

1. **Analysis Report**: `.claude/reviews/TASK-REV-SEC2-review-report.md`
2. **Recommendations Matrix**: Mapping Claude Code techniques to our tasks
3. **Code Snippets**: Reusable patterns (if any)

## Decision Options

1. **[A]ccept** - Findings documented, no immediate changes to TASK-SEC-* tasks
2. **[R]evise** - Request deeper analysis on specific aspects
3. **[U]pdate** - Update TASK-SEC-* tasks with recommended techniques
4. **[C]ancel** - Claude Code approach not applicable

## Notes

This review should be conducted BEFORE implementing TASK-SEC-001 through TASK-SEC-006 to potentially incorporate proven patterns from Claude Code's security implementation.

The Claude Code security plugin is used in production by Claude Code CLI users, making it a valuable reference for security detection patterns that work well in AI-assisted development workflows.

---

*Created to analyze Claude Code security plugin for Coach security integration*
*Related: TASK-REV-SEC1 implementation tasks*

## Decision Outcome

**Decision**: [U]pdate - Update TASK-SEC-* tasks with recommended techniques

All 6 implementation tasks (TASK-SEC-001 through TASK-SEC-006) have been updated with specific techniques from the Claude Code security tools:

| Task | Techniques Added |
|------|------------------|
| TASK-SEC-001 | Substring matching, path-based filtering, expanded patterns (JS/TS, GHA) |
| TASK-SEC-002 | Hard exclusion categories, file type filtering, environment toggle |
| TASK-SEC-003 | 10-category taxonomy, confidence scoring, post-filtering |
| TASK-SEC-004 | Category-aligned tags, high-risk category triggers |
| TASK-SEC-005 | False positive tests, confidence threshold tests |
| TASK-SEC-006 | Exclusion documentation, confidence threshold docs |

Each task now includes:
- `enhanced_by: TASK-REV-SEC2` in frontmatter
- `claude_code_techniques` list in frontmatter
- Specific requirements marked with `[From TASK-REV-SEC2]`
- Claude Code Reference section with source links
