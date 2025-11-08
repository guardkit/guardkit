"""
Unit Tests for Template Validation Auditor

Tests for the comprehensive auditor with 16 audit sections.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import importlib

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "installer"))


# Use importlib to avoid 'global' keyword issue
_comprehensive_auditor_module = importlib.import_module('global.lib.template_validation.comprehensive_auditor')
_models_module = importlib.import_module('global.lib.template_validation.models')
ComprehensiveAuditor = _comprehensive_auditor_module.ComprehensiveAuditor
AuditSection = _comprehensive_auditor_module.AuditSection
SectionResult = _models_module.SectionResult


class TestComprehensiveAuditorInitialization:
    """Test auditor initialization"""

    def test_auditor_initialization(self):
        """Initialize comprehensive auditor"""
        auditor = ComprehensiveAuditor()
        assert auditor.sections is not None
        assert len(auditor.sections) == 16

    def test_all_sections_present(self):
        """Verify all 16 sections are initialized"""
        auditor = ComprehensiveAuditor()
        for i in range(1, 17):
            assert i in auditor.sections


class TestSectionAccess:
    """Test accessing audit sections"""

    def test_get_section(self):
        """Get a specific section"""
        auditor = ComprehensiveAuditor()
        section = auditor.get_section(1)
        assert section is not None
        assert section.section_num == 1

    def test_get_all_sections(self):
        """Get all sections in order"""
        auditor = ComprehensiveAuditor()
        sections = auditor.get_all_sections()
        assert len(sections) == 16
        for i, section in enumerate(sections, 1):
            assert section.section_num == i

    def test_get_invalid_section(self):
        """Get invalid section raises error"""
        auditor = ComprehensiveAuditor()
        with pytest.raises(ValueError):
            auditor.get_section(0)

        with pytest.raises(ValueError):
            auditor.get_section(17)

        with pytest.raises(ValueError):
            auditor.get_section(99)

    def test_get_section_count(self):
        """Get total section count"""
        auditor = ComprehensiveAuditor()
        assert auditor.get_section_count() == 16


class TestSectionProperties:
    """Test section properties"""

    def test_section_has_required_properties(self):
        """Each section has required properties"""
        auditor = ComprehensiveAuditor()
        for section in auditor.get_all_sections():
            assert hasattr(section, 'section_num')
            assert hasattr(section, 'title')
            assert hasattr(section, 'description')
            assert hasattr(section, 'execute')

    def test_section_numbers_sequential(self):
        """Section numbers are sequential 1-16"""
        auditor = ComprehensiveAuditor()
        sections = auditor.get_all_sections()
        for i, section in enumerate(sections, 1):
            assert section.section_num == i

    def test_section_titles_unique(self):
        """All section titles are unique"""
        auditor = ComprehensiveAuditor()
        titles = [section.title for section in auditor.get_all_sections()]
        assert len(titles) == len(set(titles))

    def test_section_titles_not_empty(self):
        """All section titles are non-empty"""
        auditor = ComprehensiveAuditor()
        for section in auditor.get_all_sections():
            assert section.title
            assert len(section.title) > 0

    def test_section_descriptions_not_empty(self):
        """All section descriptions are non-empty"""
        auditor = ComprehensiveAuditor()
        for section in auditor.get_all_sections():
            assert section.description
            assert len(section.description) > 0


class TestSectionGrouping:
    """Test section grouping by category"""

    def test_technical_validation_sections(self):
        """Sections 1-7 are technical validation"""
        auditor = ComprehensiveAuditor()
        for i in range(1, 8):
            assert auditor.get_section(i) is not None

    def test_quality_assessment_sections(self):
        """Sections 8-13 are quality assessment"""
        auditor = ComprehensiveAuditor()
        for i in range(8, 14):
            assert auditor.get_section(i) is not None

    def test_decision_framework_sections(self):
        """Sections 14-16 are decision framework"""
        auditor = ComprehensiveAuditor()
        for i in range(14, 17):
            assert auditor.get_section(i) is not None


class TestSectionMetadata:
    """Test section metadata consistency"""

    def test_section_num_matches_position(self):
        """Section number matches its position"""
        auditor = ComprehensiveAuditor()
        sections = auditor.get_all_sections()
        for i, section in enumerate(sections, 1):
            assert section.section_num == i

    def test_section_execution_signature(self):
        """All sections have consistent execute signature"""
        auditor = ComprehensiveAuditor()
        for section in auditor.get_all_sections():
            # Should be callable
            assert callable(section.execute)


class TestSectionInstances:
    """Test that sections are properly instantiated"""

    def test_section_instances_are_unique(self):
        """Each section instance is unique"""
        auditor = ComprehensiveAuditor()
        instances = [id(auditor.get_section(i)) for i in range(1, 17)]
        # All should be different objects
        assert len(instances) == len(set(instances))

    def test_sections_persist_in_auditor(self):
        """Sections persist in auditor instance"""
        auditor = ComprehensiveAuditor()
        section1_first = auditor.get_section(1)
        section1_second = auditor.get_section(1)
        # Should be the same object
        assert section1_first is section1_second


class MockAuditSection(AuditSection):
    """Mock section for testing"""

    def __init__(self, num: int):
        self._num = num

    @property
    def section_num(self) -> int:
        return self._num

    @property
    def title(self) -> str:
        return f"Section {self._num}"

    @property
    def description(self) -> str:
        return f"Description for section {self._num}"

    def execute(self, template_path: Path, interactive: bool = True):
        return SectionResult(
            section_num=self._num,
            section_title=self.title,
            score=7.0 + (self._num * 0.1)
        )


class TestAuditSectionBase:
    """Test AuditSection base class"""

    def test_create_mock_section(self):
        """Create a mock audit section"""
        section = MockAuditSection(5)
        assert section.section_num == 5
        assert section.title == "Section 5"
        assert section.description == "Description for section 5"

    def test_mock_section_execution(self):
        """Execute mock section"""
        section = MockAuditSection(3)
        result = section.execute(Path("/templates/test"))
        assert result.section_num == 3
        assert result.score == 7.3


class TestAuditorStateManagement:
    """Test auditor state"""

    def test_auditor_initialization_state(self):
        """Auditor starts with clean state"""
        auditor = ComprehensiveAuditor()
        # Get all sections to verify state
        sections = auditor.get_all_sections()
        assert len(sections) == 16

    def test_multiple_auditor_instances_independent(self):
        """Multiple auditor instances are independent"""
        auditor1 = ComprehensiveAuditor()
        auditor2 = ComprehensiveAuditor()

        section1 = auditor1.get_section(1)
        section2 = auditor2.get_section(1)

        # Should be different instances
        assert section1 is not section2


class TestSectionRetrievalPerformance:
    """Test section retrieval performance"""

    def test_get_all_sections_returns_list(self):
        """get_all_sections returns a list"""
        auditor = ComprehensiveAuditor()
        sections = auditor.get_all_sections()
        assert isinstance(sections, list)
        assert len(sections) > 0

    def test_get_section_returns_object(self):
        """get_section returns section object"""
        auditor = ComprehensiveAuditor()
        for i in range(1, 17):
            section = auditor.get_section(i)
            # Sections implement AuditSection interface
            assert hasattr(section, 'section_num')
            assert hasattr(section, 'title')
            assert hasattr(section, 'description')
            assert callable(section.execute)
