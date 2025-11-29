"""
Agent validation engine.

Provides objective quality scoring for agent files based on GitHub best practices.
"""

from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import sys
import os

# TASK-FIX-7C3D: Import file I/O utilities
# Use importlib to match import style of other modules
import importlib
_file_io_module = importlib.import_module('installer.global.lib.utils.file_io')
safe_read_file = _file_io_module.safe_read_file

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from .checks import (
        StructureChecks,
        ExampleDensityChecks,
        BoundaryChecks,
        SpecificityChecks,
        ExampleQualityChecks,
        MaintenanceChecks
    )
    from .models import ValidationReport, CategoryScore, CheckResult, Recommendation, FileStatus
    from .scoring import ScoreAggregator
except ImportError:
    from checks import (
        StructureChecks,
        ExampleDensityChecks,
        BoundaryChecks,
        SpecificityChecks,
        ExampleQualityChecks,
        MaintenanceChecks
    )
    from models import ValidationReport, CategoryScore, CheckResult, Recommendation, FileStatus
    from scoring import ScoreAggregator


@dataclass
class ValidationConfig:
    """Configuration for validation."""
    threshold: float = 7.0
    output_format: str = "console"  # console | json | minimal
    check_categories: Optional[List[str]] = None  # None = all categories
    auto_enhance: bool = False
    suggest_fixes: bool = False
    verbose: bool = False


class AgentValidator:
    """Main validation orchestrator."""

    def __init__(self, config: ValidationConfig):
        self.config = config
        self.checks = {
            'structure': StructureChecks(),
            'example_density': ExampleDensityChecks(),
            'boundaries': BoundaryChecks(),
            'specificity': SpecificityChecks(),
            'example_quality': ExampleQualityChecks(),
            'maintenance': MaintenanceChecks()
        }
        self.scorer = ScoreAggregator()

    def validate(self, agent_file: Path) -> ValidationReport:
        """
        Validate agent file and return complete report.

        Args:
            agent_file: Path to agent file

        Returns:
            ValidationReport with scores, checks, issues, recommendations
        """
        # Read file with error handling (TASK-FIX-7C3D)
        success, content = safe_read_file(agent_file)
        if not success:
            # content is error message
            raise ValueError(f"Cannot read agent file: {content}")

        # Run all checks (or filtered subset)
        category_results = {}
        for category_name, checker in self.checks.items():
            if self._should_run_category(category_name):
                category_results[category_name] = checker.run(content)

        # Aggregate scores
        category_scores = self.scorer.aggregate_categories(category_results)
        overall_score = self.scorer.calculate_overall(category_scores)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            category_results,
            category_scores,
            overall_score
        )

        # Build report
        report = ValidationReport(
            file=str(agent_file),
            lines=len(content.split('\n')),
            overall_score=overall_score,
            category_scores=category_scores,
            checks=category_results,
            recommendations=recommendations,
            status=self._determine_status(overall_score),
            timestamp=datetime.now().isoformat()
        )

        return report

    def _should_run_category(self, category_name: str) -> bool:
        """Check if category should be run based on config."""
        if self.config.check_categories is None:
            return True
        return category_name in self.config.check_categories

    def _generate_recommendations(
        self,
        category_results: Dict,
        category_scores: Dict[str, CategoryScore],
        overall_score: float
    ) -> List[Recommendation]:
        """Generate prioritized recommendations."""
        recommendations = []

        # Find critical failures (score < 6.0)
        for category_name, results in category_results.items():
            category_score = category_scores[category_name].score
            if category_score < 6.0:
                # Collect line numbers from failed checks
                line_numbers = []
                specific_fixes = []
                for check_name, check_result in results.items():
                    if check_result.status == "fail" and check_result.line_number:
                        line_numbers.append(check_result.line_number)
                    if check_result.suggestion:
                        specific_fixes.append(check_result.suggestion)

                impact = 8.0 - category_score
                recommendations.append(Recommendation(
                    priority='P1',
                    category=category_name,
                    action=f"Improve {category_name} score from {category_score:.1f} to 8.0",
                    impact=f"+{impact:.1f} points",
                    estimated_time_minutes=self._estimate_fix_time(category_name, results),
                    line_numbers=line_numbers if line_numbers else None,
                    specific_fixes=specific_fixes if specific_fixes else None
                ))

        # Find high-value improvements (score 6.0-7.9)
        for category_name, results in category_results.items():
            category_score = category_scores[category_name].score
            if 6.0 <= category_score < 8.0:
                # Collect line numbers and fixes
                line_numbers = []
                specific_fixes = []
                for check_name, check_result in results.items():
                    if check_result.status in ["warn", "fail"] and check_result.line_number:
                        line_numbers.append(check_result.line_number)
                    if check_result.suggestion:
                        specific_fixes.append(check_result.suggestion)

                impact = 8.0 - category_score
                recommendations.append(Recommendation(
                    priority='P2',
                    category=category_name,
                    action=f"Improve {category_name} score from {category_score:.1f} to 8.0",
                    impact=f"+{impact:.1f} points",
                    estimated_time_minutes=self._estimate_fix_time(category_name, results),
                    line_numbers=line_numbers if line_numbers else None,
                    specific_fixes=specific_fixes if specific_fixes else None
                ))

        # Find optimization opportunities (score 8.0-9.5)
        for category_name, results in category_results.items():
            category_score = category_scores[category_name].score
            if 8.0 <= category_score < 9.5:
                # Only add if there are specific improvements
                specific_fixes = []
                for check_name, check_result in results.items():
                    if check_result.suggestion:
                        specific_fixes.append(check_result.suggestion)

                if specific_fixes:
                    impact = 10.0 - category_score
                    recommendations.append(Recommendation(
                        priority='P3',
                        category=category_name,
                        action=f"Optimize {category_name} to achieve perfect score",
                        impact=f"+{impact:.1f} points",
                        estimated_time_minutes=self._estimate_fix_time(category_name, results) // 2,
                        specific_fixes=specific_fixes
                    ))

        # Sort by priority and impact
        priority_order = {'P1': 0, 'P2': 1, 'P3': 2, 'P4': 3}
        recommendations.sort(
            key=lambda r: (
                priority_order[r.priority],
                -float(r.impact.split('+')[1].split()[0])
            )
        )

        return recommendations

    def _estimate_fix_time(self, category_name: str, results: Dict) -> int:
        """Estimate time to fix category issues (minutes)."""
        time_estimates = {
            'structure': 15,
            'example_density': 30,
            'boundaries': 20,
            'specificity': 10,
            'example_quality': 25,
            'maintenance': 5
        }
        return time_estimates.get(category_name, 15)

    def _determine_status(self, overall_score: float) -> str:
        """Determine status based on overall score."""
        if overall_score >= 9.0:
            return FileStatus.EXCELLENT.value
        elif overall_score >= 8.0:
            return FileStatus.GOOD.value
        elif overall_score >= 7.0:
            return FileStatus.ACCEPTABLE.value
        elif overall_score >= 6.0:
            return FileStatus.BELOW_TARGET.value
        else:
            return FileStatus.POOR.value
