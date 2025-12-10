# User Acceptance Test Scenarios - Clarifying Questions Feature

This document defines comprehensive user acceptance test (UAT) scenarios for the clarifying questions feature. These scenarios should be executed manually to validate the end-to-end functionality across all three clarification contexts.

## Test Environment Setup

### Prerequisites
- GuardKit development environment installed
- All clarification modules implemented (Waves 1-3 complete)
- Test tasks directory available
- Access to both command line and workflow execution

### Test Data
Create the following test tasks before beginning UAT:

```bash
# Low complexity task (should skip clarification)
/task-create "Add logout button to header" complexity:2

# Medium complexity task (should use quick mode)
/task-create "Implement email validation in registration form" complexity:4

# High complexity task (should use full mode)
/task-create "Add JWT authentication with refresh token support" complexity:7

# Review task
/task-create "Review authentication architecture for security vulnerabilities" task_type:review
```

---

## Scenario 1: task-work with Full Clarification

**Objective**: Verify full clarification mode for high-complexity tasks

**Context**: Implementation planning (Context C)

**Complexity**: 6

**Duration**: 10-15 minutes

### Setup
```bash
/task-create "Implement user profile management with avatar upload" complexity:6
```

### Steps
1. Execute task-work command:
   ```bash
   /task-work TASK-{generated-id}
   ```

2. **Verify Phase 1.5 triggers**
   - [ ] System displays "Clarifying Questions" header
   - [ ] Shows full mode indicator (no timeout)
   - [ ] Displays 4-6 questions across multiple categories

3. **Answer questions interactively**
   - [ ] Question 1 (Scope): Choose [S]tandard
   - [ ] Question 2 (Testing): Choose [I]ntegration
   - [ ] Question 3 (Error Handling): Choose [C]omprehensive
   - [ ] Question 4 (Documentation): Choose [Y]es
   - [ ] Additional questions as presented

4. **Verify answers recorded**
   - [ ] System shows summary of selections
   - [ ] Confirms proceeding to planning

5. **Check frontmatter persistence**
   ```bash
   cat tasks/in_progress/TASK-{id}.md
   ```
   - [ ] `clarification:` section exists
   - [ ] `context: implementation_planning`
   - [ ] `mode: full`
   - [ ] All 4+ decisions recorded
   - [ ] `default_used: false` for answered questions

6. **Verify Phase 2 uses clarification**
   - [ ] Implementation plan reflects Standard scope
   - [ ] Includes integration tests
   - [ ] Comprehensive error handling mentioned
   - [ ] Documentation tasks included

### Expected Results
- ✅ Full clarification mode triggered for complexity 6
- ✅ All answers persisted to frontmatter
- ✅ Planning phase reflects user's choices
- ✅ No default values used (user explicitly answered)

### Success Criteria
- Clarification decisions match implementation plan content
- Frontmatter YAML is valid and complete
- User feels guided through planning process

---

## Scenario 2: task-work with Quick Timeout

**Objective**: Verify quick mode timeout behavior applies defaults

**Context**: Implementation planning (Context C)

**Complexity**: 4

**Duration**: 5 minutes

### Setup
```bash
/task-create "Add password strength indicator to registration" complexity:4
```

### Steps
1. Execute task-work:
   ```bash
   /task-work TASK-{generated-id}
   ```

2. **Verify quick mode triggers**
   - [ ] System displays "Quick Clarification (15s timeout)" message
   - [ ] Shows countdown or timeout indicator
   - [ ] Displays 2-3 key questions

3. **Let timeout expire** (do not type anything)
   - [ ] Wait for 15 seconds
   - [ ] System auto-applies defaults
   - [ ] Shows "Using defaults due to timeout" message

4. **Check frontmatter**
   ```bash
   cat tasks/in_progress/TASK-{id}.md
   ```
   - [ ] `mode: quick`
   - [ ] All decisions have `default_used: true`
   - [ ] Timeout timestamp recorded

5. **Verify workflow continues**
   - [ ] Phase 2 executes with defaults
   - [ ] No workflow interruption
   - [ ] Implementation plan generated

### Expected Results
- ✅ Quick mode triggered for complexity 4
- ✅ Timeout applied after 15 seconds
- ✅ Defaults used for all questions
- ✅ Workflow continues seamlessly

### Success Criteria
- Timeout behavior is clear to user
- Defaults are reasonable
- No manual intervention required after timeout

---

## Scenario 3: task-review with Review Scope (Context A)

**Objective**: Verify review scope clarification and implement handler

**Context**: Review scope (Context A) + Implementation preferences (Context B)

**Duration**: 15-20 minutes

### Setup
```bash
/task-create "Architectural review of payment processing system" task_type:review complexity:6
```

### Steps

#### Part A: Review Scope Clarification

1. Execute task-review:
   ```bash
   /task-review TASK-{generated-id} --mode=decision
   ```

2. **Verify Context A triggers**
   - [ ] "Review Scope Clarification" header shown
   - [ ] 3-4 questions about review focus displayed
   - [ ] Questions ask about: scope, depth, criteria, specific areas

3. **Answer review scope questions**
   - [ ] Review Focus: Choose [S]ecurity
   - [ ] Review Depth: Choose [C]omprehensive
   - [ ] Specific Areas: Choose [A]uthentication and [P]ayment processing
   - [ ] Timeframe: Choose [1] 1-2 hours

4. **Verify review focuses on selected areas**
   - [ ] Review executes with security focus
   - [ ] Comprehensive depth analysis performed
   - [ ] Report focuses on auth + payment areas
   - [ ] Time budget respected

5. **Check review frontmatter**
   ```bash
   cat tasks/in_progress/TASK-{id}.md
   ```
   - [ ] `clarification.context: review_scope`
   - [ ] Security focus recorded
   - [ ] Comprehensive depth noted

#### Part B: Implementation Preferences (Context B)

6. **At review checkpoint, choose [I]mplement**
   - [ ] System presents implementation options
   - [ ] Shows 3 options from review findings

7. **Verify Context B triggers**
   - [ ] "Implementation Preferences" header shown
   - [ ] Questions ask about: scope, priority, approach
   - [ ] 2-3 questions displayed

8. **Answer implementation preferences**
   - [ ] Scope: Choose [S]tandard
   - [ ] Priority: Choose [H]igh priority items only
   - [ ] Testing: Choose [I]ntegration tests

9. **Verify subtasks reflect preferences**
   - [ ] Standard scope subtasks created (not all recommendations)
   - [ ] Only high-priority items included
   - [ ] Integration test tasks present

10. **Check implementation clarification persistence**
    - [ ] `clarification.context: implementation_prefs` in subtask metadata
    - [ ] Preferences applied consistently across subtasks

### Expected Results
- ✅ Context A guides review focus
- ✅ Context B tailors implementation
- ✅ Both clarifications persist independently
- ✅ Subtasks match preferences

### Success Criteria
- Review focuses on specified areas (not generic)
- Subtasks reflect user's implementation preferences
- Two independent clarification contexts work correctly

---

## Scenario 4: feature-plan End-to-End

**Objective**: Verify full feature-plan workflow with clarification propagation

**Context**: Review scope (Context A) + Implementation preferences (Context B)

**Duration**: 20-25 minutes

### Setup
None (feature-plan creates task automatically)

### Steps

1. Execute feature-plan:
   ```bash
   /feature-plan "add dark mode support to the application"
   ```

#### Phase 1: Review Task Creation
2. **Verify automatic review task creation**
   - [ ] System creates review task
   - [ ] Task ID shown: `TASK-{generated-id}`
   - [ ] Description includes "dark mode"

#### Phase 2: Context A - Review Scope
3. **Answer review scope questions**
   - [ ] Review Focus: Choose [F]easibility and [A]rchitecture
   - [ ] Analysis Depth: Choose [S]tandard
   - [ ] Areas to Examine: Choose [C]omponents and [S]tate management

4. **Verify review executes with focus**
   - [ ] Review findings focus on feasibility
   - [ ] Architecture analysis performed
   - [ ] Component and state management covered

5. **Review findings displayed**
   - [ ] 5-7 recommendations shown
   - [ ] 3 implementation options presented:
     - Minimal (CSS variables only)
     - Standard (CSS + toggle component)
     - Complete (Full theme system with persistence)

#### Phase 3: Context B - Implementation Preferences
6. **At [I]mplement decision point, answer preferences**
   - [ ] Implementation Scope: Choose [C]omplete
   - [ ] Priority: Choose [A]ll recommendations
   - [ ] Testing Level: Choose [U]nit + [I]ntegration
   - [ ] Documentation: Choose [Y]es

7. **Verify subtask generation**
   - [ ] 5-7 subtasks created (all recommendations)
   - [ ] Tasks include:
     - [ ] Add CSS variables for theming
     - [ ] Create theme toggle component
     - [ ] Implement theme state management
     - [ ] Add persistence (localStorage)
     - [ ] Update existing components
     - [ ] Add unit tests
     - [ ] Add integration tests
     - [ ] Update documentation

8. **Check wave organization**
   ```bash
   cat tasks/backlog/dark-mode/IMPLEMENTATION-GUIDE.md
   ```
   - [ ] Subtasks organized into waves
   - [ ] Parallel execution opportunities noted
   - [ ] Conductor workspace names included

9. **Verify clarification propagation**
   - [ ] Review clarification in review task frontmatter
   - [ ] Implementation clarification in feature README
   - [ ] Subtask scope matches "Complete" preference

### Expected Results
- ✅ Auto-creates review task
- ✅ Context A guides review focus
- ✅ Context B determines subtask scope
- ✅ All 7 subtasks generated for Complete scope
- ✅ Both clarifications persist

### Success Criteria
- Zero manual task creation required
- Clarifications flow through entire workflow
- Subtasks match user's preferences
- Ready for parallel execution (if using Conductor)

---

## Scenario 5: Skip Clarification with --no-questions

**Objective**: Verify flag correctly skips clarification

**Duration**: 5 minutes

### Setup
```bash
/task-create "Implement rate limiting for API endpoints" complexity:8
```

### Steps

1. Execute with --no-questions flag:
   ```bash
   /task-work TASK-{generated-id} --no-questions
   ```

2. **Verify Phase 1.5 skipped**
   - [ ] No clarification questions shown
   - [ ] Directly proceeds to Phase 2 planning

3. **Verify defaults used in planning**
   - [ ] Standard scope assumed
   - [ ] Typical patterns applied
   - [ ] No clarification-specific content

4. **Check frontmatter**
   ```bash
   cat tasks/in_progress/TASK-{id}.md
   ```
   - [ ] No `clarification:` section
   - [ ] OR `clarification.mode: skip`

5. **Verify workflow completes**
   - [ ] All phases execute normally
   - [ ] Implementation completed
   - [ ] Tests run

### Expected Results
- ✅ No clarification questions asked
- ✅ Flag honored across all phases
- ✅ Workflow completes with defaults
- ✅ Suitable for CI/CD automation

### Success Criteria
- Complete workflow bypass
- No user interaction required
- Reasonable defaults applied

---

## Scenario 6: Inline Answers (CI/CD Simulation)

**Objective**: Verify non-interactive --answers flag for automation

**Duration**: 5 minutes

### Setup
```bash
/task-create "Add email notification system" complexity:6
```

### Steps

1. Execute with inline answers:
   ```bash
   /task-work TASK-{generated-id} --answers="scope:complete testing:e2e error_handling:comprehensive docs:yes"
   ```

2. **Verify no interactive prompts**
   - [ ] No questions displayed to user
   - [ ] Command executes immediately
   - [ ] No waiting for input

3. **Check answers applied**
   ```bash
   cat tasks/in_progress/TASK-{id}.md
   ```
   - [ ] `clarification.mode: full` (not quick or skip)
   - [ ] Decision for `scope`: `complete`
   - [ ] Decision for `testing`: `e2e`
   - [ ] Decision for `error_handling`: `comprehensive`
   - [ ] Decision for `docs`: `yes`
   - [ ] All have `default_used: false`

4. **Verify planning reflects inline answers**
   - [ ] Complete scope implementation
   - [ ] End-to-end tests included
   - [ ] Comprehensive error handling
   - [ ] Documentation tasks present

5. **Test invalid inline answer**
   ```bash
   /task-work TASK-{id} --answers="invalid:value"
   ```
   - [ ] Error message shown
   - [ ] Lists valid question IDs
   - [ ] Workflow does not proceed

### Expected Results
- ✅ Zero user interaction
- ✅ All answers applied correctly
- ✅ Planning reflects inline answers
- ✅ Suitable for CI/CD pipelines

### Success Criteria
- Fully automated execution
- Answers validated before use
- Clear error messages for invalid input

---

## Scenario 7: Quick Mode with User Input Before Timeout

**Objective**: Verify quick mode accepts user input before timeout

**Duration**: 5 minutes

### Setup
```bash
/task-create "Add CSV export functionality" complexity:4
```

### Steps

1. Execute task-work:
   ```bash
   /task-work TASK-{generated-id}
   ```

2. **Verify quick mode**
   - [ ] 15-second timeout shown
   - [ ] 2-3 questions displayed

3. **Answer questions before timeout**
   - [ ] Type "M" for first question (Minimal scope)
   - [ ] Type "U" for second question (Unit tests)
   - [ ] Complete within 15 seconds

4. **Check answers recorded**
   ```bash
   cat tasks/in_progress/TASK-{id}.md
   ```
   - [ ] `mode: quick`
   - [ ] Decisions show `default_used: false`
   - [ ] Answers match user input ("M", "U")

5. **Verify planning uses user's answers**
   - [ ] Minimal scope (not standard)
   - [ ] Unit tests (not integration)

### Expected Results
- ✅ Quick mode timeout starts
- ✅ User input accepted before timeout
- ✅ Timeout canceled after input
- ✅ User's answers used (not defaults)

### Success Criteria
- Clear distinction between timeout and user input
- User input takes precedence over defaults
- Smooth transition to next phase

---

## Scenario 8: Complexity Boundary Testing

**Objective**: Verify correct mode selection at complexity boundaries

**Duration**: 15 minutes

### Steps

1. **Test Complexity 2 (should skip)**
   ```bash
   /task-create "Fix typo in error message" complexity:2
   /task-work TASK-{id}
   ```
   - [ ] No clarification shown
   - [ ] Directly to Phase 2

2. **Test Complexity 3 (should use quick)**
   ```bash
   /task-create "Add tooltip to button" complexity:3
   /task-work TASK-{id}
   ```
   - [ ] Quick mode (15s timeout)
   - [ ] 1-2 questions shown

3. **Test Complexity 4 (should use quick)**
   ```bash
   /task-create "Implement form validation" complexity:4
   /task-work TASK-{id}
   ```
   - [ ] Quick mode (15s timeout)
   - [ ] 2-3 questions shown

4. **Test Complexity 5 (should use full)**
   ```bash
   /task-create "Add user authentication" complexity:5
   /task-work TASK-{id}
   ```
   - [ ] Full mode (no timeout)
   - [ ] 3-4 questions shown

5. **Test Complexity 9 (should use full)**
   ```bash
   /task-create "Refactor entire authentication system" complexity:9
   /task-work TASK-{id}
   ```
   - [ ] Full mode (no timeout)
   - [ ] 5-6 questions shown

### Expected Results
- ✅ Complexity 1-2: Skip
- ✅ Complexity 3-4: Quick (15s)
- ✅ Complexity 5+: Full (blocking)
- ✅ Consistent behavior at boundaries

### Success Criteria
- Clear mode transitions at boundaries
- User understands why each mode was selected
- More complex tasks get more questions

---

## Rework Rate Measurement

**Objective**: Measure reduction in planning rework with clarification feature

**Duration**: 2-4 hours

### Methodology

#### Baseline (Without Clarification)
1. Execute 5 tasks using `--no-questions` flag
2. Track these metrics:
   - [ ] Planning phase duration
   - [ ] Number of implementation iterations
   - [ ] Number of times plan was revised
   - [ ] Test failures due to missed requirements
   - [ ] Time to completion

#### With Clarification
3. Execute same 5 task types WITH clarification
4. Track same metrics
5. Compare results

### Sample Tasks for Measurement

```bash
# Task 1: Authentication
/task-create "Implement OAuth2 authentication" complexity:7

# Task 2: API Endpoint
/task-create "Create REST API for user management" complexity:6

# Task 3: UI Component
/task-create "Build interactive data table with sorting" complexity:5

# Task 4: Data Processing
/task-create "Add batch import for CSV files" complexity:6

# Task 5: Integration
/task-create "Integrate third-party payment gateway" complexity:8
```

### Success Metrics

Target improvements:
- ✅ 30-40% reduction in planning revisions
- ✅ 20-30% reduction in implementation iterations
- ✅ 15-25% reduction in test failures from requirements mismatch
- ✅ Overall time savings despite upfront clarification time

### Data Collection Template

| Task | Mode | Planning Time | Revisions | Iterations | Test Failures | Total Time | Notes |
|------|------|--------------|-----------|------------|---------------|------------|-------|
| Auth | No Clarification | 15m | 2 | 3 | 2 | 2.5h | Missed token refresh requirement |
| Auth | With Clarification | 20m | 0 | 1 | 0 | 1.8h | Complete scope selected upfront |
| ... | ... | ... | ... | ... | ... | ... | ... |

---

## Test Execution Checklist

### Pre-Execution
- [ ] All Wave 1-3 implementations complete
- [ ] Test environment set up
- [ ] Test tasks created
- [ ] Baseline tasks executed (for rework measurement)

### Execution
- [ ] Scenario 1: Full clarification ✅
- [ ] Scenario 2: Quick timeout ✅
- [ ] Scenario 3: task-review (both contexts) ✅
- [ ] Scenario 4: feature-plan end-to-end ✅
- [ ] Scenario 5: --no-questions flag ✅
- [ ] Scenario 6: --answers flag ✅
- [ ] Scenario 7: Quick with user input ✅
- [ ] Scenario 8: Complexity boundaries ✅

### Post-Execution
- [ ] All scenarios passed
- [ ] Rework rate data collected
- [ ] Issues documented
- [ ] Feedback gathered
- [ ] Test report generated

---

## Issue Tracking Template

| Issue ID | Scenario | Severity | Description | Steps to Reproduce | Expected | Actual |
|----------|----------|----------|-------------|-------------------|----------|--------|
| CLQ-UAT-001 | 2 | High | Timeout not shown | Step 2 | 15s countdown | No countdown |
| ... | ... | ... | ... | ... | ... | ... |

---

## Sign-Off

### Test Execution
- Tester Name: _________________
- Date: _________________
- Environment: _________________

### Results
- Total Scenarios: 8
- Passed: _____
- Failed: _____
- Blocked: _____

### Approval
- [ ] All critical scenarios passed
- [ ] Rework rate improvement achieved
- [ ] No blocking issues
- [ ] Ready for production use

Approved By: _________________
Date: _________________
