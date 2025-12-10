# Review Report: TASK-REV-803B

## Executive Summary

This review analyzes the scope and complexity of renaming the project from **Taskwright** to **GuardKit**. The analysis reveals a comprehensive rename affecting **1,579+ occurrences across 200+ files**, requiring careful orchestration across multiple domains.

**Overall Assessment**: High complexity (8/10), requires phased approach with careful dependency ordering.

**Key Finding**: The rename is feasible but involves significant coordination. The project has deep integration with the name "Taskwright" in CLI commands, marker files, documentation, and GitHub infrastructure.

## Review Details

- **Mode**: Architectural Review
- **Depth**: Comprehensive
- **Duration**: ~45 minutes
- **Reviewer**: Opus 4.5 Architectural Analysis

## Findings Summary

### 1. Scope of Impact

| Category | Files Affected | Occurrences | Risk Level |
|----------|---------------|-------------|------------|
| **README.md** | 1 | 46 | High |
| **CLAUDE.md** (root) | 1 | 34 | Critical |
| **Install Script** | 1 | 63 | Critical |
| **CLI Commands** | 10+ | 40+ | Critical |
| **Documentation** | 50+ | 300+ | Medium |
| **Task Files** | 100+ | 400+ | Low |
| **Test Files** | 20+ | 100+ | Medium |
| **Python Code** | 15+ | 50+ | High |
| **Templates** | 5+ | 50+ | High |
| **Marker Files** | 3 | 15 | Critical |
| **GitHub URLs** | 30+ | 100+ | High |

**Total**: ~200+ files, 1,579+ occurrences

### 2. Critical Infrastructure Files

These files are **mission-critical** and must be renamed correctly:

#### 2.1 Installer System (`installer/scripts/install.sh`)

```bash
# Current references:
GITHUB_REPO="https://github.com/taskwright-dev/taskwright"  # Line 21
"║         Taskwright Installation System                 ║"  # Line 42
# CLI commands: taskwright, taskwright-init, tw, twi
# Shell functions: print_header references "Taskwright"
```

**Risk**: Installer failure breaks all new installations.

#### 2.2 Marker Files

| File | Purpose | Change Required |
|------|---------|-----------------|
| `~/.agentecflow/taskwright.marker.json` | Package detection | Rename to `guardkit.marker.json` |
| `installer/core/templates/taskwright.marker.json` | Template marker | Rename to `guardkit.marker.json` |
| `taskwright.sln` | VS Solution file | Rename to `guardkit.sln` |

**Risk**: Marker file migration affects existing installations.

#### 2.3 CLI Commands

Current binaries in `~/.agentecflow/bin/`:
- `taskwright` → `guardkit`
- `taskwright-init` → `guardkit-init`
- `tw` → `gk` (short alias)
- `twi` → `gki` (short alias)

**Risk**: Users must update shell aliases, scripts, CI/CD.

### 3. GitHub Infrastructure Changes

| Element | Current | New | Status |
|---------|---------|-----|--------|
| Organisation | `taskwright-dev` | `guardkit` | ✅ **COMPLETE** |
| Repository | `taskwright` | `guardkit` | ✅ **COMPLETE** |
| Documentation URL | `taskwright-dev.github.io/taskwright/` | `guardkit.github.io/guardkit/` | Pending |
| Install URL | `raw.githubusercontent.com/guardkit/guardkit/...` | Ready to use | ✅ Available |

**Status**: GitHub rename completed by user on 2025-12-03. New URL: https://github.com/guardkit/guardkit

### 4. Code References Analysis

#### 4.1 Python Files with "taskwright"

| File | References | Purpose |
|------|------------|---------|
| `installer/core/lib/constants.py` | 1 | RequireKit config |
| `installer/core/commands/lib/distribution_helpers.py` | 16 | Package distribution |
| `installer/core/commands/lib/template_packager.py` | 4 | Template packaging |
| `installer/core/commands/lib/agent_discovery.py` | 1 | Agent discovery |
| `scripts/audit_requirekit.py` | 3 | Audit script |

#### 4.2 Template Files

| Template | Files Affected |
|----------|---------------|
| `fastapi-python` | manifest.json, README.md |
| `nextjs-fullstack` | CLAUDE.md, manifest.json, README.md |
| `react-fastapi-monorepo` | manifest.json, README.md, validation-report.md |
| `react-typescript` | validation-report.md |

### 5. Documentation Files

**High-Priority Documentation**:
- `docs/guides/taskwright-workflow.md` - File needs rename + content update
- `docs/workflows/taskwright-vs-requirekit.md` - File needs rename + content update
- `docs/adr/0003-remove-taskwright-python-template.md` - Historical reference

**Note**: Many task files in `tasks/` contain historical references that may not need updating (archive/completed tasks).

## Recommendations

### Recommended Order of Operations

#### Phase 1: Pre-Rename Preparation (No Breaking Changes)

1. **Create backup branch** of current state
2. **Document all references** (this review)
3. **Create migration scripts** for automated rename
4. **Test migration locally** before production

#### Phase 2: External Infrastructure (Manual, Breaking)

~~1. **Rename GitHub organisation**: `taskwright-dev` → `guardkit`~~
~~2. **Rename GitHub repository**: `taskwright` → `guardkit`~~
~~3. **Update DNS/domain** if applicable~~
~~4. **Configure GitHub redirects** (automatic for 1 year)~~

**✅ COMPLETE**: GitHub organisation and repository renamed to https://github.com/guardkit/guardkit on 2025-12-03.

#### Phase 3: Core Identity (Implementation Tasks)

Priority order:

| Task | Description | Dependency |
|------|-------------|------------|
| 3.1 | Update `install.sh` - CLI names, URLs, branding | Phase 2 complete |
| 3.2 | Rename marker files and detection logic | 3.1 |
| 3.3 | Update CLAUDE.md (root and .claude/) | 3.2 |
| 3.4 | Update README.md with new branding | 3.3 |

#### Phase 4: Documentation & Templates

| Task | Description |
|------|-------------|
| 4.1 | Rename workflow docs (`taskwright-workflow.md` → `guardkit-workflow.md`) |
| 4.2 | Update all docs/*.md files |
| 4.3 | Update template manifests and READMEs |
| 4.4 | Update agent files with new name |

#### Phase 5: Code & Tests

| Task | Description |
|------|-------------|
| 5.1 | Update Python code references |
| 5.2 | Update test files |
| 5.3 | Update solution file (`taskwright.sln` → `guardkit.sln`) |

#### Phase 6: Validation

| Task | Description |
|------|-------------|
| 6.1 | Run full test suite |
| 6.2 | Test fresh installation from new URLs |
| 6.3 | Test all CLI commands work |
| 6.4 | Verify marker file detection |

### Migration Scripts Needed

1. **Bulk rename script** (`scripts/rename-taskwright-to-guardkit.py`):
   - Search/replace with exclusions for historical tasks
   - Handle case variations (Taskwright, TASKWRIGHT, taskwright)
   - Preserve git history with `git mv`

2. **User migration script** (`scripts/migrate-user-installation.sh`):
   - Detect existing `taskwright.marker.json`
   - Create new `guardkit.marker.json`
   - Update CLI symlinks
   - Update shell config (`.bashrc`, `.zshrc`)

3. **Validation script** (`scripts/validate-rename.sh`):
   - Check no "taskwright" references remain in critical files
   - Verify CLI commands work
   - Test marker file detection

### Decision Points for Human Review

#### Q1: Organisation Rename Strategy

**Recommendation**: Option A (direct rename) with these mitigations:
- GitHub auto-redirects existing links for 1 year
- Update curl install URL in documentation immediately after rename
- Communicate via GitHub releases

#### Q2: CLI Command Names

**Recommendation**:
- Primary: `guardkit`, `guardkit-init`
- Aliases: `gk`, `gki`
- No backward compatibility for `taskwright` (clean break)

#### Q3: Historical Task Files

**Recommendation**:
- **DO NOT** rename completed/archived task files (historical record)
- **DO** update active task files if they have tutorial/example content
- **DO** update template content that users will see

#### Q4: Version Bump

**Recommendation**: Bump to v1.0.0 to mark the rename as a major milestone.

### Rollback Strategy

1. **Before Phase 2**: Simple git reset
2. **After Phase 2**: GitHub organisation rename can be reversed
3. **After Phase 3+**: Rollback script needed (reverse of migration)

### Communication Plan

1. **GitHub Release Notes**: Announce rename with migration guide
2. **README Banner**: Add deprecation notice to old URLs (if still accessible)
3. **Documentation**: Create "Migrating from Taskwright" guide

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Curl install breaks during rename | High | High | Quick turnaround, same-day Phase 2-3 |
| Existing users confused | Medium | Medium | Migration guide, clear communication |
| Some references missed | Medium | Low | Validation scripts, grep checks |
| Test failures after rename | Low | Medium | Run full test suite in Phase 6 |

## Implementation Tasks to Create

Based on this analysis, create these implementation tasks:

1. **TASK-IMP-RENAME-PREP**: Create migration scripts and backup
2. **TASK-IMP-RENAME-INFRA**: Update installer, marker files, CLI commands
3. **TASK-IMP-RENAME-DOCS**: Update documentation (CLAUDE.md, README.md, guides)
4. **TASK-IMP-RENAME-CODE**: Update Python code and templates
5. **TASK-IMP-RENAME-TESTS**: Update test files
6. **TASK-IMP-RENAME-VALIDATE**: Full validation and testing

**External Action Required**: GitHub organisation/repository rename (manual, user action)

## Appendix

### A. File Categories Breakdown

**Critical (Must Update)**:
- `installer/scripts/install.sh`
- `CLAUDE.md`
- `.claude/CLAUDE.md`
- `README.md`
- `installer/core/templates/taskwright.marker.json`
- `taskwright.sln`

**High Priority**:
- `installer/scripts/init-project.sh`
- `installer/core/commands/*.md`
- `installer/core/lib/*.py`
- `docs/guides/taskwright-workflow.md`
- `docs/workflows/taskwright-vs-requirekit.md`

**Medium Priority**:
- `installer/core/templates/*/manifest.json`
- `installer/core/templates/*/README.md`
- `installer/core/agents/*.md`
- `tests/*.py`

**Low Priority (Historical)**:
- `tasks/completed/*` (historical record, do not change)
- `tasks/archived/*` (historical record, do not change)
- `.claude/reviews/*` (historical record, do not change)

### B. Regex Patterns for Search/Replace

```regex
# Case-insensitive patterns
taskwright-dev  → guardkit-dev
Taskwright      → GuardKit
TASKWRIGHT      → GUARDKIT
taskwright      → guardkit
tw (alias)      → gk
twi (alias)     → gki
```

### C. Estimated Effort

| Phase | Effort | Notes |
|-------|--------|-------|
| Phase 1: Prep | 2-3 hours | Scripts + testing |
| Phase 2: GitHub | 30 min | Manual, quick |
| Phase 3: Core | 2-3 hours | Critical path |
| Phase 4: Docs | 2-3 hours | Bulk update |
| Phase 5: Code | 1-2 hours | Targeted changes |
| Phase 6: Validate | 2-3 hours | Full testing |

**Total**: ~10-14 hours of implementation work

---

*Generated by Taskwright Task Review System*
*Review ID: TASK-REV-803B*
*Date: 2025-12-03*
