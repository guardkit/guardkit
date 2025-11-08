"""
Section 5: AI Agents Analysis

Validates agent relevance, prompt quality, and capabilities.
"""

from datetime import datetime
from pathlib import Path
from typing import List

from ..models import SectionResult, ValidationIssue, IssueSeverity, IssueCategory, Finding


class AIAgentsAnalysisSection:
    """Section 5: AI Agents Analysis"""

    @property
    def section_num(self) -> int:
        return 5

    @property
    def title(self) -> str:
        return "AI Agents Analysis"

    @property
    def description(self) -> str:
        return "Validate agent relevance, prompt quality, and capabilities"

    def execute(self, template_path: Path, interactive: bool = True) -> SectionResult:
        issues: List[ValidationIssue] = []
        findings: List[Finding] = []
        
        agents_dir = template_path / "agents"
        score = 10.0
        
        if not agents_dir.exists():
            issues.append(ValidationIssue(
                severity=IssueSeverity.LOW,
                category=IssueCategory.AGENTS,
                message="agents/ directory not found (optional for simple templates)",
            ))
            score = 8.0
        else:
            agent_files = list(agents_dir.glob("*.md"))
            if len(agent_files) > 0:
                findings.append(Finding(
                    title="AI Agents Included",
                    description=f"{len(agent_files)} AI agent(s) defined",
                    is_positive=True,
                    impact="Provides specialized AI assistance",
                ))
        
        return SectionResult(
            section_num=self.section_num,
            section_title=self.title,
            score=score,
            findings=findings,
            issues=issues,
            completed_at=datetime.now(),
        )
