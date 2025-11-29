"""
AI Analysis Helper Utilities

Provides reusable utilities for AI-assisted template validation, including
response validation, confidence scoring, and common AI operations.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
import json

from .ai_service import AIAnalysisService


@dataclass
class AIAnalysisResult:
    """Result from AI analysis operation."""
    success: bool
    data: Any
    confidence: float  # 0.0-1.0
    error: Optional[str] = None
    fallback_used: bool = False


def execute_ai_analysis(
    service: AIAnalysisService,
    prompt: str,
    context: Optional[Dict[str, Any]] = None,
    schema: Optional[Dict[str, Any]] = None,
    fallback_value: Optional[Any] = None,
    timeout_seconds: int = 300
) -> AIAnalysisResult:
    """Execute AI analysis with validation and fallback.

    This is the consolidated AI execution function that:
    1. Calls the AI service
    2. Validates the response against schema
    3. Falls back to provided value if AI fails
    4. Returns standardized result

    Args:
        service: AIAnalysisService instance (injected dependency)
        prompt: Analysis prompt for the AI
        context: Optional context dictionary
        schema: Optional schema for response validation
        fallback_value: Value to return if AI fails
        timeout_seconds: Maximum time to wait for AI

    Returns:
        AIAnalysisResult with success status, data, and confidence
    """
    try:
        # Execute AI analysis
        response = service.analyze(prompt, context, timeout_seconds)

        # Check if AI execution succeeded
        if not response.get("success", False):
            error_msg = response.get("error", "Unknown AI error")
            if fallback_value is not None:
                return AIAnalysisResult(
                    success=True,
                    data=fallback_value,
                    confidence=0.0,
                    error=f"AI failed, using fallback: {error_msg}",
                    fallback_used=True
                )
            else:
                return AIAnalysisResult(
                    success=False,
                    data=None,
                    confidence=0.0,
                    error=error_msg,
                    fallback_used=False
                )

        # Extract result
        result = response.get("result")

        # Validate against schema if provided
        if schema:
            is_valid, validation_error = validate_ai_response(result, schema)
            if not is_valid:
                if fallback_value is not None:
                    return AIAnalysisResult(
                        success=True,
                        data=fallback_value,
                        confidence=0.0,
                        error=f"Validation failed, using fallback: {validation_error}",
                        fallback_used=True
                    )
                else:
                    return AIAnalysisResult(
                        success=False,
                        data=None,
                        confidence=0.0,
                        error=f"Response validation failed: {validation_error}",
                        fallback_used=False
                    )

        # Calculate confidence
        confidence = response.get("confidence", calculate_confidence_score(result))

        return AIAnalysisResult(
            success=True,
            data=result,
            confidence=confidence,
            error=None,
            fallback_used=False
        )

    except TimeoutError as e:
        if fallback_value is not None:
            return AIAnalysisResult(
                success=True,
                data=fallback_value,
                confidence=0.0,
                error=f"AI timeout, using fallback: {str(e)}",
                fallback_used=True
            )
        else:
            return AIAnalysisResult(
                success=False,
                data=None,
                confidence=0.0,
                error=f"AI analysis timed out: {str(e)}",
                fallback_used=False
            )

    except Exception as e:
        if fallback_value is not None:
            return AIAnalysisResult(
                success=True,
                data=fallback_value,
                confidence=0.0,
                error=f"AI error, using fallback: {str(e)}",
                fallback_used=True
            )
        else:
            return AIAnalysisResult(
                success=False,
                data=None,
                confidence=0.0,
                error=f"AI analysis error: {str(e)}",
                fallback_used=False
            )


def validate_ai_response(
    response: Any,
    schema: Dict[str, Any]
) -> tuple[bool, Optional[str]]:
    """Validate AI response against expected schema.

    Args:
        response: The AI response to validate
        schema: Schema definition with required fields and types

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if response matches schema
        - error_message: Description of validation error, or None if valid

    Example schema:
        {
            "required_fields": ["analysis", "findings"],
            "field_types": {
                "analysis": str,
                "findings": list,
                "score": (int, float)
            },
            "list_item_types": {
                "findings": dict
            }
        }
    """
    if not isinstance(response, dict):
        return False, f"Response must be dict, got {type(response).__name__}"

    # Check required fields
    required_fields = schema.get("required_fields", [])
    for field in required_fields:
        if field not in response:
            return False, f"Missing required field: {field}"

    # Check field types
    field_types = schema.get("field_types", {})
    for field, expected_type in field_types.items():
        if field in response:
            value = response[field]
            if isinstance(expected_type, tuple):
                # Multiple acceptable types
                if not isinstance(value, expected_type):
                    type_names = [t.__name__ for t in expected_type]
                    return False, f"Field '{field}' must be one of {type_names}, got {type(value).__name__}"
            else:
                # Single expected type
                if not isinstance(value, expected_type):
                    return False, f"Field '{field}' must be {expected_type.__name__}, got {type(value).__name__}"

    # Check list item types
    list_item_types = schema.get("list_item_types", {})
    for field, item_type in list_item_types.items():
        if field in response and isinstance(response[field], list):
            for i, item in enumerate(response[field]):
                if not isinstance(item, item_type):
                    return False, f"Field '{field}[{i}]' must be {item_type.__name__}, got {type(item).__name__}"

    return True, None


def calculate_confidence_score(response: Any) -> float:
    """Calculate confidence score for AI response.

    This is an informational score based on response completeness and quality.
    It does not affect decision-making but helps users assess AI reliability.

    Args:
        response: AI response to score

    Returns:
        Confidence score between 0.0 and 1.0
    """
    if not response:
        return 0.0

    if not isinstance(response, dict):
        return 0.5  # Has data but not structured

    # Start with base score
    confidence = 0.5

    # Increase confidence for well-structured responses
    if "analysis" in response or "findings" in response:
        confidence += 0.1

    if "evidence" in response or "examples" in response:
        confidence += 0.1

    if "recommendations" in response:
        confidence += 0.1

    # Increase confidence for detailed responses
    total_content_length = 0
    for key, value in response.items():
        if isinstance(value, str):
            total_content_length += len(value)
        elif isinstance(value, list):
            total_content_length += len(value) * 100  # Estimate

    if total_content_length > 500:
        confidence += 0.1
    if total_content_length > 1000:
        confidence += 0.1

    # Cap at 1.0
    return min(confidence, 1.0)


def format_ai_findings_for_review(
    findings: Dict[str, Any],
    section_title: str
) -> str:
    """Format AI findings for human review.

    Args:
        findings: Dictionary of AI findings
        section_title: Title of the section being reviewed

    Returns:
        Formatted string for display to user
    """
    lines = []
    lines.append(f"\n{'=' * 60}")
    lines.append(f"AI Analysis: {section_title}")
    lines.append(f"{'=' * 60}\n")

    # Format each key-value pair
    for key, value in findings.items():
        if isinstance(value, list):
            lines.append(f"{key.replace('_', ' ').title()}:")
            for i, item in enumerate(value, 1):
                if isinstance(item, dict):
                    lines.append(f"  {i}. {json.dumps(item, indent=4)}")
                else:
                    lines.append(f"  {i}. {item}")
        elif isinstance(value, dict):
            lines.append(f"{key.replace('_', ' ').title()}:")
            lines.append(f"{json.dumps(value, indent=2)}")
        else:
            lines.append(f"{key.replace('_', ' ').title()}: {value}")
        lines.append("")

    lines.append(f"{'=' * 60}\n")
    return "\n".join(lines)


def create_fallback_finding(
    section_num: int,
    section_title: str,
    reason: str
) -> Dict[str, Any]:
    """Create a fallback finding when AI is unavailable.

    Args:
        section_num: Section number
        section_title: Section title
        reason: Reason for fallback

    Returns:
        Dictionary representing a manual fallback finding
    """
    return {
        "title": f"Manual Analysis Required - {section_title}",
        "description": f"AI analysis unavailable for Section {section_num}. {reason}",
        "is_positive": False,
        "impact": "Manual analysis required to complete this section",
        "evidence": "AI service unavailable or timed out",
        "ai_attempted": True,
        "ai_available": False
    }


def merge_ai_and_manual_findings(
    ai_findings: List[Dict[str, Any]],
    manual_findings: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Merge AI-generated and manual findings.

    Args:
        ai_findings: Findings from AI analysis
        manual_findings: Findings from manual analysis

    Returns:
        Combined list of findings with metadata indicating source
    """
    merged = []

    # Add AI findings with source metadata
    for finding in ai_findings:
        finding_with_source = finding.copy()
        finding_with_source["source"] = "ai"
        merged.append(finding_with_source)

    # Add manual findings with source metadata
    for finding in manual_findings:
        finding_with_source = finding.copy()
        finding_with_source["source"] = "manual"
        merged.append(finding_with_source)

    return merged


def extract_key_insights(ai_response: Dict[str, Any], top_n: int = 5) -> List[str]:
    """Extract top N key insights from AI response.

    Args:
        ai_response: AI analysis response
        top_n: Number of insights to extract

    Returns:
        List of key insight strings
    """
    insights = []

    # Extract from various possible fields
    if "insights" in ai_response:
        insights.extend(ai_response["insights"])

    if "key_findings" in ai_response:
        insights.extend(ai_response["key_findings"])

    if "recommendations" in ai_response:
        recs = ai_response["recommendations"]
        if isinstance(recs, list):
            insights.extend([r.get("description", r) if isinstance(r, dict) else str(r) for r in recs])

    # Return top N
    return insights[:top_n]


def should_use_ai_for_section(
    section_num: int,
    ai_enabled_sections: Optional[List[int]] = None
) -> bool:
    """Determine if AI should be used for a given section.

    Args:
        section_num: Section number to check
        ai_enabled_sections: List of sections with AI support (default: [8, 11, 12])

    Returns:
        True if AI should be used for this section
    """
    if ai_enabled_sections is None:
        ai_enabled_sections = [8, 11, 12]
    return section_num in ai_enabled_sections
