"""Result models for {{ProjectName}}."""
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AgentResult(BaseModel):
    """Result from agent execution.

    Example:
        ```python
        # Success
        result = AgentResult(
            success=True,
            data={"count": 42, "items": []}
        )

        # Failure
        result = AgentResult(
            success=False,
            error="Invalid input provided"
        )
        ```
    """

    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class WorkflowResult(BaseModel):
    """Result from workflow execution.

    Tracks results from each workflow step.

    Example:
        ```python
        result = WorkflowResult()
        result.add_step_result("analyze", {"metrics": {}})
        result.add_step_result("validate", {"passed": True})
        result.mark_success()
        ```
    """

    success: bool = False
    steps: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: Optional[int] = None

    def add_step_result(self, step_name: str, result: Any) -> None:
        """Add result from a workflow step.

        Args:
            step_name: Name of the step
            result: Result data from the step
        """
        self.steps[step_name] = result

    def mark_success(self) -> "WorkflowResult":
        """Mark workflow as successful.

        Returns:
            Self for method chaining
        """
        self.success = True
        return self

    def mark_failed(self, error: str) -> "WorkflowResult":
        """Mark workflow as failed.

        Args:
            error: Error message describing the failure

        Returns:
            Self for method chaining
        """
        self.success = False
        self.error = error
        return self
