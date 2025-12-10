"""
Section 13: Market Comparison

Compares template with market alternatives (OPTIONAL - deferred for MVP).
"""

from datetime import datetime
from pathlib import Path
from typing import List

from ..models import SectionResult, Finding


class MarketComparisonSection:
    """Section 13: Market Comparison (Optional)"""

    @property
    def section_num(self) -> int:
        return 13

    @property
    def title(self) -> str:
        return "Market Comparison"

    @property
    def description(self) -> str:
        return "Compare with market alternatives (optional)"

    def execute(self, template_path: Path, interactive: bool = True) -> SectionResult:
        findings: List[Finding] = []
        
        findings.append(Finding(
            title="Market Comparison Deferred",
            description="This section is optional and deferred for MVP",
            is_positive=False,
            impact="Provides market context (optional)",
            evidence="Will be implemented in future enhancement",
        ))
        
        return SectionResult(
            section_num=self.section_num,
            section_title=self.title,
            score=None,  # Optional section, no score
            findings=findings,
            completed_at=datetime.now(),
        )
