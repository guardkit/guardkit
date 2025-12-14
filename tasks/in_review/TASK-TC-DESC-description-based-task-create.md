---
id: TASK-TC-DESC
title: Description-based task-create command
status: in_review
created: 2025-12-14T00:00:00Z
updated: 2025-12-14T12:00:00Z
previous_state: in_progress
priority: high
tags: [ux, command, simplification]
complexity: 5
architectural_review_score: 82
code_review_score: 98
---

# Task: Description-based task-create command

## Description

Change `/task-create` to accept a freeform description instead of requiring a separate title. Claude will infer an appropriate title from the description, making the command more natural to use.

**Current behavior:**
```bash
/task-create "Add user authentication"  # Title only, description empty or generated
```

**Proposed behavior:**
```bash
/task-create "We need to add user authentication with JWT tokens. Users should be able to login with email/password and receive a refresh token."
# Claude infers title: "Add JWT user authentication"
# Full description stored in task file
```

## Motivation

1. **More natural** - Users describe what they want, not craft a title
2. **Better context** - The description flows into task-work for better planning
3. **Less friction** - One less thing to think about
4. **Consistent** - Matches how `/feature-plan` already works (takes a description)

## Acceptance Criteria

- [ ] `/task-create` accepts freeform text (1-500 characters)
- [ ] Claude extracts/generates a concise title (5-10 words, action verb prefix)
- [ ] Full description stored in task file `## Description` section
- [ ] Title appears in task ID filename and frontmatter
- [ ] Short descriptions (< 50 chars) can still work as title-only if appropriate
- [ ] Backward compatible - existing options (priority:, tags:, prefix:) still work

## Files to Modify

### Command Specification
1. `installer/core/commands/task-create.md`
   - Update Usage section to show description-based examples
   - Update validation (5-500 chars instead of 5-100)
   - Add title inference logic description
   - Update examples throughout

### Documentation Updates
2. `README.md`
   - Update quickstart examples
   - Update Commands section

3. `docs/index.md`
   - Update example workflow

4. `docs/concepts.md`
   - No changes needed (doesn't show task-create syntax)

5. `docs/guides/GETTING-STARTED.md`
   - Update Step 2 examples
   - Update Essential Commands section

6. `docs/guides/guardkit-workflow.md`
   - Update 5-Minute Getting Started examples
   - Update any task-create examples in workflow sections

### Related Command Review
7. `installer/core/commands/feature-plan.md`
   - Review how it invokes task-create
   - Ensure compatibility with new description-based approach
   - May need to update subtask creation logic

## Implementation Notes

### Title Inference Logic

Claude should extract a title by:
1. Identifying the main action/goal from the description
2. Using action verb prefix (Add, Fix, Implement, Update, etc.)
3. Keeping it concise (5-10 words max)
4. Avoiding implementation details in title

**Examples:**
| Description | Inferred Title |
|-------------|----------------|
| "We need to add user authentication with JWT tokens..." | "Add JWT user authentication" |
| "The login button styling is broken on mobile devices..." | "Fix mobile login button styling" |
| "Implement a caching layer for the API responses..." | "Implement API response caching" |

### Task File Structure

```yaml
---
id: TASK-a3f8
title: Add JWT user authentication  # Inferred by Claude
status: backlog
...
---

# Task: Add JWT user authentication

## Description
We need to add user authentication with JWT tokens. Users should be able to login with email/password and receive a refresh token.

## Acceptance Criteria
[Generated or left for task-work to populate]
```

### Feature-plan Integration

The `/feature-plan` command creates subtasks via task-create. Review:
- How subtask descriptions are passed
- Whether subtasks need title inference or use structured titles
- Ensure wave detection still works with new format

## Test Requirements

- [ ] Unit tests for title inference from various description formats
- [ ] Integration test: task-create with description creates valid task file
- [ ] Integration test: feature-plan subtask creation still works
- [ ] Edge cases: very short descriptions, very long descriptions, descriptions with special characters

## Dependencies

None - standalone change

## Notes

This is a UX simplification that aligns task-create with feature-plan's description-first approach. The key insight is that users naturally want to describe what they need, not craft a formal title.
