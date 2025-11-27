# Hash-Based IDs and PM Tool Integration

This guide explains how Taskwright maps internal hash-based task IDs to external sequential IDs in project management tools like JIRA, Azure DevOps, Linear, and GitHub Issues.

## The Problem: Humans Want Sequential, Systems Need Unique

Project management tools (and their users) expect sequential IDs:
- JIRA: `PROJ-123`, `PROJ-124`, `PROJ-125`
- Linear: `TEAM-45`, `TEAM-46`, `TEAM-47`
- GitHub: `#12`, `#13`, `#14`

But sequential IDs create problems for distributed/parallel workflows:
- ❌ Require coordination to prevent duplicates
- ❌ Create merge conflicts
- ❌ Don't work with Conductor.build parallel development

## The Solution: Automatic ID Mapping

Taskwright uses **hash-based IDs internally** and **maps to sequential IDs externally**:

**Internal ID** (Taskwright): `TASK-E01-b2c4`

**External IDs** (PM tools):
- JIRA: `PROJ-456`
- Azure DevOps: `#1234`
- Linear: `TEAM-789`
- GitHub: `#234`

The mapping is:
- ✅ **Automatic** - Created when tasks are exported to PM tools
- ✅ **Bidirectional** - Look up by internal or external ID
- ✅ **Persistent** - Stored in `.claude/state/external_id_mappings.json`
- ✅ **Transparent** - Users don't need to think about it

## How It Works

### 1. Create Task Internally

```bash
/task-create "Add user authentication" prefix:AUTH epic:EPIC-001
# Created: TASK-AUTH-h8j3

# Task file frontmatter (internal)
---
id: TASK-AUTH-h8j3
title: Add user authentication
epic: EPIC-001
external_ids:
  epic_jira: PROJ-123    # Epic already mapped
  jira: null             # Task not yet exported
  linear: null
  github: null
---
```

### 2. Export to PM Tool

```bash
# Export task to JIRA
/task-export TASK-AUTH-h8j3 --tool jira

# System automatically:
# 1. Creates JIRA issue (gets sequential ID: PROJ-456)
# 2. Maps internal ID → external ID
# 3. Updates task frontmatter
# 4. Saves mapping to external_id_mappings.json
```

### 3. Task Frontmatter Updated

```yaml
---
id: TASK-AUTH-h8j3
title: Add user authentication
epic: EPIC-001
external_ids:
  epic_jira: PROJ-123
  jira: PROJ-456         # ← Mapped!
  linear: null
  github: null
---
```

### 4. Mapping Persisted

File: `.claude/state/external_id_mappings.json`

```json
{
  "task_mappings": {
    "TASK-AUTH-h8j3": {
      "jira": "PROJ-456",
      "linear": null,
      "github": null,
      "azure_devops": null
    },
    "TASK-E01-b2c4": {
      "jira": "PROJ-457",
      "linear": "TEAM-123",
      "github": null,
      "azure_devops": null
    }
  },
  "epic_mappings": {
    "EPIC-001": {
      "jira": "PROJ-123",
      "linear": "TEAM-100",
      "github": null,
      "azure_devops": null
    }
  }
}
```

## Bidirectional Lookup

### Look Up by Internal ID

```bash
/task-status TASK-AUTH-h8j3

# Output includes external IDs
Task: TASK-AUTH-h8j3
Title: Add user authentication
Status: in_progress
External IDs:
  JIRA: PROJ-456 (https://yourorg.atlassian.net/browse/PROJ-456)
  Linear: Not exported
  GitHub: Not exported
```

### Look Up by External ID

```bash
/task-status PROJ-456

# System automatically:
# 1. Looks up mapping: PROJ-456 → TASK-AUTH-h8j3
# 2. Loads internal task
# 3. Displays full task details

Task: TASK-AUTH-h8j3 (JIRA: PROJ-456)
Title: Add user authentication
Status: in_progress
...
```

## PM Tool Integration Examples

### JIRA Integration

```bash
# 1. Create task with epic linking
/task-create "Implement OAuth" prefix:AUTH epic:EPIC-001
# Created: TASK-AUTH-k2m9

# 2. Export to JIRA
/task-export TASK-AUTH-k2m9 --tool jira

# System creates JIRA issue:
# - Project: PROJ (from epic mapping)
# - Issue Type: Task
# - Summary: "Implement OAuth"
# - Parent: PROJ-123 (epic's JIRA ID)
# - Gets ID: PROJ-458

# 3. Mapping saved
# Internal: TASK-AUTH-k2m9
# External: PROJ-458

# 4. Sync status back
/task-sync TASK-AUTH-k2m9 --from jira
# Updates local task status from JIRA
```

### Azure DevOps Integration

```bash
# 1. Create task
/task-create "Add logging" prefix:LOG epic:EPIC-002
# Created: TASK-LOG-n7p4

# 2. Export to Azure DevOps
/task-export TASK-LOG-n7p4 --tool azdo

# System creates work item:
# - Project: MyProject
# - Work Item Type: Task
# - Title: "Add logging"
# - Parent: 1200 (epic's Azure DevOps ID)
# - Gets ID: 1234

# 3. Mapping saved
# Internal: TASK-LOG-n7p4
# External: #1234
```

### Linear Integration

```bash
# 1. Create task
/task-create "Fix search bug" prefix:FIX epic:EPIC-003
# Created: TASK-FIX-p3q8

# 2. Export to Linear
/task-export TASK-FIX-p3q8 --tool linear

# System creates issue:
# - Team: ENG
# - Title: "Fix search bug"
# - Project: PRJ-100 (epic's Linear project)
# - Gets ID: TEAM-456

# 3. Mapping saved
# Internal: TASK-FIX-p3q8
# External: TEAM-456
```

### GitHub Issues Integration

```bash
# 1. Create task
/task-create "Update docs" prefix:DOC epic:EPIC-004
# Created: TASK-DOC-r9s2

# 2. Export to GitHub
/task-export TASK-DOC-r9s2 --tool github

# System creates issue:
# - Repo: owner/repo
# - Title: "Update docs"
# - Labels: documentation, epic-004
# - Milestone: EPIC-004 (if mapped)
# - Gets ID: #234

# 3. Mapping saved
# Internal: TASK-DOC-r9s2
# External: #234
```

## Epic-Level Integration

Epics are mapped first, then tasks inherit the project/parent context:

```bash
# 1. Create epic
/epic-create "User Authentication System" export:jira,linear

# Epic created: EPIC-001
# JIRA: PROJ-123 (Epic)
# Linear: PROJECT-100

# 2. Create tasks under epic
/task-create "OAuth integration" epic:EPIC-001
# Created: TASK-t4u7

# 3. Export task
/task-export TASK-t4u7 --tool jira

# System automatically:
# - Uses epic's JIRA project (PROJ)
# - Sets parent to PROJ-123 (epic's JIRA ID)
# - Creates PROJ-458
# - Maps TASK-t4u7 → PROJ-458
```

## Mapping File Structure

`.claude/state/external_id_mappings.json`:

```json
{
  "version": "1.0",
  "last_updated": "2025-01-27T10:00:00Z",
  "task_mappings": {
    "TASK-AUTH-h8j3": {
      "jira": "PROJ-456",
      "jira_url": "https://yourorg.atlassian.net/browse/PROJ-456",
      "linear": "TEAM-123",
      "linear_url": "https://linear.app/team/issue/TEAM-123",
      "github": null,
      "azure_devops": null,
      "created_at": "2025-01-27T09:00:00Z",
      "updated_at": "2025-01-27T09:30:00Z"
    }
  },
  "epic_mappings": {
    "EPIC-001": {
      "jira": "PROJ-123",
      "jira_url": "https://yourorg.atlassian.net/browse/PROJ-123",
      "linear": "PROJECT-100",
      "linear_url": "https://linear.app/team/project/PROJECT-100",
      "github": null,
      "azure_devops": null
    }
  },
  "reverse_mappings": {
    "jira": {
      "PROJ-456": "TASK-AUTH-h8j3",
      "PROJ-123": "EPIC-001"
    },
    "linear": {
      "TEAM-123": "TASK-AUTH-h8j3",
      "PROJECT-100": "EPIC-001"
    }
  }
}
```

## Benefits of Mapping Approach

### 1. Best of Both Worlds

- **Internal**: Hash-based IDs (collision-free, parallel-safe)
- **External**: Sequential IDs (user-friendly, familiar)

### 2. Zero User Friction

Users in PM tools see familiar sequential IDs:
- "Working on PROJ-456" (not "TASK-AUTH-h8j3")
- GitHub PR: "Closes #234" (not "Closes TASK-DOC-r9s2")

### 3. Technical Correctness

Developers work with hash IDs internally:
- Zero collision risk
- Parallel development enabled
- Clean merges

### 4. Bidirectional Sync

```bash
# Update from PM tool
/task-sync TASK-AUTH-h8j3 --from jira
# Pulls status, comments, assignee from PROJ-456

# Update to PM tool
/task-sync TASK-AUTH-h8j3 --to jira
# Pushes status, description updates to PROJ-456
```

## Common Workflows

### Workflow 1: Internal Task → External Issue

```bash
# 1. Create task internally
/task-create "Add caching" prefix:PERF
# Created: TASK-PERF-v5w8

# 2. Work on it (Taskwright workflow)
/task-work TASK-PERF-v5w8
# Phases 2-5.5 complete

# 3. Export to PM tool
/task-export TASK-PERF-v5w8 --tool jira
# Mapped: TASK-PERF-v5w8 → PROJ-459

# 4. Team sees PROJ-459 in JIRA
# Developers work with TASK-PERF-v5w8 in code
```

### Workflow 2: External Issue → Internal Task

```bash
# 1. PM creates issue in JIRA: PROJ-460

# 2. Import to Taskwright
/task-import --tool jira --id PROJ-460
# Created: TASK-x3y7
# Mapped: TASK-x3y7 → PROJ-460

# 3. Work on it
/task-work TASK-x3y7

# 4. Status syncs back to JIRA
/task-sync TASK-x3y7 --to jira
# PROJ-460 status updated
```

### Workflow 3: Multi-Tool Export

```bash
# 1. Create task
/task-create "Security audit" prefix:SEC
# Created: TASK-SEC-z8a2

# 2. Export to multiple tools
/task-export TASK-SEC-z8a2 --tool jira
# Mapped: TASK-SEC-z8a2 → PROJ-461

/task-export TASK-SEC-z8a2 --tool github
# Mapped: TASK-SEC-z8a2 → #235

# 3. Task frontmatter shows both
external_ids:
  jira: PROJ-461
  github: #235
  linear: null
```

## Troubleshooting

### Problem: Mapping File Missing

**Symptom**: External ID lookups fail

**Solution**:
```bash
# Regenerate mapping file from task frontmatter
/task-rebuild-mappings
# Scans all tasks, rebuilds external_id_mappings.json
```

### Problem: Duplicate External IDs

**Symptom**: Two internal tasks claim same external ID

**Solution**:
```bash
# Audit mappings
/task-audit-mappings
# Reports conflicts, suggests resolution

# Manual fix: Edit task frontmatter
# Remove incorrect external_id entry
# Run rebuild
/task-rebuild-mappings
```

### Problem: Mapping Out of Sync

**Symptom**: Task status in PM tool doesn't match Taskwright

**Solution**:
```bash
# Sync from PM tool (authoritative source)
/task-sync TASK-xxx --from jira --force

# Or sync to PM tool (Taskwright authoritative)
/task-sync TASK-xxx --to jira --force
```

## See Also

- [Parallel Development Guide](hash-id-parallel-development.md) - Why hash IDs enable parallel workflows
- [External ID Integration](external-ids-integration.md) - Detailed implementation guide
- [Task ID Strategy Analysis](../research/task-id-strategy-analysis.md) - Technical architecture
- [Task ID Decision Guide](../research/task-id-decision-guide.md) - Why mapping approach?

## Summary

**Key Takeaway**: Hash-based IDs internally + sequential IDs externally = best of both worlds

- ✅ Developers get collision-free parallel development
- ✅ PM tools get familiar sequential IDs
- ✅ Bidirectional sync keeps everything in sync
- ✅ Zero coordination overhead
- ✅ Works with JIRA, Azure DevOps, Linear, GitHub
