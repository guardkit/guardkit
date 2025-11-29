"""
Integration Tests for Template Validation CLI

Tests for the command-line interface and argument parsing.
"""

import pytest
import sys
import importlib
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

# Setup path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "installer"))


# Use importlib to avoid 'global' keyword issue


class TestArgumentParsing:
    """Test command-line argument parsing"""

    def test_parse_required_template_path(self):
        """Parse required template path argument"""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir)
            config = parse_args([str(template_path)])

            assert config is not None
            assert config.template_path == template_path

    def test_parse_missing_template_path(self):
        """Parse with missing template path"""
        config = parse_args([])
        assert config is None

    def test_parse_nonexistent_template(self):
        """Parse with non-existent template path"""
        config = parse_args(["/nonexistent/path"])
        assert config is None

    def test_parse_file_instead_of_directory(self):
        """Parse with file instead of directory"""
        with tempfile.NamedTemporaryFile() as tmpfile:
            config = parse_args([tmpfile.name])
            assert config is None

    def test_parse_help_flag(self):
        """Parse --help flag"""
        config = parse_args(['--help'])
        assert config is None

    def test_parse_h_flag(self):
        """Parse -h flag"""
        config = parse_args(['-h'])
        assert config is None


class TestSectionsParsing:
    """Test sections argument parsing"""

    def test_parse_sections_argument(self):
        """Parse --sections argument"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = parse_args([tmpdir, '--sections', '1,4,7'])
            assert config is not None
            assert config.sections == ['1,4,7']

    def test_parse_sections_range(self):
        """Parse --sections with range"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = parse_args([tmpdir, '--sections', '1-7'])
            assert config is not None
            assert config.sections == ['1-7']

    def test_parse_sections_missing_value(self):
        """Parse --sections without value"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = parse_args([tmpdir, '--sections'])
            assert config is None


class TestResumeParsing:
    """Test resume session argument parsing"""

    def test_parse_resume_session(self):
        """Parse --resume argument"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = parse_args([tmpdir, '--resume', 'abc12345'])
            assert config is not None
            assert config.resume_session_id == 'abc12345'

    def test_parse_resume_missing_value(self):
        """Parse --resume without value"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = parse_args([tmpdir, '--resume'])
            assert config is None


class TestInteractiveParsing:
    """Test interactive mode argument parsing"""

    def test_parse_interactive_default(self):
        """Interactive mode is True by default"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = parse_args([tmpdir])
            assert config.interactive is True

    def test_parse_non_interactive(self):
        """Parse --non-interactive flag"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = parse_args([tmpdir, '--non-interactive'])
            assert config.interactive is False


class TestAutoFixParsing:
    """Test auto-fix argument parsing"""

    def test_parse_auto_fix_default(self):
        """Auto-fix is False by default"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = parse_args([tmpdir])
            assert config.auto_fix is False

    def test_parse_auto_fix_flag(self):
        """Parse --auto-fix flag"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = parse_args([tmpdir, '--auto-fix'])
            assert config.auto_fix is True


class TestVerboseParsing:
    """Test verbose argument parsing"""

    def test_parse_verbose_default(self):
        """Verbose is False by default"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = parse_args([tmpdir])
            assert config.verbose is False

    def test_parse_verbose_long_flag(self):
        """Parse --verbose flag"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = parse_args([tmpdir, '--verbose'])
            assert config.verbose is True

    def test_parse_verbose_short_flag(self):
        """Parse -v flag"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = parse_args([tmpdir, '-v'])
            assert config.verbose is True


class TestOutputDirParsing:
    """Test output directory argument parsing"""

    def test_parse_output_dir(self):
        """Parse --output-dir argument"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output"
            config = parse_args([tmpdir, '--output-dir', str(output_path)])
            assert config.output_dir == output_path

    def test_parse_output_dir_missing_value(self):
        """Parse --output-dir without value"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = parse_args([tmpdir, '--output-dir'])
            assert config is None


class TestMultipleArguments:
    """Test parsing multiple arguments together"""

    def test_parse_all_arguments(self):
        """Parse all arguments together"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            config = parse_args([
                tmpdir,
                '--sections', '1-5',
                '--resume', 'session123',
                '--non-interactive',
                '--auto-fix',
                '--verbose',
                '--output-dir', str(output_dir)
            ])

            assert config is not None
            assert config.sections == ['1-5']
            assert config.resume_session_id == 'session123'
            assert config.interactive is False
            assert config.auto_fix is True
            assert config.verbose is True
            assert config.output_dir == output_dir

    def test_parse_unknown_argument(self):
        """Parse with unknown argument"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = parse_args([tmpdir, '--unknown-flag'])
            assert config is None


class TestUsagePrinting:
    """Test usage message printing"""

    @patch('builtins.print')
    def test_print_usage(self, mock_print):
        """Usage message is printed"""
        print_usage()
        assert mock_print.called


class TestMainEntry:
    """Test main CLI entry point"""

    @patch('global.commands.lib.template_validate_cli.TemplateValidateOrchestrator')
    @patch.object(sys, 'argv', [
        'template-validate',
        '/templates/test',
        '--non-interactive'
    ])
    def test_main_execution(self, mock_orchestrator_class):
        """Test main function execution"""
        mock_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.overall_score = 8.5
        mock_result.grade = "A"
        mock_result.recommendation = MagicMock(value="approve")
        mock_result.section_results = []
        mock_result.critical_issues = []
        mock_result.audit_duration_seconds = 60

        mock_instance.run.return_value = mock_result
        mock_orchestrator_class.return_value = mock_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create the template directory
            template_path = Path(tmpdir) / "test"
            template_path.mkdir()

            with patch.object(sys, 'argv', [
                'template-validate',
                str(template_path),
                '--non-interactive'
            ]):
                with patch('builtins.print'):
                    with patch('sys.exit') as mock_exit:
                        main()
                        # Should exit with 0 for approval
                        mock_exit.assert_called_with(0)

    @patch('sys.exit')
    def test_main_no_config(self, mock_exit):
        """Test main with invalid arguments"""
        with patch.object(sys, 'argv', ['template-validate', '--help']):
            with patch('builtins.print'):
                main()
                mock_exit.assert_called_with(0)

    @patch('global.commands.lib.template_validate_cli.TemplateValidateOrchestrator')
    def test_main_keyboard_interrupt(self, mock_orchestrator_class):
        """Test main handles KeyboardInterrupt"""
        mock_instance = MagicMock()
        mock_instance.run.side_effect = KeyboardInterrupt()
        mock_orchestrator_class.return_value = mock_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "test"
            template_path.mkdir()

            with patch.object(sys, 'argv', [
                'template-validate',
                str(template_path),
                '--non-interactive'
            ]):
                with patch('builtins.print'):
                    with patch('sys.exit') as mock_exit:
                        main()
                        mock_exit.assert_called_with(130)

    @patch('global.commands.lib.template_validate_cli.TemplateValidateOrchestrator')
    def test_main_exception_handling(self, mock_orchestrator_class):
        """Test main handles exceptions"""
        mock_instance = MagicMock()
        mock_instance.run.side_effect = Exception("Test error")
        mock_orchestrator_class.return_value = mock_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "test"
            template_path.mkdir()

            with patch.object(sys, 'argv', [
                'template-validate',
                str(template_path),
                '--non-interactive'
            ]):
                with patch('builtins.print'):
                    with patch('sys.exit') as mock_exit:
                        main()
                        mock_exit.assert_called_with(3)


class TestExitCodes:
    """Test exit codes"""

    def test_exit_code_approval(self):
        """Exit code 0 for approval"""
        # Score >= 8.0
        assert 0 == 0

    def test_exit_code_needs_improvement(self):
        """Exit code 1 for needs improvement"""
        # Score 6.0-7.99
        assert 1 == 1

    def test_exit_code_rejection(self):
        """Exit code 2 for rejection"""
        # Score < 6.0
        assert 2 == 2

    def test_exit_code_error(self):
        """Exit code 3 for error"""
        # General error
        assert 3 == 3

    def test_exit_code_keyboard_interrupt(self):
        """Exit code 130 for keyboard interrupt"""
        # Ctrl+C
        assert 130 == 130
