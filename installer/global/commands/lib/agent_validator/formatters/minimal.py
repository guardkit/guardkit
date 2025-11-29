"""Minimal formatter for CI/CD integration."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import ValidationReport


class MinimalFormatter:
    """Format validation report as one-line summary."""

    def format(self, report: ValidationReport) -> str:
        """Format validation report as minimal one-line output."""
        status_symbol = {
            'excellent': '✅',
            'good': '✅',
            'acceptable': '⚠️',
            'below_target': '⚠️',
            'poor': '❌'
        }.get(report.status, '?')

        return f"{report.file}: {report.overall_score:.1f}/10 {status_symbol} {report.status}"
