"""
Per-task progress logger for parallel execution diagnostics.

Writes dedicated log files at `.guardkit/autobuild/{task_id}/progress.log`
with periodic snapshots during SDK invocations. This enables post-mortem
diagnosis of timed-out tasks that would otherwise be black boxes.

Architecture:
    - Each parallel task gets its own log file (no interleaving)
    - Snapshots written at configurable intervals (default: 60s)
    - Integrates with existing async_heartbeat pattern
    - Console output unchanged (progress logs are additive)

Example:
    >>> logger = TaskProgressLogger(task_id="TASK-001", repo_root=Path.cwd())
    >>> logger.log_start(phase="Player invocation")
    >>> logger.log_snapshot(elapsed=60, phase="Player invocation",
    ...     files_changed=3, last_tool="Edit")
    >>> logger.log_timeout(elapsed=2400, last_state="Player invocation at 2340s")
    >>> logger.close()
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_LOG_INTERVAL = 60  # seconds


class TaskProgressLogger:
    """Writes per-task progress snapshots to a dedicated log file.

    Each task gets a separate log file at:
        .guardkit/autobuild/{task_id}/progress.log

    Snapshots include: elapsed time, current phase, files changed,
    last tool observed. These are written periodically during SDK
    invocations and on timeout events.

    Attributes
    ----------
    task_id : str
        Task identifier
    log_path : Path
        Path to the progress log file
    interval : int
        Seconds between progress snapshots
    """

    def __init__(
        self,
        task_id: str,
        repo_root: Path,
        interval: int = DEFAULT_LOG_INTERVAL,
    ):
        """Initialize TaskProgressLogger.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        repo_root : Path
            Repository root directory (log written relative to this)
        interval : int, optional
            Seconds between snapshots (default: 60)
        """
        self.task_id = task_id
        self.interval = interval
        self._start_time: Optional[float] = None
        self._current_phase: Optional[str] = None
        self._last_tool: Optional[str] = None
        self._files_changed: int = 0
        self._snapshot_count: int = 0

        # Create log directory and file
        log_dir = repo_root / ".guardkit" / "autobuild" / task_id
        log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = log_dir / "progress.log"

        # Open file handle for appending
        self._file = open(self.log_path, "a", encoding="utf-8")

    def log_start(self, phase: str) -> None:
        """Log the start of a phase (e.g., SDK invocation).

        Parameters
        ----------
        phase : str
            Phase description (e.g., "Player invocation turn 1")
        """
        self._start_time = time.monotonic()
        self._current_phase = phase
        self._last_tool = None
        self._files_changed = 0
        self._snapshot_count = 0

        timestamp = datetime.now().isoformat(timespec="seconds")
        self._write(f"[{timestamp}] START {self.task_id}: {phase}")

    def log_snapshot(
        self,
        elapsed: float,
        phase: str,
        files_changed: int = 0,
        last_tool: Optional[str] = None,
    ) -> None:
        """Write a progress snapshot.

        Parameters
        ----------
        elapsed : float
            Seconds elapsed since phase start
        phase : str
            Current phase description
        files_changed : int, optional
            Number of files changed so far
        last_tool : Optional[str], optional
            Last tool use observed (e.g., "Edit", "Bash")
        """
        self._current_phase = phase
        self._last_tool = last_tool or self._last_tool
        self._files_changed = files_changed
        self._snapshot_count += 1

        timestamp = datetime.now().isoformat(timespec="seconds")
        tool_info = f", last_tool={self._last_tool}" if self._last_tool else ""
        self._write(
            f"[{timestamp}] SNAPSHOT {self.task_id}: "
            f"elapsed={int(elapsed)}s, phase={phase}, "
            f"files_changed={files_changed}{tool_info}"
        )

    def log_timeout(self, elapsed: float, last_state: Optional[str] = None) -> None:
        """Log timeout event with last known state.

        Parameters
        ----------
        elapsed : float
            Seconds elapsed when timeout occurred
        last_state : Optional[str], optional
            Description of last known state
        """
        timestamp = datetime.now().isoformat(timespec="seconds")
        state_info = last_state or self._format_last_state()
        self._write(
            f"[{timestamp}] TIMEOUT {self.task_id}: "
            f"elapsed={int(elapsed)}s, snapshots={self._snapshot_count}, "
            f"last_state={state_info}"
        )

    def log_complete(self, elapsed: float, decision: str) -> None:
        """Log successful completion.

        Parameters
        ----------
        elapsed : float
            Total seconds elapsed
        decision : str
            Final decision (e.g., "approved", "max_turns_exceeded")
        """
        timestamp = datetime.now().isoformat(timespec="seconds")
        self._write(
            f"[{timestamp}] COMPLETE {self.task_id}: "
            f"elapsed={int(elapsed)}s, decision={decision}, "
            f"snapshots={self._snapshot_count}"
        )

    def get_last_state(self) -> str:
        """Return formatted last known state for timeout diagnostics.

        Returns
        -------
        str
            Human-readable last known state
        """
        return self._format_last_state()

    def close(self) -> None:
        """Flush and close the log file."""
        if self._file and not self._file.closed:
            self._file.flush()
            self._file.close()

    def _format_last_state(self) -> str:
        """Format last known state from tracked fields.

        Returns
        -------
        str
            Formatted state string
        """
        parts = []
        if self._current_phase:
            parts.append(f"phase={self._current_phase}")
        if self._last_tool:
            parts.append(f"last_tool={self._last_tool}")
        parts.append(f"files_changed={self._files_changed}")
        parts.append(f"snapshots={self._snapshot_count}")
        return ", ".join(parts) if parts else "no state captured"

    def _write(self, line: str) -> None:
        """Write a line to the progress log.

        Parameters
        ----------
        line : str
            Log line to write
        """
        try:
            self._file.write(line + "\n")
            self._file.flush()
        except (IOError, ValueError):
            # File closed or I/O error - log but don't crash
            logger.warning(f"Failed to write progress log for {self.task_id}")

    def __enter__(self) -> "TaskProgressLogger":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()
