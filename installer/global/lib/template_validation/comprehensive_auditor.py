"""
Comprehensive Auditor

16-section audit framework for template validation.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

from .models import SectionResult
from .ai_service import TaskAgentService
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

    def __init__(self, enable_ai: bool = True, verbose: bool = False):
        """Initialize auditor.

        Args:
            enable_ai: Whether to enable AI assistance for sections 8, 11, 12
            verbose: Verbose logging for AI operations
        """
        self.enable_ai = enable_ai
        self.verbose = verbose
        self.ai_service = TaskAgentService(verbose=verbose) if enable_ai else None
        self.section_results: Dict[int, SectionResult] = {}
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
            8: ComparisonWithSourceSection(ai_service=self.ai_service),
            9: ProductionReadinessSection(),
            10: ScoringRubricSection(),
            11: DetailedFindingsSection(ai_service=self.ai_service, previous_results=None),  # Updated dynamically
            12: ValidationTestingSection(ai_service=self.ai_service),
            13: MarketComparisonSection(),
            14: FinalRecommendationsSection(),
            15: TestingRecommendationsSection(),
            16: SummaryReportSection(),
        }

    def get_section(self, section_num: int) -> AuditSection:
        """Get audit section by number.

        For Section 11, updates previous_results before returning.

        Args:
            section_num: Section number (1-16)

        Returns:
            AuditSection instance
        """
        if section_num not in self.sections:
            raise ValueError(f"Invalid section number: {section_num}")

        section = self.sections[section_num]

        # Special handling for Section 11 (Detailed Findings)
        # Update with results from sections 1-10
        if section_num == 11:
            previous_results = [
                self.section_results[i]
                for i in range(1, 11)
                if i in self.section_results
            ]
            section.previous_results = previous_results

        return section

    def record_result(self, section_num: int, result: SectionResult) -> None:
        """Record result from completed section.

        Args:
            section_num: Section number
            result: Section result
        """
        self.section_results[section_num] = result

    def get_all_sections(self) -> List[AuditSection]:
        """Get all audit sections in order"""
        return [self.sections[i] for i in sorted(self.sections.keys())]

    def get_section_count(self) -> int:
        """Get total number of sections"""
        return len(self.sections)
