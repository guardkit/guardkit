"""
AI Analysis Service Protocol

Provides abstraction layer for AI analysis services, enabling dependency injection
and testability.
"""

from typing import Protocol, Dict, Any, Optional
from pathlib import Path
import json


class AIAnalysisService(Protocol):
    """Protocol for AI analysis services.

    This protocol defines the interface that all AI analysis services must implement.
    It enables dependency injection and makes testing easier by allowing mock implementations.
    """

    def analyze(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 300
    ) -> Dict[str, Any]:
        """Execute AI analysis with given prompt and context.

        Args:
            prompt: The analysis prompt/task for the AI
            context: Optional context dictionary (template_path, manifest, etc.)
            timeout_seconds: Maximum time to wait for AI response (default: 5 minutes)

        Returns:
            Dictionary containing AI response with structure:
            {
                "success": bool,
                "result": Any,  # The actual AI analysis result
                "confidence": float,  # 0.0-1.0
                "error": Optional[str],  # Error message if success=False
                "metadata": Dict  # Additional metadata (model, tokens, duration, etc.)
            }

        Raises:
            TimeoutError: If AI takes longer than timeout_seconds
            Exception: Other errors during AI execution
        """
        ...


class TaskAgentService:
    """Concrete implementation of AIAnalysisService using Task agent.

    This is the production implementation that uses the GuardKit Task agent
    for AI analysis.
    """

    def __init__(self, verbose: bool = False):
        """Initialize Task agent service.

        Args:
            verbose: If True, log detailed information about AI calls
        """
        self.verbose = verbose

    def analyze(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 300
    ) -> Dict[str, Any]:
        """Execute AI analysis using Task agent.

        Args:
            prompt: The analysis prompt/task for the AI
            context: Optional context dictionary
            timeout_seconds: Maximum time to wait for AI response

        Returns:
            Dictionary containing AI response (see Protocol docstring)
        """
        import time
        start_time = time.time()

        try:
            if self.verbose:
                print(f"[TaskAgentService] Starting AI analysis...")
                print(f"[TaskAgentService] Prompt length: {len(prompt)} chars")
                if context:
                    print(f"[TaskAgentService] Context keys: {list(context.keys())}")

            # Prepare full prompt with context
            full_prompt = self._prepare_prompt(prompt, context)

            # Execute Task agent
            # NOTE: This is a placeholder - actual Task agent execution would go here
            # In real implementation, this would call the Task agent via the Task tool
            result = self._execute_task_agent(full_prompt, timeout_seconds)

            duration = time.time() - start_time

            if self.verbose:
                print(f"[TaskAgentService] AI analysis completed in {duration:.2f}s")

            return {
                "success": True,
                "result": result,
                "confidence": self._calculate_confidence(result),
                "error": None,
                "metadata": {
                    "model": "task-agent",
                    "duration_seconds": duration,
                    "prompt_length": len(full_prompt),
                }
            }

        except TimeoutError as e:
            duration = time.time() - start_time
            error_msg = f"AI analysis timed out after {timeout_seconds}s"

            if self.verbose:
                print(f"[TaskAgentService] {error_msg}")

            return {
                "success": False,
                "result": None,
                "confidence": 0.0,
                "error": error_msg,
                "metadata": {
                    "model": "task-agent",
                    "duration_seconds": duration,
                    "timeout": True,
                }
            }

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"AI analysis failed: {str(e)}"

            if self.verbose:
                print(f"[TaskAgentService] {error_msg}")

            return {
                "success": False,
                "result": None,
                "confidence": 0.0,
                "error": error_msg,
                "metadata": {
                    "model": "task-agent",
                    "duration_seconds": duration,
                    "error_type": type(e).__name__,
                }
            }

    def _prepare_prompt(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Prepare full prompt by combining prompt and context.

        Args:
            prompt: Base prompt
            context: Context dictionary

        Returns:
            Full prompt with context included
        """
        if not context:
            return prompt

        context_str = json.dumps(context, indent=2, default=str)
        return f"{prompt}\n\n**Context:**\n```json\n{context_str}\n```"

    def _execute_task_agent(self, prompt: str, timeout_seconds: int) -> Any:
        """Execute Task agent with the given prompt.

        This is a placeholder that will be replaced with actual Task agent execution.
        In real implementation, this would use the Task tool to launch an agent.

        Args:
            prompt: The full prompt to send to Task agent
            timeout_seconds: Maximum execution time

        Returns:
            AI analysis result

        Raises:
            TimeoutError: If execution exceeds timeout
            Exception: Other execution errors
        """
        # TODO: Replace with actual Task agent execution
        # For now, return a placeholder
        # In real implementation:
        # from ..utils import execute_task_agent
        # return execute_task_agent(prompt, timeout=timeout_seconds)

        # Placeholder response
        return {
            "analysis": "AI analysis result would go here",
            "findings": [],
            "recommendations": []
        }

    def _calculate_confidence(self, result: Any) -> float:
        """Calculate confidence score for AI result.

        Args:
            result: AI analysis result

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # TODO: Implement actual confidence calculation
        # For now, return default medium confidence
        # In real implementation, this could be based on:
        # - Presence of specific fields in result
        # - Quality of evidence/citations
        # - Internal AI confidence if provided
        # - Consistency checks

        if not result:
            return 0.0

        # Default to medium confidence for placeholder
        return 0.75


class MockAIService:
    """Mock implementation for testing.

    This mock service allows tests to run without requiring actual AI infrastructure.
    Tests can configure the mock to return specific responses.
    """

    def __init__(self, mock_response: Optional[Dict[str, Any]] = None):
        """Initialize mock service.

        Args:
            mock_response: Predefined response to return from analyze()
        """
        self.mock_response = mock_response or {
            "success": True,
            "result": {"mock": "response"},
            "confidence": 1.0,
            "error": None,
            "metadata": {"model": "mock"}
        }
        self.call_count = 0
        self.last_prompt = None
        self.last_context = None

    def analyze(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 300
    ) -> Dict[str, Any]:
        """Return mock response.

        Args:
            prompt: The analysis prompt (recorded but not used)
            context: Context dictionary (recorded but not used)
            timeout_seconds: Timeout (ignored)

        Returns:
            The mock_response provided at initialization
        """
        self.call_count += 1
        self.last_prompt = prompt
        self.last_context = context
        return self.mock_response

    def set_response(self, response: Dict[str, Any]) -> None:
        """Update the mock response.

        Args:
            response: New mock response to return
        """
        self.mock_response = response

    def reset(self) -> None:
        """Reset call tracking."""
        self.call_count = 0
        self.last_prompt = None
        self.last_context = None
