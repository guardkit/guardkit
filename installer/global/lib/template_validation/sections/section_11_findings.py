"""
Section 11: Detailed Findings

Summarizes strengths, weaknesses, and critical issues using AI-assisted synthesis.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import json

from ..models import SectionResult, Finding
from ..ai_service import AIAnalysisService
from ..ai_analysis_helpers import (
    execute_ai_analysis,
    create_fallback_finding,
    AIAnalysisResult
)


class DetailedFindingsSection:
    """Section 11: Detailed Findings (AI-Enhanced)"""

    def __init__(
        self,
        ai_service: Optional[AIAnalysisService] = None,
        previous_results: Optional[List[SectionResult]] = None
    ):
        """Initialize section with optional AI service and previous results.

        Args:
            ai_service: AI analysis service for findings synthesis.
                       If None, section provides basic summary.
            previous_results: Results from sections 1-10 for aggregation.
        """
        self.ai_service = ai_service
        self.previous_results = previous_results or []

    @property
    def section_num(self) -> int:
        return 11

    @property
    def title(self) -> str:
        return "Detailed Findings"

    @property
    def description(self) -> str:
        return "Summarize strengths, weaknesses, and critical issues"

    def execute(self, template_path: Path, interactive: bool = True) -> SectionResult:
        """Execute section with AI assistance if available.

        Args:
            template_path: Path to template directory
            interactive: Whether to allow interactive review

        Returns:
            SectionResult with synthesized findings and score
        """
        findings: List[Finding] = []
        score = 8.0  # Default score

        if not self.previous_results:
            # No previous results to analyze
            findings.append(Finding(
                title="No Previous Results",
                description="Cannot synthesize findings without results from sections 1-10",
                is_positive=False,
                impact="Detailed findings analysis not available"
            ))
            score = 7.0

        elif not self.ai_service:
            # AI service not available, basic summary only
            basic_summary = self._create_basic_summary()
            findings.append(Finding(
                title="Basic Findings Summary",
                description=basic_summary,
                is_positive=True,
                impact="Provides high-level overview",
                evidence=f"Based on {len(self.previous_results)} previous sections"
            ))

        else:
            # AI service available - perform AI-assisted synthesis
            synthesis_result = self._ai_synthesize_findings(template_path, interactive)
            findings.extend(synthesis_result.findings)
            score = synthesis_result.score

        return SectionResult(
            section_num=self.section_num,
            section_title=self.title,
            score=score,
            findings=findings,
            completed_at=datetime.now(),
            metadata={
                "previous_sections_count": len(self.previous_results),
                "ai_assisted": self.ai_service is not None
            }
        )

    def _create_basic_summary(self) -> str:
        """Create basic findings summary without AI.

        Returns:
            Summary string
        """
        total_sections = len(self.previous_results)
        avg_score = sum(r.score for r in self.previous_results if r.score is not None) / max(total_sections, 1)

        sections_with_issues = sum(1 for r in self.previous_results if r.has_issues())
        sections_with_critical = sum(1 for r in self.previous_results if r.has_critical_issues())

        return (
            f"Analyzed {total_sections} sections. "
            f"Average score: {avg_score:.1f}/10. "
            f"Sections with issues: {sections_with_issues}. "
            f"Sections with critical issues: {sections_with_critical}."
        )

    def _ai_synthesize_findings(
        self,
        template_path: Path,
        interactive: bool
    ) -> Dict[str, Any]:
        """Use AI to synthesize strengths, weaknesses, and critical issues.

        Args:
            template_path: Path to template directory
            interactive: Whether to allow interactive review

        Returns:
            Dictionary with findings and score
        """
        # Aggregate all findings from previous sections
        aggregated_data = self._aggregate_previous_sections()

        # Build prompts for different analyses
        strengths_prompt = self._build_strengths_prompt(aggregated_data)
        weaknesses_prompt = self._build_weaknesses_prompt(aggregated_data)
        critical_prompt = self._build_critical_issues_prompt(aggregated_data)

        # Execute AI analyses
        strengths = self._ai_identify_strengths(strengths_prompt, aggregated_data)
        weaknesses = self._ai_identify_weaknesses(weaknesses_prompt, aggregated_data)
        critical_issues = self._ai_identify_critical_issues(critical_prompt, aggregated_data)

        # Parse results into findings
        findings = []
        findings.extend(self._parse_strengths(strengths))
        findings.extend(self._parse_weaknesses(weaknesses))
        findings.extend(self._parse_critical_issues(critical_issues))

        # Calculate score based on strengths vs weaknesses/critical
        strength_count = len(strengths.data.get("strengths", [])) if strengths.success else 0
        weakness_count = len(weaknesses.data.get("weaknesses", [])) if weaknesses.success else 0
        critical_count = len(critical_issues.data.get("critical_issues", [])) if critical_issues.success else 0

        # Scoring: Start at 8, add for strengths, subtract for weaknesses/critical
        score = 8.0
        score += min(strength_count * 0.3, 2.0)  # Max +2 for strengths
        score -= min(weakness_count * 0.3, 2.0)  # Max -2 for weaknesses
        score -= min(critical_count * 1.0, 3.0)  # Max -3 for critical issues

        score = max(min(score, 10.0), 0.0)  # Clamp to 0-10

        return {
            "findings": findings,
            "score": score
        }

    def _aggregate_previous_sections(self) -> Dict[str, Any]:
        """Aggregate findings from all previous sections.

        Returns:
            Dictionary with aggregated data
        """
        aggregated = {
            "sections": [],
            "total_sections": len(self.previous_results),
            "average_score": 0.0,
            "all_findings": [],
            "all_issues": [],
            "sections_with_issues": 0,
            "sections_with_critical": 0
        }

        scores = []
        for result in self.previous_results:
            section_data = {
                "num": result.section_num,
                "title": result.section_title,
                "score": result.score,
                "findings_count": len(result.findings),
                "issues_count": len(result.issues)
            }
            aggregated["sections"].append(section_data)

            if result.score is not None:
                scores.append(result.score)

            aggregated["all_findings"].extend([
                {
                    "section": result.section_num,
                    "title": f.title,
                    "description": f.description,
                    "is_positive": f.is_positive,
                    "impact": f.impact
                }
                for f in result.findings
            ])

            aggregated["all_issues"].extend([
                {
                    "section": result.section_num,
                    "severity": i.severity.value,
                    "message": i.message
                }
                for i in result.issues
            ])

            if result.has_issues():
                aggregated["sections_with_issues"] += 1

            if result.has_critical_issues():
                aggregated["sections_with_critical"] += 1

        aggregated["average_score"] = sum(scores) / len(scores) if scores else 0.0

        return aggregated

    def _build_strengths_prompt(self, aggregated_data: Dict[str, Any]) -> str:
        """Build prompt for identifying strengths.

        Args:
            aggregated_data: Aggregated data from previous sections

        Returns:
            Prompt string
        """
        return f"""
Based on the audit findings from Sections 1-10, identify the top 5 strengths of this template.

**Audit Summary**:
- Total Sections: {aggregated_data['total_sections']}
- Average Score: {aggregated_data['average_score']:.1f}/10
- Positive Findings: {sum(1 for f in aggregated_data['all_findings'] if f.get('is_positive'))}

**Detailed Findings**:
```json
{json.dumps(aggregated_data['all_findings'][:20], indent=2)}
```

**Your Task**:
1. Identify the top 5 strengths based on high scores (≥8/10) and positive findings
2. For each strength, provide:
   - Title (concise)
   - Description (what makes it a strength)
   - Evidence (specific scores or findings)
   - Impact (value provided)

**Output Format**:
```json
{{
    "strengths": [
        {{
            "title": "Strength title",
            "description": "Why this is a strength",
            "evidence": "Specific evidence from audit",
            "impact": "Value/benefit provided"
        }}
    ]
}}
```

Focus on exceptional scores, innovative patterns, and production-ready aspects.
"""

    def _build_weaknesses_prompt(self, aggregated_data: Dict[str, Any]) -> str:
        """Build prompt for identifying weaknesses.

        Args:
            aggregated_data: Aggregated data from previous sections

        Returns:
            Prompt string
        """
        return f"""
Based on the audit findings from Sections 1-10, identify the top 5 weaknesses of this template.

**Audit Summary**:
- Total Sections: {aggregated_data['total_sections']}
- Average Score: {aggregated_data['average_score']:.1f}/10
- Negative Findings: {sum(1 for f in aggregated_data['all_findings'] if not f.get('is_positive'))}
- Issues: {len(aggregated_data['all_issues'])}

**Detailed Findings**:
```json
{json.dumps(aggregated_data['all_findings'][:20], indent=2)}
```

**Your Task**:
1. Identify the top 5 weaknesses based on low scores (<7/10) and negative findings
2. For each weakness, provide:
   - Title (concise)
   - Description (what the issue is)
   - Evidence (specific scores or findings)
   - Impact (consequences if not fixed)
   - Recommendation (how to fix)
   - Effort (low/medium/high to fix)

**Output Format**:
```json
{{
    "weaknesses": [
        {{
            "title": "Weakness title",
            "description": "What the issue is",
            "evidence": "Specific evidence from audit",
            "impact": "Consequences if not fixed",
            "recommendation": "How to fix it",
            "effort": "low|medium|high"
        }}
    ]
}}
```

Focus on missing functionality, quality issues, usability problems.
"""

    def _build_critical_issues_prompt(self, aggregated_data: Dict[str, Any]) -> str:
        """Build prompt for identifying critical issues.

        Args:
            aggregated_data: Aggregated data from previous sections

        Returns:
            Prompt string
        """
        return f"""
Based on the audit findings, identify any CRITICAL issues that would block production deployment.

**Audit Summary**:
- Sections with Critical Issues: {aggregated_data['sections_with_critical']}
- Critical Issues Found: {sum(1 for i in aggregated_data['all_issues'] if i.get('severity') == 'critical')}
- Sections with Score <6: {sum(1 for s in aggregated_data['sections'] if s.get('score', 10) < 6)}

**All Issues**:
```json
{json.dumps(aggregated_data['all_issues'], indent=2)}
```

**Your Task**:
Identify CRITICAL issues that are:
- Scores <6/10 in any section
- Missing core functionality
- Security vulnerabilities
- Data loss risks
- Broken compilation
- Major architectural flaws

For each critical issue, provide:
- Title (concise)
- Description (detailed issue description)
- Severity (critical or high)
- Impact (what happens if deployed)
- Fix_priority (1-5, where 1 is highest)
- Recommended_fix (how to resolve)

**Output Format**:
```json
{{
    "critical_issues": [
        {{
            "title": "Issue title",
            "description": "Detailed issue description",
            "severity": "critical",
            "impact": "Impact if deployed",
            "fix_priority": 1,
            "recommended_fix": "How to resolve"
        }}
    ]
}}
```

Only return TRUE critical/blocking issues. Don't include minor issues.
"""

    def _ai_identify_strengths(
        self,
        prompt: str,
        context: Dict[str, Any]
    ) -> AIAnalysisResult:
        """Use AI to identify top strengths.

        Args:
            prompt: Analysis prompt
            context: Aggregated data context

        Returns:
            AIAnalysisResult with strengths
        """
        schema = {
            "required_fields": ["strengths"],
            "field_types": {"strengths": list},
            "list_item_types": {"strengths": dict}
        }

        fallback = {"strengths": []}

        return execute_ai_analysis(
            service=self.ai_service,
            prompt=prompt,
            context=context,
            schema=schema,
            fallback_value=fallback,
            timeout_seconds=180
        )

    def _ai_identify_weaknesses(
        self,
        prompt: str,
        context: Dict[str, Any]
    ) -> AIAnalysisResult:
        """Use AI to identify top weaknesses.

        Args:
            prompt: Analysis prompt
            context: Aggregated data context

        Returns:
            AIAnalysisResult with weaknesses
        """
        schema = {
            "required_fields": ["weaknesses"],
            "field_types": {"weaknesses": list},
            "list_item_types": {"weaknesses": dict}
        }

        fallback = {"weaknesses": []}

        return execute_ai_analysis(
            service=self.ai_service,
            prompt=prompt,
            context=context,
            schema=schema,
            fallback_value=fallback,
            timeout_seconds=180
        )

    def _ai_identify_critical_issues(
        self,
        prompt: str,
        context: Dict[str, Any]
    ) -> AIAnalysisResult:
        """Use AI to identify critical issues.

        Args:
            prompt: Analysis prompt
            context: Aggregated data context

        Returns:
            AIAnalysisResult with critical issues
        """
        schema = {
            "required_fields": ["critical_issues"],
            "field_types": {"critical_issues": list},
            "list_item_types": {"critical_issues": dict}
        }

        fallback = {"critical_issues": []}

        return execute_ai_analysis(
            service=self.ai_service,
            prompt=prompt,
            context=context,
            schema=schema,
            fallback_value=fallback,
            timeout_seconds=180
        )

    def _parse_strengths(self, result: AIAnalysisResult) -> List[Finding]:
        """Parse AI strengths into Finding objects.

        Args:
            result: AI analysis result

        Returns:
            List of Finding objects
        """
        if not result.success or not result.data:
            return []

        findings = []
        strengths = result.data.get("strengths", [])

        if strengths:
            findings.append(Finding(
                title=f"Top Strengths Identified: {len(strengths)}",
                description="AI identified the following strengths",
                is_positive=True,
                impact=f"Template has {len(strengths)} major strengths",
                evidence=f"AI confidence: {result.confidence:.0%}"
            ))

            for i, strength in enumerate(strengths[:5], 1):
                findings.append(Finding(
                    title=f"Strength #{i}: {strength.get('title', 'Untitled')}",
                    description=strength.get('description', ''),
                    is_positive=True,
                    impact=strength.get('impact', ''),
                    evidence=strength.get('evidence', '')
                ))

        return findings

    def _parse_weaknesses(self, result: AIAnalysisResult) -> List[Finding]:
        """Parse AI weaknesses into Finding objects.

        Args:
            result: AI analysis result

        Returns:
            List of Finding objects
        """
        if not result.success or not result.data:
            return []

        findings = []
        weaknesses = result.data.get("weaknesses", [])

        if weaknesses:
            findings.append(Finding(
                title=f"Top Weaknesses Identified: {len(weaknesses)}",
                description="AI identified the following weaknesses",
                is_positive=False,
                impact=f"Template has {len(weaknesses)} areas for improvement",
                evidence=f"AI confidence: {result.confidence:.0%}"
            ))

            for i, weakness in enumerate(weaknesses[:5], 1):
                findings.append(Finding(
                    title=f"Weakness #{i}: {weakness.get('title', 'Untitled')}",
                    description=(
                        f"{weakness.get('description', '')}\n"
                        f"Recommendation: {weakness.get('recommendation', 'N/A')}\n"
                        f"Effort: {weakness.get('effort', 'unknown')}"
                    ),
                    is_positive=False,
                    impact=weakness.get('impact', ''),
                    evidence=weakness.get('evidence', '')
                ))

        return findings

    def _parse_critical_issues(self, result: AIAnalysisResult) -> List[Finding]:
        """Parse AI critical issues into Finding objects.

        Args:
            result: AI analysis result

        Returns:
            List of Finding objects
        """
        if not result.success or not result.data:
            return []

        findings = []
        critical_issues = result.data.get("critical_issues", [])

        if critical_issues:
            findings.append(Finding(
                title=f"CRITICAL ISSUES DETECTED: {len(critical_issues)}",
                description="AI identified production-blocking issues",
                is_positive=False,
                impact="Template NOT ready for production",
                evidence=f"AI confidence: {result.confidence:.0%}"
            ))

            for i, issue in enumerate(critical_issues, 1):
                findings.append(Finding(
                    title=f"Critical #{i}: {issue.get('title', 'Untitled')}",
                    description=(
                        f"{issue.get('description', '')}\n"
                        f"Severity: {issue.get('severity', 'unknown')}\n"
                        f"Fix: {issue.get('recommended_fix', 'N/A')}"
                    ),
                    is_positive=False,
                    impact=issue.get('impact', ''),
                    evidence=f"Priority: {issue.get('fix_priority', 'unknown')}"
                ))
        else:
            findings.append(Finding(
                title="No Critical Issues",
                description="AI found no production-blocking issues",
                is_positive=True,
                impact="Template appears production-ready",
                evidence=f"AI confidence: {result.confidence:.0%}"
            ))

        return findings
