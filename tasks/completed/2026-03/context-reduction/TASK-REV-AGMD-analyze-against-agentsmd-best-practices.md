---
id: TASK-REV-AGMD
title: Analyze FEAT-CR01 changes against GitHub AGENTS.md best practices
status: review_complete
created: 2026-02-06T02:00:00+00:00
updated: 2026-02-06T15:00:00+00:00
completed: 2026-02-06T15:00:00+00:00
priority: high
tags:
- review
- best-practices
- context-reduction
- quality-assurance
task_type: review
decision_required: true
complexity: 4
parent_feature: FEAT-CR01
related_documents:
- tasks/backlog/context-reduction/README.md
- tasks/backlog/context-reduction/IMPLEMENTATION-GUIDE.md
- .claude/reviews/TASK-REV-CROPT-review-report.md
external_references:
- url: https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/
  title: "How to write a great AGENTS.md – lessons from over 2,500 repositories"
  retrieved: 2026-02-06
review_results:
  mode: code-quality
  depth: standard
  score: 100
  findings_count: 5
  recommendations_count: 3
  decision: accept
  report_path: .claude/reviews/TASK-REV-AGMD-review-report.md
  completed_at: 2026-02-06T15:00:00Z
---

# Review: Analyze FEAT-CR01 Changes Against AGENTS.md Best Practices

## Background

The FEAT-CR01 feature (Context Reduction via Path-Gating and Trimming) has planned significant reductions to core documentation files. While the goal of reducing token usage is valid, there is concern that the trimming approach may inadvertently remove content that aligns with GitHub's AGENTS.md best practices.

**User Concern:** "I saw some task summary output which said DO/DON'T sections had been removed for example"

This review will ensure context reduction preserves essential best practices while achieving token savings.

## GitHub AGENTS.md Best Practices Reference

Based on GitHub's analysis of 2,500+ repositories (retrieved 2026-02-06):

### 6 Core Sections (Must Preserve)

1. **Persona/Role Definition**
   - Clear agent identity and expertise
   - Tone and communication style
   - What the agent is an expert in

2. **Executable Commands**
   - Specific commands with flags (not just tool names)
   - Exact syntax examples
   - When to use each command

3. **Project Knowledge**
   - Directory structure overview
   - Key technologies and versions
   - Architecture decisions

4. **Code Style Examples**
   - Real code snippets over verbose explanations
   - Pattern examples from actual codebase
   - Formatting conventions

5. **Boundaries (Three-Tier System)** ⚠️ CRITICAL
   - **DO**: Actions agent should always take
   - **ASK FIRST**: Actions requiring human confirmation
   - **DON'T**: Actions agent should never take
   - This three-tier system is explicitly recommended by GitHub

6. **Testing/Validation**
   - How to run tests
   - Coverage expectations
   - Validation commands

### Key Principles

- **Code over prose**: Real snippets beat verbose explanations
- **Specific over generic**: Exact commands with flags, not tool names
- **Examples are documentation**: Show, don't tell
- **Clear boundaries**: Explicit DO/DON'T/ASK FIRST sections

## Review Objectives

1. **Audit planned changes** - Review all FEAT-CR01 task specifications
2. **Map to best practices** - Identify which best practices each task affects
3. **Risk assessment** - Flag tasks that may remove critical content
4. **Mitigation recommendations** - Provide specific guidance to preserve best practices
5. **Update task specs** - Add constraints to prevent best practice removal

## Scope

### Files to Analyze

**Core Documentation (Wave 1-2):**
- TASK-CR-001: Root CLAUDE.md (996 → 300 lines planned)
- TASK-CR-002: .claude/CLAUDE.md (113 → 30 lines planned)
- TASK-CR-004: graphiti-knowledge.md content trim

**Template Documentation (Wave 3-4):**
- TASK-CR-T01: FastAPI CLAUDE.md (1,056 → 450 lines planned)
- TASK-CR-T02: Consolidate duplicated examples
- TASK-CR-T03: Trim oversized agent-ext files
- TASK-CR-T04: Standardize agent role sections

### Best Practice Mapping Matrix

| Best Practice | Affected Tasks | Risk Level |
|---------------|----------------|------------|
| DO/DON'T/ASK FIRST boundaries | CR-001, CR-002, CR-T01 | HIGH |
| Code examples preservation | CR-T02, CR-T03, CR-T04 | MEDIUM |
| Persona/role definitions | CR-T04 | MEDIUM |
| Executable commands | CR-001, CR-002 | MEDIUM |
| Project knowledge | CR-001, CR-004 | LOW |
| Testing instructions | CR-001, CR-002 | MEDIUM |

## Key Questions to Address

### Q1: DO/DON'T Section Preservation
- Do current CLAUDE.md files have explicit DO/DON'T/ASK FIRST sections?
- Are these sections being preserved or marked for removal?
- If removed, where will this boundary guidance live?

### Q2: Code Examples vs Prose
- Are tasks removing code examples in favor of trimming?
- Is the "code over prose" principle being followed?
- Are we accidentally removing examples while keeping prose?

### Q3: Command Specificity
- Are specific command examples being preserved?
- Is the trimming removing command flags/options?
- Will users still have exact syntax references?

### Q4: Agent Role Sections
- TASK-CR-T04 "standardizes" 32 agent role sections
- Does standardization mean removal of specialized guidance?
- Are three-tier boundaries preserved in agent files?

### Q5: Template-Specific Guidance
- FastAPI CLAUDE.md reducing from 1,056 to 450 lines (57% reduction)
- What specific sections are being removed?
- Are technology-specific best practices preserved?

## Expected Deliverables

1. **Best Practices Compliance Matrix** - Each task rated against 6 core sections
2. **Risk Register** - Tasks that may violate best practices
3. **Mitigation Recommendations** - Specific constraints to add to task specs
4. **Updated Task Specs** - Modified acceptance criteria to preserve best practices
5. **Decision Summary** - Proceed as-is, modify tasks, or add safeguards

## Review Mode

- **Mode**: code-quality (assessing compliance with external standards)
- **Depth**: standard (1-2 hours)
- **Focus**: Best practices preservation during optimization

## Acceptance Criteria

- [x] All 7 trimming tasks audited against 6 best practice sections
- [x] DO/DON'T/ASK FIRST presence verified in current files (60+ instances found)
- [x] Risk register with severity ratings (high/medium/low)
- [x] Mitigation recommendations for each high-risk item (all mitigated)
- [x] Updated acceptance criteria for affected tasks (no updates needed)
- [x] Human decision checkpoint executed (Accept)

## Methodology

### Phase 1: Current State Audit
1. Read current CLAUDE.md files (root, .claude/, templates)
2. Identify existing DO/DON'T sections
3. Identify existing code examples
4. Map current structure to 6 core sections

### Phase 2: Planned Change Analysis
1. Read each task specification
2. Identify what content is marked for removal
3. Cross-reference with best practices

### Phase 3: Gap Analysis
1. Create compliance matrix
2. Identify violations
3. Rate risk severity

### Phase 4: Recommendations
1. Propose mitigation strategies
2. Update task acceptance criteria
3. Present decision checkpoint

## Decision Checkpoint Options

After review completion:
- **[A]ccept** - Tasks are already best-practice compliant, proceed
- **[M]odify** - Update task specs with recommended constraints
- **[R]evise** - Request deeper analysis on specific concern
- **[H]alt** - Pause FEAT-CR01 until best practices integrated

## Next Steps After Review

1. If tasks need modification, update individual task files
2. Add explicit "Preserve" sections to task acceptance criteria
3. Consider adding best practices checklist to IMPLEMENTATION-GUIDE.md
4. Execute Wave 1 tasks with enhanced constraints
