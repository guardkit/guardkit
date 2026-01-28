---
id: TASK-5E55
title: "Review greenfield project initialization workflow and compare with template-create improvements"
status: review_complete
created: 2025-11-26T00:00:00Z
updated: 2025-11-26T07:15:00Z
priority: high
tags: [architecture-review, greenfield, template-init, improvement-opportunity, review]
complexity: 5
estimated_hours: 4
actual_hours: 2
task_type: review
decision_required: true
review_mode: decision
review_depth: standard
review_results:
  mode: decision
  depth: standard
  model_used: claude-opus-4-20250514
  findings_count: 13
  recommendations_count: 4
  decision: port_features
  user_choice: accept
  report_path: docs/decisions/template-init-vs-template-create-analysis.md
  completed_at: 2025-11-26T07:00:00Z
  decision_accepted_at: 2025-11-26T07:15:00Z
  quality_score: 95
  implementation_roadmap: 5_weeks_60_hours
  tasks_to_create: 11
test_results:
  status: not_applicable
  coverage: null
  last_run: null
---

# Task: Review Greenfield Project Initialization Workflow

## Executive Summary

Evaluate the current greenfield project initialization workflow (likely `guardkit init` or similar Q&A-based command) and assess whether it can benefit from the extensive improvements made to `/template-create`. The goal is to identify gaps, opportunities, and determine if the greenfield workflow is fit for purpose or needs enhancement.

## Context and Background

### Recent /template-create Improvements

The `/template-create` command has undergone significant enhancements including:
- **Agent enhancement with boundary sections** (ALWAYS/NEVER/ASK framework)
- **Automatic task creation** for agent improvements
- **Validation levels** (Level 1: automatic, Level 2: extended with `--validate`, Level 3: comprehensive audit)
- **GitHub best practices integration** (boundary sections from 2,500+ repo analysis)
- **Quality scoring** (8-10/10 for production templates)
- **Two-location support** (personal `~/.agentecflow/templates/` and repository `installer/core/templates/`)
- **Template philosophy** (templates as learning resources, not production code)

### Current Greenfield Workflow

The user mentions:
> "We also have another command. I think it's like template init for greenfields where it's going to Q&A session."

This suggests:
- Interactive Q&A-based initialization
- Designed for projects with no existing codebase
- Likely creates basic project structure
- May not include the sophisticated features of `/template-create`

## Problem Statement

**Questions to Answer:**
1. **Feature Parity**: Does the greenfield init workflow include agent enhancement, boundary sections, validation, and quality gates?
2. **Q&A Experience**: Is the interactive Q&A session as robust as the template-create workflow?
3. **Learning Resources**: Does it provide the same learning value (reference templates, best practices)?
4. **Quality Standards**: Does it meet the 8-10/10 quality bar established for templates?
5. **Boundary Clarity**: Are agents created with explicit ALWAYS/NEVER/ASK sections?
6. **Validation**: Does it offer validation levels like `/template-create --validate`?
7. **Task Generation**: Does it automatically create enhancement tasks for next steps?
8. **Fit for Purpose**: Is the current implementation sufficient, or does it need modernization?

## Scope of Review

### 1. Discovery Phase
- **Find the command**: Locate the actual greenfield initialization command (e.g., `guardkit init`, `/init`, `/greenfield-create`)
- **Read implementation**: Review the Q&A session logic (`greenfield_qa_session.py` exists in `lib/`)
- **Compare architecture**: Map greenfield workflow to `/template-create` phases

### 2. Feature Comparison Matrix

Create a side-by-side comparison:

```
┌────────────────────────┬──────────────────┬────────────────────┐
│ Feature                │ /template-create │ Greenfield Init    │
├────────────────────────┼──────────────────┼────────────────────┤
│ Agent Enhancement      │ ✅ Full support  │ ❓ Unknown         │
│ Boundary Sections      │ ✅ ALWAYS/NEVER  │ ❓ Unknown         │
│ Validation Levels      │ ✅ 3 levels      │ ❓ Unknown         │
│ Quality Scoring        │ ✅ 0-10 scale    │ ❓ Unknown         │
│ Task Generation        │ ✅ Automatic     │ ❓ Unknown         │
│ Reference Templates    │ ✅ 6 templates   │ ❓ Unknown         │
│ GitHub Best Practices  │ ✅ Integrated    │ ❓ Unknown         │
│ Two-Location Support   │ ✅ Personal/Repo │ ❓ Unknown         │
└────────────────────────┴──────────────────┴────────────────────┘
```

### 3. Gap Analysis

Identify specific gaps in:
- **Agent Quality**: Do greenfield-created agents lack boundary sections?
- **Validation**: Is there no validation for greenfield projects?
- **Learning Value**: Are users missing out on reference templates and best practices?
- **Task Guidance**: Do users know what to do after initialization?

### 4. Improvement Opportunities

Evaluate potential enhancements:
- **Option A**: Merge greenfield init into `/template-create` (unified workflow)
- **Option B**: Port `/template-create` improvements to greenfield init (parallel workflows)
- **Option C**: Keep as-is (if current implementation is sufficient)
- **Option D**: Deprecate greenfield init, recommend `/template-create` instead

### 5. User Experience Assessment

Review UX considerations:
- **Q&A Flow**: Is the interactive Q&A better than `/template-create`'s approach?
- **Onboarding**: Do new users prefer Q&A or template selection?
- **Complexity**: Does greenfield init avoid overwhelming users?
- **Output Quality**: Does it produce production-ready projects or just scaffolding?

## Analysis Approach

### Phase 1: Code Discovery (30 minutes)
1. Locate greenfield initialization command definition
2. Read `greenfield_qa_session.py` implementation
3. Identify related files and dependencies
4. Map workflow phases (if any)

### Phase 2: Feature Mapping (1 hour)
1. Document current greenfield workflow
2. Create feature comparison matrix
3. Identify missing features vs `/template-create`
4. Note unique features in greenfield that `/template-create` lacks

### Phase 3: Gap Analysis (1 hour)
1. Assess impact of missing features
2. Evaluate whether gaps are intentional (simplicity) or accidental (debt)
3. Consider user personas (beginner vs expert)
4. Review recent user feedback or issues

### Phase 4: Recommendation Synthesis (1.5 hours)
1. Evaluate Option A-D trade-offs
2. Propose specific enhancements (if needed)
3. Estimate effort for improvements
4. Define success criteria

## Expected Deliverables

1. **Feature Comparison Report**
   - Side-by-side matrix of greenfield vs `/template-create`
   - Detailed notes on implementation differences

2. **Gap Analysis Document**
   - List of missing features
   - Assessment of impact (high/medium/low)
   - User personas affected

3. **Recommendation**
   - Clear choice: A (merge), B (port), C (keep), or D (deprecate)
   - Justification with cost/benefit analysis
   - Implementation effort estimate

4. **Action Plan** (if changes recommended)
   - Specific tasks to close gaps
   - Priority order
   - Estimated hours per task

## Success Criteria

### Review Quality
- [ ] All greenfield initialization code reviewed
- [ ] Complete feature comparison matrix created
- [ ] Gaps identified with impact assessment
- [ ] Clear recommendation with justification

### Decision Quality
- [ ] Recommendation is actionable (can be implemented immediately)
- [ ] Trade-offs clearly articulated
- [ ] Cost/benefit analysis included
- [ ] User impact considered (beginner vs expert)

### Deliverable Quality
- [ ] Report is comprehensive (covers all aspects)
- [ ] Report is concise (no unnecessary detail)
- [ ] Report is actionable (clear next steps)
- [ ] Report includes code examples (if recommending changes)

## Out of Scope

- **Implementation**: This is a review task, not an implementation task
- **User Testing**: No need to conduct user interviews or surveys
- **Competitive Analysis**: No need to compare with other tools (Yeoman, create-react-app, etc.)
- **Complete Redesign**: Focus on incremental improvements, not wholesale rewrite

## Related Context

### Key Files to Review
- `installer/core/lib/greenfield_qa_session.py` (exists)
- `installer/core/commands/*.md` (check for greenfield-related commands)
- `installer/scripts/guardkit` or `installer/scripts/guardkit-init` (CLI entry points)
- Recent changes to `/template-create` (TASK-STND-773D, TASK-UX-3A8D)

### Reference Documentation
- [Template Philosophy Guide](docs/guides/template-philosophy.md)
- [Agent Enhancement with Boundary Sections](CLAUDE.md#agent-enhancement-with-boundary-sections)
- [Template Validation Guide](docs/guides/template-validation-guide.md)
- [GitHub Agent Best Practices Analysis](docs/analysis/github-agent-best-practices-analysis.md)

## Next Steps After Review

Based on the recommendation:

**If Option A (Merge)**: Create task to merge greenfield into `/template-create`
**If Option B (Port)**: Create tasks to port specific features to greenfield
**If Option C (Keep)**: Document decision and close review
**If Option D (Deprecate)**: Create deprecation plan task

---

## Notes

- This is a **review task** - use `/task-review TASK-5E55 --mode=decision --depth=standard`
- Focus on **decision quality** over implementation details
- The goal is **clarity on next steps**, not perfection
- User values `/template-create` improvements - ensure greenfield workflow is comparable

---

**Created**: 2025-11-26
**Estimated Effort**: 4 hours
**Priority**: High
**Complexity**: 5/10 (straightforward review, clear scope)
**Task Type**: Review/Analysis (decision-making)
