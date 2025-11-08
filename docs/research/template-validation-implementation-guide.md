# Template Validation Implementation Guide

**Date**: 2025-01-08
**Purpose**: Workflow guide for implementing the 4-phase template validation strategy
**Status**: Implementation Ready

---

## Executive Summary

This guide provides a structured approach to implementing TASK-043, TASK-044, TASK-045, and TASK-045A using the `/task-work` command and identifies opportunities for parallel development with Conductor + git worktrees.

**Total Effort**: 7-10 days (56-80 hours)
**Recommended Approach**: Sequential with parallel sub-tasks using Conductor
**Primary Tool**: `/task-work` for all implementation tasks

---

## Quick Reference

| Phase | Task | Duration | Parallel? | Conductor Worktrees |
|-------|------|----------|-----------|---------------------|
| **Phase 1** | TASK-043 | 1 day | Partial | 2-3 worktrees |
| **Phase 2** | TASK-044 | 3-5 days | Yes | 4-5 worktrees |
| **Phase 3** | TASK-045 | 2-3 days | Yes | 4 worktrees |
| **Phase 4** | TASK-045A | 1 day | No | N/A |

---

## Phase 1: TASK-043 - Extended Validation Flag

### Task Overview

**Task**: [TASK-043: Implement Extended Validation Flag](../../tasks/backlog/TASK-043-implement-extended-validation-flag.md)

**Goal**: Add `--validate` flag to `/template-create` with extended validation and report generation

**Duration**: 1 day (6-8 hours)

**Complexity**: 3/10 (Low-Medium)

**Why `/task-work`?**
- Clear implementation scope
- Standard feature development
- Automated quality gates beneficial
- Testing requirements well-defined

### Implementation Workflow

#### Step 1: Start Task with `/task-work`

```bash
cd ~/Projects/appmilla_github/taskwright

# Start TASK-043 in standard mode
/task-work TASK-043
```

**Expected Phases**:
1. ✓ Requirements Analysis (skipped - task is well-defined)
2. ✓ Implementation Planning (AI creates plan from task spec)
3. ✓ Architectural Review (Phase 2.5)
4. ✓ Implementation (Phase 3)
5. ✓ Testing (Phase 4)
6. ✓ Code Review (Phase 5)

**Estimated `/task-work` Duration**: 6-8 hours (single session)

### Parallel Development Opportunity (Limited)

**Can be parallelized** (if multiple developers or using Conductor for sub-tasks):

```bash
# Main repo - Foundation
cd ~/Projects/appmilla_github/taskwright
/task-work TASK-043

# While Phase 3 (Implementation) is in progress, split into worktrees:

# Worktree 1: Extended Validator Implementation
cd ~/conductor-worktrees/taskwright-validator
/task-create "Implement ExtendedValidator class (TASK-043)"
/task-work TASK-XXX
# → Focus: installer/global/lib/template_validation/extended_validator.py

# Worktree 2: Report Generator Implementation
cd ~/conductor-worktrees/taskwright-reports
/task-create "Implement ValidationReportGenerator class (TASK-043)"
/task-work TASK-YYY
# → Focus: installer/global/lib/template_validation/report_generator.py

# Worktree 3: Orchestrator Integration
cd ~/conductor-worktrees/taskwright-orchestrator
/task-create "Integrate --validate flag into orchestrator (TASK-043)"
/task-work TASK-ZZZ
# → Focus: installer/global/commands/lib/template_create_orchestrator.py
```

**Conductor Setup**:
```bash
# Create worktrees for parallel development
git worktree add ~/conductor-worktrees/taskwright-validator -b feature/task-043-validator
git worktree add ~/conductor-worktrees/taskwright-reports -b feature/task-043-reports
git worktree add ~/conductor-worktrees/taskwright-orchestrator -b feature/task-043-integration

# Each worktree has access to:
# - Same .claude/commands/* (via symlinks from install script)
# - Same .claude/agents/* (via symlinks)
# - Shared .claude/state (automatic state sync)
```

**Benefits**:
- 3 parallel development streams
- Each focused on one component
- Automatic state synchronization
- Merge PRs sequentially: validator → reports → orchestrator

**Recommended**: **No** for Phase 1 (too small, overhead not worth it)

### Phase 1 Deliverables

- [ ] `--validate` flag functional
- [ ] Extended validation runs after Phase 5.5
- [ ] `ExtendedValidator` class implemented
- [ ] `ValidationReportGenerator` class implemented
- [ ] Markdown reports generated
- [ ] Exit codes working (0/1/2)
- [ ] Tests passing (≥80% coverage)
- [ ] Documentation updated

---

## Phase 2: TASK-044 - Template Validate Command

### Task Overview

**Task**: [TASK-044: Create Template Validate Command](../../tasks/backlog/TASK-044-create-template-validate-command.md)

**Goal**: Create `/template-validate` command for comprehensive 16-section audit

**Duration**: 3-5 days (24-40 hours)

**Complexity**: 6/10 (Medium)

**Dependencies**: TASK-043 must be completed first

**Why `/task-work`?**
- Complex multi-component feature
- Clear architectural boundaries
- Quality gates critical (16 sections must be accurate)
- Integration testing required

### Implementation Workflow

#### Step 1: Foundation with `/task-work`

```bash
cd ~/Projects/appmilla_github/taskwright

# Ensure TASK-043 is completed and merged to main
git checkout main
git pull

# Start TASK-044
/task-work TASK-044
```

**Phase 2 (Planning) Output**:
The implementation plan should identify these components:
1. Command specification
2. Interactive orchestrator
3. Comprehensive auditor (16 sections)
4. Session management
5. Audit report generator

**Architectural Review (Phase 2.5)**:
- Review 16-section design
- Validate session save/resume approach
- Approve modular section architecture

#### Step 2: Parallel Development with Conductor

**After Phase 2.7 Checkpoint (Implementation Plan Approved)**:

Create parallel development streams:

```bash
# Foundation (Main Repo) - DO NOT parallelize
cd ~/Projects/appmilla_github/taskwright
# Keep working on infrastructure:
# - Command spec
# - Interactive orchestrator skeleton
# - Session management
# - Report generator

# === Parallel Worktrees (16 Sections) ===

# Worktree Group A: Technical Validation (Sections 1-7)
cd ~/conductor-worktrees

git worktree add taskwright-sections-1-4 -b feature/task-044-sections-1-4
git worktree add taskwright-sections-5-7 -b feature/task-044-sections-5-7

# Worktree Group B: Quality Assessment (Sections 8-13)
git worktree add taskwright-sections-8-10 -b feature/task-044-sections-8-10
git worktree add taskwright-sections-11-13 -b feature/task-044-sections-11-13

# Worktree Group C: Decision Framework (Sections 14-16)
git worktree add taskwright-sections-14-16 -b feature/task-044-sections-14-16
```

**Development Workflow**:

```bash
# === Main Repo: Foundation (Day 1) ===
cd ~/Projects/appmilla_github/taskwright
/task-create "TASK-044: Build foundation - orchestrator, session, reports"
/task-work TASK-044-FOUNDATION

# Deliverables:
# ✓ template-validate.md command spec
# ✓ TemplateValidateOrchestrator class (skeleton)
# ✓ AuditSession class (save/resume)
# ✓ AuditReportGenerator class
# ✓ Base AuditSection class (abstract)

# === Parallel Worktrees: Sections (Day 2-4) ===

# Worktree 1: Sections 1-4
cd ~/conductor-worktrees/taskwright-sections-1-4
/task-create "Implement audit sections 1-4 (Manifest, Settings, Docs, Templates)"
/task-work TASK-044-SEC-1-4
# → Implements: ManifestAnalysisSection, SettingsAnalysisSection,
#               DocumentationAnalysisSection, TemplateFilesAnalysisSection

# Worktree 2: Sections 5-7
cd ~/conductor-worktrees/taskwright-sections-5-7
/task-create "Implement audit sections 5-7 (Agents, README, Global)"
/task-work TASK-044-SEC-5-7
# → Implements: AIAgentsAnalysisSection, ReadmeReviewSection,
#               GlobalTemplateValidationSection

# Worktree 3: Sections 8-10
cd ~/conductor-worktrees/taskwright-sections-8-10
/task-create "Implement audit sections 8-10 (Source, Readiness, Scoring)"
/task-work TASK-044-SEC-8-10
# → Implements: ComparisonWithSourceSection, ProductionReadinessSection,
#               ScoringRubricSection

# Worktree 4: Sections 11-13
cd ~/conductor-worktrees/taskwright-sections-11-13
/task-create "Implement audit sections 11-13 (Findings, Testing, Market)"
/task-work TASK-044-SEC-11-13
# → Implements: DetailedFindingsSection, ValidationTestingSection,
#               MarketComparisonSection

# Worktree 5: Sections 14-16
cd ~/conductor-worktrees/taskwright-sections-14-16
/task-create "Implement audit sections 14-16 (Recommendations, Summary)"
/task-work TASK-044-SEC-14-16
# → Implements: FinalRecommendationsSection, TestingRecommendationsSection,
#               SummaryReportSection

# === Integration (Day 4-5) ===
# After all sections complete, merge PRs in order:
# 1. Foundation (main repo) → main
# 2. Sections 1-4 → main
# 3. Sections 5-7 → main
# 4. Sections 8-10 → main
# 5. Sections 11-13 → main
# 6. Sections 14-16 → main

# Final integration testing in main repo
cd ~/Projects/appmilla_github/taskwright
/task-create "TASK-044: Integration testing and final polish"
/task-work TASK-044-INTEGRATION
```

### Conductor State Management

**Automatic State Sync** (via symlinks from install script):
```bash
# All worktrees share:
~/.agentecflow/state/        # Global state (commands, agents)

# Each worktree has:
{worktree}/.claude/state/    # Local state (symlinked to main repo)

# Commands work identically in all worktrees:
cd ~/conductor-worktrees/taskwright-sections-1-4
/task-work TASK-044-SEC-1-4   # ✓ Works
/task-status                   # ✓ Shows all tasks across worktrees
```

### Parallel Development Timeline

**Day 1** (Sequential - Main Repo):
- Foundation implementation
- Base classes and infrastructure
- 1 developer or main session

**Days 2-4** (Parallel - Conductor Worktrees):
- 5 parallel streams (if team) or sequential sessions (if solo)
- Each implements 3-4 sections
- Independent development
- Automatic state sync via Taskwright

**Day 4-5** (Sequential - Main Repo):
- Merge PRs sequentially
- Integration testing
- End-to-end validation
- Documentation

### Benefits of Conductor for Phase 2

**With Conductor** (Team or Solo):
- ✅ 16 sections split into 5 logical groups
- ✅ Each worktree focuses on one group
- ✅ No merge conflicts (different files)
- ✅ Parallel testing (each worktree can run its section tests)
- ✅ State automatically synchronized
- ✅ Can work on multiple sections in different terminal sessions

**Without Conductor**:
- ❌ Sequential implementation of 16 sections
- ❌ Single branch (main or feature branch)
- ❌ Slower progress (no parallelization)
- ⚠️ Still works fine, just takes longer

**Recommendation**: **YES** - Conductor adds significant value for Phase 2

### Phase 2 Deliverables

- [ ] `/template-validate` command functional
- [ ] All 16 sections implemented
- [ ] Interactive section navigation
- [ ] Session save/resume working
- [ ] Inline fixes functional
- [ ] Comprehensive reports generated
- [ ] Tests passing (≥75% coverage)
- [ ] Documentation complete

---

## Phase 3: TASK-045 - AI-Assisted Validation

### Task Overview

**Task**: [TASK-045: Implement AI-Assisted Validation](../../tasks/backlog/TASK-045-implement-ai-assisted-validation.md)

**Goal**: Add AI assistance to sections 8, 11, 12, 13 to reduce audit time by 50-70%

**Duration**: 2-3 days (16-24 hours)

**Complexity**: 5/10 (Medium)

**Dependencies**: TASK-044 must be completed first

**Why `/task-work`?**
- AI integration benefits from architectural review
- Quality gates ensure AI accuracy
- Testing critical for AI validation

### Implementation Workflow

#### Step 1: Foundation with `/task-work`

```bash
cd ~/Projects/appmilla_github/taskwright

# Ensure TASK-044 is completed and merged to main
git checkout main
git pull

# Start TASK-045
/task-work TASK-045
```

**Phase 2 (Planning) Output**:
Components to implement:
1. AI analysis helper utilities
2. Section 8 AI enhancement (source comparison)
3. Section 11 AI enhancement (detailed findings)
4. Section 12 AI enhancement (validation testing)
5. Section 13 AI enhancement (market comparison)

#### Step 2: Parallel Development with Conductor

**After Phase 2.7 Checkpoint**:

```bash
# === Main Repo: AI Utilities (Day 1) ===
cd ~/Projects/appmilla_github/taskwright
/task-create "TASK-045: Build AI analysis utilities and framework"
/task-work TASK-045-FOUNDATION

# Deliverables:
# ✓ ai_analysis_helpers.py
# ✓ execute_task_agent()
# ✓ execute_analysis_agent()
# ✓ validate_ai_response()
# ✓ present_ai_findings()

# === Parallel Worktrees: AI Enhancements (Day 1-2) ===

# Worktree 1: Section 8 AI Enhancement
cd ~/conductor-worktrees/taskwright-ai-section-8
git worktree add . -b feature/task-045-ai-section-8
/task-create "Add AI assistance to Section 8 (Source Comparison)"
/task-work TASK-045-AI-SEC-8
# → Enhance ComparisonWithSourceSection with AI

# Worktree 2: Section 11 AI Enhancement
cd ~/conductor-worktrees/taskwright-ai-section-11
git worktree add . -b feature/task-045-ai-section-11
/task-create "Add AI assistance to Section 11 (Detailed Findings)"
/task-work TASK-045-AI-SEC-11
# → Enhance DetailedFindingsSection with AI

# Worktree 3: Section 12 AI Enhancement
cd ~/conductor-worktrees/taskwright-ai-section-12
git worktree add . -b feature/task-045-ai-section-12
/task-create "Add AI assistance to Section 12 (Validation Testing)"
/task-work TASK-045-AI-SEC-12
# → Enhance ValidationTestingSection with AI

# Worktree 4: Section 13 AI Enhancement
cd ~/conductor-worktrees/taskwright-ai-section-13
git worktree add . -b feature/task-045-ai-section-13
/task-create "Add AI assistance to Section 13 (Market Comparison)"
/task-work TASK-045-AI-SEC-13
# → Enhance MarketComparisonSection with AI

# === Integration (Day 3) ===
# Merge PRs in order:
# 1. Foundation (AI utilities) → main
# 2. Section 8 enhancement → main
# 3. Section 11 enhancement → main
# 4. Section 12 enhancement → main
# 5. Section 13 enhancement → main

# Final testing
cd ~/Projects/appmilla_github/taskwright
/task-create "TASK-045: End-to-end AI validation testing"
/task-work TASK-045-TESTING
```

### Parallel Development Timeline

**Day 1 Morning** (Sequential - Main Repo):
- AI utilities implementation
- Base AI helper functions
- 4 hours

**Day 1 Afternoon - Day 2** (Parallel - Conductor Worktrees):
- 4 parallel streams for sections 8, 11, 12, 13
- Each adds AI assistance to one section
- Independent development
- Can run in parallel or sequential sessions

**Day 3** (Sequential - Main Repo):
- Merge all AI enhancements
- End-to-end testing
- Validate AI accuracy vs manual
- Documentation

### Benefits of Conductor for Phase 3

**With Conductor**:
- ✅ 4 sections enhanced in parallel
- ✅ Each worktree tests AI accuracy independently
- ✅ Faster iteration on AI prompts
- ✅ Parallel experimentation with different AI approaches

**Without Conductor**:
- ⚠️ Sequential section enhancement (still manageable)
- ⚠️ 4 sections aren't too many to do one-by-one

**Recommendation**: **MAYBE** - Conductor helpful but optional for Phase 3

### Phase 3 Deliverables

- [ ] AI utilities implemented
- [ ] Section 8 AI-enhanced (source comparison)
- [ ] Section 11 AI-enhanced (detailed findings)
- [ ] Section 12 AI-enhanced (validation testing)
- [ ] Section 13 AI-enhanced (market comparison)
- [ ] AI accuracy ≥85% vs manual
- [ ] Human review/override working
- [ ] Tests passing (≥75% coverage)
- [ ] Documentation complete

---

## Conductor Workflow Summary

### When to Use Conductor

**Use Conductor When**:
- ✅ Task has 3+ independent components that can be developed in parallel
- ✅ Components have clear boundaries (different files)
- ✅ Team has multiple developers OR solo dev wants parallel sessions
- ✅ Task duration > 2 days

**Don't Use Conductor When**:
- ❌ Task is < 1 day (overhead not worth it)
- ❌ Components are tightly coupled (frequent conflicts)
- ❌ Solo developer doing sequential work

### Conductor Setup (One-time)

```bash
# 1. Install Taskwright (if not already)
cd ~/Projects/appmilla_github/taskwright
./installer/scripts/install.sh

# 2. Create conductor worktrees directory
mkdir -p ~/conductor-worktrees

# 3. Verify symlinks work
cd ~/conductor-worktrees
git worktree add taskwright-test -b test-worktree
cd taskwright-test
ls .claude/commands/  # Should show all commands via symlinks
ls .claude/agents/    # Should show all agents via symlinks
/task-status          # Should work

# 4. Remove test worktree
cd ~/Projects/appmilla_github/taskwright
git worktree remove taskwright-test
git branch -d test-worktree
```

### Conductor Workflow Pattern

```bash
# === Phase 1: Foundation (Main Repo) ===
cd ~/Projects/appmilla_github/taskwright
/task-work TASK-XXX
# → Build infrastructure, base classes

# === Phase 2: Parallel Development (Worktrees) ===

# Create worktrees
git worktree add ~/conductor-worktrees/component-a -b feature/component-a
git worktree add ~/conductor-worktrees/component-b -b feature/component-b
git worktree add ~/conductor-worktrees/component-c -b feature/component-c

# Develop in parallel (separate terminal sessions or team)
cd ~/conductor-worktrees/component-a
/task-create "Implement Component A"
/task-work TASK-XXX-A

cd ~/conductor-worktrees/component-b
/task-create "Implement Component B"
/task-work TASK-XXX-B

cd ~/conductor-worktrees/component-c
/task-create "Implement Component C"
/task-work TASK-XXX-C

# === Phase 3: Integration (Main Repo) ===

# Merge PRs in dependency order
cd ~/Projects/appmilla_github/taskwright
gh pr create --head feature/component-a --title "Component A"
gh pr merge feature/component-a --squash

gh pr create --head feature/component-b --title "Component B"
gh pr merge feature/component-b --squash

gh pr create --head feature/component-c --title "Component C"
gh pr merge feature/component-c --squash

# Integration testing
/task-create "Integration testing for TASK-XXX"
/task-work TASK-XXX-INTEGRATION

# Cleanup worktrees
git worktree remove ~/conductor-worktrees/component-a
git worktree remove ~/conductor-worktrees/component-b
git worktree remove ~/conductor-worktrees/component-c
```

---

## Implementation Recommendations

### For Solo Developer

**Phase 1 (TASK-043)**:
- ✅ Use `/task-work TASK-043` in main repo
- ❌ Skip Conductor (too small)
- **Duration**: 1 day

**Phase 2 (TASK-044)**:
- ✅ Use `/task-work TASK-044` for foundation
- ✅ Use Conductor for sections (optional but recommended)
- **Benefit**: Can work on sections in parallel terminal sessions
- **Duration**: 3-5 days (3 days with Conductor, 5 days without)

**Phase 3 (TASK-045)**:
- ✅ Use `/task-work TASK-045` for foundation
- ⚠️ Use Conductor for sections (optional)
- **Benefit**: Can experiment with AI approaches in parallel
- **Duration**: 2-3 days (2 days with Conductor, 3 days without)

**Total**: 6-9 days (6 days with Conductor, 9 days without)

### For Team (2-3 Developers)

**Phase 1 (TASK-043)**:
- ✅ One developer: `/task-work TASK-043` in main repo
- **Duration**: 1 day

**Phase 2 (TASK-044)**:
- ✅ Lead dev: Foundation in main repo
- ✅ Team: Split 5 worktrees across 2-3 developers
- **Worktree Assignment**:
  - Dev 1: Sections 1-4, Sections 5-7
  - Dev 2: Sections 8-10, Sections 11-13
  - Dev 3: Sections 14-16, Integration
- **Duration**: 2-3 days (parallel)

**Phase 3 (TASK-045)**:
- ✅ Lead dev: AI utilities in main repo
- ✅ Team: Split 4 worktrees across developers
- **Worktree Assignment**:
  - Dev 1: Section 8, Section 11
  - Dev 2: Section 12, Section 13
- **Duration**: 1-2 days (parallel)

**Total**: 4-6 days (with team and Conductor)

---

## Timeline Comparison

### Sequential Approach (No Conductor)

```
Week 1:
Mon: TASK-043 (Phase 1) ✓
Tue-Thu: TASK-044 Foundation + Sections 1-7
Fri-Mon: TASK-044 Sections 8-16
Tue: TASK-044 Integration + Testing ✓

Week 2:
Wed: TASK-045 Foundation
Thu: TASK-045 Sections 8-13
Fri: TASK-045 Integration + Testing ✓

Total: 9 days
```

### Parallel Approach (Conductor - Solo)

```
Week 1:
Mon: TASK-043 (Phase 1) ✓
Tue AM: TASK-044 Foundation
Tue PM-Wed: TASK-044 Sections 1-7 (worktree 1) + Sections 8-13 (worktree 2) parallel
Thu: TASK-044 Sections 14-16 (worktree 3) + Integration ✓
Fri: TASK-045 Foundation + Start sections

Week 2:
Mon: TASK-045 Sections 8-13 (parallel worktrees)
Tue: TASK-045 Integration + Testing ✓

Total: 6 days
```

### Parallel Approach (Conductor - Team of 3)

```
Week 1:
Mon: TASK-043 (Dev 1) ✓
Tue: TASK-044 Foundation (Dev 1) + Sections 1-4 (Dev 1) + Sections 5-7 (Dev 2) + Sections 8-10 (Dev 3) - PARALLEL
Wed: TASK-044 Sections 11-13 (Dev 2) + Sections 14-16 (Dev 3) + Integration (Dev 1) ✓
Thu: TASK-045 Foundation (Dev 1) + Sections 8,11 (Dev 2) + Sections 12,13 (Dev 3) - PARALLEL
Fri: TASK-045 Integration + Testing (Team) ✓

Total: 4-5 days
```

---

## Quality Gates & Testing Strategy

### Phase 1 (TASK-043)

**Automated Quality Gates** (via `/task-work`):
- ✅ Phase 2.5: Architectural Review
  - Validate extended validator design
  - Approve report generation approach
- ✅ Phase 4: Test Enforcement
  - Unit tests ≥80% coverage
  - Integration tests pass
  - Extended validation works with existing templates
- ✅ Phase 5: Code Review
  - SOLID compliance
  - Pattern consistency
  - Documentation completeness

**Manual Testing**:
```bash
# Test with existing templates
/template-create --validate --dry-run

# Check report generation
ls -la validation-report.md

# Verify exit codes
/template-create --validate
echo $?  # Should be 0, 1, or 2 based on quality
```

### Phase 2 (TASK-044)

**Automated Quality Gates** (via `/task-work` on each sub-task):
- ✅ Each section task gets architectural review
- ✅ Each section task gets test enforcement
- ✅ Integration task validates complete workflow

**Manual Testing**:
```bash
# Test each section independently
/template-validate ./templates/test-template --sections 1
/template-validate ./templates/test-template --sections 2
# ... etc

# Test session save/resume
/template-validate ./templates/test-template --sections 1-5
# Interrupt (Ctrl+C)
/template-validate ./templates/test-template --resume <session-id>

# Test full audit
/template-validate ./templates/test-template
```

**Integration Checkpoint**:
- All 16 sections pass independently
- Session save/resume works
- Reports generated correctly
- Interactive UI smooth

### Phase 3 (TASK-045)

**Automated Quality Gates** (via `/task-work` on each AI enhancement):
- ✅ AI accuracy validation (compare to manual baseline)
- ✅ Response schema validation
- ✅ Fallback to manual if AI fails

**AI Accuracy Testing**:
```bash
# For each AI-enhanced section:

# 1. Run manual baseline
/template-validate ./templates/test-template --sections 8 --no-ai
# Save manual results

# 2. Run AI-enhanced
/template-validate ./templates/test-template --sections 8 --ai
# Save AI results

# 3. Compare accuracy
python scripts/compare_ai_vs_manual.py

# Target: ≥85% agreement
```

**Manual Testing**:
```bash
# Test AI assistance
/template-validate ./templates/test-template --sections 8,11,12,13

# Test human override
# → During section 8, override AI findings
# → Verify override is saved

# Test fallback
# → Disable AI (simulate failure)
# → Verify fallback to manual
```

---

## Risk Mitigation

### Risk 1: Conductor Worktree Merge Conflicts

**Scenario**: Multiple worktrees modify overlapping files

**Mitigation**:
- Establish clear file boundaries for each worktree
- Phase 2: Each worktree owns specific section files
- Phase 3: Each worktree enhances one section file
- Use PR review to catch conflicts early

**Example Boundary (TASK-044)**:
```
Worktree 1 (Sections 1-4):
- comprehensive_auditor.py (lines 1-300)
  - ManifestAnalysisSection
  - SettingsAnalysisSection
  - DocumentationAnalysisSection
  - TemplateFilesAnalysisSection

Worktree 2 (Sections 5-7):
- comprehensive_auditor.py (lines 301-500)
  - AIAgentsAnalysisSection
  - ReadmeReviewSection
  - GlobalTemplateValidationSection

# No overlap = No conflicts
```

### Risk 2: Task Dependencies in `/task-work`

**Scenario**: Sub-tasks depend on each other, but being worked in parallel

**Mitigation**:
- Foundation first (sequential)
- Then parallel on independent components
- Integration last (sequential)

**Example (TASK-044)**:
```
Day 1: Foundation (main repo)
- Base classes
- Session management
- Report generator
✓ All sections can now depend on these

Day 2-4: Sections (parallel worktrees)
- Each section implements AuditSection interface
- No cross-dependencies
✓ Can work independently

Day 5: Integration (main repo)
- Merge all sections
- Test complete workflow
✓ Validate everything works together
```

### Risk 3: State Synchronization Across Worktrees

**Scenario**: Task state gets out of sync between worktrees

**Mitigation**:
- Taskwright handles this automatically via symlinks
- `.claude/state` is symlinked to main repo
- All worktrees share same state

**Verify State Sync**:
```bash
# Main repo
cd ~/Projects/appmilla_github/taskwright
/task-create "Test task"
/task-status  # Shows TASK-XXX

# Worktree
cd ~/conductor-worktrees/taskwright-test
/task-status  # Shows TASK-XXX (same state)
```

### Risk 4: Quality Degradation with Parallel Development

**Scenario**: Parallel worktrees skip quality gates

**Mitigation**:
- Use `/task-work` in EVERY worktree
- Each worktree gets full quality gates
- Integration task validates complete system

**Quality Gate Coverage**:
```bash
# Each worktree task goes through:
/task-work TASK-XXX-COMPONENT-A
# ✓ Phase 2.5: Architectural review
# ✓ Phase 4: Test enforcement (≥75% coverage)
# ✓ Phase 5: Code review

# Integration task validates:
/task-work TASK-XXX-INTEGRATION
# ✓ All components work together
# ✓ End-to-end tests pass
# ✓ No integration regressions
```

---

## Success Metrics

### Phase 1 (TASK-043)

**Quantitative**:
- ✅ Implementation complete in 1 day
- ✅ Test coverage ≥80%
- ✅ Extended validation runs in <5 minutes
- ✅ Exit codes 100% accurate

**Qualitative**:
- ✅ Reports are actionable
- ✅ Users understand findings
- ✅ Validation improves template quality

### Phase 2 (TASK-044)

**Quantitative**:
- ✅ Implementation complete in 3-5 days (3 with Conductor)
- ✅ All 16 sections functional
- ✅ Test coverage ≥75%
- ✅ Session save/resume 100% reliable

**Qualitative**:
- ✅ Audit feels systematic
- ✅ Interactive UI is smooth
- ✅ Reports are comprehensive
- ✅ Decision framework is clear

### Phase 3 (TASK-045)

**Quantitative**:
- ✅ Implementation complete in 2-3 days (2 with Conductor)
- ✅ AI accuracy ≥85% vs manual
- ✅ Audit time reduced by 50-70%
- ✅ Test coverage ≥75%

**Qualitative**:
- ✅ AI insights are accurate
- ✅ Human override is easy
- ✅ Fallback works reliably
- ✅ Audit quality maintained

---

## Appendix A: Command Reference

### Task Management

```bash
# Create task
/task-create "Task description" [priority:high|medium|low]

# Work on task
/task-work TASK-XXX [--mode=standard|tdd]

# Complete task
/task-complete TASK-XXX

# Check status
/task-status [TASK-XXX]
```

### Conductor Worktrees

```bash
# Create worktree
git worktree add <path> -b <branch-name>

# List worktrees
git worktree list

# Remove worktree
git worktree remove <path>

# Cleanup stale worktrees
git worktree prune
```

### Testing Validation

```bash
# Test extended validation (TASK-043)
/template-create --validate
/template-create --dry-run --validate

# Test comprehensive audit (TASK-044)
/template-validate <path>
/template-validate <path> --sections 1,4,7
/template-validate <path> --sections 1-7
/template-validate <path> --resume <session-id>

# Test AI assistance (TASK-045)
/template-validate <path> --sections 8,11,12,13
/template-validate <path> --no-ai  # Disable AI, manual only
```

---

## Appendix B: Directory Structure

### After TASK-043

```
installer/global/
├── commands/
│   ├── template-create.md (updated with --validate flag)
│   └── lib/
│       └── template_create_orchestrator.py (Phase 5.7 added)
└── lib/
    └── template_validation/
        ├── extended_validator.py (NEW)
        └── report_generator.py (NEW)

tests/
├── unit/
│   └── test_extended_validator.py (NEW)
└── integration/
    └── test_validate_flag.py (NEW)
```

### After TASK-044

```
installer/global/
├── commands/
│   ├── template-validate.md (NEW)
│   └── lib/
│       └── template_validate_interactive.py (NEW)
└── lib/
    └── template_validation/
        ├── comprehensive_auditor.py (NEW)
        ├── audit_session.py (NEW)
        └── audit_report_generator.py (NEW)

tests/
├── unit/
│   └── test_comprehensive_auditor.py (NEW)
└── integration/
    └── test_template_validate_command.py (NEW)
```

### After TASK-045

```
installer/global/
└── lib/
    └── template_validation/
        ├── ai_analysis_helpers.py (NEW)
        └── comprehensive_auditor.py (updated with AI)

tests/
├── unit/
│   └── test_ai_assisted_validation.py (NEW)
└── integration/
    └── test_ai_validation_e2e.py (NEW)
```

---

## Phase 4: TASK-045A - Documentation Updates (Day 10)

### Task Overview

**Task**: [TASK-045A: Update Documentation for Template Validation](../../tasks/backlog/TASK-045A-update-validation-documentation.md)

**Goal**: Update all documentation to reflect the 3-level validation system and provide comprehensive user guides

**Duration**: 1 day (6-8 hours)

**Complexity**: 3/10 (Low-Medium)

**Why `/task-work`?**
- Documentation benefits from quality review
- Ensures thorough coverage
- Validates examples work
- Tests all links

### Implementation Workflow

```bash
cd ~/Projects/appmilla_github/taskwright

# Ensure all previous phases completed
git checkout main
git pull

# Start documentation task
/task-work TASK-045A
```

**Expected Phases**:
1. ✓ Requirements Analysis (skipped - task is well-defined)
2. ✓ Implementation Planning
3. ✓ Implementation (documentation updates)
4. ✓ Testing (verify examples, links)
5. ✓ Code Review (documentation review)

### Documentation Updates

**Files to Create**:
- `docs/guides/template-validation-guide.md` - Main user guide
- `docs/guides/template-validation-workflows.md` - Common workflows
- `docs/guides/template-validation-ai-assistance.md` - AI features

**Files to Modify**:
- `CLAUDE.md` - Add validation section
- `README.md` - Link to validation guides
- `installer/global/commands/template-create.md` - Document `--validate` flag
- `docs/guides/template-commands-getting-started.md` - Reference validation
- `docs/workflows/template-creation-workflow.md` - Add validation step

### Parallel Development Opportunity

**Recommendation**: **No** - Documentation task is best done sequentially after all features complete

**Why Sequential**:
- Documentation should reflect actual implementation
- Examples need working features to test
- Consistency across all docs requires single author/review
- 1 day duration doesn't benefit from parallelization

### Phase 4 Deliverables

- [ ] CLAUDE.md updated with validation section
- [ ] User guides created (3 guides)
- [ ] Command docs updated
- [ ] Research docs linked
- [ ] FAQ section added
- [ ] All examples tested
- [ ] All links verified
- [ ] Documentation reviewed

### Completion Criteria

```bash
# Test all documented examples
/template-create --validate
/template-validate ./templates/test-template
/template-validate ./templates/test-template --sections 1,4,7

# Verify all links
find docs -name "*.md" -exec grep -l "template-validation" {} \;

# Check for broken links
# (manual verification or use markdown link checker)
```

---

## Conclusion

This implementation guide provides a structured path for implementing the 4-phase template validation strategy using `/task-work` and Conductor.

**Key Takeaways**:

1. **Use `/task-work` for all implementation** - Ensures quality gates and comprehensive testing
2. **Use Conductor for TASK-044** - Significant benefit for 16-section parallelization
3. **Use Conductor optionally for TASK-045** - Helpful but not critical for 4 sections
4. **Documentation last (TASK-045A)** - After all features complete
5. **Solo developer**: 7 days with Conductor, 10 days without
6. **Team of 3**: 5-6 days with Conductor

**Next Steps**:
1. Complete TASK-043 with `/task-work TASK-043`
2. Set up Conductor worktrees for TASK-044
3. Implement TASK-044 foundation → parallel sections → integration
4. Implement TASK-045 with AI assistance
5. Complete TASK-045A documentation updates

---

**Document Status**: Implementation Ready
**Version**: 1.0
**Last Updated**: 2025-01-08
**Related**: [Template Validation Strategy](./template-validation-strategy.md)
