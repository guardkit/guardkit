"""
MCP Response Size Monitoring

This module provides classes for tracking and monitoring MCP request/response
metrics, including token usage, variance detection, and reporting.

Classes:
    - MCPRequest: Represents an MCP request with expected token budget
    - MCPResponse: Represents an MCP response with actual token usage
    - MCPMonitor: Monitors MCP calls and generates usage reports

Example:
    >>> monitor = MCPMonitor()
    >>> request = monitor.record_request(
    ...     mcp_name="context7",
    ...     method="get_library_docs",
    ...     query={"library_id": "/fastapi", "topic": "DI"},
    ...     expected_tokens=1000,
    ...     phase="phase_2"
    ... )
    >>> monitor.record_response(
    ...     request=request,
    ...     actual_tokens=850,
    ...     duration_seconds=1.2,
    ...     success=True
    ... )
    >>> report = monitor.generate_report()
    >>> monitor.save_report("mcp_usage_report.json")
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import json
import os


@dataclass
class MCPRequest:
    """
    Represents an MCP request with expected token budget.

    Attributes:
        mcp_name: Name of the MCP server (e.g., "context7", "design-patterns")
        method: MCP method being called (e.g., "get_library_docs")
        query: Dictionary of query parameters
        expected_tokens: Expected token budget for this request
        phase: Workflow phase (e.g., "phase_2", "phase_3")
        timestamp: Request timestamp (auto-generated)

    Example:
        >>> request = MCPRequest(
        ...     mcp_name="context7",
        ...     method="get_library_docs",
        ...     query={"library_id": "/fastapi"},
        ...     expected_tokens=1000,
        ...     phase="phase_2"
        ... )
    """

    mcp_name: str
    method: str
    query: dict
    expected_tokens: int
    phase: str
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate request fields after initialization."""
        if self.expected_tokens < 0:
            raise ValueError("Expected tokens must be non-negative")
        if not self.mcp_name:
            raise ValueError("MCP name cannot be empty")
        if not self.method:
            raise ValueError("Method cannot be empty")


@dataclass
class MCPResponse:
    """
    Represents an MCP response with token usage metrics.

    Attributes:
        request: The associated MCPRequest
        actual_tokens: Actual token count in response
        duration_seconds: Request duration in seconds
        success: Whether the request succeeded
        error_message: Optional error message if request failed
        variance: Token variance from budget (auto-calculated)

    The variance is automatically calculated as:
        variance = (actual_tokens - expected_tokens) / expected_tokens

    Example:
        >>> response = MCPResponse(
        ...     request=request,
        ...     actual_tokens=850,
        ...     duration_seconds=1.2,
        ...     success=True
        ... )
        >>> response.variance
        -0.15  # 15% under budget
    """

    request: MCPRequest
    actual_tokens: int
    duration_seconds: float
    success: bool
    error_message: Optional[str] = None
    variance: float = field(init=False)

    def __post_init__(self):
        """Calculate variance after initialization."""
        if self.request.expected_tokens > 0:
            self.variance = (
                (self.actual_tokens - self.request.expected_tokens)
                / self.request.expected_tokens
            )
        else:
            # If expected tokens is 0, variance is undefined
            self.variance = 0.0

        # Validate fields
        if self.actual_tokens < 0:
            raise ValueError("Actual tokens must be non-negative")
        if self.duration_seconds < 0:
            raise ValueError("Duration must be non-negative")

    def is_over_budget(self, threshold: float = 0.20) -> bool:
        """
        Check if response exceeded budget by more than threshold.

        Args:
            threshold: Variance threshold (default: 0.20 = 20%)

        Returns:
            bool: True if variance > threshold

        Example:
            >>> response.is_over_budget()
            False  # -15% variance is under budget
        """
        return self.variance > threshold

    def variance_percentage(self) -> float:
        """
        Get variance as percentage.

        Returns:
            float: Variance as percentage (e.g., 20.5 for 20.5%)

        Example:
            >>> response.variance_percentage()
            -15.0  # 15% under budget
        """
        return self.variance * 100


class MCPMonitor:
    """
    Monitor MCP requests and responses for token usage tracking.

    Features:
        - Real-time variance detection (warns at >20% over budget)
        - Phase-specific tracking
        - Historical data for budget tuning
        - JSON report generation

    Attributes:
        requests: List of all recorded requests
        responses: List of all recorded responses
        variance_threshold: Threshold for over-budget warnings (default: 0.20)

    Example:
        >>> monitor = MCPMonitor()
        >>> request = monitor.record_request(
        ...     mcp_name="context7",
        ...     method="get_library_docs",
        ...     query={"library_id": "/fastapi", "topic": "DI"},
        ...     expected_tokens=1000,
        ...     phase="phase_2"
        ... )
        >>> monitor.record_response(
        ...     request=request,
        ...     actual_tokens=850,
        ...     duration_seconds=1.2,
        ...     success=True
        ... )
        >>> report = monitor.generate_report()
        >>> monitor.save_report("mcp_usage_report.json")
    """

    def __init__(self, variance_threshold: float = 0.20):
        """
        Initialize MCPMonitor.

        Args:
            variance_threshold: Threshold for over-budget warnings (default: 0.20 = 20%)
        """
        self.requests: List[MCPRequest] = []
        self.responses: List[MCPResponse] = []
        self._variance_threshold = variance_threshold

    @property
    def variance_threshold(self) -> float:
        """Get the variance threshold for over-budget detection."""
        return self._variance_threshold

    @variance_threshold.setter
    def variance_threshold(self, value: float):
        """
        Set the variance threshold.

        Args:
            value: New threshold value (must be positive)

        Raises:
            ValueError: If value is not positive
        """
        if value <= 0:
            raise ValueError("Variance threshold must be positive")
        self._variance_threshold = value

    def record_request(
        self,
        mcp_name: str,
        method: str,
        query: dict,
        expected_tokens: int,
        phase: str
    ) -> MCPRequest:
        """
        Record an MCP request before execution.

        Args:
            mcp_name: Name of the MCP server
            method: MCP method being called
            query: Query parameters
            expected_tokens: Expected token budget
            phase: Workflow phase

        Returns:
            MCPRequest: The created request object

        Example:
            >>> request = monitor.record_request(
            ...     mcp_name="context7",
            ...     method="get_library_docs",
            ...     query={"library_id": "/fastapi"},
            ...     expected_tokens=1000,
            ...     phase="phase_2"
            ... )
        """
        request = MCPRequest(
            mcp_name=mcp_name,
            method=method,
            query=query,
            expected_tokens=expected_tokens,
            phase=phase
        )
        self.requests.append(request)

        # Real-time console output
        print(f"📡 MCP Request: {mcp_name}/{method} (Phase {phase})")
        print(f"   Budget: {expected_tokens:,} tokens")

        return request

    def record_response(
        self,
        request: MCPRequest,
        actual_tokens: int,
        duration_seconds: float,
        success: bool,
        error_message: Optional[str] = None
    ) -> MCPResponse:
        """
        Record an MCP response after execution.

        Args:
            request: The associated request
            actual_tokens: Actual token count in response
            duration_seconds: Request duration
            success: Whether request succeeded
            error_message: Optional error message

        Returns:
            MCPResponse: The created response object

        Example:
            >>> response = monitor.record_response(
            ...     request=request,
            ...     actual_tokens=850,
            ...     duration_seconds=1.2,
            ...     success=True
            ... )
        """
        response = MCPResponse(
            request=request,
            actual_tokens=actual_tokens,
            duration_seconds=duration_seconds,
            success=success,
            error_message=error_message
        )
        self.responses.append(response)

        # Real-time console output
        status_emoji = "✅" if success else "❌"
        print(f"{status_emoji} MCP Response: {request.mcp_name}/{request.method}")
        print(f"   Actual: {actual_tokens:,} tokens")

        # Variance detection
        variance_pct = response.variance_percentage()

        if response.is_over_budget(self.variance_threshold):
            # Over budget - warn
            print(f"   ⚠️ Variance: {variance_pct:+.1f}% from budget")
            print(f"   WARNING: Exceeded budget by {variance_pct:.1f}%")
        elif abs(response.variance) > self.variance_threshold:
            # Significantly under budget - informational
            print(f"   ℹ️ Variance: {variance_pct:+.1f}% from budget")
        else:
            # Within acceptable range
            print(f"   ✓ Variance: {variance_pct:+.1f}% from budget")

        if not success and error_message:
            print(f"   Error: {error_message}")

        return response

    def generate_report(self) -> dict:
        """
        Generate comprehensive usage report.

        Returns:
            dict: Report containing summary statistics, phase breakdown,
                  and per-request details

        Example:
            >>> report = monitor.generate_report()
            >>> report['summary']['total_calls']
            3
            >>> report['summary']['total_variance_pct']
            -8.67
        """
        if not self.responses:
            return {"message": "No MCP requests tracked"}

        total_calls = len(self.responses)
        successful_calls = sum(1 for r in self.responses if r.success)
        failed_calls = total_calls - successful_calls

        total_expected = sum(r.request.expected_tokens for r in self.responses)
        total_actual = sum(r.actual_tokens for r in self.responses)
        total_variance = (
            (total_actual - total_expected) / total_expected
            if total_expected > 0 else 0
        )

        over_budget_calls = sum(
            1 for r in self.responses
            if r.is_over_budget(self.variance_threshold)
        )

        # Phase breakdown
        phases: Dict[str, Dict] = {}
        for response in self.responses:
            phase = response.request.phase
            if phase not in phases:
                phases[phase] = {
                    "calls": 0,
                    "expected_tokens": 0,
                    "actual_tokens": 0,
                    "over_budget": 0
                }

            phases[phase]["calls"] += 1
            phases[phase]["expected_tokens"] += response.request.expected_tokens
            phases[phase]["actual_tokens"] += response.actual_tokens
            if response.is_over_budget(self.variance_threshold):
                phases[phase]["over_budget"] += 1

        return {
            "summary": {
                "total_calls": total_calls,
                "successful_calls": successful_calls,
                "failed_calls": failed_calls,
                "total_expected_tokens": total_expected,
                "total_actual_tokens": total_actual,
                "total_variance_pct": total_variance * 100,
                "over_budget_calls": over_budget_calls,
                "over_budget_pct": (
                    (over_budget_calls / total_calls * 100)
                    if total_calls > 0 else 0
                )
            },
            "phases": phases,
            "requests": [
                {
                    "mcp": r.request.mcp_name,
                    "method": r.request.method,
                    "phase": r.request.phase,
                    "expected_tokens": r.request.expected_tokens,
                    "actual_tokens": r.actual_tokens,
                    "variance_pct": r.variance_percentage(),
                    "duration_seconds": r.duration_seconds,
                    "success": r.success,
                    "error_message": r.error_message
                }
                for r in self.responses
            ]
        }

    def save_report(self, filepath: str):
        """
        Save report to JSON file.

        Creates parent directories if they don't exist.

        Args:
            filepath: Path to save report to (e.g., "docs/state/TASK-001/mcp_usage_report.json")

        Raises:
            IOError: If file cannot be written

        Example:
            >>> monitor.save_report("mcp_usage_report.json")
        """
        report = self.generate_report()

        # Create parent directories if needed
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        try:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"📊 MCP Usage Report saved: {filepath}")
        except IOError as e:
            print(f"❌ Error saving report to {filepath}: {e}")
            raise

    def get_total_calls(self) -> int:
        """Get total number of MCP calls tracked."""
        return len(self.responses)

    def get_successful_calls(self) -> int:
        """Get number of successful MCP calls."""
        return sum(1 for r in self.responses if r.success)

    def get_failed_calls(self) -> int:
        """Get number of failed MCP calls."""
        return sum(1 for r in self.responses if not r.success)

    def get_total_tokens_used(self) -> int:
        """Get total actual tokens used across all calls."""
        return sum(r.actual_tokens for r in self.responses)

    def get_total_tokens_budgeted(self) -> int:
        """Get total budgeted tokens across all calls."""
        return sum(r.request.expected_tokens for r in self.responses)

    def clear(self):
        """Clear all recorded requests and responses."""
        self.requests.clear()
        self.responses.clear()
