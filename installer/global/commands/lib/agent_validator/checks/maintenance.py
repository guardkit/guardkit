"""Maintenance validation checks."""

import re
from datetime import datetime
from typing import Dict
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import CheckResult


class MaintenanceChecks:
    """Validates maintenance and completeness indicators."""

    WEIGHT = 0.05  # 5% of overall score

    def run(self, content: str) -> Dict[str, CheckResult]:
        """Run all maintenance checks."""
        return {
            'last_updated': self._check_last_updated(content),
            'completeness': self._check_completeness(content)
        }

    def _check_last_updated(self, content: str) -> CheckResult:
        """Check if last updated date is present and recent."""
        # Look for date patterns in frontmatter
        lines = content.split('\n')

        date_found = None
        in_frontmatter = False

        for line in lines:
            if line.strip() == '---':
                in_frontmatter = not in_frontmatter
                if not in_frontmatter:
                    break
                continue

            if in_frontmatter:
                # Look for updated/last_updated/modified fields
                if re.match(r'(updated|last_updated|modified|date):', line, re.IGNORECASE):
                    date_str = line.split(':', 1)[1].strip()
                    try:
                        # Try parsing common date formats
                        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y']:
                            try:
                                date_found = datetime.strptime(date_str, fmt)
                                break
                            except ValueError:
                                continue
                    except:
                        pass

        if date_found is None:
            return CheckResult(
                name="Last Updated Date",
                measured_value="not found",
                threshold="present and recent",
                score=5.0,
                weight=0.40,
                status="warn",
                message="No last updated date found",
                line_number=None,
                suggestion="Add 'updated: YYYY-MM-DD' field to frontmatter"
            )

        # Check if date is recent (within last 6 months)
        days_old = (datetime.now() - date_found).days

        if days_old <= 180:  # 6 months
            score = 10.0
            status = "pass"
            message = f"Updated {days_old} days ago (recent)"
            suggestion = None
        elif days_old <= 365:  # 1 year
            score = 7.0
            status = "warn"
            message = f"Updated {days_old} days ago (consider reviewing)"
            suggestion = "Consider reviewing and updating agent content"
        else:
            score = 4.0
            status = "warn"
            message = f"Updated {days_old} days ago (outdated)"
            suggestion = "Review and update agent content, update date field"

        return CheckResult(
            name="Last Updated Date",
            measured_value=days_old,
            threshold=180,
            score=score,
            weight=0.40,
            status=status,
            message=message,
            line_number=None,
            suggestion=suggestion
        )

    def _check_completeness(self, content: str) -> CheckResult:
        """Check for TODO/placeholder markers indicating incompleteness."""
        content_lower = content.lower()

        # Count incomplete markers
        todo_count = content_lower.count('todo')
        tbd_count = content_lower.count('tbd')
        placeholder_count = content_lower.count('placeholder')
        fixme_count = content_lower.count('fixme')

        total_incomplete = todo_count + tbd_count + placeholder_count + fixme_count

        if total_incomplete == 0:
            score = 10.0
            status = "pass"
            message = "No incomplete markers found"
            suggestion = None
        elif total_incomplete <= 2:
            score = 6.0
            status = "warn"
            message = f"{total_incomplete} incomplete markers found (TODO/TBD/PLACEHOLDER)"
            suggestion = "Complete or remove TODO/TBD/PLACEHOLDER markers"
        else:
            score = 3.0
            status = "fail"
            message = f"{total_incomplete} incomplete markers found (indicates work in progress)"
            suggestion = "Complete all sections marked with TODO/TBD/PLACEHOLDER/FIXME"

        return CheckResult(
            name="Completeness Check",
            measured_value=total_incomplete,
            threshold=0,
            score=score,
            weight=0.60,
            status=status,
            message=message,
            line_number=None,
            suggestion=suggestion
        )
