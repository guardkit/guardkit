---
id: TASK-IMP-RENAME-DOCS
title: "Update All Documentation for GuardKit Rename"
status: backlog
task_type: implementation
created: 2025-12-03T10:35:00Z
updated: 2025-12-03T10:35:00Z
priority: high
tags: [rename, documentation, guardkit]
complexity: 5
parent: TASK-REV-803B
dependencies: [TASK-IMP-RENAME-INFRA]
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

- [ ] CLAUDE.md (root) updated with GuardKit branding
- [ ] .claude/CLAUDE.md updated
- [ ] README.md updated with new branding and URLs
- [ ] Workflow docs renamed and updated
- [ ] All docs/*.md files updated
- [ ] mkdocs.yml updated for documentation site
- [ ] CONTRIBUTING.md updated
- [ ] CHANGELOG.md updated
- [ ] All GitHub URLs point to guardkit/guardkit
- [ ] No "guardkit" references in user-facing docs

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
