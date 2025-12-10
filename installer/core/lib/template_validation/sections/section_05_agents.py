"""
Section 5: AI Agents Analysis

Validates agent relevance, prompt quality, and capabilities.
Includes progressive disclosure split structure validation.
"""

from datetime import datetime
from pathlib import Path
from typing import List

from ..models import SectionResult, ValidationIssue, IssueSeverity, IssueCategory, Finding
from ..progressive_disclosure_validator import validate_agent_split_structure


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
        metadata = {}

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
            # Count all agent files (including -ext.md)
            agent_files = list(agents_dir.glob("*.md"))
            core_files = [f for f in agent_files if not f.stem.endswith('-ext')]

            if len(core_files) > 0:
                findings.append(Finding(
                    title="AI Agents Included",
                    description=f"{len(core_files)} AI agent(s) defined",
                    is_positive=True,
                    impact="Provides specialized AI assistance",
                ))

                # Validate progressive disclosure split structure
                split_issues, split_findings, split_metadata = validate_agent_split_structure(agents_dir)
                issues.extend(split_issues)
                findings.extend(split_findings)
                metadata.update(split_metadata)

                # Adjust score based on split structure compliance
                split_count = split_metadata.get('split_count', 0)
                total_agents = split_metadata.get('total_agents', 0)

                if split_count > 0 and total_agents > 0:
                    # Calculate adoption rate
                    adoption_rate = split_count / total_agents

                    # Check if split agents meet quality thresholds
                    split_agents_data = split_metadata.get('split_agents', [])
                    meeting_targets = sum(
                        1 for agent in split_agents_data
                        if agent.get('meets_target', False) and agent.get('has_loading_instruction', False)
                    )

                    if meeting_targets == split_count:
                        # Bonus for all split agents meeting targets
                        score += 0.5
                    elif meeting_targets > 0:
                        # Partial credit for some agents meeting targets
                        score += 0.25

                    # Small penalty for agents not meeting reduction threshold
                    poor_reduction_count = sum(
                        1 for agent in split_agents_data
                        if agent.get('reduction_percent', 0) < 40
                    )
                    if poor_reduction_count > 0:
                        score -= 0.5 * (poor_reduction_count / split_count)

        return SectionResult(
            section_num=self.section_num,
            section_title=self.title,
            score=max(0.0, min(10.0, score)),  # Clamp between 0 and 10
            findings=findings,
            issues=issues,
            metadata=metadata,
            completed_at=datetime.now(),
        )
