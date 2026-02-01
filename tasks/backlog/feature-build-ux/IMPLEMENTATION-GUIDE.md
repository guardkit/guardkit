# Implementation Guide: Feature-Build UX Improvements

**Feature ID**: FEAT-FB-UX
**Created**: 2025-01-31

## Overview

This guide provides wave-by-wave execution instructions for Phase 1 of the Feature-Build UX improvements. Phase 1 focuses on immediate fixes using file polling, establishing the foundation for future event-driven architecture.

## Prerequisites

- Python 3.10+
- GuardKit development environment
- Understanding of Rich library (for TTY detection)

## Wave Execution

### Wave 1: Foundation (Parallel Execution)

These tasks establish the foundation and can be executed in parallel.

| Task | Title | Mode | Conductor Workspace |
|------|-------|------|---------------------|
| TASK-FB-001 | TTY detection in ProgressDisplay | direct | `fb-001-tty-detection` |
| TASK-FB-002 | Simple text output fallback | task-work | `fb-002-text-fallback` |
| TASK-FB-003 | Progress file writer | task-work | `fb-003-progress-file` |

#### TASK-FB-001: TTY Detection (Direct)

**File**: [guardkit/orchestrator/progress.py](../../../guardkit/orchestrator/progress.py)

**Changes Required**:
```python
# In ProgressDisplay.__init__()
import sys

self.is_tty = sys.stdout.isatty()
```

**Verification**:
```bash
# Test in terminal (should be True)
python -c "import sys; print(sys.stdout.isatty())"

# Test piped (should be False)
python -c "import sys; print(sys.stdout.isatty())" | cat
```

#### TASK-FB-002: Text Output Fallback (Task-Work)

**Depends on**: TASK-FB-001

**File**: [guardkit/orchestrator/progress.py](../../../guardkit/orchestrator/progress.py)

**New Class**: `SimpleTextProgress` - fallback when `is_tty=False`

**Output Format**:
```
[14:30:15] Turn 1/5: Player Implementation starting...
[14:30:45] Turn 1/5: Writing tests...
[14:31:02] Turn 1/5: Player Implementation complete (success)
[14:31:05] Turn 1/5: Coach Validation starting...
```

**Run**: `/task-work TASK-FB-002 --mode=tdd`

#### TASK-FB-003: Progress File Writer (Task-Work)

**Depends on**: TASK-FB-001

**File**: [guardkit/orchestrator/progress.py](../../../guardkit/orchestrator/progress.py)

**New Class**: `ProgressFileWriter` - writes JSON progress file

**Output Location**: `.guardkit/autobuild/{task_id}/progress.json`

**JSON Schema**:
```json
{
  "task_id": "TASK-XXX",
  "status": "running",
  "turn": 2,
  "turn_max": 5,
  "phase": "Coach Validation",
  "last_message": "Validating test coverage...",
  "updated_at": "2025-01-31T14:31:02Z",
  "metrics": {
    "elapsed_seconds": 127,
    "files_modified": 3,
    "tests_passed": 5,
    "tests_total": 5
  }
}
```

**Run**: `/task-work TASK-FB-003 --mode=tdd`

---

### Wave 2: Integration (Sequential after Wave 1)

These tasks depend on Wave 1 completion.

| Task | Title | Mode | Depends On |
|------|-------|------|------------|
| TASK-FB-004 | /feature-build polling integration | task-work | FB-002, FB-003 |
| TASK-FB-005 | Timeout documentation update | direct | None |
| TASK-FB-006 | --timeout flag passthrough | direct | FB-005 |

#### TASK-FB-004: Polling Integration (Task-Work)

**Depends on**: TASK-FB-002, TASK-FB-003

**File**: [installer/core/commands/feature-build.md](../../../installer/core/commands/feature-build.md)

**Changes**:
1. Run `guardkit autobuild` in background
2. Poll `.guardkit/autobuild/{task_id}/progress.json` every 30 seconds
3. Display progress updates to user
4. Handle completion/error states

**Execution Flow**:
```
Claude Code runs /feature-build TASK-XXX
    │
    ├── Launch: guardkit autobuild task TASK-XXX (background)
    │
    └── Poll Loop (every 30s):
            │
            ├── Read progress.json
            ├── Display: "Turn 2/5: Coach Validation (45s elapsed)"
            └── Check status == "completed" or "error"
```

**Run**: `/task-work TASK-FB-004 --mode=tdd`

#### TASK-FB-005: Timeout Documentation (Direct)

**File**: [.claude/rules/autobuild.md](../../../.claude/rules/autobuild.md)

**Changes**:
- Document Bash tool 120s default timeout
- Explain SDK 900s timeout difference
- Add recommendations for VS Code extension usage
- Clarify when to run from terminal vs Claude Code

#### TASK-FB-006: Timeout Flag Passthrough (Direct)

**Depends on**: TASK-FB-005

**File**: [installer/core/commands/feature-build.md](../../../installer/core/commands/feature-build.md)

**New Flags**:
| Flag | Description | Default |
|------|-------------|---------|
| `--bash-timeout S` | Bash tool timeout in seconds | 600 |
| `--sdk-timeout S` | Claude SDK operation timeout | 300 |

**Example**:
```bash
/feature-build TASK-AUTH-001 --bash-timeout 1800 --sdk-timeout 900
```

---

## Testing Strategy

### Unit Tests

Each task should include unit tests:

```python
# tests/unit/test_progress.py

def test_tty_detection_terminal():
    """TTY detection returns True in terminal."""
    # Mock sys.stdout.isatty() to return True
    with patch('sys.stdout.isatty', return_value=True):
        display = ProgressDisplay(max_turns=5)
        assert display.is_tty is True

def test_tty_detection_pipe():
    """TTY detection returns False when piped."""
    with patch('sys.stdout.isatty', return_value=False):
        display = ProgressDisplay(max_turns=5)
        assert display.is_tty is False

def test_simple_text_output_format():
    """SimpleTextProgress outputs correct format."""
    progress = SimpleTextProgress(max_turns=5)
    output = progress.format_message(turn=1, phase="Player", message="Writing tests")
    assert "[" in output  # Timestamp
    assert "Turn 1/5" in output
    assert "Writing tests" in output

def test_progress_file_atomic_write():
    """Progress file uses atomic write pattern."""
    writer = ProgressFileWriter(task_id="TASK-001")
    # Verify temp file + rename pattern
```

### Integration Tests

```python
# tests/integration/test_feature_build_polling.py

def test_polling_detects_completion():
    """Polling loop detects when build completes."""
    # Setup mock progress file
    # Run polling
    # Verify completion detected

def test_polling_handles_missing_file():
    """Polling gracefully handles missing progress file."""
    # Don't create progress file
    # Run polling
    # Verify no crash, appropriate message
```

---

## Verification Checklist

### Wave 1 Complete When:

- [ ] `ProgressDisplay.is_tty` property exists and works
- [ ] `SimpleTextProgress` class outputs readable text when `is_tty=False`
- [ ] `ProgressFileWriter` creates valid JSON at expected path
- [ ] All unit tests pass
- [ ] Manual test: Run via Claude Code Bash tool, verify text output visible

### Wave 2 Complete When:

- [ ] `/feature-build` polls progress file and displays updates
- [ ] Timeout documentation updated in autobuild.md
- [ ] `--bash-timeout` and `--sdk-timeout` flags working
- [ ] Integration tests pass
- [ ] Manual test: Full `/feature-build` run shows progress every 30s

---

## Success Metrics

| Metric | Before | After (Target) |
|--------|--------|----------------|
| User sees progress during build | No | Yes (polled) |
| Time to first feedback | >5 min | <60s |
| Non-TTY output quality | Poor (nothing) | Acceptable (text) |

---

## Future Phases (Reference)

### Phase 2 (Q1): Event-Driven Foundation

- NATS JetStream integration
- Real-time event publishing
- `guardkit watch` CLI command
- MCP bridge for Claude Code

### Phase 3 (Q2): Multi-Interface

- Web dashboard (React + WebSocket)
- A2A protocol semantics
- Voice notifications (Reachy integration)
- Multi-project orchestration

See [README.md](README.md) for complete roadmap and architecture diagrams.

---

## Troubleshooting

### Progress file not created

```bash
# Check directory exists
ls -la .guardkit/autobuild/TASK-XXX/

# Check file permissions
touch .guardkit/autobuild/TASK-XXX/test.json
```

### Text output not visible

```bash
# Verify TTY detection
python -c "from guardkit.orchestrator.progress import ProgressDisplay; p = ProgressDisplay(5); print(p.is_tty)"

# Force non-TTY mode for testing
TERM=dumb guardkit autobuild task TASK-XXX
```

### Polling not working

```bash
# Manual progress file check
cat .guardkit/autobuild/TASK-XXX/progress.json | jq .

# Check timestamps are updating
watch -n5 'cat .guardkit/autobuild/TASK-XXX/progress.json | jq .updated_at'
```
