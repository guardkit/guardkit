# Create Migration Guides from Other Tools

**Priority**: Enhancement
**Category**: Documentation - Onboarding
**Estimated Effort**: 3-4 hours

## Problem

Users migrating from Linear, JIRA, or GitHub Projects need guidance on how to transition their workflows and data to GuardKit. Clear migration paths reduce adoption friction.

## Migration Guides Needed

### 1. Migrating from Linear
- Export Linear issues to GuardKit tasks
- Mapping Linear states to GuardKit states
- Handling Linear cycles/sprints
- Team collaboration transition
- Timeline and estimate conversion

### 2. Migrating from JIRA
- Export JIRA issues to GuardKit tasks
- Epic/Story/Task hierarchy mapping
- Custom field migration
- Workflow status mapping
- Integration preservation (if any)

### 3. Migrating from GitHub Projects
- Issue/PR to task conversion
- Label to tag mapping
- Project board to kanban mapping
- Maintaining Git integration
- Automation rule conversion

### 4. Migrating from Manual Workflows
- From TODO comments to tasks
- From spreadsheets to task files
- From Notion/Trello to GuardKit
- Best practices for initial setup

## Acceptance Criteria

1. Create separate migration guide for each major tool
2. Place in `docs/guides/migration/` directory
3. Each guide must include:
   - Pre-migration checklist
   - Export process from source tool
   - Import/conversion to GuardKit
   - Data mapping table
   - State transition mapping
   - Verification steps
   - Rollback procedure (if needed)
4. Provide migration scripts if applicable
5. Include example conversion
6. Add troubleshooting section

## Migration Script Requirements

- Python-based (consistency with ecosystem)
- Dry-run mode for preview
- Validation before conversion
- Progress reporting
- Error handling and recovery
- Backup creation

## Example Structure

```markdown
# Migrating from Linear to GuardKit

## Pre-Migration Checklist
- [ ] Export Linear data
- [ ] Install GuardKit
- [ ] Backup existing tasks
- [ ] Review state mapping

## Export from Linear
[Step-by-step export instructions]

## Convert to GuardKit Format
[Conversion process or script usage]

## Data Mapping
| Linear | GuardKit |
|--------|-----------|
| To Do | BACKLOG |
| In Progress | IN_PROGRESS |
| In Review | IN_REVIEW |
| Done | COMPLETED |

## Verification
[How to verify migration success]
```

## Implementation Notes

- Test migration scripts thoroughly
- Provide sample data for testing
- Document limitations/edge cases
- Include post-migration workflow tips
- Link to comparison guide for context

## References

- Linear API documentation
- JIRA REST API
- GitHub GraphQL API
- GuardKit task file format
