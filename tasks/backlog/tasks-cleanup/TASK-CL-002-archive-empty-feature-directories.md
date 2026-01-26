---
id: TASK-CL-002
title: Archive empty feature directories
status: backlog
created: 2026-01-26T14:45:00Z
updated: 2026-01-26T14:45:00Z
priority: medium
tags: [cleanup, housekeeping, archive]
task_type: implementation
complexity: 2
parent_review: TASK-REV-BL01
feature_id: FEAT-CLEANUP
implementation_mode: direct
parallel_group: wave-1
---

# Task: Archive empty feature directories

## Description

Move 17 empty/near-empty feature directories (containing only README.md and/or IMPLEMENTATION-GUIDE.md with no subtasks) to archived location.

## Actions Required

### Create archive destination

```bash
mkdir -p tasks/archived/features/
```

### Move empty feature directories (17 directories)

```bash
git mv tasks/backlog/autobuild-task-work-delegation/ tasks/archived/features/
git mv tasks/backlog/direct-mode-race-fix/ tasks/archived/features/
git mv tasks/backlog/feature-build-cli-native/ tasks/archived/features/
git mv tasks/backlog/feature-build-design-phase-fix/ tasks/archived/features/
git mv tasks/backlog/feature-build-fixes/ tasks/archived/features/
git mv tasks/backlog/feature-build-performance/ tasks/archived/features/
git mv tasks/backlog/feature-build-regression-fix/ tasks/archived/features/
git mv tasks/backlog/feature-plan-schema-fix/ tasks/archived/features/
git mv tasks/backlog/file-tracking-fix/ tasks/archived/features/
git mv tasks/backlog/nested-directory-support/ tasks/archived/features/
git mv tasks/backlog/player-report-harmonization/ tasks/archived/features/
git mv tasks/backlog/preloop-documentation/ tasks/archived/features/
git mv tasks/backlog/quality-gates-integration/ tasks/archived/features/
git mv tasks/backlog/sdk-delegation-fix/ tasks/archived/features/
git mv tasks/backlog/sdk-error-handling/ tasks/archived/features/
git mv tasks/backlog/task-type-expansion/ tasks/archived/features/
git mv tasks/backlog/task-work-performance/ tasks/archived/features/
```

## Directories Being Archived

| Directory | Contents | Reason |
|-----------|----------|--------|
| autobuild-task-work-delegation/ | README, GUIDE | No subtasks |
| direct-mode-race-fix/ | README only | No subtasks |
| feature-build-cli-native/ | README, GUIDE | No subtasks |
| feature-build-design-phase-fix/ | README, GUIDE | No subtasks |
| feature-build-fixes/ | README, GUIDE | No subtasks |
| feature-build-performance/ | README, GUIDE | No subtasks |
| feature-build-regression-fix/ | README, GUIDE | No subtasks |
| feature-plan-schema-fix/ | README, GUIDE | No subtasks |
| file-tracking-fix/ | README, GUIDE | No subtasks |
| nested-directory-support/ | README, GUIDE | No subtasks |
| player-report-harmonization/ | README, GUIDE | No subtasks |
| preloop-documentation/ | README, GUIDE | No subtasks |
| quality-gates-integration/ | README only | No subtasks |
| sdk-delegation-fix/ | README, GUIDE | No subtasks |
| sdk-error-handling/ | README, GUIDE | No subtasks |
| task-type-expansion/ | README, GUIDE | No subtasks |
| task-work-performance/ | README, GUIDE | No subtasks |

## Acceptance Criteria

- [ ] tasks/archived/features/ directory created
- [ ] All 17 empty feature directories moved
- [ ] Git history preserved via `git mv`
- [ ] No feature directories with only README/GUIDE remain in backlog

## Notes

- These directories contain planning artifacts but no implementation tasks
- Archive preserves the planning work for future reference
- Can be restored if feature work resumes
