"""
Validation Report Generator

Generates markdown validation reports for agent formatting results.
"""

from pathlib import Path
from typing import Optional

from .validator import ValidationResult
from .metrics import QualityMetrics


class ValidationReporter:
    """Generates validation reports for formatting results."""

    STATUS_ICONS = {
        'PASS': '✅',
        'WARN': '⚠️',
        'FAIL': '❌',
    }

    def generate_report(
        self, validation: ValidationResult, agent_path: Path, dry_run: bool = False
    ) -> str:
        """
        Generate markdown validation report.

        Args:
            validation: Validation result
            agent_path: Path to agent file
            dry_run: Whether this was a dry run

        Returns:
            Markdown formatted report
        """
        before_status = validation.metrics_before.get_status()
        after_status = validation.metrics_after.get_status()

        before_icon = self.STATUS_ICONS[before_status]
        after_icon = self.STATUS_ICONS[after_status]

        # Build report
        report_lines = [
            '# Agent Formatting Report',
            '',
            f'**Agent**: {agent_path.name}',
            f'**Status**: {before_icon} {before_status} → {after_icon} {after_status}',
        ]

        if dry_run:
            report_lines.append('**Mode**: DRY RUN (no changes applied)')

        report_lines.extend(['', '## Quality Metrics', ''])

        # Metrics table
        report_lines.append(
            '| Metric | Before | After | Status |'
        )
        report_lines.append(
            '|--------|--------|-------|--------|'
        )

        # Time to first example
        before_ttfe = validation.metrics_before.time_to_first_example
        after_ttfe = validation.metrics_after.time_to_first_example
        ttfe_status = self.STATUS_ICONS['PASS'] if after_ttfe < 50 and after_ttfe != -1 else self.STATUS_ICONS['FAIL']
        before_ttfe_str = f'{before_ttfe} lines' if before_ttfe != -1 else 'Not found'
        after_ttfe_str = f'{after_ttfe} lines' if after_ttfe != -1 else 'Not found'
        report_lines.append(
            f'| Time to First Example | {before_ttfe_str} | {after_ttfe_str} | {ttfe_status} |'
        )

        # Example density
        before_density = validation.metrics_before.example_density
        after_density = validation.metrics_after.example_density
        density_status = (
            self.STATUS_ICONS['PASS'] if after_density >= 40
            else self.STATUS_ICONS['WARN'] if after_density >= 30
            else self.STATUS_ICONS['FAIL']
        )
        report_lines.append(
            f'| Example Density | {before_density:.1f}% | {after_density:.1f}% | {density_status} |'
        )

        # Boundary sections
        before_boundary = sum(validation.metrics_before.boundary_sections.values())
        after_boundary = sum(validation.metrics_after.boundary_sections.values())
        boundary_status = self.STATUS_ICONS['PASS'] if after_boundary == 3 else self.STATUS_ICONS['FAIL']
        report_lines.append(
            f'| Boundary Sections | {before_boundary}/3 | {after_boundary}/3 | {boundary_status} |'
        )

        # Commands first
        before_cmd = validation.metrics_before.commands_first
        after_cmd = validation.metrics_after.commands_first
        cmd_status = self.STATUS_ICONS['PASS'] if after_cmd < 50 and after_cmd != -1 else self.STATUS_ICONS['FAIL']
        before_cmd_str = f'{before_cmd} lines' if before_cmd != -1 else 'Not found'
        after_cmd_str = f'{after_cmd} lines' if after_cmd != -1 else 'Not found'
        report_lines.append(
            f'| Commands First | {before_cmd_str} | {after_cmd_str} | {cmd_status} |'
        )

        # Code-to-text ratio
        before_ratio = validation.metrics_before.code_to_text_ratio
        after_ratio = validation.metrics_after.code_to_text_ratio
        ratio_status = (
            self.STATUS_ICONS['PASS'] if after_ratio >= 1.0
            else self.STATUS_ICONS['WARN'] if after_ratio >= 0.8
            else self.STATUS_ICONS['FAIL']
        )
        report_lines.append(
            f'| Code-to-Text Ratio | {before_ratio:.2f}:1 | {after_ratio:.2f}:1 | {ratio_status} |'
        )

        # Specificity score
        before_spec = validation.metrics_before.specificity_score
        after_spec = validation.metrics_after.specificity_score
        spec_status = self.STATUS_ICONS['PASS'] if after_spec >= 8 else self.STATUS_ICONS['FAIL']
        report_lines.append(
            f'| Specificity Score | {before_spec}/10 | {after_spec}/10 | {spec_status} |'
        )

        # Issues section
        if validation.issues:
            report_lines.extend(['', '## Issues', ''])
            for issue in validation.issues:
                report_lines.append(f'- {issue}')
        else:
            report_lines.extend(['', '## Issues', '', 'No issues found'])

        # Recommendations
        report_lines.extend(['', '## Recommendations', ''])
        recommendations = self._generate_recommendations(validation.metrics_after)
        if recommendations:
            for rec in recommendations:
                report_lines.append(f'- {rec}')
        else:
            report_lines.append('No additional recommendations - agent meets all quality criteria!')

        return '\n'.join(report_lines)

    def _generate_recommendations(self, metrics: QualityMetrics) -> list[str]:
        """
        Generate recommendations based on metrics.

        Args:
            metrics: Quality metrics to analyze

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Time to first example
        if metrics.time_to_first_example >= 50 or metrics.time_to_first_example == -1:
            recommendations.append(
                'Add Quick Start section with working code example within first 50 lines'
            )

        # Example density
        if metrics.example_density < 30:
            recommendations.append(
                f'Add more code examples to reach 40% density (currently {metrics.example_density:.1f}%)'
            )
        elif metrics.example_density < 40:
            recommendations.append(
                f'Consider adding more code examples to reach ideal 40% density (currently {metrics.example_density:.1f}%)'
            )

        # Boundary sections
        missing_boundaries = [
            section
            for section, present in metrics.boundary_sections.items()
            if not present
        ]
        if missing_boundaries:
            recommendations.append(
                f'Add missing boundary sections: {", ".join(missing_boundaries)}'
            )

        # Commands first
        if metrics.commands_first >= 50 or metrics.commands_first == -1:
            recommendations.append(
                'Add bash/shell command example within first 50 lines (Quick Start section)'
            )

        # Code-to-text ratio
        if metrics.code_to_text_ratio < 0.8:
            recommendations.append(
                f'Improve code-to-text ratio by adding examples (currently {metrics.code_to_text_ratio:.2f}:1, target: ≥1:1)'
            )
        elif metrics.code_to_text_ratio < 1.0:
            recommendations.append(
                f'Consider adding more code examples to reach ideal 1:1 ratio (currently {metrics.code_to_text_ratio:.2f}:1)'
            )

        # Specificity score
        if metrics.specificity_score < 8:
            recommendations.append(
                f'Enhance role description to be more specific (score: {metrics.specificity_score}/10, target: ≥8). Include tech stack, domain, and standards.'
            )

        return recommendations

    def generate_summary(self, results: list[tuple[Path, ValidationResult]]) -> str:
        """
        Generate summary report for batch operations.

        Args:
            results: List of (agent_path, validation_result) tuples

        Returns:
            Markdown formatted summary
        """
        total = len(results)

        # Count status
        pass_count = sum(
            1 for _, v in results if v.metrics_after.get_status() == 'PASS'
        )
        warn_count = sum(
            1 for _, v in results if v.metrics_after.get_status() == 'WARN'
        )
        fail_count = sum(
            1 for _, v in results if v.metrics_after.get_status() == 'FAIL'
        )

        pass_pct = (pass_count / total * 100) if total > 0 else 0
        warn_pct = (warn_count / total * 100) if total > 0 else 0
        fail_pct = (fail_count / total * 100) if total > 0 else 0

        summary_lines = [
            '# Batch Formatting Summary',
            '',
            f'**Total Agents**: {total}',
            '',
            '## Status Distribution',
            '',
            f'- ✅ PASS: {pass_count} ({pass_pct:.1f}%)',
            f'- ⚠️ WARN: {warn_count} ({warn_pct:.1f}%)',
            f'- ❌ FAIL: {fail_count} ({fail_pct:.1f}%)',
            '',
            '## Individual Results',
            '',
        ]

        # List each agent
        for agent_path, validation in results:
            status = validation.metrics_after.get_status()
            icon = self.STATUS_ICONS[status]
            summary_lines.append(f'- {icon} {agent_path.name} ({status})')

        return '\n'.join(summary_lines)
