---
id: TASK-FC-003
title: Implement feature folder archival
status: backlog
created: 2026-01-24T12:00:00Z
updated: 2026-01-24T12:00:00Z
priority: medium
tags: [feature-complete, archival, file-management]
complexity: 2
parent_review: TASK-REV-FC01
feature_id: FEAT-FC-001
implementation_mode: direct
wave: 1
dependencies: []
estimated_minutes: 30
---

# Task: Implement feature folder archival

## Description

Implement the Phase 3 logic in `FeatureCompleteOrchestrator` that moves the feature folder from `tasks/backlog/{slug}/` to `tasks/completed/{date}/{slug}/` and updates the feature YAML status.

## Requirements

1. Add `_archive_phase()` method to `FeatureCompleteOrchestrator`:
   - Move feature folder: `tasks/backlog/{slug}/` → `tasks/completed/{date}/{slug}/`
   - Date format: `YYYY-MM-DD`
   - Update feature YAML: set `status: awaiting_merge`
   - Update `completion.archived_at` timestamp

2. Feature YAML updates in `.guardkit/features/FEAT-XXX.yaml`:
   ```yaml
   status: awaiting_merge
   completion:
     archived_at: "2026-01-24T12:00:00Z"
     archived_to: "tasks/completed/2026-01-24/fastapi-health/"
     tasks_completed: 5
     tasks_failed: 0
   ```

3. Handle edge cases:
   - Feature folder doesn't exist (already archived or manual move)
   - Target directory already exists (append suffix or error)
   - Permission errors

## Acceptance Criteria

- [ ] `_archive_phase()` method implemented
- [ ] Feature folder moved to `tasks/completed/{date}/{slug}/`
- [ ] Feature YAML status updated to `awaiting_merge`
- [ ] Completion metadata added to feature YAML
- [ ] Works on both macOS and Linux
- [ ] Handles missing folder gracefully
- [ ] Unit tests for archival logic

## Technical Notes

```python
def _archive_phase(self, feature: Feature) -> None:
    """Archive feature folder and update YAML."""
    today = datetime.now().strftime("%Y-%m-%d")

    # Detect feature slug from tasks
    slug = self._detect_feature_slug(feature)

    # Source and destination paths
    src = self.repo_root / "tasks" / "backlog" / slug
    dst = self.repo_root / "tasks" / "completed" / today / slug

    if src.exists():
        # Create parent directory
        dst.parent.mkdir(parents=True, exist_ok=True)

        # Move folder
        shutil.move(str(src), str(dst))
        console.print(f"  ✓ Moved to: {dst.relative_to(self.repo_root)}")
    else:
        console.print(f"  [dim]⏭ Folder already archived or not found: {src}[/dim]")

    # Update feature YAML
    feature.status = "awaiting_merge"
    feature.completion = FeatureCompletion(
        archived_at=datetime.now().isoformat(),
        archived_to=str(dst.relative_to(self.repo_root)),
        tasks_completed=...,
        tasks_failed=...,
    )
    FeatureLoader.save_feature(feature, self.repo_root)
```

## Files to Modify

- **Modify**: `guardkit/orchestrator/feature_complete.py`
- **Modify**: `guardkit/orchestrator/feature_loader.py` (add `FeatureCompletion` model if needed)
- **Create**: `tests/orchestrator/test_feature_complete_archival.py`
