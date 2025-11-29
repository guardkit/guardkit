"""
Section 8: Comparison with Source

Validates pattern coverage and false positives/negatives using AI-assisted analysis.
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


class ComparisonWithSourceSection:
    """Section 8: Comparison with Source (AI-Enhanced)"""

    def __init__(self, ai_service: Optional[AIAnalysisService] = None):
        """Initialize section with optional AI service.

        Args:
            ai_service: AI analysis service for pattern comparison.
                       If None, section falls back to manual mode.
        """
        self.ai_service = ai_service

    @property
    def section_num(self) -> int:
        return 8

    @property
    def title(self) -> str:
        return "Comparison with Source"

    @property
    def description(self) -> str:
        return "Validate pattern coverage and false positives/negatives"

    def execute(self, template_path: Path, interactive: bool = True) -> SectionResult:
        """Execute section with AI assistance if available.

        Args:
            template_path: Path to template directory
            interactive: Whether to allow interactive review

        Returns:
            SectionResult with findings and score
        """
        findings: List[Finding] = []
        score = 7.0  # Default neutral score

        # Try to get source repository info
        source_repo = self._get_source_repo(template_path)

        if not source_repo:
            # No source repository specified in manifest
            findings.append(Finding(
                title="No Source Repository",
                description="Template manifest does not specify source repository",
                is_positive=False,
                impact="Cannot verify pattern fidelity against source",
                evidence="source_repository not found in manifest.json"
            ))
            score = 6.0

        elif not self.ai_service:
            # AI service not available, manual comparison required
            findings.append(Finding(
                title="Manual Comparison Required",
                description=f"Compare template patterns with source manually: {source_repo}",
                is_positive=False,
                impact="Ensures pattern fidelity",
                evidence=f"Source: {source_repo}"
            ))
            score = 7.0

        else:
            # AI service available - perform AI-assisted comparison
            comparison_result = self._ai_compare_to_source(
                template_path,
                source_repo,
                interactive
            )

            findings.extend(comparison_result.findings)
            score = comparison_result.score

        return SectionResult(
            section_num=self.section_num,
            section_title=self.title,
            score=score,
            findings=findings,
            completed_at=datetime.now(),
            metadata={
                "source_repository": source_repo,
                "ai_assisted": self.ai_service is not None
            }
        )

    def _get_source_repo(self, template_path: Path) -> Optional[str]:
        """Extract source repository from template manifest.

        Args:
            template_path: Path to template directory

        Returns:
            Source repository URL or None if not specified
        """
        manifest_path = template_path / "manifest.json"

        if not manifest_path.exists():
            return None

        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
                return manifest.get("source_repository") or manifest.get("source_repo")
        except Exception:
            return None

    def _ai_compare_to_source(
        self,
        template_path: Path,
        source_repo: str,
        interactive: bool
    ) -> Dict[str, Any]:
        """Use AI to compare template patterns to source repository.

        Args:
            template_path: Path to template directory
            source_repo: Source repository URL
            interactive: Whether to allow interactive review

        Returns:
            Dictionary with findings and score
        """
        prompt = self._build_comparison_prompt(source_repo)

        context = {
            "template_path": str(template_path),
            "source_repository": source_repo,
            "template_files": self._list_template_files(template_path)
        }

        schema = {
            "required_fields": ["coverage_score", "false_positives", "false_negatives", "fidelity_score"],
            "field_types": {
                "coverage_score": (int, float),
                "false_positives": list,
                "false_negatives": list,
                "fidelity_score": (int, float),
                "detailed_findings": list
            }
        }

        # Execute AI analysis with fallback
        fallback = self._create_fallback_comparison(source_repo)

        result: AIAnalysisResult = execute_ai_analysis(
            service=self.ai_service,
            prompt=prompt,
            context=context,
            schema=schema,
            fallback_value=fallback,
            timeout_seconds=300
        )

        if result.fallback_used:
            # AI failed, return manual comparison required
            return {
                "findings": [
                    Finding(
                        title="AI Analysis Failed - Manual Comparison Required",
                        description=f"AI comparison failed: {result.error}",
                        is_positive=False,
                        impact="Manual comparison required",
                        evidence=f"Source: {source_repo}"
                    )
                ],
                "score": 7.0
            }

        # Parse AI results into findings
        data = result.data
        findings = self._parse_comparison_findings(data, source_repo, result.confidence)

        # Calculate score based on coverage and fidelity
        coverage = float(data.get("coverage_score", 7.0))
        fidelity = float(data.get("fidelity_score", 7.0))
        score = (coverage * 0.6 + fidelity * 0.4)  # Weighted average

        # Penalize for false positives/negatives
        false_pos_count = len(data.get("false_positives", []))
        false_neg_count = len(data.get("false_negatives", []))

        if false_pos_count > 0:
            score -= min(false_pos_count * 0.5, 2.0)

        if false_neg_count > 0:
            score -= min(false_neg_count * 0.5, 2.0)

        score = max(min(score, 10.0), 0.0)  # Clamp to 0-10

        return {
            "findings": findings,
            "score": score
        }

    def _build_comparison_prompt(self, source_repo: str) -> str:
        """Build prompt for AI comparison analysis.

        Args:
            source_repo: Source repository URL

        Returns:
            Prompt string for AI
        """
        return f"""
Analyze this template package and compare it against its source repository to assess pattern coverage and fidelity.

**Source Repository**: {source_repo}

**Analysis Tasks**:

1. **Pattern Coverage Assessment**: Identify major patterns/components in the source repository and verify they are represented in the template.

2. **False Positive Detection**: Identify any template files that represent patterns NOT present in the source repository.

3. **False Negative Detection**: Identify any source patterns that are MISSING from the templates.

4. **Fidelity Assessment**: For templates that DO correspond to source patterns, assess how accurately they represent the source implementation.

**Required Output Format**:
```json
{{
    "coverage_score": <0-10>,  // How well templates cover source patterns
    "fidelity_score": <0-10>,  // How accurately templates represent source
    "false_positives": [
        {{
            "template": "filename.ext",
            "reason": "Why this template has no source equivalent"
        }}
    ],
    "false_negatives": [
        {{
            "pattern": "Pattern name",
            "reason": "Why this source pattern is missing from templates"
        }}
    ],
    "detailed_findings": [
        {{
            "title": "Finding title",
            "description": "Detailed description",
            "is_positive": true/false,
            "evidence": "Supporting evidence"
        }}
    ]
}}
```

**Scoring Guidelines**:
- Coverage: 10 = All major patterns covered, 0 = Most patterns missing
- Fidelity: 10 = Templates match source exactly, 0 = Significant deviations

Provide a thorough analysis with specific examples.
"""

    def _list_template_files(self, template_path: Path) -> List[str]:
        """List all template files in the template directory.

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
                        rel_path = file_path.relative_to(dir_path)
                        files.append(str(rel_path))

        return files

    def _create_fallback_comparison(self, source_repo: str) -> Dict[str, Any]:
        """Create fallback comparison result when AI is unavailable.

        Args:
            source_repo: Source repository URL

        Returns:
            Fallback comparison data
        """
        return {
            "coverage_score": 7.0,
            "fidelity_score": 7.0,
            "false_positives": [],
            "false_negatives": [],
            "detailed_findings": [
                {
                    "title": "Manual Comparison Required",
                    "description": f"AI comparison unavailable. Manual comparison with {source_repo} required.",
                    "is_positive": False,
                    "evidence": "AI service unavailable"
                }
            ]
        }

    def _parse_comparison_findings(
        self,
        data: Dict[str, Any],
        source_repo: str,
        confidence: float
    ) -> List[Finding]:
        """Parse AI comparison data into Finding objects.

        Args:
            data: AI comparison result data
            source_repo: Source repository URL
            confidence: AI confidence score

        Returns:
            List of Finding objects
        """
        findings: List[Finding] = []

        coverage = data.get("coverage_score", 7.0)
        fidelity = data.get("fidelity_score", 7.0)

        # Main coverage finding
        findings.append(Finding(
            title=f"Pattern Coverage: {coverage}/10",
            description=f"Template covers patterns from source repository (AI confidence: {confidence:.0%})",
            is_positive=coverage >= 7.0,
            impact="Indicates completeness of template package",
            evidence=f"Source: {source_repo}"
        ))

        # Fidelity finding
        findings.append(Finding(
            title=f"Pattern Fidelity: {fidelity}/10",
            description="Template patterns accurately represent source implementation",
            is_positive=fidelity >= 7.0,
            impact="Indicates quality of template patterns",
            evidence=f"AI confidence: {confidence:.0%}"
        ))

        # False positives
        false_positives = data.get("false_positives", [])
        if false_positives:
            fp_list = "\n".join([f"- {fp.get('template', 'unknown')}: {fp.get('reason', 'no reason')}"
                                for fp in false_positives])
            findings.append(Finding(
                title=f"False Positives Detected: {len(false_positives)}",
                description=f"Templates with no source equivalent:\n{fp_list}",
                is_positive=False,
                impact="May indicate over-engineering or incorrect patterns",
                evidence="AI-detected mismatches"
            ))

        # False negatives
        false_negatives = data.get("false_negatives", [])
        if false_negatives:
            fn_list = "\n".join([f"- {fn.get('pattern', 'unknown')}: {fn.get('reason', 'no reason')}"
                                for fn in false_negatives])
            findings.append(Finding(
                title=f"False Negatives Detected: {len(false_negatives)}",
                description=f"Source patterns missing from templates:\n{fn_list}",
                is_positive=False,
                impact="Indicates incomplete template coverage",
                evidence="AI-detected gaps"
            ))

        # Additional detailed findings from AI
        detailed_findings = data.get("detailed_findings", [])
        for df in detailed_findings[:5]:  # Limit to top 5 detailed findings
            if isinstance(df, dict):
                findings.append(Finding(
                    title=df.get("title", "AI Finding"),
                    description=df.get("description", ""),
                    is_positive=df.get("is_positive", False),
                    impact=df.get("impact", "See description"),
                    evidence=df.get("evidence", "AI analysis")
                ))

        return findings
