# Enhance Documentation with Real Code Examples

**Priority**: Enhancement
**Category**: Documentation - Practical Learning
**Estimated Effort**: 3-4 hours

## Problem

Documentation would benefit from real, tested code examples showing GuardKit in action across different scenarios and stacks. Users learn best from concrete examples.

## Examples Needed

### 1. Complete Workflow Example
- Real-world feature implementation
- Show full `/task-create` → `/task-work` → `/task-complete` flow
- Include actual output from each phase
- Show quality gate results

### 2. Design-First Workflow Example
- Complex task requiring approval
- `--design-only` output and checkpoint
- Human review decision
- `--implement-only` execution

### 3. TDD Mode Example
- Business logic implementation
- Red → Green → Refactor cycle
- Test-first approach demonstration

### 4. Parallel Development Example
- 3-5 tasks in different worktrees
- State synchronization in action
- Context switching demonstration

### 5. Stack-Specific Examples
- React/TypeScript component
- FastAPI endpoint
- .NET domain model
- Show technology detection

### 6. Review Workflow Example
- Architectural review task
- Review modes in action
- Decision checkpoint with options
- Implementation task generation

### 7. Agent Enhancement Example
- Before/after agent content
- Boundary sections addition
- Quality improvement demonstration

## Acceptance Criteria

1. Add code examples to relevant documentation pages
2. Examples must be:
   - Real (not pseudo-code)
   - Tested (actually work)
   - Complete (not fragments)
   - Annotated (comments explaining key points)
3. Include expected output for each example
4. Show both success and failure scenarios where relevant
5. Use syntax highlighting appropriate to stack

## Implementation Notes

- Test all examples before documenting
- Use realistic feature names (not "foo/bar")
- Include actual command output
- Show file structure context
- Add troubleshooting notes for common issues

## Example Format

```markdown
### Example: User Authentication Feature

#### Create Task
\`\`\`bash
/task-create "Add JWT-based user authentication" priority:high
# Created: TASK-AUTH-k2m9
\`\`\`

#### Work on Task
\`\`\`bash
/task-work TASK-AUTH-k2m9

# Output:
# Phase 2: Implementation Planning ✅
# Phase 2.5: Architectural Review (Score: 78/100) ✅
# ...
\`\`\`
```

## References

- README.md lines 509-534 (existing example)
- Actual task execution logs
- Template-specific examples
