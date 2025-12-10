"""Unit tests for security audit mode."""

import pytest
import json
import sys
from pathlib import Path

lib_path = Path(__file__).parent.parent.parent.parent.parent / "installer" / "core" / "commands" / "lib"
sys.path.insert(0, str(lib_path))

from review_modes import security_audit


def test_security_audit_basic():
    """Test basic security audit."""
    task_context = {
        "task_id": "TASK-001",
        "review_scope": ["src/auth/"]
    }
    results = security_audit.execute(task_context, "standard")

    assert results["mode"] == "security"
    assert results["depth"] == "standard"
    assert "risk_score" in results
    assert 0 <= results["risk_score"] <= 100
    assert "vulnerabilities" in results
    assert "owasp_analysis" in results
    assert "remediation_plan" in results


def test_parse_security_response_valid():
    """Test parsing valid security response."""
    response = json.dumps({
        "risk_score": 35,
        "vulnerabilities": [
            {
                "severity": "high",
                "category": "Injection",
                "title": "SQL Injection",
                "description": "Unsanitized user input",
                "location": "auth.py:42",
                "cwe_id": "CWE-89",
                "cvss_score": 8.5
            }
        ],
        "owasp_analysis": {
            "A01_broken_access_control": {"found": False}
        },
        "dependency_analysis": {"checked": True, "vulnerable_packages": []},
        "auth_authz_analysis": {"findings": []},
        "remediation_plan": []
    })

    results = security_audit.parse_security_response(response)

    assert results["risk_score"] == 35
    assert len(results["vulnerabilities"]) == 1
    assert results["vulnerabilities"][0]["severity"] == "high"


def test_parse_security_response_invalid():
    """Test parsing invalid security response."""
    response = "Not valid JSON"

    results = security_audit.parse_security_response(response)

    # Should return fallback structure
    assert results["risk_score"] == 50
    assert len(results["vulnerabilities"]) > 0
    assert results["dependency_analysis"]["checked"] is False


def test_calculate_risk_score():
    """Test risk score calculation."""
    vulnerabilities = [
        {"severity": "critical"},
        {"severity": "high"},
        {"severity": "medium"},
        {"severity": "low"}
    ]

    score = security_audit.calculate_risk_score(vulnerabilities)

    assert score > 0
    assert score <= 100


def test_calculate_risk_score_empty():
    """Test risk score with no vulnerabilities."""
    score = security_audit.calculate_risk_score([])

    assert score == 0


def test_prioritize_remediation():
    """Test remediation prioritization."""
    vulnerabilities = [
        {
            "severity": "low",
            "title": "Low severity issue",
            "cvss_score": 2.0,
            "remediation": "Fix it"
        },
        {
            "severity": "critical",
            "title": "Critical issue",
            "cvss_score": 9.5,
            "remediation": "Fix ASAP"
        },
        {
            "severity": "high",
            "title": "High severity issue",
            "cvss_score": 7.5,
            "remediation": "Fix soon"
        }
    ]

    plan = security_audit.prioritize_remediation(vulnerabilities)

    # Critical should be first
    assert plan[0]["priority"] == "critical"
    assert plan[0]["vulnerability"] == "Critical issue"


def test_estimate_remediation_effort():
    """Test remediation effort estimation."""
    vuln_high = {"category": "Insecure Design"}
    vuln_low = {"category": "Security Misconfiguration"}
    vuln_med = {"category": "Other"}

    assert security_audit.estimate_remediation_effort(vuln_high) == "high"
    assert security_audit.estimate_remediation_effort(vuln_low) == "low"
    assert security_audit.estimate_remediation_effort(vuln_med) == "medium"
