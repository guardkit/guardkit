---
id: TASK-IMP-RENAME-DOCS
title: "Update All Documentation for GuardKit Rename"
status: completed
task_type: implementation
created: 2025-12-03T10:35:00Z
updated: 2025-12-03T10:50:00Z
completed: 2025-12-03T10:50:00Z
priority: high
tags: [rename, documentation, guardkit]
complexity: 5
parent: TASK-REV-803B
dependencies: [TASK-IMP-RENAME-INFRA]
completion_metrics:
  total_duration: "15 minutes"
  files_modified: 45
  lines_changed: 870
  documentation_build: "success"
  remaining_references: 0
---

# Implementation Task: Update Documentation

## Context

Part of the GuardKit → GuardKit rename initiative. This task updates all user-facing documentation.

**Parent Review**: TASK-REV-803B
**GitHub Rename**: ✅ Complete (https://github.com/guardkit/guardkit)

## Scope

### 1. Critical Documentation (Highest Priority)

| File | Occurrences | Notes |
|------|-------------|-------|
| `CLAUDE.md` | 34 | Root project instructions |
| `.claude/CLAUDE.md` | 4 | Claude workspace instructions |
| `README.md` | 46 | Main project README |

### 2. File Renames

| Current | New |
|---------|-----|
| `docs/guides/guardkit-workflow.md` | `docs/guides/guardkit-workflow.md` |
| `docs/workflows/guardkit-vs-requirekit.md` | `docs/workflows/guardkit-vs-requirekit.md` |

### 3. Bulk Documentation Updates

**docs/ Directory** (~50 files):
- `docs/guides/*.md`
- `docs/workflows/*.md`
- `docs/concepts.md`
- `docs/troubleshooting.md`
- `docs/agents.md`
- `docs/mcp-integration.md`
- `docs/templates/*.md`

**Other Documentation**:
- `CONTRIBUTING.md` (13 occurrences)
- `CHANGELOG.md` (5 occurrences)
- `LICENSE` (1 occurrence - copyright holder name)
- `mkdocs.yml` (10 occurrences - site configuration)

### 4. URL Updates

All documentation URLs need updating:
- `https://github.com/guardkit/guardkit` → `https://github.com/guardkit/guardkit`
- `https://guardkit.github.io/guardkit/` → `https://guardkit.github.io/guardkit/`
- `https://raw.githubusercontent.com/guardkit/guardkit/...` → `https://raw.githubusercontent.com/guardkit/guardkit/...`

## Acceptance Criteria

- [x] CLAUDE.md (root) updated with GuardKit branding
- [x] .claude/CLAUDE.md updated
- [x] README.md updated with new branding and URLs
- [x] Workflow docs renamed and updated
- [x] All docs/*.md files updated
- [x] mkdocs.yml updated for documentation site
- [x] CONTRIBUTING.md updated
- [x] CHANGELOG.md updated
- [x] All GitHub URLs point to guardkit/guardkit
- [x] No "taskwright" references in user-facing docs

## Exclusions

Do NOT update:
- `docs/adr/0003-remove-guardkit-python-template.md` (historical ADR)
- Historical references in completed tasks
- Review reports (`.claude/reviews/*`)

## Testing

```bash
# Build docs to verify no broken links
mkdocs build

# Search for remaining references
grep -ri "guardkit" docs/ --include="*.md" | grep -v "adr/"
```

## Estimated Effort

2-3 hours
