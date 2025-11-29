"""
Integration Tests for Template Validation Orchestrator

Tests for the interactive orchestrator that coordinates the audit workflow.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import importlib
from io import StringIO

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "installer"))


# Use importlib to avoid 'global' keyword issue
_orchestrator_module = importlib.import_module('global.lib.template_validation.orchestrator')
TemplateValidateOrchestrator = _orchestrator_module.TemplateValidateOrchestrator
_models_module = importlib.import_module('global.lib.template_validation.models')
ValidateConfig = _models_module.ValidateConfig
AuditRecommendation = _models_module.AuditRecommendation
_audit_session_module = importlib.import_module('global.lib.template_validation.audit_session')
AuditSession = _audit_session_module.AuditSession


class TestOrchestratorInitialization:
    """Test orchestrator initialization"""

    def test_create_orchestrator(self):
        """Create an orchestrator instance"""
        config = ValidateConfig(
            template_path=Path("/templates/test"),
            interactive=False
        )
        orchestrator = TemplateValidateOrchestrator(config)

        assert orchestrator.config == config
        assert orchestrator.auditor is not None
        assert orchestrator.report_generator is not None
        assert orchestrator.session is None


class TestSessionCreation:
    """Test session creation in orchestrator"""

    @patch('builtins.input', return_value='all')
    def test_create_new_session(self, mock_input):
        """Create new session"""
        config = ValidateConfig(
            template_path=Path("/templates/test"),
            interactive=False
        )
        orchestrator = TemplateValidateOrchestrator(config)
        session = orchestrator._create_session()

        assert session is not None
        assert session.template_path == Path("/templates/test")
        assert session.session_id is not None


class TestSessionLoading:
    """Test session loading"""

    def test_load_nonexistent_session(self):
        """Load non-existent session creates new one"""
        config = ValidateConfig(
            template_path=Path("/templates/test"),
            interactive=False
        )
        orchestrator = TemplateValidateOrchestrator(config)
        session = orchestrator._load_session("fake-id")

        assert session is not None
        assert session.session_id != "fake-id"

    def test_load_existing_session(self):
        """Load existing session"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            template_path = Path("/templates/test")

            # Create and save a session
            original = AuditSession.create(template_path)
            original.save(output_dir / f"audit-session-{original.session_id}.json")

            config = ValidateConfig(
                template_path=template_path,
                output_dir=output_dir,
                interactive=False,
                resume_session_id=original.session_id
            )
            orchestrator = TemplateValidateOrchestrator(config)
            loaded = orchestrator._load_session(original.session_id)

            assert loaded.session_id == original.session_id
            assert loaded.template_path == template_path


class TestSectionSelection:
    """Test section selection"""

    def test_select_all_sections_non_interactive(self):
        """Non-interactive mode selects all sections"""
        config = ValidateConfig(
            template_path=Path("/templates/test"),
            interactive=False,
            sections=None
        )
        orchestrator = TemplateValidateOrchestrator(config)
        sections = orchestrator._select_sections()

        assert len(sections) == 16
        assert sections == list(range(1, 17))

    def test_select_specific_sections(self):
        """Select specific sections"""
        config = ValidateConfig(
            template_path=Path("/templates/test"),
            interactive=False,
            sections=['1,3,5']
        )
        orchestrator = TemplateValidateOrchestrator(config)
        sections = orchestrator._select_sections()

        assert 1 in sections
        assert 3 in sections
        assert 5 in sections

    @patch('builtins.input', return_value='tech')
    def test_select_technical_sections_interactive(self, mock_input):
        """Interactive mode: select technical sections"""
        config = ValidateConfig(
            template_path=Path("/templates/test"),
            interactive=True,
            sections=None
        )
        orchestrator = TemplateValidateOrchestrator(config)
        sections = orchestrator._select_sections()

        assert sections == list(range(1, 8))


class TestSectionSpecParsing:
    """Test section specification parsing"""

    def test_parse_single_section(self):
        """Parse single section number"""
        config = ValidateConfig(template_path=Path("/templates/test"), interactive=False)
        orchestrator = TemplateValidateOrchestrator(config)
        sections = orchestrator._parse_section_spec(['5'])

        assert sections == [5]

    def test_parse_comma_separated_sections(self):
        """Parse comma-separated sections"""
        config = ValidateConfig(template_path=Path("/templates/test"), interactive=False)
        orchestrator = TemplateValidateOrchestrator(config)
        sections = orchestrator._parse_section_spec(['1,4,7'])

        assert 1 in sections
        assert 4 in sections
        assert 7 in sections

    def test_parse_range_sections(self):
        """Parse section range"""
        config = ValidateConfig(template_path=Path("/templates/test"), interactive=False)
        orchestrator = TemplateValidateOrchestrator(config)
        sections = orchestrator._parse_section_spec(['1-5'])

        assert sections == [1, 2, 3, 4, 5]

    def test_parse_mixed_format(self):
        """Parse mixed format specifications"""
        config = ValidateConfig(template_path=Path("/templates/test"), interactive=False)
        orchestrator = TemplateValidateOrchestrator(config)
        sections = orchestrator._parse_section_spec(['1-3', '8', '15-16'])

        expected = [1, 2, 3, 8, 15, 16]
        assert sections == expected

    def test_parse_removes_duplicates(self):
        """Parsing removes duplicate sections"""
        config = ValidateConfig(template_path=Path("/templates/test"), interactive=False)
        orchestrator = TemplateValidateOrchestrator(config)
        sections = orchestrator._parse_section_spec(['1,1,3,1'])

        assert sections.count(1) == 1
        assert sections == [1, 3]

    def test_parse_invalid_range(self):
        """Invalid range returns empty list or logs error"""
        config = ValidateConfig(template_path=Path("/templates/test"), interactive=False)
        orchestrator = TemplateValidateOrchestrator(config)

        # Suppress print output
        with patch('builtins.print'):
            sections = orchestrator._parse_section_spec(['invalid'])

        assert isinstance(sections, list)

    def test_parse_enforces_bounds(self):
        """Parsing enforces 1-16 section bounds"""
        config = ValidateConfig(template_path=Path("/templates/test"), interactive=False)
        orchestrator = TemplateValidateOrchestrator(config)
        sections = orchestrator._parse_section_spec(['0,5,20'])

        # Should filter out 0 and 20
        assert 0 not in sections
        assert 20 not in sections
        assert 5 in sections


class TestSessionSaving:
    """Test session saving"""

    def test_save_session(self):
        """Save session to file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            config = ValidateConfig(
                template_path=Path("/templates/test"),
                output_dir=output_dir,
                interactive=False
            )
            orchestrator = TemplateValidateOrchestrator(config)
            orchestrator.session = orchestrator._create_session()

            orchestrator._save_session()

            # Check file was created
            files = list(output_dir.glob("audit-session-*.json"))
            assert len(files) == 1


class TestReportGeneration:
    """Test report generation"""

    def test_generate_report(self):
        """Generate audit report"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            config = ValidateConfig(
                template_path=Path("/templates/test"),
                output_dir=output_dir,
                interactive=False
            )
            orchestrator = TemplateValidateOrchestrator(config)
            orchestrator.session = orchestrator._create_session()

            report_path = orchestrator._generate_report()

            assert report_path.exists()
            assert report_path.name == "audit-report.md"


class TestResultCreation:
    """Test audit result creation"""

    def test_create_result_empty_session(self):
        """Create result from empty session"""
        config = ValidateConfig(
            template_path=Path("/templates/test"),
            interactive=False
        )
        orchestrator = TemplateValidateOrchestrator(config)
        orchestrator.session = orchestrator._create_session()

        result = orchestrator._create_result()

        assert result is not None
        assert result.overall_score == 0.0
        assert result.recommendation == AuditRecommendation.REJECT

    def test_create_result_with_scores(self):
        """Create result with section scores"""
        from global.lib.template_validation.models import SectionResult

        config = ValidateConfig(
            template_path=Path("/templates/test"),
            interactive=False
        )
        orchestrator = TemplateValidateOrchestrator(config)
        orchestrator.session = orchestrator._create_session()

        # Add results
        for i in range(1, 4):
            section_result = SectionResult(
                section_num=i,
                section_title=f"Section {i}",
                score=8.0
            )
            orchestrator.session.add_result(i, section_result)

        result = orchestrator._create_result()

        assert result.overall_score == 8.0
        assert result.recommendation == AuditRecommendation.APPROVE


class TestOrchestratorWorkflow:
    """Test complete orchestrator workflow"""

    @patch.object(TemplateValidateOrchestrator, '_execute_section')
    @patch('builtins.input', return_value='')
    def test_orchestrator_run_workflow(self, mock_input, mock_execute):
        """Test complete orchestrator workflow"""
        mock_execute.return_value = True

        config = ValidateConfig(
            template_path=Path("/templates/test"),
            interactive=False
        )
        orchestrator = TemplateValidateOrchestrator(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            config.output_dir = Path(tmpdir)
            orchestrator.config = config

            # Suppress print output
            with patch('builtins.print'):
                result = orchestrator.run()

            assert result is not None
            assert result.template_name == "test"
            assert result.overall_score >= 0


class TestErrorHandling:
    """Test error handling"""

    def test_orchestrator_handles_missing_template(self):
        """Orchestrator handles missing template gracefully"""
        config = ValidateConfig(
            template_path=Path("/nonexistent/template"),
            interactive=False
        )
        orchestrator = TemplateValidateOrchestrator(config)

        # Should not raise, but handle gracefully
        assert orchestrator.config.template_path == Path("/nonexistent/template")

    def test_orchestrator_handles_invalid_output_dir(self):
        """Orchestrator creates output directory if needed"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "nested" / "dir"
            config = ValidateConfig(
                template_path=Path("/templates/test"),
                output_dir=output_dir,
                interactive=False
            )
            orchestrator = TemplateValidateOrchestrator(config)
            orchestrator.session = orchestrator._create_session()

            # Should create directory
            orchestrator._save_session()
            assert output_dir.exists()
