"""
Comprehensive Auditor

16-section audit framework for template validation.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List

from .models import SectionResult
from .sections import (
    ManifestAnalysisSection,
    SettingsAnalysisSection,
    DocumentationAnalysisSection,
    TemplateFilesAnalysisSection,
    AIAgentsAnalysisSection,
    ReadmeReviewSection,
    GlobalTemplateValidationSection,
    ComparisonWithSourceSection,
    ProductionReadinessSection,
    ScoringRubricSection,
    DetailedFindingsSection,
    ValidationTestingSection,
    MarketComparisonSection,
    FinalRecommendationsSection,
    TestingRecommendationsSection,
    SummaryReportSection,
)


class AuditSection(ABC):
    """Base class for audit sections"""

    @property
    @abstractmethod
    def section_num(self) -> int:
        """Section number (1-16)"""

    @property
    @abstractmethod
    def title(self) -> str:
        """Section title"""

    @property
    @abstractmethod
    def description(self) -> str:
        """Section description"""

    @abstractmethod
    def execute(
        self,
        template_path: Path,
        interactive: bool = True
    ) -> SectionResult:
        """Execute section audit"""


class ComprehensiveAuditor:
    """16-section comprehensive audit implementation"""

    def __init__(self):
        self.sections = self._initialize_sections()

    def _initialize_sections(self) -> Dict[int, AuditSection]:
        """Initialize all 16 audit sections"""
        return {
            1: ManifestAnalysisSection(),
            2: SettingsAnalysisSection(),
            3: DocumentationAnalysisSection(),
            4: TemplateFilesAnalysisSection(),
            5: AIAgentsAnalysisSection(),
            6: ReadmeReviewSection(),
            7: GlobalTemplateValidationSection(),
            8: ComparisonWithSourceSection(),
            9: ProductionReadinessSection(),
            10: ScoringRubricSection(),
            11: DetailedFindingsSection(),
            12: ValidationTestingSection(),
            13: MarketComparisonSection(),
            14: FinalRecommendationsSection(),
            15: TestingRecommendationsSection(),
            16: SummaryReportSection(),
        }

    def get_section(self, section_num: int) -> AuditSection:
        """Get audit section by number"""
        if section_num not in self.sections:
            raise ValueError(f"Invalid section number: {section_num}")
        return self.sections[section_num]

    def get_all_sections(self) -> List[AuditSection]:
        """Get all audit sections in order"""
        return [self.sections[i] for i in sorted(self.sections.keys())]

    def get_section_count(self) -> int:
        """Get total number of sections"""
        return len(self.sections)
