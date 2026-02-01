---
complexity: 4
dependencies: []
estimate_hours: 2
feature_id: FEAT-0F4A
id: TASK-GR3-001
implementation_mode: task-work
parallel_group: wave1-gr003
parent_review: TASK-REV-0CD7
status: design_approved
sub_feature: GR-003
task_type: feature
title: Implement FeatureDetector class
wave: 1
---

# Implement FeatureDetector class

## Description

Create the `FeatureDetector` class that detects feature specs from IDs and descriptions. This is the foundation for auto-detecting feature context during `/feature-plan`.

## Acceptance Criteria

- [ ] `detect_feature_id(description: str) -> Optional[str]` extracts FEAT-XXX pattern from text
- [ ] `find_feature_spec(feature_id: str) -> Optional[Path]` searches default paths for matching spec
- [ ] `find_related_features(feature_id: str) -> List[Path]` finds features with same prefix
- [ ] Searches `docs/features/`, `.guardkit/features/`, `features/` directories
- [ ] Unit tests cover pattern matching and file discovery

## Technical Details

**Location**: `guardkit/knowledge/feature_detector.py`

**Pattern**: `FEAT-[A-Z0-9]+-\d+` (e.g., FEAT-SKEL-001, FEAT-GR-003)

**Reference**: See `docs/research/graphiti-refinement/FEAT-GR-003-feature-spec-integration.md` for full specification.

## Implementation Notes

```python
import re
from pathlib import Path
from typing import Optional, List

class FeatureDetector:
    FEATURE_ID_PATTERN = re.compile(r'FEAT-[A-Z0-9]+-\d+')
    DEFAULT_FEATURE_PATHS = [
        "docs/features",
        ".guardkit/features",
        "features"
    ]
    # ... implementation
```