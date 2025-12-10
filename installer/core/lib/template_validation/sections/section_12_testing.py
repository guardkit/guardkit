"""
Section 12: Validation Testing

Tests placeholder replacement, agent integration, and cross-references using AI simulation.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..models import SectionResult, ValidationIssue, IssueSeverity, IssueCategory, Finding
from ..ai_service import AIAnalysisService
from ..ai_analysis_helpers import execute_ai_analysis, AIAnalysisResult


class ValidationTestingSection:
    """Section 12: Validation Testing (AI-Enhanced)"""

    def __init__(self, ai_service: Optional[AIAnalysisService] = None):
        """Initialize section with optional AI service.

        Args:
            ai_service: AI analysis service for testing simulation.
                       If None, manual testing required.
        """
        self.ai_service = ai_service

    @property
    def section_num(self) -> int:
        return 12

    @property
    def title(self) -> str:
        return "Validation Testing"

    @property
    def description(self) -> str:
        return "Test placeholder replacement and integration"

    def execute(self, template_path: Path, interactive: bool = True) -> SectionResult:
        """Execute section with AI assistance if available.

        Args:
            template_path: Path to template directory
            interactive: Whether to allow interactive review

        Returns:
            SectionResult with test findings and score
        """
        issues: List[ValidationIssue] = []
        findings: List[Finding] = []
        score = 7.0

        if not self.ai_service:
            # Manual testing required
            findings.append(Finding(
                title="Manual Testing Required",
                description="Test placeholder replacement and integration manually",
                is_positive=False,
                impact="Ensures template functionality",
            ))
        else:
            # AI-assisted testing
            test_result = self._ai_test_placeholders(template_path, interactive)
            findings.extend(test_result.findings)
            issues.extend(test_result.issues)
            score = test_result.score

        return SectionResult(
            section_num=self.section_num,
            section_title=self.title,
            score=score,
            findings=findings,
            issues=issues,
            completed_at=datetime.now(),
            metadata={"ai_assisted": self.ai_service is not None}
        )

    def _ai_test_placeholders(
        self,
        template_path: Path,
        interactive: bool
    ) -> Dict[str, Any]:
        """Use AI to simulate placeholder replacement testing.

        Args:
            template_path: Path to template directory
            interactive: Whether to allow interactive review

        Returns:
            Dictionary with findings, issues, and score
        """
        prompt = """
Simulate placeholder replacement testing for this template package.

**Test Scenarios**:
1. Replace {{ProjectName}} with "MyShop"
2. Replace {{EntityName}} with "Product"
3. Replace {{EntityNamePlural}} with "Products"

**For each template file, verify**:
- Placeholder replacement completeness (all placeholders replaced)
- Naming consistency (PascalCase, camelCase, snake_case maintained)
- No broken references after replacement
- No semantic conflicts
- No placeholder collisions

**Output Format**:
```json
{
    "pass_rate": <0.0-1.0>,
    "issues_found": [
        {
            "severity": "critical|high|medium|low",
            "category": "placeholder|naming|references",
            "file": "filename",
            "description": "Issue description"
        }
    ],
    "findings": [
        {
            "title": "Finding title",
            "description": "Description",
            "is_positive": true/false
        }
    ]
}
```
"""

        context = {
            "template_path": str(template_path),
            "template_files": self._list_template_files(template_path)
        }

        schema = {
            "required_fields": ["pass_rate"],
            "field_types": {
                "pass_rate": (int, float),
                "issues_found": list,
                "findings": list
            }
        }

        fallback = {
            "pass_rate": 0.7,
            "issues_found": [],
            "findings": [
                {
                    "title": "Manual Testing Required",
                    "description": "AI testing unavailable",
                    "is_positive": False
                }
            ]
        }

        result: AIAnalysisResult = execute_ai_analysis(
            service=self.ai_service,
            prompt=prompt,
            context=context,
            schema=schema,
            fallback_value=fallback,
            timeout_seconds=180
        )

        # Parse results
        data = result.data
        pass_rate = float(data.get("pass_rate", 0.7))

        # Convert issues
        issues = []
        for issue_data in data.get("issues_found", []):
            severity_str = issue_data.get("severity", "medium")
            category_str = issue_data.get("category", "testing")

            issues.append(ValidationIssue(
                severity=IssueSeverity(severity_str),
                category=IssueCategory.TESTING,
                message=issue_data.get("description", ""),
                location=issue_data.get("file"),
                fixable=False
            ))

        # Convert findings
        findings = []
        for finding_data in data.get("findings", []):
            findings.append(Finding(
                title=finding_data.get("title", ""),
                description=finding_data.get("description", ""),
                is_positive=finding_data.get("is_positive", False),
                impact="See description",
                evidence=f"AI confidence: {result.confidence:.0%}"
            ))

        # Add summary finding
        findings.insert(0, Finding(
            title=f"Placeholder Testing: {pass_rate:.0%} Pass Rate",
            description=f"AI simulated placeholder replacement with {len(issues)} issues found",
            is_positive=pass_rate >= 0.8,
            impact="Indicates template robustness",
            evidence=f"AI confidence: {result.confidence:.0%}"
        ))

        # Calculate score based on pass rate
        score = pass_rate * 10  # 0.8 pass rate = 8.0 score
        score = max(min(score, 10.0), 0.0)

        return {
            "findings": findings,
            "issues": issues,
            "score": score
        }

    def _list_template_files(self, template_path: Path) -> List[str]:
        """List all template files.

        Args:
            template_path: Path to template directory

        Returns:
            List of relative file paths
        """
        files = []
        template_dirs = ["templates", "files"]
        for dir_name in template_dirs:
            dir_path = template_path / dir_name
            if dir_path.exists() and dir_path.is_dir():
                for file_path in dir_path.rglob("*"):
                    if file_path.is_file():
                        files.append(str(file_path.relative_to(dir_path)))
        return files
