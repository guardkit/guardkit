"""Pytest fixtures for review mode tests."""

import pytest
import sys
from pathlib import Path
from typing import Dict, Any

# Add lib path for imports
lib_path = Path(__file__).parent.parent.parent.parent.parent / "installer" / "global" / "commands" / "lib"
sys.path.insert(0, str(lib_path))


class MockAgentInvoker:
    """Mock agent invoker for testing (doesn't exit with code 42)."""

    def invoke(self, agent_name: str, prompt: str, timeout_seconds: int = 120, context: Dict[str, Any] = None) -> str:
        """Mock invoke that returns test data instead of exiting."""
        if agent_name == "architectural-reviewer":
            if context and context.get("analysis") == "design":
                # For technical debt - design analysis
                return '{"debt_items": [{"category": "design", "description": "Design debt item", "impact": "high", "effort": "medium", "risk": "high", "location": "module"}]}'
            else:
                return '{"overall_score": 75, "solid_score": 80, "dry_score": 70, "yagni_score": 75, "findings": [], "recommendations": [], "evidence_files": []}'
        elif agent_name == "code-reviewer":
            if context and context.get("analysis") == "code":
                # For technical debt - code analysis
                return '{"debt_items": [{"category": "code", "description": "Code debt item", "impact": "medium", "effort": "low", "risk": "low", "location": "file.py:10"}]}'
            else:
                return '{"quality_score": 7.5, "complexity_metrics": {"avg_cyclomatic": 5}, "code_smells": [], "style_issues": [], "test_coverage": null, "findings": [], "recommendations": []}'
        elif agent_name == "software-architect":
            return '{"options": [{"name": "Option A", "scores": {}, "total_score": 0, "pros": [], "cons": []}], "recommendation": "Option A", "confidence": "medium", "criteria": [], "justification": ""}'
        elif agent_name == "security-specialist":
            return '{"risk_score": 25, "vulnerabilities": [], "owasp_analysis": {}, "dependency_analysis": {"checked": false}, "auth_authz_analysis": {"findings": []}, "remediation_plan": []}'
        else:
            return '{}'


@pytest.fixture(autouse=True)
def mock_agent_invoker(monkeypatch):
    """Auto-use fixture to mock AgentBridgeInvoker for all tests."""
    # Mock the AgentBridgeInvoker in all review mode modules
    from review_modes import (
        architectural_review,
        code_quality_review,
        decision_analysis,
        technical_debt_assessment,
        security_audit
    )

    # Replace AgentInvoker in each module
    monkeypatch.setattr(architectural_review, "AgentInvoker", MockAgentInvoker)
    monkeypatch.setattr(code_quality_review, "AgentInvoker", MockAgentInvoker)
    monkeypatch.setattr(decision_analysis, "AgentInvoker", MockAgentInvoker)
    monkeypatch.setattr(technical_debt_assessment, "AgentInvoker", MockAgentInvoker)
    monkeypatch.setattr(security_audit, "AgentInvoker", MockAgentInvoker)
