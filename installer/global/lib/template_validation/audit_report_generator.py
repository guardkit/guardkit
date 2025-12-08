"""
Audit Report Generator

Generates comprehensive audit reports in Markdown format.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .audit_session import AuditSession
from .models import AuditRecommendation, IssueSeverity, SectionResult
from .progressive_disclosure_validator import generate_split_validation_report


class AuditReportGenerator:
    """Generate comprehensive audit reports"""

    def generate_report(
        self,
        session: AuditSession,
        template_name: str,
        output_path: Path
    ) -> Path:
        """Generate full audit report"""
        content = self._build_comprehensive_report(session, template_name)

        # Ensure output directory exists
        output_path.mkdir(parents=True, exist_ok=True)

        report_path = output_path / "audit-report.md"
        report_path.write_text(content)

        return report_path

    def _build_comprehensive_report(
        self,
        session: AuditSession,
        template_name: str
    ) -> str:
        """Build comprehensive audit report content"""
        overall_score = self._calculate_overall_score(session)
        grade = self._calculate_grade(overall_score)
        recommendation = self._generate_recommendation(overall_score)

        return f"""# Template Comprehensive Audit Report

**Template**: {template_name}
**Audit Date**: {session.created_at.strftime("%Y-%m-%d")}
**Session ID**: {session.session_id}
**Sections Completed**: {len(session.sections_completed)}/16
**Overall Score**: {overall_score:.1f}/10
**Grade**: {grade}

## Executive Summary

{self._generate_executive_summary(session, overall_score)}

**Recommendation**: {recommendation.value.upper()}

## Section Scores

| Section | Title | Score | Status |
|---------|-------|-------|--------|
{self._generate_section_scores_table(session)}

## Detailed Section Results

{self._generate_detailed_sections(session)}

{self._generate_progressive_disclosure_metrics(session)}

## Overall Quality Assessment

### Strengths (Top 5)

{self._generate_strengths(session)}

### Weaknesses (Top 5)

{self._generate_weaknesses(session)}

### Critical Issues

{self._generate_critical_issues(session)}

## Production Readiness Decision

**Final Score**: {overall_score:.1f}/10
**Grade**: {grade}
**Recommendation**: {recommendation.value.upper()}

**Reasoning**:
{self._generate_recommendation_reasoning(overall_score, session)}

## Pre-Release Checklist

{self._generate_prerelease_checklist(session, overall_score)}

## Next Steps

{self._generate_next_steps(recommendation, session)}

---

**Audit Duration**: {self._calculate_duration(session)}
**Audit Session ID**: {session.session_id}
**Fixes Applied**: {len(session.fixes_applied)}
**Report Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

    def _calculate_overall_score(self, session: AuditSession) -> float:
        """Calculate overall score from section results"""
        if not session.section_results:
            return 0.0

        # Filter out optional sections (score = None)
        scores = [
            result.score
            for result in session.section_results.values()
            if result.score is not None
        ]

        if not scores:
            return 0.0

        return sum(scores) / len(scores)

    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from score"""
        if score >= 9.5:
            return "A+"
        elif score >= 9.0:
            return "A"
        elif score >= 8.5:
            return "A-"
        elif score >= 8.0:
            return "B+"
        elif score >= 7.0:
            return "B"
        elif score >= 6.0:
            return "C"
        elif score >= 5.0:
            return "D"
        else:
            return "F"

    def _generate_recommendation(self, score: float) -> AuditRecommendation:
        """Generate final recommendation based on score"""
        if score >= 8.0:
            return AuditRecommendation.APPROVE
        elif score >= 6.0:
            return AuditRecommendation.NEEDS_IMPROVEMENT
        else:
            return AuditRecommendation.REJECT

    def _generate_executive_summary(
        self,
        session: AuditSession,
        overall_score: float
    ) -> str:
        """Generate executive summary"""
        total_issues = sum(
            len(result.issues)
            for result in session.section_results.values()
        )

        critical_issues = sum(
            sum(1 for issue in result.issues if issue.severity == IssueSeverity.CRITICAL)
            for result in session.section_results.values()
        )

        return f"""This comprehensive audit evaluated {len(session.sections_completed)} sections of the template.
The template received an overall score of **{overall_score:.1f}/10** ({self._calculate_grade(overall_score)}).

**Key Metrics:**
- Total Issues Found: {total_issues}
- Critical Issues: {critical_issues}
- Sections Audited: {len(session.sections_completed)}/16
- Fixes Applied: {len(session.fixes_applied)}
"""

    def _generate_section_scores_table(self, session: AuditSession) -> str:
        """Generate section scores table"""
        rows = []
        for section_num in sorted(session.sections_completed):
            if section_num in session.section_results:
                result = session.section_results[section_num]
                score_str = f"{result.score:.1f}/10" if result.score is not None else "N/A"
                status = "✅ Pass" if result.score and result.score >= 7.0 else "⚠️ Review"
                if result.has_critical_issues():
                    status = "❌ Fail"
                rows.append(
                    f"| {section_num} | {result.section_title} | {score_str} | {status} |"
                )
        return "\n".join(rows)

    def _generate_detailed_sections(self, session: AuditSession) -> str:
        """Generate detailed section results"""
        sections = []
        for section_num in sorted(session.sections_completed):
            if section_num in session.section_results:
                result = session.section_results[section_num]
                sections.append(self._format_section_detail(result))
        return "\n\n".join(sections)

    def _format_section_detail(self, result: SectionResult) -> str:
        """Format a single section's detailed results"""
        score_str = f"{result.score:.1f}/10" if result.score is not None else "N/A (Optional)"

        content = f"""### Section {result.section_num}: {result.section_title}

**Score**: {score_str}

"""

        if result.findings:
            content += "**Findings:**\n\n"
            for finding in result.findings:
                icon = "✅" if finding.is_positive else "⚠️"
                content += f"- {icon} **{finding.title}**: {finding.description}\n"
            content += "\n"

        if result.issues:
            content += "**Issues:**\n\n"
            for issue in result.issues:
                severity_icon = {
                    IssueSeverity.CRITICAL: "🔴",
                    IssueSeverity.HIGH: "🟠",
                    IssueSeverity.MEDIUM: "🟡",
                    IssueSeverity.LOW: "🟢",
                    IssueSeverity.INFO: "ℹ️",
                }
                icon = severity_icon.get(issue.severity, "•")
                content += f"- {icon} **{issue.severity.value.upper()}**: {issue.message}\n"
            content += "\n"

        if result.recommendations:
            content += "**Recommendations:**\n\n"
            for rec in result.recommendations:
                content += f"- **{rec.title}**: {rec.description} (Effort: {rec.effort}, Priority: {rec.priority.value})\n"

        return content

    def _generate_strengths(self, session: AuditSession) -> str:
        """Generate top 5 strengths"""
        all_strengths = []
        for result in session.section_results.values():
            all_strengths.extend([
                f for f in result.findings if f.is_positive
            ])

        # Sort by impact and take top 5
        all_strengths.sort(key=lambda f: len(f.impact), reverse=True)
        top_strengths = all_strengths[:5]

        if not top_strengths:
            return "No significant strengths identified."

        return "\n".join([
            f"{i+1}. **{s.title}**: {s.description}"
            for i, s in enumerate(top_strengths)
        ])

    def _generate_weaknesses(self, session: AuditSession) -> str:
        """Generate top 5 weaknesses"""
        all_weaknesses = []
        for result in session.section_results.values():
            all_weaknesses.extend([
                f for f in result.findings if not f.is_positive
            ])

        # Sort by impact and take top 5
        all_weaknesses.sort(key=lambda f: len(f.impact), reverse=True)
        top_weaknesses = all_weaknesses[:5]

        if not top_weaknesses:
            return "No significant weaknesses identified."

        return "\n".join([
            f"{i+1}. **{w.title}**: {w.description}"
            for i, w in enumerate(top_weaknesses)
        ])

    def _generate_critical_issues(self, session: AuditSession) -> str:
        """Generate critical issues list"""
        critical_issues = []
        for result in session.section_results.values():
            critical_issues.extend([
                i for i in result.issues
                if i.severity == IssueSeverity.CRITICAL
            ])

        if not critical_issues:
            return "✅ No critical issues found."

        return "\n".join([
            f"- 🔴 **{issue.message}** (Section {session.sections_completed[0] if session.sections_completed else '?'})"
            for issue in critical_issues
        ])

    def _generate_recommendation_reasoning(
        self,
        overall_score: float,
        session: AuditSession
    ) -> str:
        """Generate reasoning for recommendation"""
        if overall_score >= 8.0:
            return """The template meets production quality standards with a score of 8.0 or higher.
All critical issues have been resolved, and the template provides comprehensive coverage."""
        elif overall_score >= 6.0:
            return """The template shows promise but requires improvements before production release.
Address the identified issues and re-audit to ensure quality standards are met."""
        else:
            return """The template does not meet minimum quality standards for production use.
Significant issues must be resolved before this template can be recommended."""

    def _generate_prerelease_checklist(
        self,
        session: AuditSession,
        overall_score: float
    ) -> str:
        """Generate pre-release checklist"""
        checklist = [
            f"{'✅' if overall_score >= 8.0 else '❌'} Overall score ≥ 8.0",
            f"{'✅' if not any(r.has_critical_issues() for r in session.section_results.values()) else '❌'} No critical issues",
            f"{'✅' if len(session.sections_completed) >= 12 else '❌'} At least 12 sections completed",
        ]
        return "\n".join(checklist)

    def _generate_next_steps(
        self,
        recommendation: AuditRecommendation,
        session: AuditSession
    ) -> str:
        """Generate next steps based on recommendation"""
        if recommendation == AuditRecommendation.APPROVE:
            return """1. Deploy template to production
2. Add to template library
3. Update documentation
4. Announce to users"""
        elif recommendation == AuditRecommendation.NEEDS_IMPROVEMENT:
            return """1. Address identified issues
2. Re-run validation
3. Update documentation
4. Re-audit before deployment"""
        else:
            return """1. Review critical issues
2. Consider template redesign
3. Address fundamental problems
4. Re-audit from scratch"""

    def _calculate_duration(self, session: AuditSession) -> str:
        """Calculate audit duration"""
        duration = session.updated_at - session.created_at
        hours = duration.total_seconds() / 3600
        if hours < 1:
            minutes = duration.total_seconds() / 60
            return f"{minutes:.0f} minutes"
        return f"{hours:.1f} hours"

    def _generate_progressive_disclosure_metrics(self, session: AuditSession) -> str:
        """Generate progressive disclosure metrics section"""
        # Extract split metrics from section 3 (Documentation) and section 5 (Agents)
        section_3 = session.section_results.get(3)
        section_5 = session.section_results.get(5)

        # If neither section was run, skip this section
        if not section_3 and not section_5:
            return ""

        content = ["## Progressive Disclosure Metrics", ""]

        # CLAUDE.md metrics (from section 3)
        if section_3 and section_3.metadata:
            claude_md_size = section_3.metadata.get('claude_md_size_kb')
            if claude_md_size is not None:
                status = "✅" if section_3.metadata.get('meets_target', False) else "⚠️"
                content.append("### CLAUDE.md")
                content.append(f"- Size: {claude_md_size:.1f}KB {status}")
                content.append("- Target: ≤10KB")

                has_split = section_3.metadata.get('has_split_structure', False)
                if has_split:
                    content.append("- Split Structure: ✅")
                    patterns_count = section_3.metadata.get('patterns_count', 0)
                    reference_count = section_3.metadata.get('reference_count', 0)
                    if patterns_count > 0:
                        content.append(f"  - Patterns: {patterns_count} files")
                    if reference_count > 0:
                        content.append(f"  - Reference: {reference_count} files")
                else:
                    content.append("- Split Structure: Single-file mode")

                content.append("")

        # Agent metrics (from section 5)
        if section_5 and section_5.metadata:
            split_agents = section_5.metadata.get('split_agents', [])
            total_agents = section_5.metadata.get('total_agents', 0)
            split_count = section_5.metadata.get('split_count', 0)

            if total_agents > 0:
                content.append("### Agents")
                content.append(f"- Total Agents: {total_agents}")
                content.append(f"- Using Split Structure: {split_count}/{total_agents}")

                if split_agents:
                    content.append("")
                    content.append("**Split Agents:**")
                    for agent in split_agents:
                        name = agent.get('name', 'Unknown')
                        core_size = agent.get('core_size_kb', 0)
                        reduction = agent.get('reduction_percent', 0)
                        meets_target = agent.get('meets_target', False)
                        has_loading = agent.get('has_loading_instruction', False)

                        status = "✅" if meets_target and has_loading and reduction >= 40 else "⚠️"
                        content.append(f"- {name}: {core_size:.1f}KB core, {reduction:.0f}% reduction {status}")

                    # Show non-split agents if any
                    non_split_count = total_agents - split_count
                    if non_split_count > 0:
                        content.append("")
                        content.append(f"**Non-Split Agents:** {non_split_count} agent(s) using single-file mode")

                content.append("")

        # If no metrics were added, return empty string
        if len(content) <= 2:  # Only header and empty line
            return ""

        return "\n".join(content)
