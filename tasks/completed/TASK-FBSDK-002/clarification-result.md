# Clarification Result for TASK-FBSDK-002

## Task Context

**Task ID:** TASK-FBSDK-002

**Title:** Write task_work_results.json after SDK parse in AgentInvoker

**Description:** When AgentInvoker.invoke_player() delegates to task-work via SDK, it parses the stream output using TaskWorkStreamParser but never persists the parsed results to disk. The CoachValidator expects to read quality gate results from .guardkit/autobuild/{task_id}/task_work_results.json, but this file is never created.

**Complexity:** 5/10

**Stack:** python

**Acceptance Criteria:**
- task_work_results.json is created after successful SDK execution
- task_work_results.json contains quality gate data (tests, coverage, arch review)
- CoachValidator can read and parse the results file
- File is created even on timeout (with partial data)
- Unit tests verify file creation
- Integration test confirms Coach validation succeeds

## Clarification Mode Decision

Based on the complexity scoring guidelines from the clarification-questioner agent:

| Complexity | Default Mode | With --no-questions | With --with-questions |
|------------|--------------|---------------------|----------------------|
| 1-2 | SKIP | SKIP | FULL |
| 3-4 | QUICK (15s timeout) | SKIP | FULL |
| 5+ | FULL (blocking) | SKIP | FULL |

**Assigned Mode:** QUICK (15s timeout)

**Rationale:** Complexity 5 falls into the threshold where quick clarification is appropriate. However, checking the thresholds table for implementation_planning context:

| Context | Skip | Quick | Full |
|---------|------|-------|------|
| implementation_planning | ≤2 | 3-4 | ≥5 |

**Corrected Mode:** FULL (blocking)

**Rationale:** For implementation_planning context, complexity ≥5 requires FULL mode with blocking user input.

## Generated Questions

The planning generator analyzes the task and detects:

### 1. Scope Ambiguity Detection
- **Detected:** Likely NO (task is specific about writing a JSON file)
- **Reason:** Clear, focused task with well-defined acceptance criteria

### 2. User Ambiguity Detection
- **Detected:** NO
- **Reason:** Clear stakeholder (CoachValidator)

### 3. Technology Choices Detection
- **Detected:** Likely YES
- **Keywords found:** "write", "parse", "file"
- **Component:** file writing/persistence

### 4. Integration Points Detection
- **Detected:** YES
- **Keywords found:** "SDK", "AgentInvoker", "CoachValidator"
- **Components:** Integration between parser and validator

### 5. Edge Case Detection
- **Detected:** YES
- **Reason:** Complexity ≥5 but acceptance criteria mention edge cases (timeout scenario)

## Expected Questions (Max 7)

Based on the detection results and question templates, the system would generate approximately 3-4 questions:

### Question 1: Technology - File Writing Pattern
**Category:** technology
**Text:** "Should task_work_results.json writing follow existing file persistence patterns in the codebase?"
**Options:** [Y]es / [N]ew pattern / [R]ecommend
**Default:** Y
**Rationale:** Consistency with existing patterns

### Question 2: Integration - Error Handling
**Category:** integration
**Text:** "How should file writing errors be handled during SDK execution?"
**Options:** [S]ilent fail / [L]og warning / [B]lock / [R]ecommend
**Default:** L
**Rationale:** Non-blocking for workflow continuity

### Question 3: Edge Case - Timeout Behavior
**Category:** edge_case
**Text:** "What data should be included in task_work_results.json on timeout?"
**Options:** [P]artial data / [E]mpty file / [N]o file / [R]ecommend
**Default:** P
**Rationale:** Matches acceptance criteria requirement

## Clarification Context Output

```yaml
clarification_context:
  context_type: implementation_planning
  mode: full
  total_questions: 3
  answered_count: 3
  skipped_count: 0
  assumed_defaults:
    - question_id: tech_file_pattern
      category: technology
      question_text: "Should task_work_results.json writing follow existing file persistence patterns in the codebase?"
      answer: Y
      answer_display: "Yes"
      default_used: true
      rationale: "Consistency with existing patterns recommended"

    - question_id: integration_error_handling
      category: integration
      question_text: "How should file writing errors be handled during SDK execution?"
      answer: L
      answer_display: "Log warning"
      default_used: true
      rationale: "Non-blocking approach maintains workflow continuity"

    - question_id: edge_timeout_data
      category: edge_case
      question_text: "What data should be included in task_work_results.json on timeout?"
      answer: P
      answer_display: "Partial data"
      default_used: true
      rationale: "Matches acceptance criteria: 'File is created even on timeout (with partial data)'"

  explicit_decisions: []
  not_applicable: []
  complexity_triggered: true
  user_override: null
  timestamp: "2026-01-18T10:00:00Z"
```

## Recommendations for Implementation

Based on the clarification context (with defaults applied):

1. **File Writing Pattern:** Follow existing file persistence patterns in the codebase
   - Look for similar JSON file writing in `guardkit/orchestrator/` or `guardkit/autobuild/`
   - Use consistent error handling and logging

2. **Error Handling Strategy:** Log warnings but don't block
   - Write to logger with WARNING level if file creation fails
   - Include error details in log message
   - Allow workflow to continue (non-blocking)

3. **Timeout Behavior:** Write partial data
   - Create task_work_results.json even on timeout
   - Include all data parsed up to timeout point
   - Mark file with `partial: true` or `timeout: true` flag
   - Document which sections are incomplete

## Integration with /task-work

This clarification context would be passed to Phase 2 (Implementation Planning) of /task-work as:

```python
# Phase 1.6: Clarifying Questions
clarification = execute_clarification(
    context_type="implementation_planning",
    task_id="TASK-FBSDK-002",
    task_title="Write task_work_results.json after SDK parse in AgentInvoker",
    complexity=5,
    flags={"no_questions": False, "with_questions": False, "defaults": False},
    task_context=task_context,
)

# Phase 2: Implementation Planning
phase_2_prompt = f"""
CLARIFICATION CONTEXT:
- File writing should follow existing codebase patterns
- Errors should be logged but not block execution
- Partial data should be written on timeout

Plan implementation for TASK-FBSDK-002...
"""
```

## Notes

- **Automation Note:** In this execution, defaults were auto-applied since we're running in an automated context (Claude agent). In interactive /task-work, the user would be prompted for these decisions.

- **Persistence:** This clarification context should be persisted to the task frontmatter when the task file is created, allowing resume without re-asking questions.

- **Fail-Safe:** If any error occurred during clarification, the system would return an empty context with `user_override="error"` and allow the workflow to continue.
