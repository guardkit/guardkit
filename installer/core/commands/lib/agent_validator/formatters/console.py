"""Console formatter for validation reports."""

import sys
import os
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import ValidationReport


class ConsoleFormatter:
    """Format validation report for console output with colors and Unicode."""

    # Color codes
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

    # Unicode symbols
    CHECK = '✅'
    WARN = '⚠️'
    FAIL = '❌'
    ARROW = '→'
    BULLET = '•'

    def format(self, report: ValidationReport) -> str:
        """Format validation report for console display."""
        lines = []

        # Header
        lines.append(self._format_header(report))
        lines.append('')

        # Overall score
        lines.append(self._format_overall_score(report))
        lines.append('')

        # Category breakdown
        lines.append(self._format_categories(report))
        lines.append('')

        # Recommendations
        if report.recommendations:
            lines.append(self._format_recommendations(report))
            lines.append('')

        # Footer
        lines.append(self._format_footer(report))

        return '\n'.join(lines)

    def _format_header(self, report: ValidationReport) -> str:
        """Format report header."""
        return f"{self.BOLD}{'=' * 80}{self.RESET}\n" \
               f"{self.BOLD}AGENT VALIDATION REPORT{self.RESET}\n" \
               f"File: {report.file}\n" \
               f"Lines: {report.lines}\n" \
               f"{'=' * 80}"

    def _format_overall_score(self, report: ValidationReport) -> str:
        """Format overall score section."""
        score = report.overall_score
        status = report.status

        # Color based on score
        if score >= 8.0:
            color = self.GREEN
            symbol = self.CHECK
        elif score >= 6.0:
            color = self.YELLOW
            symbol = self.WARN
        else:
            color = self.RED
            symbol = self.FAIL

        return f"{self.BOLD}Overall Score:{self.RESET} " \
               f"{color}{score:.1f}/10.0{self.RESET} " \
               f"{symbol} {status.replace('_', ' ').title()}"

    def _format_categories(self, report: ValidationReport) -> str:
        """Format category breakdown."""
        lines = [f"{self.BOLD}Category Scores:{self.RESET}"]

        for name, category in report.category_scores.items():
            score = category.score
            weight = category.weight

            # Color and symbol
            if score >= 8.0:
                color = self.GREEN
                symbol = self.CHECK
            elif score >= 6.0:
                color = self.YELLOW
                symbol = self.WARN
            else:
                color = self.RED
                symbol = self.FAIL

            lines.append(
                f"  {symbol} {name.replace('_', ' ').title():<25} "
                f"{color}{score:.1f}/10.0{self.RESET} "
                f"(weight: {weight * 100:.0f}%)"
            )

            # Show failed/warning checks
            for check_name, check in category.checks.items():
                if check.status in ['fail', 'warn']:
                    check_symbol = self.FAIL if check.status == 'fail' else self.WARN
                    lines.append(f"    {check_symbol} {check.message}")
                    if check.suggestion:
                        lines.append(f"       {self.ARROW} {check.suggestion}")

        return '\n'.join(lines)

    def _format_recommendations(self, report: ValidationReport) -> str:
        """Format recommendations section."""
        lines = [f"{self.BOLD}Recommendations:{self.RESET}"]

        for i, rec in enumerate(report.recommendations[:5], 1):  # Top 5
            # Priority color
            if rec.priority == 'P1':
                priority_color = self.RED
            elif rec.priority == 'P2':
                priority_color = self.YELLOW
            else:
                priority_color = self.BLUE

            lines.append(
                f"\n{i}. [{priority_color}{rec.priority}{self.RESET}] "
                f"{rec.action}"
            )
            lines.append(f"   Impact: {self.GREEN}{rec.impact}{self.RESET}")
            lines.append(f"   Time: ~{rec.estimated_time_minutes} minutes")

            if rec.specific_fixes:
                lines.append(f"   Fixes:")
                for fix in rec.specific_fixes[:3]:  # Top 3 fixes
                    lines.append(f"     {self.BULLET} {fix}")

        if len(report.recommendations) > 5:
            lines.append(f"\n... and {len(report.recommendations) - 5} more recommendations")

        return '\n'.join(lines)

    def _format_footer(self, report: ValidationReport) -> str:
        """Format report footer."""
        return f"{'=' * 80}\n" \
               f"Generated: {report.timestamp}"
