"""
Security Audit mode for /task-review command.

Performs security analysis using the security-specialist agent, checking for
OWASP Top 10 vulnerabilities, dependency CVEs, and auth/authz issues.
"""

import json
import re
from typing import Dict, Any, List, Literal

try:
    import sys
    from pathlib import Path
    lib_path = Path(__file__).parent.parent.parent / "lib"
    if str(lib_path) not in sys.path:
        sys.path.insert(0, str(lib_path))
    from agent_bridge.invoker import AgentBridgeInvoker as AgentInvoker
except (ImportError, ModuleNotFoundError):
    # Fallback for testing
    class AgentInvoker:
        def invoke(self, agent_name: str, prompt: str, timeout_seconds: int, context: Dict[str, Any]) -> str:
            return '{"vulnerabilities": [], "risk_score": 25, "remediation_plan": []}'


RiskLevel = Literal["critical", "high", "medium", "low", "info"]


def execute(task_context: Dict[str, Any], depth: str) -> Dict[str, Any]:
    """
    Execute security audit.

    Args:
        task_context: Task metadata including review_scope
        depth: Analysis depth (quick, standard, comprehensive)

    Returns:
        Structured security audit with vulnerabilities and remediation plan
    """
    # Build prompt based on depth
    prompt = build_security_prompt(task_context, depth)

    # Invoke security-specialist agent
    bridge = AgentInvoker()
    response = bridge.invoke(
        agent_name="security-specialist",
        prompt=prompt,
        timeout_seconds=get_timeout_for_depth(depth),
        context={"mode": "security", "depth": depth}
    )

    # Parse response into structured format
    results = parse_security_response(response)

    return {
        "mode": "security",
        "depth": depth,
        "risk_score": results["risk_score"],  # 0-100
        "vulnerabilities": results["vulnerabilities"],
        "owasp_analysis": results["owasp_analysis"],
        "dependency_analysis": results["dependency_analysis"],
        "auth_authz_analysis": results["auth_authz_analysis"],
        "remediation_plan": results["remediation_plan"],
        "compliance_notes": results.get("compliance_notes", [])
    }


def build_security_prompt(task_context: Dict[str, Any], depth: str) -> str:
    """
    Build prompt for security audit based on depth.

    Args:
        task_context: Task metadata including review_scope
        depth: Analysis depth (quick, standard, comprehensive)

    Returns:
        Formatted prompt string for the agent
    """
    scope = task_context.get("review_scope", [])
    task_id = task_context.get("task_id", "UNKNOWN")
    scope_str = ", ".join(scope) if scope else "entire codebase"

    owasp_top_10 = [
        "A01:2021 - Broken Access Control",
        "A02:2021 - Cryptographic Failures",
        "A03:2021 - Injection",
        "A04:2021 - Insecure Design",
        "A05:2021 - Security Misconfiguration",
        "A06:2021 - Vulnerable and Outdated Components",
        "A07:2021 - Identification and Authentication Failures",
        "A08:2021 - Software and Data Integrity Failures",
        "A09:2021 - Security Logging and Monitoring Failures",
        "A10:2021 - Server-Side Request Forgery (SSRF)"
    ]

    if depth == "quick":
        # Surface-level analysis (15-30 min)
        return f"""Quick security audit for task {task_id}.

Review scope: {scope_str}

Focus on high-severity issues:
- Check for obvious OWASP Top 10 vulnerabilities:
  {chr(10).join([f"  - {item}" for item in owasp_top_10[:5]])}
- Identify hardcoded secrets/credentials
- Check authentication implementation
- Review authorization logic
- Check for SQL injection risks
- Identify XSS vulnerabilities

Time budget: 20 minutes

Return structured JSON with:
{{
  "risk_score": <0-100>,
  "vulnerabilities": [
    {{
      "severity": "critical|high|medium|low|info",
      "category": "OWASP category",
      "title": "Brief title",
      "description": "What the vulnerability is",
      "location": "file.py:42",
      "cwe_id": "CWE-XXX",
      "cvss_score": <0.0-10.0>,
      "proof_of_concept": "How to exploit (if applicable)"
    }}
  ],
  "owasp_analysis": {{
    "A01_broken_access_control": {{"found": true|false, "details": "..."}},
    ...
  }},
  "dependency_analysis": {{"checked": false, "reason": "Quick mode"}},
  "auth_authz_analysis": {{"findings": [...]}},
  "remediation_plan": [
    {{"priority": "critical|high|medium|low", "action": "...", "effort": "low|medium|high"}}
  ]
}}
"""
    elif depth == "comprehensive":
        # Exhaustive analysis (4-6 hours)
        return f"""Comprehensive security audit for task {task_id}.

Review scope: {scope_str}

Exhaustive security analysis:

1. OWASP Top 10 (2021):
{chr(10).join([f"   - {item}" for item in owasp_top_10])}

2. Dependency Analysis:
   - Scan for known CVEs in dependencies
   - Check dependency versions
   - Identify supply chain risks
   - Review dependency licenses

3. Authentication & Authorization:
   - Authentication mechanism review
   - Session management
   - Password storage and hashing
   - Multi-factor authentication
   - Authorization logic and RBAC
   - Token handling (JWT, OAuth, etc.)
   - API key management

4. Data Protection:
   - Encryption in transit (TLS/SSL)
   - Encryption at rest
   - Sensitive data handling
   - PII protection
   - Key management

5. Additional Checks:
   - CORS configuration
   - CSP headers
   - Rate limiting
   - Input validation
   - Output encoding
   - File upload security
   - API security
   - Error handling and information disclosure

6. Compliance:
   - GDPR considerations
   - PCI-DSS requirements (if applicable)
   - HIPAA requirements (if applicable)

Time budget: 5 hours

Return structured JSON with:
{{
  "risk_score": <0-100>,
  "vulnerabilities": [
    {{
      "severity": "critical|high|medium|low|info",
      "category": "OWASP category or other",
      "title": "...",
      "description": "Detailed description",
      "location": "file.py:42",
      "cwe_id": "CWE-XXX",
      "cvss_score": <0.0-10.0>,
      "proof_of_concept": "Exploitation steps",
      "remediation": "How to fix",
      "references": ["url1", "url2"]
    }}
  ],
  "owasp_analysis": {{
    "A01_broken_access_control": {{"found": true|false, "details": "...", "examples": [...]}},
    ...
  }},
  "dependency_analysis": {{
    "checked": true,
    "vulnerable_packages": [...],
    "outdated_packages": [...],
    "license_issues": [...]
  }},
  "auth_authz_analysis": {{
    "authentication": {{"score": <0-10>, "findings": [...]}},
    "authorization": {{"score": <0-10>, "findings": [...]}},
    "session_management": {{"score": <0-10>, "findings": [...]}}
  }},
  "remediation_plan": [...],
  "compliance_notes": {{
    "gdpr": [...],
    "pci_dss": [...],
    "hipaa": [...]
  }}
}}
"""
    else:  # standard
        # Thorough analysis (1-2 hours)
        return f"""Security audit for task {task_id}.

Review scope: {scope_str}

Standard security analysis:

1. OWASP Top 10 Check:
{chr(10).join([f"   - {item}" for item in owasp_top_10])}

2. Authentication & Authorization:
   - Authentication implementation
   - Authorization checks
   - Session handling
   - Token management

3. Common Vulnerabilities:
   - SQL Injection
   - XSS (Cross-Site Scripting)
   - CSRF (Cross-Site Request Forgery)
   - Path Traversal
   - Command Injection
   - Hardcoded secrets

4. Dependency Check:
   - Known CVEs in dependencies (if tools available)

Time budget: 90 minutes

Return structured JSON with:
{{
  "risk_score": <0-100>,
  "vulnerabilities": [
    {{
      "severity": "critical|high|medium|low|info",
      "category": "OWASP category",
      "title": "...",
      "description": "...",
      "location": "file.py:42",
      "cwe_id": "CWE-XXX",
      "cvss_score": <0.0-10.0>,
      "remediation": "How to fix"
    }}
  ],
  "owasp_analysis": {{
    "A01_broken_access_control": {{"found": true|false, "details": "..."}},
    ...
  }},
  "dependency_analysis": {{"checked": true, "vulnerable_packages": [...]}},
  "auth_authz_analysis": {{"findings": [...]}},
  "remediation_plan": [
    {{"priority": "critical|high|medium|low", "action": "...", "effort": "low|medium|high"}}
  ]
}}
"""


def get_timeout_for_depth(depth: str) -> int:
    """
    Get timeout in seconds based on depth.

    Args:
        depth: Analysis depth (quick, standard, comprehensive)

    Returns:
        Timeout in seconds
    """
    timeouts = {
        "quick": 1800,        # 30 minutes
        "standard": 7200,     # 2 hours
        "comprehensive": 21600  # 6 hours
    }
    return timeouts.get(depth, 7200)


def parse_security_response(response: str) -> Dict[str, Any]:
    """
    Parse agent response into structured format.

    Args:
        response: JSON string from security-specialist agent

    Returns:
        Parsed dictionary with security findings
    """
    try:
        # Try to parse as JSON first
        if isinstance(response, str):
            # Extract JSON from markdown code blocks if present
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                response = json_match.group(1)

            data = json.loads(response)
        else:
            data = response

        # Validate and normalize data
        return {
            "risk_score": min(100, max(0, data.get("risk_score", 0))),
            "vulnerabilities": data.get("vulnerabilities", []),
            "owasp_analysis": data.get("owasp_analysis", {}),
            "dependency_analysis": data.get("dependency_analysis", {"checked": False}),
            "auth_authz_analysis": data.get("auth_authz_analysis", {"findings": []}),
            "remediation_plan": data.get("remediation_plan", []),
            "compliance_notes": data.get("compliance_notes", {})
        }
    except (json.JSONDecodeError, ValueError) as e:
        # Fallback structure
        return {
            "risk_score": 50,
            "vulnerabilities": [
                {
                    "severity": "high",
                    "category": "Unknown",
                    "title": "Failed to parse security analysis",
                    "description": f"Error: {str(e)}",
                    "location": "",
                    "cwe_id": "",
                    "cvss_score": 0.0,
                    "remediation": "Re-run security audit"
                }
            ],
            "owasp_analysis": {},
            "dependency_analysis": {"checked": False, "error": str(e)},
            "auth_authz_analysis": {"findings": []},
            "remediation_plan": [
                {
                    "priority": "high",
                    "action": "Re-run security audit with proper output format",
                    "effort": "low"
                }
            ],
            "compliance_notes": {}
        }


def calculate_risk_score(vulnerabilities: List[Dict[str, Any]]) -> int:
    """
    Calculate overall risk score from vulnerabilities.

    Args:
        vulnerabilities: List of vulnerability dictionaries

    Returns:
        Risk score (0-100, higher is worse)
    """
    if not vulnerabilities:
        return 0

    severity_weights = {
        "critical": 25,
        "high": 15,
        "medium": 8,
        "low": 3,
        "info": 1
    }

    total_risk = 0
    for vuln in vulnerabilities:
        severity = vuln.get("severity", "low")
        total_risk += severity_weights.get(severity, 3)

    # Normalize to 0-100 scale (cap at 100)
    return min(100, total_risk)


def prioritize_remediation(vulnerabilities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Prioritize vulnerabilities for remediation.

    Args:
        vulnerabilities: List of vulnerability dictionaries

    Returns:
        Sorted list of remediation actions
    """
    # Sort by severity (critical > high > medium > low > info)
    severity_order = {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
        "info": 4
    }

    sorted_vulns = sorted(
        vulnerabilities,
        key=lambda v: (severity_order.get(v.get("severity", "low"), 3), -v.get("cvss_score", 0))
    )

    # Generate remediation plan
    remediation_plan = []
    for vuln in sorted_vulns:
        remediation_plan.append({
            "priority": vuln.get("severity", "low"),
            "action": vuln.get("remediation", f"Fix {vuln.get('title', 'vulnerability')}"),
            "vulnerability": vuln.get("title", ""),
            "location": vuln.get("location", ""),
            "effort": estimate_remediation_effort(vuln)
        })

    return remediation_plan


def estimate_remediation_effort(vulnerability: Dict[str, Any]) -> str:
    """
    Estimate effort required to remediate a vulnerability.

    Args:
        vulnerability: Vulnerability dictionary

    Returns:
        Effort estimate (low, medium, high)
    """
    # Simple heuristic based on vulnerability type
    category = vulnerability.get("category", "").lower()

    high_effort_categories = [
        "insecure design",
        "vulnerable and outdated components",
        "broken access control"
    ]

    low_effort_categories = [
        "security misconfiguration",
        "security logging"
    ]

    if any(cat in category for cat in high_effort_categories):
        return "high"
    elif any(cat in category for cat in low_effort_categories):
        return "low"
    else:
        return "medium"
