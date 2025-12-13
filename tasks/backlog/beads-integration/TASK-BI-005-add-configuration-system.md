---
id: TASK-BI-005
title: Add configuration system for backend selection
status: backlog
priority: 2
created_at: 2025-12-13T00:00:00Z
parent_id: TASK-REV-BEADS
implementation_mode: task-work
wave: 3
conductor_workspace: wave3-1
complexity: 4
estimated_hours: 2-3
tags:
  - configuration
  - backend
  - phase-3
blocking_ids:
  - TASK-BI-004
---

# Add Configuration System for Backend Selection

## Objective

Create a configuration system that allows users to explicitly select their preferred backend and configure backend-specific settings.

## Context

While auto-detection works for most cases, users need the ability to explicitly configure their backend preference, especially when migrating from Markdown to Beads.

## Implementation Details

### Location

Create: `installer/core/lib/config.py`

### Configuration Structure

```python
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List

@dataclass
class BeadsConfig:
    """Beads-specific configuration."""
    auto_sync: bool = True
    default_labels: List[str] = field(default_factory=list)
    sync_on_close: bool = True

@dataclass
class BacklogMdConfig:
    """Backlog.md configuration (future)."""
    connection: str = "mcp"  # "mcp" or "cli"
    sync_status: bool = True

@dataclass
class GuardKitConfig:
    """GuardKit project configuration."""

    # Backend selection
    backend: str = "auto"  # "auto", "beads", "markdown"

    # Backend-specific settings
    beads: BeadsConfig = field(default_factory=BeadsConfig)
    backlog_md: BacklogMdConfig = field(default_factory=BacklogMdConfig)

    # Quality gate settings (existing)
    min_test_coverage: float = 80.0

    # File locations
    config_file: str = ".guardkit/config.json"

    @classmethod
    def load(cls, project_root: Path = None) -> "GuardKitConfig":
        """Load config from .guardkit/config.json or return defaults."""
        project_root = project_root or Path.cwd()
        config_file = project_root / ".guardkit" / "config.json"

        if config_file.exists():
            data = json.loads(config_file.read_text())

            # Handle nested configs
            beads_data = data.pop("beads", {})
            backlog_data = data.pop("backlog_md", {})

            return cls(
                **data,
                beads=BeadsConfig(**beads_data),
                backlog_md=BacklogMdConfig(**backlog_data)
            )

        return cls()

    def save(self, project_root: Path = None):
        """Save config to .guardkit/config.json."""
        project_root = project_root or Path.cwd()
        config_dir = project_root / ".guardkit"
        config_dir.mkdir(parents=True, exist_ok=True)

        config_file = config_dir / "config.json"

        # Convert to dict, handling nested dataclasses
        data = asdict(self)
        del data["config_file"]  # Don't save the path in the file

        config_file.write_text(json.dumps(data, indent=2))

    def get_backend_preference(self) -> Optional[str]:
        """Get explicit backend preference, or None for auto-detect."""
        if self.backend == "auto":
            return None
        return self.backend


# CLI commands for configuration

def set_backend(backend: str, project_root: Path = None):
    """Set the preferred backend."""
    if backend not in ["auto", "beads", "markdown"]:
        raise ValueError(f"Unknown backend: {backend}")

    config = GuardKitConfig.load(project_root)
    config.backend = backend
    config.save(project_root)

    return config

def get_config(project_root: Path = None) -> GuardKitConfig:
    """Get current configuration."""
    return GuardKitConfig.load(project_root)
```

### Integration with Registry

Update `BackendRegistry.get_backend()` to respect configuration:

```python
@classmethod
def get_backend(cls,
                preferred: Optional[str] = None,
                project_root: Path = None) -> TaskBackend:
    project_root = project_root or Path.cwd()

    # Load config if no explicit preference
    if preferred is None:
        from ..lib.config import GuardKitConfig
        config = GuardKitConfig.load(project_root)
        preferred = config.get_backend_preference()

    # ... rest of detection logic
```

### Example Config File

```json
{
  "backend": "beads",
  "beads": {
    "auto_sync": true,
    "default_labels": ["team-alpha"],
    "sync_on_close": true
  },
  "backlog_md": {
    "connection": "mcp",
    "sync_status": true
  },
  "min_test_coverage": 80.0
}
```

## Acceptance Criteria

- [ ] `GuardKitConfig` dataclass with all backend settings
- [ ] Load/save from `.guardkit/config.json`
- [ ] `set_backend()` function for CLI usage
- [ ] BackendRegistry respects configuration
- [ ] Nested config support for Beads and Backlog.md
- [ ] Default values for all settings
- [ ] Unit tests for config load/save

## Testing

```python
# tests/lib/test_config.py
def test_default_config():
    config = GuardKitConfig()
    assert config.backend == "auto"
    assert config.beads.auto_sync == True

def test_load_save_roundtrip(temp_project):
    config = GuardKitConfig(backend="beads")
    config.beads.default_labels = ["team-alpha"]
    config.save(temp_project)

    loaded = GuardKitConfig.load(temp_project)
    assert loaded.backend == "beads"
    assert loaded.beads.default_labels == ["team-alpha"]

def test_set_backend(temp_project):
    set_backend("beads", temp_project)
    config = get_config(temp_project)
    assert config.backend == "beads"
```

## Dependencies

- TASK-BI-004 (Backend registry)

## Notes

- Config file location: `.guardkit/config.json`
- Consider adding `guardkit config` CLI command in future task
- Backlog.md config included for future-proofing
