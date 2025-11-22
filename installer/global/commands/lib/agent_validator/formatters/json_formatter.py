"""JSON formatter for validation reports."""

import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import ValidationReport


class JSONFormatter:
    """Format validation report as JSON."""

    def format(self, report: ValidationReport) -> str:
        """Format validation report as JSON string."""
        return json.dumps(report.to_dict(), indent=2)
