---
paths: "**/state*.py", "**/*_state.py", "**/*result*.py", "**/*context*.py"
---

# Dataclass Patterns

These patterns are extracted from GuardKit's actual codebase.

## Basic State Containers

Use dataclasses for minimal state objects:

```python
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

@dataclass
class OrchestrationState:
    """Minimal state for checkpoint-resume."""
    agent_file: str
    template_dir: str
    strategy: str
    dry_run: bool
    verbose: bool
    timestamp: str
```

## Optional Fields with Defaults

```python
@dataclass
class EnhancementResult:
    """Result of agent enhancement operation."""
    success: bool
    agent_name: str
    sections: List[str]
    error: Optional[str] = None
    core_file: Optional[Path] = None
    extended_file: Optional[Path] = None
    split_output: bool = False
```

## JSON Serialization with asdict()

```python
from dataclasses import dataclass, asdict
import json

@dataclass
class OrchestrationState:
    agent_file: str
    template_dir: str
    timestamp: str

# Serialize to JSON
state = OrchestrationState(
    agent_file="/path/to/agent.md",
    template_dir="/path/to/template",
    timestamp="2025-12-13T15:00:00Z"
)

# Write as JSON
json_str = json.dumps(asdict(state), indent=2)
Path("state.json").write_text(json_str)
```

## Computed Properties

```python
@dataclass
class EnhancementResult:
    """Result of agent enhancement operation."""
    success: bool
    core_file: Optional[Path] = None
    extended_file: Optional[Path] = None

    @property
    def files(self) -> List[Path]:
        """Return list of created files."""
        if self.core_file is None:
            return []
        if self.extended_file is not None:
            return [self.core_file, self.extended_file]
        return [self.core_file]
```

## Path Results

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

@dataclass
class SplitContent:
    """Represents content split between core and extended files."""
    core_path: Path
    extended_path: Optional[Path]
    core_sections: List[str]
    extended_sections: List[str]
```

## Loading from JSON

```python
def _load_state(self) -> OrchestrationState:
    """Load state from checkpoint file."""
    data = json.loads(self.state_file.read_text())
    return OrchestrationState(**data)
```

## When to Use Dataclass vs Pydantic

**Use dataclass when:**
- Simple internal state containers
- No validation needed
- Need asdict() for JSON serialization
- Minimal overhead preferred
- State passed between internal functions

**Use Pydantic when:**
- Data comes from external sources
- Need validation (constraints, patterns)
- Need serialization with configuration
- Need JSON schema generation

## Common Patterns

### Checkpoint State

```python
@dataclass
class CheckpointState:
    """State for checkpoint-resume workflow."""
    phase: int
    phase_name: str
    completed: bool = False
    result: Optional[dict] = None
    timestamp: str = ""
```

### Operation Result

```python
@dataclass
class OperationResult:
    """Result of an operation with optional error."""
    success: bool
    message: str
    data: Optional[dict] = None
    error: Optional[str] = None
```

### File Processing Result

```python
@dataclass
class ProcessedFile:
    """Result of file processing."""
    source_path: Path
    output_path: Path
    lines_changed: int = 0
    warnings: List[str] = field(default_factory=list)
```

## Using field() for Mutable Defaults

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class ProcessedFile:
    source_path: Path
    output_path: Path
    # NEVER use [] as default, use field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
```
