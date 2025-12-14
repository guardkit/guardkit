---
id: TASK-BI-011
title: Standardize RequireKit marker detection
status: backlog
priority: low
type: task
parent_id: beads-integration
blocking_ids: []
labels: [requirekit, detection, cleanup]
created_at: 2025-12-13
complexity: 2
methodology_mode: standard
---

# TASK-BI-011: Standardize RequireKit Marker Detection

## Problem Statement

RequireKit integration currently supports two marker file formats:
1. `~/.agentecflow/require-kit.marker.json` (JSON format, preferred)
2. `~/.agentecflow/require-kit.marker` (legacy, plain file)

This inconsistency creates:
- Multiple code paths for detection
- Confusion in documentation
- Potential race conditions if both exist

## Acceptance Criteria

1. Create unified detection function in `lib/feature_detection.py`:
   ```python
   def detect_requirekit() -> RequireKitInfo | None
   ```

2. Detection priority:
   - Check JSON marker first (preferred)
   - Fall back to legacy marker
   - Return None if neither exists

3. Return structured info:
   ```python
   @dataclass
   class RequireKitInfo:
       installed: bool
       version: Optional[str]
       marker_path: Path
       marker_type: Literal["json", "legacy"]
   ```

4. Update all BDD mode detection to use this function

5. Add deprecation warning when legacy marker used

6. Update documentation to recommend JSON format

## Technical Approach

```python
# installer/core/lib/feature_detection.py

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Literal
import json
import warnings

AGENTECFLOW_DIR = Path.home() / ".agentecflow"
REQUIREKIT_MARKER_JSON = AGENTECFLOW_DIR / "require-kit.marker.json"
REQUIREKIT_MARKER_LEGACY = AGENTECFLOW_DIR / "require-kit.marker"


@dataclass
class RequireKitInfo:
    """Information about RequireKit installation."""
    installed: bool
    version: Optional[str] = None
    marker_path: Optional[Path] = None
    marker_type: Optional[Literal["json", "legacy"]] = None


def detect_requirekit() -> RequireKitInfo:
    """
    Detect RequireKit installation.

    Checks for marker files in order of preference:
    1. require-kit.marker.json (JSON format, preferred)
    2. require-kit.marker (legacy plain file)

    Returns:
        RequireKitInfo with installation details
    """
    # Check JSON marker first (preferred)
    if REQUIREKIT_MARKER_JSON.exists():
        try:
            data = json.loads(REQUIREKIT_MARKER_JSON.read_text())
            return RequireKitInfo(
                installed=True,
                version=data.get("version"),
                marker_path=REQUIREKIT_MARKER_JSON,
                marker_type="json"
            )
        except (json.JSONDecodeError, IOError):
            pass  # Fall through to legacy check

    # Check legacy marker
    if REQUIREKIT_MARKER_LEGACY.exists():
        warnings.warn(
            "Using legacy require-kit.marker file. "
            "Consider upgrading to require-kit.marker.json format.",
            DeprecationWarning
        )
        return RequireKitInfo(
            installed=True,
            version=None,  # Legacy format doesn't store version
            marker_path=REQUIREKIT_MARKER_LEGACY,
            marker_type="legacy"
        )

    # Not installed
    return RequireKitInfo(installed=False)


def supports_bdd() -> bool:
    """
    Check if BDD mode is supported (RequireKit installed).

    Convenience function for quick checks.
    """
    return detect_requirekit().installed
```

### Update Existing Usage

```python
# Before (scattered checks)
if Path("~/.agentecflow/require-kit.marker.json").expanduser().exists():
    # BDD mode available
elif Path("~/.agentecflow/require-kit.marker").expanduser().exists():
    # BDD mode available (legacy)

# After (unified)
from lib.feature_detection import supports_bdd, detect_requirekit

if supports_bdd():
    info = detect_requirekit()
    if info.marker_type == "legacy":
        print("Consider upgrading RequireKit marker format")
```

## Dependencies

- **Depends on:** None
- **Blocks:** None (cleanup task)

## Effort Estimate

- **Complexity:** 2/10
- **Effort:** 1-2 hours
- **Wave:** Can be done anytime (independent)

## Testing

```python
# tests/lib/test_feature_detection.py

def test_detect_json_marker(tmp_path, monkeypatch):
    """Test JSON marker detection."""
    marker = tmp_path / "require-kit.marker.json"
    marker.write_text('{"version": "1.0.0"}')
    monkeypatch.setattr("lib.feature_detection.REQUIREKIT_MARKER_JSON", marker)

    info = detect_requirekit()
    assert info.installed
    assert info.version == "1.0.0"
    assert info.marker_type == "json"


def test_detect_legacy_marker_with_warning(tmp_path, monkeypatch):
    """Test legacy marker triggers deprecation warning."""
    marker = tmp_path / "require-kit.marker"
    marker.touch()
    monkeypatch.setattr("lib.feature_detection.REQUIREKIT_MARKER_LEGACY", marker)
    monkeypatch.setattr("lib.feature_detection.REQUIREKIT_MARKER_JSON", tmp_path / "nonexistent")

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        info = detect_requirekit()

        assert info.installed
        assert info.marker_type == "legacy"
        assert len(w) == 1
        assert "legacy" in str(w[0].message).lower()


def test_detect_not_installed(tmp_path, monkeypatch):
    """Test detection when not installed."""
    monkeypatch.setattr("lib.feature_detection.REQUIREKIT_MARKER_JSON", tmp_path / "nonexistent1")
    monkeypatch.setattr("lib.feature_detection.REQUIREKIT_MARKER_LEGACY", tmp_path / "nonexistent2")

    info = detect_requirekit()
    assert not info.installed
    assert info.version is None
```

## Documentation Update

Update `docs/guides/bdd-workflow-for-agentic-systems.md`:

```markdown
### Verify RequireKit Installation

```bash
# Preferred: JSON marker (includes version)
ls ~/.agentecflow/require-kit.marker.json

# Legacy: Plain marker (deprecated)
ls ~/.agentecflow/require-kit.marker
```

**Note:** The legacy plain marker file is deprecated. If you see a
deprecation warning, re-run the RequireKit installer to upgrade.
```

## References

- Review finding: G2 (RequireKit marker detection inconsistent)
- [TASK-REV-b8c3 Review Report](../../../.claude/reviews/TASK-REV-b8c3-review-report.md)
- [BDD Workflow Guide](../../../docs/guides/bdd-workflow-for-agentic-systems.md)
