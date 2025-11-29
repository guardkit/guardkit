"""
Template Q&A Orchestrator

Orchestrates interactive Q&A session for template customization.
Saves results to .template-create-config.json for use by /template-create.

TASK-9038: Create /template-qa Command for Optional Customization
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

# Import dependencies with proper error handling
try:
    # Try relative imports first
    from .template_config_handler import TemplateConfigHandler, ConfigValidationError
except ImportError:
    # Fall back to absolute imports
    from template_config_handler import TemplateConfigHandler, ConfigValidationError

# Import Q&A session using importlib to avoid 'global' keyword issue
import importlib

_template_qa_module = importlib.import_module('installer.global.commands.lib.template_qa_session')
TemplateQASession = _template_qa_module.TemplateQASession
GreenfieldAnswers = _template_qa_module.GreenfieldAnswers


@dataclass
class QAOrchestrationConfig:
    """Configuration for Q&A orchestration."""
    config_path: Optional[Path] = None  # Where to save config file (default: current directory)
    resume: bool = False  # Resume from existing config
    verbose: bool = False  # Show detailed output


@dataclass
class QAOrchestrationResult:
    """Result of Q&A orchestration."""
    success: bool
    config_file: Optional[Path] = None
    error: Optional[str] = None
    template_name: Optional[str] = None
    language: Optional[str] = None
    framework: Optional[str] = None


class TemplateQAOrchestrator:
    """
    Orchestrates Q&A session for template customization.

    Workflow:
    1. Check for existing config (if --resume)
    2. Run Q&A session (TemplateQASession)
    3. Validate answers
    4. Save to .template-create-config.json

    Usage:
        config = QAOrchestrationConfig(config_path=Path("."))
        orchestrator = TemplateQAOrchestrator(config)
        result = orchestrator.run()

        if result.success:
            print(f"Config saved: {result.config_file}")
        else:
            print(f"Error: {result.error}")
    """

    def __init__(
        self,
        config: QAOrchestrationConfig,
        qa_session: Optional[TemplateQASession] = None,
        config_handler: Optional[TemplateConfigHandler] = None
    ):
        """
        Initialize orchestrator.

        Args:
            config: Orchestration configuration
            qa_session: Optional TemplateQASession instance (for dependency injection/testing)
            config_handler: Optional TemplateConfigHandler instance (for dependency injection/testing)
        """
        self.config = config
        self.config_path = config.config_path or Path.cwd()

        # Dependency injection for testability (architectural review recommendation)
        self.config_handler = config_handler or TemplateConfigHandler(self.config_path)
        self.qa_session = qa_session  # Will be initialized in run() if not provided

        self.answers: Optional[GreenfieldAnswers] = None

    def run(self) -> QAOrchestrationResult:
        """
        Execute Q&A orchestration workflow.

        Returns:
            QAOrchestrationResult with success status and config file path
        """
        try:
            self._print_header()

            # Phase 1: Check for existing config (if --resume)
            if self.config.resume:
                if not self._handle_resume():
                    return QAOrchestrationResult(
                        success=False,
                        error="Config file not found or invalid"
                    )

            # Phase 2: Run Q&A session
            self.answers = self._run_qa_session()
            if not self.answers:
                return QAOrchestrationResult(
                    success=False,
                    error="Q&A session cancelled or failed"
                )

            # Phase 3: Save configuration
            config_file = self._save_configuration()
            if not config_file:
                return QAOrchestrationResult(
                    success=False,
                    error="Failed to save configuration"
                )

            # Success!
            self._print_success(config_file)

            return QAOrchestrationResult(
                success=True,
                config_file=config_file,
                template_name=self.answers.template_name,
                language=self.answers.primary_language,
                framework=self.answers.framework
            )

        except KeyboardInterrupt:
            self._print_info("\n\nQ&A session interrupted.")
            return QAOrchestrationResult(
                success=False,
                error="User interrupted"
            )
        except Exception as e:
            self._print_error(f"Unexpected error: {e}")
            return QAOrchestrationResult(
                success=False,
                error=str(e)
            )

    def _handle_resume(self) -> bool:
        """
        Handle resume from existing config.

        Returns:
            True if config loaded successfully, False otherwise
        """
        self._print_phase_header("Resuming from Existing Config")

        # Check if config exists
        if not self.config_handler.config_exists(self.config_path):
            self._print_error(f"Config file not found: {self.config_handler.config_file}")
            return False

        # Load config
        try:
            config_data = self.config_handler.load_config(self.config_path)

            # Show summary
            summary = self.config_handler.get_config_summary(self.config_path)
            self._print_info("\nExisting Configuration:")
            self._print_info(f"  Template: {summary['template_name']}")
            self._print_info(f"  Language: {summary['language']}")
            self._print_info(f"  Framework: {summary['framework']}")
            self._print_info(f"  Architecture: {summary['architecture']}")
            self._print_info(f"  Last updated: {summary['updated_at']}")

            # Convert config_data to GreenfieldAnswers
            self.answers = GreenfieldAnswers.from_dict(config_data)

            # Initialize Q&A session with existing answers
            # This allows user to edit values during session
            if not self.qa_session:
                self.qa_session = TemplateQASession(skip_qa=False)
                # Pre-populate answers
                self.qa_session.answers = config_data

            self._print_success_line("Config loaded successfully")
            self._print_info("\nYou can now edit any values in the following Q&A session.\n")

            return True

        except FileNotFoundError as e:
            self._print_error(f"Config file not found: {e}")
            return False
        except ConfigValidationError as e:
            self._print_error(f"Invalid config file: {e}")
            return False
        except Exception as e:
            self._print_error(f"Failed to load config: {e}")
            return False

    def _run_qa_session(self) -> Optional[GreenfieldAnswers]:
        """
        Run Q&A session.

        Returns:
            GreenfieldAnswers with user responses, or None if cancelled
        """
        self._print_phase_header("Template Customization Q&A")

        try:
            # Initialize Q&A session if not already done (dependency injection)
            if not self.qa_session:
                self.qa_session = TemplateQASession(skip_qa=False)

            # Run session
            answers = self.qa_session.run()

            if not answers:
                self._print_error("Q&A session cancelled")
                return None

            self._print_success_line("Q&A session complete")

            return answers

        except Exception as e:
            self._print_error(f"Q&A session failed: {e}")
            return None

    def _save_configuration(self) -> Optional[Path]:
        """
        Save configuration to file.

        Returns:
            Path to saved config file, or None if failed
        """
        self._print_phase_header("Saving Configuration")

        try:
            # Convert answers to dictionary
            config_data = self.answers.to_dict()

            # Save to file
            config_file = self.config_handler.save_config(config_data, self.config_path)

            self._print_success_line(f"Config saved: {config_file}")

            # Show file size if file exists
            try:
                if config_file and config_file.exists():
                    file_size = config_file.stat().st_size
                    self._print_info(f"  File size: {file_size} bytes")
            except (OSError, AttributeError):
                # Ignore stat errors (e.g., in tests with mocks)
                pass

            return config_file

        except ConfigValidationError as e:
            self._print_error(f"Config validation failed: {e}")
            return None
        except IOError as e:
            self._print_error(f"Failed to save config: {e}")
            return None
        except Exception as e:
            self._print_error(f"Unexpected error saving config: {e}")
            return None

    def _print_header(self) -> None:
        """Print main header."""
        print("\n" + "="*60)
        print("  /template-qa - Template Customization Q&A")
        print("="*60 + "\n")

        if self.config.resume:
            print("Mode: Resume (editing existing configuration)\n")
        else:
            print("Mode: New configuration\n")

    def _print_phase_header(self, phase: str) -> None:
        """Print phase header."""
        print(f"\n{phase}")
        print("-" * 60)

    def _print_success(self, config_file: Path) -> None:
        """Print success summary."""
        print("\n" + "="*60)
        print("  ✅ Configuration Saved Successfully!")
        print("="*60)

        print(f"\n📁 Config file: {config_file}")
        print(f"📝 Template: {self.answers.template_name}")
        print(f"🔤 Language: {self.answers.primary_language}")
        print(f"🛠️  Framework: {self.answers.framework}")

        print("\n📝 Next Steps:")
        print(f"   /template-create --config")
        print(f"   # OR")
        print(f"   /template-create  # Will auto-detect and use config file")
        print()

    def _print_success_line(self, message: str) -> None:
        """Print success line."""
        print(f"  ✓ {message}")

    def _print_info(self, message: str) -> None:
        """Print info message."""
        print(message)

    def _print_error(self, message: str) -> None:
        """Print error message."""
        print(f"  ❌ {message}")


def run_template_qa(
    config_path: Optional[Path] = None,
    resume: bool = False,
    verbose: bool = False
) -> QAOrchestrationResult:
    """
    Convenience function to run template Q&A.

    Args:
        config_path: Where to save config file (default: current directory)
        resume: Resume from existing config
        verbose: Show detailed output

    Returns:
        QAOrchestrationResult

    Example:
        result = run_template_qa()
        if result.success:
            print(f"Config saved: {result.config_file}")
        else:
            print(f"Error: {result.error}")
    """
    config = QAOrchestrationConfig(
        config_path=config_path,
        resume=resume,
        verbose=verbose
    )

    orchestrator = TemplateQAOrchestrator(config)
    return orchestrator.run()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Template Q&A - Interactive customization session"
    )
    parser.add_argument(
        "--path",
        type=str,
        help="Where to save config file (default: current directory)"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing config file"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output"
    )

    args = parser.parse_args()

    result = run_template_qa(
        config_path=Path(args.path) if args.path else None,
        resume=args.resume,
        verbose=args.verbose
    )

    sys.exit(0 if result.success else 1)


# Module exports
__all__ = [
    "TemplateQAOrchestrator",
    "QAOrchestrationConfig",
    "QAOrchestrationResult",
    "run_template_qa"
]
