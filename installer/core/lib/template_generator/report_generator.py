"""
Validation Report Generator

Generates markdown validation reports for extended template validation.

TASK-043: Implement Extended Validation Flag (Phase 1)
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from .extended_validator import ExtendedValidationReport, SpotCheckResult


class ValidationReportGenerator:
    """Generate markdown validation reports"""

    def generate_report(
        self,
        report: ExtendedValidationReport,
        template_name: str,
        output_path: Path
    ) -> Path:
        """
        Generate validation report as markdown.

        The report is generated in the template directory, regardless of
        whether the template was created in ~/.agentecflow/templates/
        (personal use) or installer/core/templates/ (repo distribution).

        Args:
            report: ExtendedValidationReport with findings
            template_name: Name of the template
            output_path: Directory to save the report

        Returns:
            Path to generated report
        """
        content = self._build_report_content(report, template_name)
        report_path = output_path / "validation-report.md"
        report_path.write_text(content, encoding='utf-8')

        return report_path

    def _build_report_content(
        self,
        report: ExtendedValidationReport,
        template_name: str
    ) -> str:
        """
        Build markdown report content.

        Args:
            report: ExtendedValidationReport
            template_name: Template name

        Returns:
            Markdown content
        """
        return f"""# Template Validation Report

**Template**: {template_name}
**Generated**: {report.validation_timestamp}
**Overall Score**: {report.overall_score:.1f}/10 ({report.get_grade()})
**Duration**: {report.duration}

## Executive Summary

{self._generate_summary(report)}

## Quality Scores

| Category | Score | Status |
|----------|-------|--------|
| CRUD Completeness (Phase 5.5) | {report.completeness_score:.1f}/10 | {self._status_icon(report.completeness_score)} |
| Placeholder Consistency | {report.placeholder_consistency_score:.1f}/10 | {self._status_icon(report.placeholder_consistency_score)} |
| Pattern Fidelity | {report.pattern_fidelity_score:.1f}/10 | {self._status_icon(report.pattern_fidelity_score)} |
| Documentation Quality | {report.documentation_score:.1f}/10 | {self._status_icon(report.documentation_score)} |
| Agent Validation | {report.agent_validation_score:.1f}/10 | {self._status_icon(report.agent_validation_score)} |
| Manifest Accuracy | {report.manifest_accuracy_score:.1f}/10 | {self._status_icon(report.manifest_accuracy_score)} |
| **Overall** | **{report.overall_score:.1f}/10** | **{self._status_icon(report.overall_score)}** |

### Score Weights

The overall score is calculated using the following weights:
- **CRUD Completeness**: 50% (from Phase 5.5 validation)
- **Placeholder Consistency**: 10%
- **Pattern Fidelity**: 10%
- **Documentation Quality**: 10%
- **Agent Validation**: 10%
- **Manifest Accuracy**: 10%

## Detailed Findings

{self._generate_detailed_findings(report)}

## Pattern Fidelity Spot-Checks

{self._generate_spot_check_section(report)}

## Recommendations

{self._generate_recommendations(report)}

## Production Readiness

**Status**: {self._production_readiness_status(report)}

**Threshold**: ≥8.0/10 for production deployment

{self._generate_blocking_issues(report)}

## Exit Code

**Exit Code**: {report.get_exit_code()}

- `0` = Score ≥8.0 (Production ready)
- `1` = Score 6.0-7.9 (Needs improvement)
- `2` = Score <6.0 (Not ready)

---

**Report Generated**: {report.validation_timestamp}
**Validation Duration**: {report.duration}
"""

    def _generate_summary(self, report: ExtendedValidationReport) -> str:
        """
        Generate executive summary.

        Args:
            report: ExtendedValidationReport

        Returns:
            Summary text
        """
        if report.is_production_ready():
            return f"""✅ **This template is production-ready** with an overall score of {report.overall_score:.1f}/10 (Grade: {report.get_grade()}).

The template has passed all quality gates and meets the standards for team distribution and production use."""
        elif report.overall_score >= 6.0:
            return f"""⚠️ **This template needs improvement** with an overall score of {report.overall_score:.1f}/10 (Grade: {report.get_grade()}).

While the template is functional, addressing the recommendations below will improve quality and maintainability."""
        else:
            return f"""❌ **This template is not ready for production** with an overall score of {report.overall_score:.1f}/10 (Grade: {report.get_grade()}).

Significant improvements are required before this template can be used reliably. Please address critical issues below."""

    def _generate_detailed_findings(self, report: ExtendedValidationReport) -> str:
        """
        Generate detailed findings section.

        Args:
            report: ExtendedValidationReport

        Returns:
            Findings markdown
        """
        if not report.issues:
            return """✅ **No critical issues found**

All validation checks passed successfully."""

        findings = ["### Issues Found\n"]

        for i, issue in enumerate(report.issues, 1):
            findings.append(f"{i}. {issue}")

        return "\n".join(findings)

    def _generate_spot_check_section(self, report: ExtendedValidationReport) -> str:
        """
        Generate spot-check results section.

        Args:
            report: ExtendedValidationReport

        Returns:
            Spot-check markdown
        """
        if not report.spot_check_results:
            return "No spot-checks performed (no templates to validate)."

        sections = [
            f"**Total Spot-Checks**: {len(report.spot_check_results)}",
            f"**Average Score**: {sum(sc.score for sc in report.spot_check_results) / len(report.spot_check_results):.1f}/10\n"
        ]

        for i, spot_check in enumerate(report.spot_check_results, 1):
            status = "✅ Passed" if spot_check.passed else "⚠️ Issues Found"
            sections.append(f"### Spot-Check {i}: {spot_check.template_path}")
            sections.append(f"**Status**: {status}")
            sections.append(f"**Score**: {spot_check.score:.1f}/10")
            sections.append(f"**Checks Performed**: {', '.join(spot_check.checks_performed)}")

            if spot_check.issues_found:
                sections.append("\n**Issues**:")
                for issue in spot_check.issues_found:
                    sections.append(f"- {issue}")

            sections.append("")  # Blank line

        return "\n".join(sections)

    def _generate_recommendations(self, report: ExtendedValidationReport) -> str:
        """
        Generate recommendations section.

        Args:
            report: ExtendedValidationReport

        Returns:
            Recommendations markdown
        """
        if not report.recommendations:
            return "No recommendations - template quality is excellent!"

        recs = []
        for i, recommendation in enumerate(report.recommendations, 1):
            recs.append(f"{i}. {recommendation}")

        return "\n".join(recs)

    def _production_readiness_status(self, report: ExtendedValidationReport) -> str:
        """
        Generate production readiness status.

        Args:
            report: ExtendedValidationReport

        Returns:
            Status string with emoji
        """
        if report.is_production_ready():
            return "✅ **Production Ready**"
        elif report.overall_score >= 6.0:
            return "⚠️ **Needs Improvement**"
        else:
            return "❌ **Not Ready**"

    def _generate_blocking_issues(self, report: ExtendedValidationReport) -> str:
        """
        Generate blocking issues section.

        Args:
            report: ExtendedValidationReport

        Returns:
            Blocking issues markdown
        """
        if report.is_production_ready():
            return ""

        blocking = []

        if report.completeness_score < 8.0:
            blocking.append("- CRUD completeness below threshold")

        if report.placeholder_consistency_score < 8.0:
            blocking.append("- Placeholder naming inconsistencies")

        if report.pattern_fidelity_score < 8.0:
            blocking.append("- Pattern fidelity issues detected")

        if report.documentation_score < 8.0:
            blocking.append("- Documentation incomplete")

        if report.agent_validation_score < 8.0:
            blocking.append("- Agent validation failures")

        if report.manifest_accuracy_score < 8.0:
            blocking.append("- Manifest accuracy issues")

        if not blocking:
            return ""

        return "\n### Blocking Issues\n\n" + "\n".join(blocking)

    def _status_icon(self, score: float) -> str:
        """
        Get status icon for score.

        Args:
            score: Score value

        Returns:
            Status emoji
        """
        if score >= 8.0:
            return "✅"
        elif score >= 6.0:
            return "⚠️"
        else:
            return "❌"
