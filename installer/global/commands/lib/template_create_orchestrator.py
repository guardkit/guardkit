"""
Template Create Orchestrator

Orchestrates complete template creation workflow from existing codebases.
Coordinates Q&A, AI analysis, and component generation phases.

TASK-010: /template-create Command Orchestrator
"""

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import json
import logging
import uuid

# === BEGIN: Repository Root Resolution ===
def _add_repo_to_path():
    """Add repository root and commands/lib to sys.path if not already present.

    Two paths are needed:
    1. repo_root: For modules in installer/global/lib/ (via lib symlink)
    2. commands_lib: For local modules like template_qa_session.py
    """
    script_path = Path(__file__).resolve()
    # Navigate: lib/ -> commands/ -> global/ -> installer/ -> taskwright/ (5 levels up)
    repo_root = script_path.parent.parent.parent.parent.parent
    repo_root_str = str(repo_root)

    # Also add the commands/lib directory for local imports (template_qa_session, etc.)
    commands_lib = script_path.parent  # installer/global/commands/lib/
    commands_lib_str = str(commands_lib)

    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)

    if commands_lib_str not in sys.path:
        sys.path.insert(0, commands_lib_str)

_add_repo_to_path()
# === END: Repository Root Resolution ===

# Import component modules using importlib to avoid 'global' keyword issue
import importlib
# template_qa_session is in commands/lib/ (same dir as this file), imported directly
_template_qa_module = importlib.import_module('template_qa_session')
_codebase_analyzer_module = importlib.import_module('lib.codebase_analyzer.ai_analyzer')
_manifest_gen_module = importlib.import_module('lib.template_creation.manifest_generator')
_settings_gen_module = importlib.import_module('lib.settings_generator.generator')
_claude_md_gen_module = importlib.import_module('lib.template_generator.claude_md_generator')
_template_gen_module = importlib.import_module('lib.template_generator.template_generator')
_agent_gen_module = importlib.import_module('lib.agent_generator.agent_generator')

TemplateQASession = _template_qa_module.TemplateQASession
CodebaseAnalyzer = _codebase_analyzer_module.CodebaseAnalyzer
ManifestGenerator = _manifest_gen_module.ManifestGenerator
SettingsGenerator = _settings_gen_module.SettingsGenerator
ClaudeMdGenerator = _claude_md_gen_module.ClaudeMdGenerator
TemplateGenerator = _template_gen_module.TemplateGenerator
AIAgentGenerator = _agent_gen_module.AIAgentGenerator

# TASK-BRIDGE-002: Agent Bridge Integration
_agent_bridge_invoker_module = importlib.import_module('lib.agent_bridge.invoker')
_agent_bridge_state_module = importlib.import_module('lib.agent_bridge.state_manager')
AgentBridgeInvoker = _agent_bridge_invoker_module.AgentBridgeInvoker
StateManager = _agent_bridge_state_module.StateManager
TemplateCreateState = _agent_bridge_state_module.TemplateCreateState

# TASK-FIX-7C3D: File I/O Error Handling
_file_io_module = importlib.import_module('lib.utils.file_io')
safe_read_file = _file_io_module.safe_read_file
safe_write_file = _file_io_module.safe_write_file

# TASK-IMP-REVERT-V097: Orchestrator Error Detection and Messaging
_error_messages_module = importlib.import_module('lib.orchestrator_error_messages')
detect_orchestrator_failure = _error_messages_module.detect_orchestrator_failure
display_orchestrator_failure = _error_messages_module.display_orchestrator_failure

# TASK-040: Phase 5.5 Completeness Validation
_validator_module = importlib.import_module('lib.template_generator.completeness_validator')
_models_module = importlib.import_module('lib.template_generator.models')
CompletenessValidator = _validator_module.CompletenessValidator
ValidationReport = _models_module.ValidationReport
TemplateCollection = _models_module.TemplateCollection

# TASK-043: Phase 5.7 Extended Validation
_extended_validator_module = importlib.import_module('lib.template_generator.extended_validator')
_report_generator_module = importlib.import_module('lib.template_generator.report_generator')
ExtendedValidator = _extended_validator_module.ExtendedValidator
ExtendedValidationReport = _extended_validator_module.ExtendedValidationReport
ValidationReportGenerator = _report_generator_module.ValidationReportGenerator

# TASK-PHASE-7-5-BATCH-PROCESSING: Import WorkflowPhase from constants to avoid circular import
_constants_module = importlib.import_module('lib.template_creation.constants')
WorkflowPhase = _constants_module.WorkflowPhase

# REMOVED: Phase 7.5 Agent Enhancement (TASK-SIMP-9ABE)
# See TASK-PHASE-8-INCREMENTAL for incremental enhancement approach


logger = logging.getLogger(__name__)


@dataclass
class OrchestrationConfig:
    """Configuration for template creation orchestration"""
    codebase_path: Optional[Path] = None
    output_path: Optional[Path] = None  # DEPRECATED: Use output_location instead
    output_location: str = 'global'  # TASK-068: 'global' or 'repo'
    max_templates: Optional[int] = None
    dry_run: bool = False
    save_analysis: bool = False
    no_agents: bool = False
    verbose: bool = False
    skip_validation: bool = False  # TASK-040: Skip Phase 5.5 validation
    auto_fix_templates: bool = True  # TASK-040: Auto-fix completeness issues
    interactive_validation: bool = True  # TASK-040: Prompt user for validation decisions
    validate: bool = False  # TASK-043: Run extended validation and generate quality report
    resume: bool = False  # TASK-BRIDGE-002: Resume from checkpoint after agent invocation
    custom_name: Optional[str] = None  # TASK-FDB2: User-provided template name override
    create_agent_tasks: bool = True  # TASK-UX-3A8D: Default ON (opt-out via --no-create-agent-tasks)


@dataclass
class OrchestrationResult:
    """Result of template creation orchestration"""
    success: bool
    template_name: str
    output_path: Optional[Path]
    manifest_path: Optional[Path]
    settings_path: Optional[Path]
    claude_md_path: Optional[Path]
    template_count: int
    agent_count: int
    confidence_score: int
    errors: List[str]
    warnings: List[str]
    validation_report_path: Optional[Path] = None  # TASK-043: Extended validation report
    exit_code: int = 0  # TASK-043: Exit code based on validation score


class TemplateCreateOrchestrator:
    """
    Main orchestrator for /template-create command.

    Coordinates all phases of template creation from existing codebases:
    1. Q&A session (TASK-001)
    2. AI analysis (TASK-002)
    3. Manifest generation (TASK-005)
    4. Settings generation (TASK-006)
    5. Template file generation (TASK-008) [REORDERED - was Phase 6]
    6. Agent recommendation (TASK-009) [REORDERED - was Phase 7]
    7. Agent writing (TASK-C7A9) [NEW - extracted from Phase 9]
       ↑ Agents written to disk BEFORE CLAUDE.md generation
    8. CLAUDE.md generation (TASK-007) [REORDERED - was Phase 5]
       ↑ NOW can scan actual agent files from disk
    9. Template package assembly (TASK-C7A9) [REORDERED - was Phase 8]

    Phase Reordering (TASK-019A, TASK-C7A9):
    - Agents are now written to disk BEFORE CLAUDE.md generation
    - Eliminates AI hallucinations about non-existent agents
    - CLAUDE.md can now scan and document actual agent files
    - Clean separation: agent writing → CLAUDE.md → packaging

    Usage:
        config = OrchestrationConfig(codebase_path=Path("/path/to/code"))
        orchestrator = TemplateCreateOrchestrator(config)
        result = orchestrator.run()
    """

    def __init__(self, config: OrchestrationConfig):
        """
        Initialize orchestrator.

        Args:
            config: Orchestration configuration
        """
        self.config = config
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.phase_5_5_report: Optional[ValidationReport] = None  # TASK-043: Track Phase 5.5 report

        # TASK-BRIDGE-002: Bridge integration
        self.state_manager = StateManager()
        self.agent_invoker = AgentBridgeInvoker(
            phase=WorkflowPhase.PHASE_6,
            phase_name="agent_generation"
        )

        # Storage for phase results (used for state persistence)
        self.qa_answers: Optional[Dict[str, Any]] = None
        self.analysis: Optional[Any] = None
        self.manifest: Optional[Any] = None
        self.settings: Optional[Any] = None
        self.templates: Optional[Any] = None
        self.agent_inventory: Optional[List[Any]] = None
        self.agents: Optional[List[Any]] = None
        self.claude_md: Optional[Any] = None

        # TASK-PHASE-7-5-TEMPLATE-PREWRITE-FIX: Track if templates written to disk
        self._templates_written_to_disk = False

        # Configure logging
        if config.verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        # If resuming, load state
        if self.config.resume:
            self._resume_from_checkpoint()

    def run(self) -> OrchestrationResult:
        """
        Execute complete template creation workflow.

        TASK-BRIDGE-002: Modified to support checkpoint-resume pattern.
        If config.resume is True, checks phase from state and routes accordingly:
        - Phase 5: _run_from_phase_5() (agent generation)
        - Phase 7: _run_from_phase_7() (agent enhancement)
        Otherwise, executes all phases 1-9.5 from start.

        TASK-IMP-REVERT-V097: Added pre-flight dependency check before execution.

        Returns:
            OrchestrationResult with success status and generated artifacts
        """
        try:
            # TASK-IMP-REVERT-V097: Pre-flight check - verify dependencies before running
            # Only check on initial run, not on resume (dependencies already validated)
            if not self.config.resume:
                can_run, error_type, details = detect_orchestrator_failure()
                if not can_run:
                    display_orchestrator_failure(error_type, details)
                    return self._create_error_result(
                        error=f"Orchestrator unavailable: {error_type}",
                        error_details=details
                    )

            # If resuming, route based on phase number
            if self.config.resume:
                state = self.state_manager.load_state()
                phase = state.phase

                if phase == WorkflowPhase.PHASE_7:
                    return self._run_from_phase_7()
                else:
                    # Default to Phase 5 (backward compatibility)
                    return self._run_from_phase_5()

            # Normal execution: Phases 1-9.5
            return self._run_all_phases()

        except KeyboardInterrupt:
            self._print_info("\n\nTemplate creation interrupted.")
            return self._create_error_result("User interrupted")
        except Exception as e:
            logger.exception("Unexpected error in orchestration")
            return self._create_error_result(f"Unexpected error: {e}")

    def _run_all_phases(self) -> OrchestrationResult:
        """
        Execute phases 1-7 from start (TASK-51B2: AI-native workflow).

        Saves checkpoint before Phase 5 to enable resume after agent invocation.

        Returns:
            OrchestrationResult with success status and generated artifacts
        """
        self._print_header()

        # Get codebase path
        codebase_path = self.config.codebase_path or Path.cwd()
        if not codebase_path.exists():
            return self._create_error_result(f"Codebase path does not exist: {codebase_path}")

        # Phase 1: AI-Native Codebase Analysis (TASK-51B2)
        # AI analyzes codebase directly and infers all metadata
        self.analysis = self._phase1_ai_analysis(codebase_path)
        if not self.analysis:
            return self._create_error_result("AI analysis failed")

        # Save analysis if requested
        if self.config.save_analysis:
            self._save_analysis_json(self.analysis)

        # Phase 2: Manifest Generation
        self.manifest = self._phase2_manifest_generation(self.analysis)
        if not self.manifest:
            return self._create_error_result("Manifest generation failed")

        # Phase 3: Settings Generation
        self.settings = self._phase3_settings_generation(self.analysis)
        if not self.settings:
            return self._create_error_result("Settings generation failed")

        # Phase 4: Template File Generation
        self.templates = self._phase4_template_generation(self.analysis)
        if not self.templates:
            self.warnings.append("No template files generated")

        # ===== Phase 4.5: Completeness Validation (TASK-040) =====
        if not self.config.skip_validation and self.templates:
            self.templates = self._phase4_5_completeness_validation(
                templates=self.templates,
                analysis=self.analysis
            )

        # IMPORTANT: Save state before Phase 5
        # (Phase 5 may exit with code 42 to request agent invocation)
        self._save_checkpoint("templates_generated", phase=WorkflowPhase.PHASE_4)

        # Phase 5: Agent Recommendation (may exit with code 42)
        self.agents = []
        if not self.config.no_agents:
            self.agents = self._phase5_agent_recommendation(self.analysis)

        # Phase 6-7: Complete workflow
        return self._complete_workflow()

    def _run_from_phase_5(self) -> OrchestrationResult:
        """
        Continue from Phase 5 after agent invocation (TASK-BRIDGE-002).

        State has been restored in __init__, now complete the workflow.

        Returns:
            OrchestrationResult with success status and generated artifacts
        """
        self._print_header()
        print("  (Resuming from checkpoint)")

        # Phase 5: Complete agent generation with loaded response
        self.agents = []
        if not self.config.no_agents:
            self.agents = self._phase5_agent_recommendation(self.analysis)

        # Phase 6-7: Complete workflow
        return self._complete_workflow()

    def _run_from_phase_7(self) -> OrchestrationResult:
        """
        Continue from Phase 7 after agent writing.

        REMOVED: Phase 7.5 agent enhancement (TASK-SIMP-9ABE)
        Now proceeds directly from Phase 7 to Phase 8.

        Returns:
            OrchestrationResult with success status and generated artifacts
        """
        self._print_header()
        print("  (Resuming from checkpoint - Phase 7)")

        # Determine output path (needed for Phase 8 onwards)
        output_path = self._get_output_path()

        # Phase 8-9.5: Complete workflow from Phase 8 onwards
        return self._complete_workflow_from_phase_8(output_path)

    def _complete_workflow(self) -> OrchestrationResult:
        """
        Complete phases 6-9 (TASK-C7A9).

        Shared by both _run_all_phases and _run_from_phase_5.

        Returns:
            OrchestrationResult with success status and generated artifacts
        """
        # Determine output path early (needed for Phase 8)
        output_path = self._get_output_path()

        # Phase 7: Agent Writing
        if self.config.dry_run:
            self._print_dry_run_summary(self.manifest, self.settings, self.templates, self.agents)
            return self._create_dry_run_result(self.manifest, len(self.templates.templates if self.templates else []), len(self.agents))

        if self.agents:
            agent_paths = self._phase7_write_agents(self.agents, output_path)

            # Debug logging for Phase 7.5 issue investigation
            logger.debug(f"Phase 7 complete: agent_paths type={type(agent_paths)}, value={agent_paths}")
            logger.debug(f"Phase 7 complete: {len(self.agents)} agents, returned {len(agent_paths) if agent_paths else 0} paths")

            # CRITICAL FIX: Use explicit None check instead of falsy check
            # agent_paths can be:
            # - None (error occurred)
            # - [] (no agents - should not happen here since self.agents is truthy)
            # - [Path, Path, ...] (success)
            if agent_paths is None:
                self.warnings.append("Agent writing failed")
                logger.error("Phase 7 failed: agent_paths is None")
            elif len(agent_paths) == 0:
                # This shouldn't happen since self.agents is truthy, but handle defensively
                self.warnings.append("No agent files written despite agents existing")
                logger.warning(f"Phase 7 warning: {len(self.agents)} agents but 0 paths returned")
            else:
                # SUCCESS: agent_paths contains paths to written agent files
                logger.info(f"Phase 7 success: {len(agent_paths)} agent files written")

                # REMOVED: Phase 7.5 Agent Enhancement (TASK-SIMP-9ABE)
                # Templates are now written in Phase 4, agents in Phase 7
                # See TASK-PHASE-8-INCREMENTAL for incremental enhancement approach

        # Phase 8-9.5: Complete workflow from Phase 8 onwards
        return self._complete_workflow_from_phase_8(output_path)

    def _get_output_path(self) -> Path:
        """
        Determine output path based on configuration (DRY principle).

        Architectural Context:
        - Centralizes output path logic (was duplicated in 2 places)
        - Validates manifest exists before path determination
        - Supports 3 path modes: explicit, repo, global (default)

        Path Priority:
        1. Explicit path (config.output_path) - highest priority
        2. Repository location (config.output_location == 'repo')
        3. Global location (default: ~/.agentecflow/templates/)

        Returns:
            Path to template output directory

        Raises:
            ValueError: If manifest not generated yet

        TASK-PHASE-7-5-FIX-FOUNDATION: DRY improvement (+6 SOLID points)
        """
        if not self.manifest:
            raise ValueError("Manifest must be generated before determining output path")

        if self.config.output_path:
            return self.config.output_path
        elif self.config.output_location == 'repo':
            return Path("installer/global/templates") / self.manifest.name
        else:
            return Path.home() / ".agentecflow" / "templates" / self.manifest.name

    def _ensure_templates_on_disk(self, output_path: Path) -> None:
        """
        Ensure templates are written to disk.

        DEPRECATED (TASK-SIMP-9ABE): This method was originally created for Phase 7.5
        agent enhancement, which has been removed. Templates are now written in Phase 4.

        This method is kept for backward compatibility but may be removed in future.

        Idempotent: Safe to call multiple times (only writes once).

        Args:
            output_path: Template output directory
        """
        # Idempotent check: only write once
        if self._templates_written_to_disk:
            logger.debug("Templates already written to disk, skipping")
            return

        # Check if we have templates to write
        if not self.templates or self.templates.total_count == 0:
            logger.debug("No templates to write to disk")
            self._templates_written_to_disk = True  # Mark as done even if no templates
            return

        logger.info(f"Writing {self.templates.total_count} templates to disk")
        success = self._write_templates_to_disk(self.templates, output_path)

        if success:
            self._templates_written_to_disk = True
            logger.info(f"Successfully wrote {self.templates.total_count} template files")
        else:
            # Non-fatal: Phase 7.5 can handle missing templates
            logger.warning("Failed to pre-write templates")
            # Don't set flag - allow retry on next call
            # Phase 7.5 will handle gracefully if templates missing

    def _write_templates_to_disk(self, templates: TemplateCollection, output_path: Path) -> bool:
        """
        Write template files to disk (DRY principle).

        Architectural Context:
        - Centralizes template writing logic (was duplicated in 2 places)
        - Provides consistent error handling across all template writes
        - Handles SystemExit propagation for bridge pattern
        - Returns success/failure for optional error handling

        Used By:
        - _ensure_templates_on_disk() - Pre-writes for Phase 7.5
        - _phase9_package_assembly() - Final template writing

        Args:
            templates: TemplateCollection to write
            output_path: Template output directory

        Returns:
            True if successful, False otherwise

        Note:
            Propagates SystemExit(42) for bridge pattern compatibility.
            Other exceptions are logged and return False.

        TASK-PHASE-7-5-FIX-FOUNDATION: DRY improvement (+6 SOLID points)
        """
        if not templates or templates.total_count == 0:
            logger.debug("No templates to write")
            return True

        try:
            template_gen = TemplateGenerator(None, None)
            template_gen.save_templates(templates, output_path)
            logger.info(f"Wrote {templates.total_count} template files to {output_path}")
            return True
        except SystemExit as e:
            # Propagate bridge exit codes (code 42 = agent invocation needed)
            if e.code == 42:
                raise
            # Other SystemExit codes indicate errors
            logger.error(f"Template writing failed with exit code {e.code}")
            return False
        except Exception as e:
            logger.error(f"Failed to write templates: {e}")
            return False

    def _complete_workflow_from_phase_8(self, output_path: Path) -> OrchestrationResult:
        """
        Complete phases 8-10.5 (TASK-PHASE-8-INCREMENTAL).

        Shared by _complete_workflow and _run_from_phase_7.

        Args:
            output_path: Template output directory

        Returns:
            OrchestrationResult with success status and generated artifacts
        """
        # Phase 8: Agent Task Creation (TASK-PHASE-8-INCREMENTAL) [OPTIONAL]
        # Creates individual tasks for each agent if --create-agent-tasks flag is set
        task_result = self._run_phase_8_create_agent_tasks(output_path)
        if not task_result["success"]:
            # Non-fatal: Log warning but continue
            logger.warning(f"Phase 8 agent task creation had issues: {task_result.get('error', 'Unknown error')}")

        # Phase 9: CLAUDE.md Generation (was Phase 8)
        # NOW agents exist and can be documented accurately
        self.claude_md = self._phase8_claude_md_generation(self.analysis, self.agents, output_path)
        if not self.claude_md:
            return self._create_error_result("CLAUDE.md generation failed")

        # Phase 9: Template Package Assembly
        output_path = self._phase9_package_assembly(
            manifest=self.manifest,
            settings=self.settings,
            claude_md=self.claude_md,
            templates=self.templates,
            output_path=output_path
        )

        if not output_path:
            return self._create_error_result("Package assembly failed")

        # ===== Phase 9.5: Extended Validation (TASK-043) =====
        # Run after package assembly when all files are in place
        validation_report_path = None
        exit_code = 0
        if self.config.validate and self.templates:
            validation_report_path, exit_code = self._phase9_5_extended_validation(
                templates=self.templates,
                manifest=self.manifest,
                settings=self.settings,
                claude_md_path=output_path / "CLAUDE.md",
                agents=self.agents,
                output_path=output_path
            )

        # Cleanup state on success
        self.state_manager.cleanup()

        # Success!
        # TASK-068: Pass location_type to success message
        location_type = "personal" if self.config.output_location == 'global' else "distribution"
        if self.config.output_path:
            location_type = "custom"
        self._print_success(output_path, self.manifest, self.templates, self.agents, location_type, validation_report_path)

        return OrchestrationResult(
            success=True,
            template_name=self.manifest.name,
            output_path=output_path,
            manifest_path=output_path / "manifest.json",
            settings_path=output_path / "settings.json",
            claude_md_path=output_path / "CLAUDE.md",
            template_count=len(self.templates.templates) if self.templates else 0,
            agent_count=len(self.agents),
            confidence_score=self.manifest.confidence_score,
            errors=self.errors,
            warnings=self.warnings,
            validation_report_path=validation_report_path,
            exit_code=exit_code
        )

    def _phase1_ai_analysis(self, codebase_path: Path) -> Optional[Any]:
        """
        Phase 1: AI-Native Codebase Analysis (TASK-51B2).

        AI analyzes codebase directly and infers all metadata:
        - Language (from file extensions, config files)
        - Framework (from dependencies)
        - Architecture (from folder structure)
        - Testing framework (from test files)
        - Template name (suggested from project)

        Args:
            codebase_path: Path to codebase to analyze

        Returns:
            CodebaseAnalysis or None if failed
        """
        self._print_phase_header("Phase 1: AI Codebase Analysis")

        try:
            if not codebase_path.exists():
                self._print_error(f"Codebase path does not exist: {codebase_path}")
                return None

            # AI-native analysis: No template_context needed!
            # AI will infer language, framework, architecture from codebase
            # TASK-51B2-B: Increased from 10 to 30 to provide better context for template generation
            # TASK-769D: Pass AgentBridgeInvoker for checkpoint-resume pattern
            analyzer = CodebaseAnalyzer(
                max_files=30,
                bridge_invoker=self.agent_invoker
            )

            self._print_info(f"  Analyzing: {codebase_path}")
            analysis = analyzer.analyze_codebase(
                codebase_path=codebase_path,
                template_context=None,  # AI infers everything
                save_results=False
            )

            # Display what AI inferred
            if hasattr(analysis, 'metadata'):
                self._print_info(f"  Language: {getattr(analysis.metadata, 'primary_language', 'unknown')}")
                self._print_info(f"  Framework: {getattr(analysis.metadata, 'framework', 'unknown')}")
                self._print_info(f"  Template: {getattr(analysis.metadata, 'template_name', 'unknown')}")

            self._print_success_line(f"Analysis complete (confidence: {analysis.overall_confidence.percentage}%)")

            return analysis

        except Exception as e:
            self._print_error(f"Analysis failed: {e}")
            logger.exception("Analysis error")
            return None

    def _validate_template_name(self, name: str) -> Tuple[bool, str]:
        """
        Validate custom template name (TASK-FDB2).

        Pattern: lowercase letters, numbers, and hyphens only
        Length: 3-50 characters

        Args:
            name: Template name to validate

        Returns:
            (is_valid, error_message) tuple
        """
        import re

        if not name:
            return True, ""  # Empty is valid (use AI generation)

        if len(name) < 3 or len(name) > 50:
            return False, "Template name must be 3-50 characters"

        if not re.match(r'^[a-z0-9-]+$', name):
            return False, "Template name must contain only lowercase letters, numbers, and hyphens"

        return True, ""

    def _phase2_manifest_generation(self, analysis: Any) -> Optional[Any]:
        """
        Phase 2: Generate manifest.json.

        TASK-FDB2: Supports custom template name override via --name flag.

        Args:
            analysis: CodebaseAnalysis from phase 1

        Returns:
            TemplateManifest or None if failed
        """
        self._print_phase_header("Phase 2: Manifest Generation")

        try:
            generator = ManifestGenerator(analysis)
            manifest = generator.generate()

            # TASK-FDB2: Override AI-generated name if custom name provided
            if self.config.custom_name:
                is_valid, error_msg = self._validate_template_name(self.config.custom_name)
                if not is_valid:
                    self._print_error(f"Invalid template name: {error_msg}")
                    self._print_info(f"  Example valid names: my-api-template, react-admin, dotnet-api")
                    return None

                manifest.name = self.config.custom_name
                self._print_info(f"  Using custom template name: {self.config.custom_name}")
            else:
                self._print_info(f"  Using AI-generated name: {manifest.name}")

            self._print_success_line(f"Template: {manifest.name}")
            self._print_info(f"  Language: {manifest.language} ({manifest.language_version or 'any version'})")
            self._print_info(f"  Architecture: {manifest.architecture}")
            self._print_info(f"  Complexity: {manifest.complexity}/10")

            return manifest

        except Exception as e:
            self._print_error(f"Manifest generation failed: {e}")
            logger.exception("Manifest generation error")
            return None

    def _phase3_settings_generation(self, analysis: Any) -> Optional[Any]:
        """
        Phase 3: Generate settings.json.

        Args:
            analysis: CodebaseAnalysis from phase 1

        Returns:
            TemplateSettings or None if failed
        """
        self._print_phase_header("Phase 3: Settings Generation")

        try:
            generator = SettingsGenerator(analysis)
            settings = generator.generate()

            convention_count = len(settings.naming_conventions)
            layer_count = len(settings.layer_mappings)

            self._print_success_line(f"{convention_count} naming conventions")
            self._print_success_line(f"{layer_count} layer mappings")
            self._print_info(f"  Code style: {settings.code_style.indentation} ({settings.code_style.indent_size} spaces)")

            return settings

        except Exception as e:
            self._print_error(f"Settings generation failed: {e}")
            logger.exception("Settings generation error")
            return None

    def _phase4_template_generation(self, analysis: Any) -> Optional[Any]:
        """
        Phase 4: Generate .template files.

        Args:
            analysis: CodebaseAnalysis from phase 1

        Returns:
            TemplateCollection or None if failed
        """
        self._print_phase_header("Phase 4: Template File Generation")

        try:
            generator = TemplateGenerator(analysis)
            templates = generator.generate(max_templates=self.config.max_templates)

            if templates and templates.total_count > 0:
                # Show some examples
                for template in templates.templates[:3]:
                    self._print_success_line(f"{template.template_path}")

                if templates.total_count > 3:
                    self._print_info(f"  ... and {templates.total_count - 3} more")

                self._print_info(f"  Total: {templates.total_count} template files")
            else:
                self.warnings.append("No template files generated")
                self._print_warning("No template files generated")

            return templates

        except Exception as e:
            self._print_error(f"Template generation failed: {e}")
            logger.exception("Template generation error")
            return None

    def _phase5_agent_recommendation(self, analysis: Any) -> List[Any]:
        """
        Phase 5: Recommend and generate custom agents.

        TASK-BRIDGE-002: Modified to pass AgentBridgeInvoker to generator.
        May exit with code 42 if agent invocation needed.

        Args:
            analysis: CodebaseAnalysis from phase 1

        Returns:
            List of GeneratedAgent objects
        """
        self._print_phase_header("Phase 5: Agent Recommendation")

        try:
            # Import agent scanner to get inventory
            _agent_scanner_module = importlib.import_module('lib.agent_scanner')
            MultiSourceAgentScanner = _agent_scanner_module.MultiSourceAgentScanner
            scanner = MultiSourceAgentScanner()
            inventory = scanner.scan()

            # CRITICAL: Pass AgentBridgeInvoker to generator (TASK-BRIDGE-002)
            generator = AIAgentGenerator(
                inventory,
                ai_invoker=self.agent_invoker  # ← BRIDGE INTEGRATION
            )

            # This may exit with code 42 if agent invocation needed
            agents = generator.generate(analysis)

            if agents:
                self._print_info(f"  Generated {len(agents)} custom agents")
            else:
                self._print_info("  All capabilities covered by existing agents")

            return agents

        except SystemExit as e:
            # Code 42 is expected - re-raise to exit orchestrator
            if e.code == 42:
                raise
            # Other exit codes are errors
            self._print_error(f"Agent generation exited with code {e.code}")
            return []

        except Exception as e:
            self._print_warning(f"Agent generation failed: {e}")
            logger.exception("Agent generation error")
            return []

    def _phase7_write_agents(self, agents: List[Any], output_path: Path) -> Optional[List[Path]]:
        """
        Phase 7: Write agent files to disk (TASK-C7A9).

        Extracted from _phase9_package_assembly to ensure agents are written
        before CLAUDE.md generation can scan them.

        Args:
            agents: List of GeneratedAgent objects
            output_path: Template output directory

        Returns:
            List of written agent file paths, or None if failed
        """
        self._print_phase_header("Phase 7: Agent Writing")

        try:
            if not agents:
                self._print_info("  No agents to write")
                return []

            agents_dir = output_path / "agents"
            agents_dir.mkdir(parents=True, exist_ok=True)

            # Import markdown formatter for proper YAML frontmatter formatting
            _markdown_formatter_module = importlib.import_module('lib.agent_generator.markdown_formatter')
            format_agent_markdown = _markdown_formatter_module.format_agent_markdown

            agent_paths = []
            for agent in agents:
                agent_path = agents_dir / f"{agent.name}.md"

                # Check if full_definition is already properly formatted markdown
                # or if we need to format it from agent attributes
                if agent.full_definition and agent.full_definition.strip().startswith('---'):
                    # Already has YAML frontmatter, use as-is
                    markdown_content = agent.full_definition
                else:
                    # Need to format as markdown with YAML frontmatter
                    # Convert GeneratedAgent to dict format expected by formatter
                    # Handle tags/technologies - ensure it's a list
                    tags = getattr(agent, 'tags', [])
                    if not isinstance(tags, list):
                        try:
                            tags = list(tags)
                        except TypeError:
                            tags = []

                    agent_dict = {
                        'name': agent.name,
                        'description': agent.description,
                        'reason': getattr(agent, 'reason', f"Specialized agent for {agent.name.replace('-', ' ')}"),
                        'technologies': tags,
                        'priority': getattr(agent, 'priority', 7)
                    }
                    markdown_content = format_agent_markdown(agent_dict)

                # TASK-FIX-7C3D: Use safe_write_file for error handling
                success, error_msg = safe_write_file(agent_path, markdown_content)
                if not success:
                    logger.error(f"  ✗ Failed to write {agent_path.name}: {error_msg}")
                    continue  # Skip this agent, continue with others
                agent_paths.append(agent_path)

            self._print_success_line(f"{len(agents)} agent files written")
            return agent_paths

        except Exception as e:
            self._print_error(f"Agent writing failed: {e}")
            logger.exception("Agent writing error")
            return None

    # REMOVED: _phase7_5_enhance_agents() method (TASK-SIMP-9ABE)
    # Phase 7.5 had 0% success rate and has been removed
    # See TASK-PHASE-8-INCREMENTAL for incremental enhancement approach

    def _run_phase_8_create_agent_tasks(
        self,
        output_path: Path
    ) -> Dict[str, Any]:
        """
        Phase 8: Create individual agent enhancement tasks (TASK-PHASE-8-INCREMENTAL).

        Only runs if config.create_agent_tasks is True.

        Creates one task per agent file for incremental enhancement.
        Tasks can be worked through individually using /task-work.

        Args:
            output_path: Template output directory containing agents/ subdirectory

        Returns:
            Dict with:
                - success: bool
                - tasks_created: int
                - task_ids: List[str]

        Raises:
            Exception: If task creation fails (non-fatal - returns success=False instead)
        """
        if not self.config.create_agent_tasks:
            logger.info("Skipping agent task creation (--create-agent-tasks not specified)")
            return {"success": True, "tasks_created": 0, "task_ids": []}

        # Find agent files in output directory
        agents_dir = output_path / "agents"
        if not agents_dir.exists():
            logger.warning("No agents directory found to create tasks for")
            return {"success": True, "tasks_created": 0, "task_ids": []}

        agent_files = list(agents_dir.glob("*.md"))
        if not agent_files:
            logger.warning("No agent files found to create tasks for")
            return {"success": True, "tasks_created": 0, "task_ids": []}

        self._print_phase_header("Phase 8: Agent Task Creation")
        self._print_info(f"Creating enhancement tasks for {len(agent_files)} agents...")

        # Import task creation utilities
        # Using relative import since we're in the same package
        try:
            # FIXME: This import needs to be implemented - placeholder for now
            # from lib.task_management.task_creator import create_task
            # For now, we'll create a simplified version
            task_ids = self._create_agent_tasks_simplified(agent_files, output_path)

            if task_ids:
                self._print_success_line(f"Created {len(task_ids)} agent enhancement tasks")

                # TASK-UX-2F95: Display Option A/B format with /agent-enhance as primary
                agent_names = [agent_file.stem for agent_file in agent_files]
                template_name = output_path.name
                self._print_agent_enhancement_instructions(task_ids, agent_names, template_name)

            return {
                "success": True,
                "tasks_created": len(task_ids),
                "task_ids": task_ids
            }

        except Exception as e:
            logger.exception(f"Failed to create agent tasks: {e}")
            self.warnings.append(f"Agent task creation failed: {e}")
            return {"success": False, "tasks_created": 0, "task_ids": [], "error": str(e)}

    def _generate_task_id(self, agent_name: str) -> str:
        """
        Generate unique task ID for agent enhancement.

        Uses UUID-based generation to guarantee uniqueness even for agents with
        similar names. This prevents task ID collisions that could occur with
        timestamp-based generation.

        Format: TASK-{agent-name-prefix}-{uuid}
        Example: TASK-REPOSITORY-PA-A3F2B1C8

        Args:
            agent_name: Full agent name (e.g., 'repository-pattern-specialist')

        Returns:
            str: Unique task ID with format TASK-{PREFIX}-{UUID}

        Note:
            - Uses up to 15 chars of agent name for readability
            - Uses 8 chars of UUID for uniqueness (collision probability: ~1 in 4 billion)
            - Hyphens in agent name are preserved in prefix
        """
        # Use up to 15 chars of agent name for readability
        # Preserve hyphens for better readability
        prefix = agent_name[:15].upper()

        # Use 8 chars of UUID for uniqueness
        # UUID4 provides 122 bits of randomness
        # 8 hex chars = 32 bits = ~4.3 billion possibilities
        unique_id = uuid.uuid4().hex[:8].upper()

        return f"TASK-{prefix}-{unique_id}"

    def _create_agent_tasks_simplified(
        self,
        agent_files: List[Path],
        template_dir: Path
    ) -> List[str]:
        """
        Create tasks for agent enhancement (simplified version).

        This is a temporary implementation until we integrate with the
        full task management system.

        Args:
            agent_files: List of agent file paths
            template_dir: Template output directory

        Returns:
            List of task IDs created
        """
        import datetime
        from pathlib import Path as PathlibPath

        template_name = template_dir.name
        task_ids = []

        # Create tasks directory if it doesn't exist
        tasks_backlog = PathlibPath("tasks/backlog")
        tasks_backlog.mkdir(parents=True, exist_ok=True)

        for agent_file in agent_files:
            agent_name = agent_file.stem

            # Generate unique task ID using UUID-based method
            # This prevents collisions from similar agent names or rapid creation
            task_id = self._generate_task_id(agent_name)

            # Create task metadata
            task_content = f"""# {task_id}: Enhance {agent_name} agent for {template_name} template

**Task ID**: {task_id}
**Priority**: MEDIUM
**Status**: BACKLOG
**Created**: {datetime.datetime.now().isoformat()}

## Description

Enhance the {agent_name} agent with template-specific content:
- Add related template references
- Include code examples from templates
- Document best practices
- Add anti-patterns to avoid (if applicable)

**Agent File**: {agent_file}
**Template Directory**: {template_dir}

## Command

```bash
/agent-enhance {template_name}/{agent_name}
```

## Acceptance Criteria

- [ ] Agent file enhanced with template-specific sections
- [ ] Relevant templates identified and documented
- [ ] Code examples from templates included
- [ ] Best practices documented
- [ ] Anti-patterns documented (if applicable)

## Metadata

```json
{{
    "type": "agent_enhancement",
    "agent_file": "{agent_file}",
    "template_dir": "{template_dir}",
    "template_name": "{template_name}",
    "agent_name": "{agent_name}"
}}
```
"""

            # Write task file
            task_file = tasks_backlog / f"{task_id}.md"
            # TASK-FIX-7C3D: Use safe_write_file for error handling
            success, error_msg = safe_write_file(task_file, task_content)
            if not success:
                logger.error(f"  ✗ Failed to create {task_id}: {error_msg}")
                continue  # Skip this task, continue with others

            task_ids.append(task_id)
            logger.info(f"  ✓ Created {task_id} for {agent_name}")

        return task_ids

    def _phase8_claude_md_generation(self, analysis: Any, agents: List[Any], output_path: Path) -> Optional[Any]:
        """
        Phase 8: Generate CLAUDE.md (TASK-C7A9).

        NOW runs AFTER agents are written to disk, so it can scan actual agent files
        instead of working from in-memory objects.

        Args:
            analysis: CodebaseAnalysis from phase 2
            agents: List of GeneratedAgent objects from phase 6
            output_path: Template output directory (for agent scanning)

        Returns:
            TemplateClaude or None if failed
        """
        self._print_phase_header("Phase 8: CLAUDE.md Generation")

        try:
            # Pass agents and output_path to generator for accurate documentation
            # TASK-C7A9: output_path enables scanning actual agent files from disk
            generator = ClaudeMdGenerator(analysis, agents=agents, output_path=output_path)
            claude_md = generator.generate()

            example_count = len(analysis.example_files)

            self._print_success_line("Architecture overview")
            self._print_success_line("Technology stack")
            self._print_success_line(f"{example_count} code examples")
            self._print_success_line("Quality standards")

            if agents:
                self._print_success_line(f"Agent usage ({len(agents)} agents documented)")
            else:
                self._print_success_line("Agent usage (generic guidance)")

            return claude_md

        except Exception as e:
            self._print_error(f"CLAUDE.md generation failed: {e}")
            logger.exception("CLAUDE.md generation error")
            return None

    def _phase4_5_completeness_validation(
        self,
        templates: TemplateCollection,
        analysis: Any
    ) -> TemplateCollection:
        """
        Phase 4.5: Completeness Validation (TASK-040).

        Validates template completeness and optionally auto-fixes issues.

        Args:
            templates: TemplateCollection to validate
            analysis: CodebaseAnalysis for context

        Returns:
            Updated TemplateCollection (possibly with auto-generated templates)
        """
        self._print_phase_header("Phase 4.5: Completeness Validation")

        try:
            # Create validator
            validator = CompletenessValidator()

            # Run validation
            self._print_info("  Validating template completeness...")
            validation_report = validator.validate(templates, analysis)

            # TASK-043: Store Phase 4.5 report for Phase 9.5 extended validation
            self.phase_5_5_report = validation_report

            # Display validation report
            self._print_validation_report(validation_report)

            # Handle validation issues if present
            if not validation_report.is_complete:
                if self.config.interactive_validation:
                    action = self._handle_validation_issues_interactive(validation_report)
                else:
                    action = self._handle_validation_issues_noninteractive(validation_report)

                if action == 'auto_fix':
                    # Auto-generate missing templates
                    self._print_info("\n  Auto-generating missing templates...")
                    new_templates = validator.generate_missing_templates(
                        recommendations=validation_report.recommended_templates,
                        existing_templates=templates
                    )

                    if new_templates:
                        # Add new templates to collection
                        templates.templates.extend(new_templates)
                        templates.total_count += len(new_templates)

                        self._print_success_line(f"Generated {len(new_templates)} missing templates")
                        self._print_info(f"  Updated total: {templates.total_count} templates")

                        # Recalculate FN score
                        new_score = validator._calculate_false_negative_score(
                            templates_generated=templates.total_count,
                            templates_expected=validation_report.templates_expected
                        )
                        self._print_success_line(f"False Negative score improved: {validation_report.false_negative_score:.2f} → {new_score:.2f}")
                    else:
                        self._print_warning("Could not auto-generate missing templates")

                elif action == 'quit':
                    self._print_info("\n  Template creation cancelled by user")
                    sys.exit(0)

                # action == 'continue' means proceed without fixing

            else:
                self._print_success_line("All templates complete, no issues found")

            return templates

        except Exception as e:
            self._print_error(f"Validation failed: {e}")
            logger.exception("Validation error")
            # Don't fail the entire workflow, just warn
            self.warnings.append(f"Validation failed: {e}")
            return templates

    def _print_validation_report(self, report: ValidationReport) -> None:
        """
        Display validation report in readable format.

        Args:
            report: ValidationReport to display
        """
        print(f"\n  Templates Generated: {report.templates_generated}")
        print(f"  Templates Expected: {report.templates_expected}")
        print(f"  False Negative Score: {report.false_negative_score:.2f}/10")

        if report.is_complete:
            print(f"  Status: ✅ Complete")
        else:
            print(f"  Status: ⚠️  Incomplete ({len(report.issues)} issues)")

        if report.issues:
            print(f"\n  Issues Found:")
            for issue in report.issues[:5]:  # Show first 5 issues
                severity_icon = {
                    'critical': '🔴',
                    'high': '🟠',
                    'medium': '🟡',
                    'low': '🟢'
                }.get(issue.severity, '⚪')

                print(f"    {severity_icon} {issue.message}")

            if len(report.issues) > 5:
                print(f"    ... and {len(report.issues) - 5} more")

        if report.recommended_templates:
            print(f"\n  Recommendations: {len(report.recommended_templates)} missing templates")
            auto_generable = sum(1 for rec in report.recommended_templates if rec.can_auto_generate)
            if auto_generable > 0:
                print(f"    ({auto_generable} can be auto-generated)")

    def _handle_validation_issues_interactive(
        self,
        validation_report: ValidationReport
    ) -> str:
        """
        Handle validation issues in interactive mode.

        Prompts: [A]uto-fix / [C]ontinue / [Q]uit

        Args:
            validation_report: ValidationReport with issues

        Returns:
            Action: 'auto_fix', 'continue', or 'quit'
        """
        print("\n  Options:")
        print("    [A] Auto-fix - Generate missing templates automatically")
        print("    [C] Continue - Proceed without fixing issues")
        print("    [Q] Quit - Cancel template creation")

        while True:
            try:
                choice = input("\n  Your choice (A/C/Q): ").strip().upper()

                if choice == 'A':
                    return 'auto_fix'
                elif choice == 'C':
                    return 'continue'
                elif choice == 'Q':
                    return 'quit'
                else:
                    print("  Invalid choice. Please enter A, C, or Q.")

            except (EOFError, KeyboardInterrupt):
                print("\n  Cancelled by user")
                return 'quit'

    def _handle_validation_issues_noninteractive(
        self,
        validation_report: ValidationReport
    ) -> str:
        """
        Handle validation issues in non-interactive mode.

        Default: auto_fix if possible, fail if not

        Args:
            validation_report: ValidationReport with issues

        Returns:
            Action: 'auto_fix' or 'continue'
        """
        if self.config.auto_fix_templates:
            # Check if issues can be auto-fixed
            auto_fixable = any(
                rec.can_auto_generate
                for rec in validation_report.recommended_templates
            )

            if auto_fixable:
                self._print_info("\n  Non-interactive mode: Auto-fixing completeness issues...")
                return 'auto_fix'
            else:
                self._print_warning("\n  Issues found but cannot auto-fix. Continuing anyway...")
                return 'continue'
        else:
            self._print_warning("\n  Issues found. Auto-fix disabled, continuing...")
            return 'continue'

    def _phase9_package_assembly(
        self,
        manifest: Any,
        settings: Any,
        claude_md: Any,
        templates: Any,
        output_path: Path
    ) -> Optional[Path]:
        """
        Phase 9: Assemble complete template package (TASK-C7A9).

        Agent writing now happens in Phase 7, before CLAUDE.md generation.

        Args:
            manifest: TemplateManifest
            settings: TemplateSettings
            claude_md: TemplateClaude
            templates: TemplateCollection
            output_path: Template output directory (already determined)

        Returns:
            Path to output directory or None if failed
        """
        self._print_phase_header("Phase 9: Package Assembly")

        try:
            # TASK-C7A9: output_path is now passed as parameter (determined in _complete_workflow)
            # Ensure directory exists
            output_path.mkdir(parents=True, exist_ok=True)

            # Save manifest.json
            manifest_path = output_path / "manifest.json"
            manifest_gen = ManifestGenerator(None)  # Need to pass analysis, but we have manifest
            with open(manifest_path, 'w') as f:
                json.dump(manifest.to_dict() if hasattr(manifest, 'to_dict') else vars(manifest), f, indent=2)
            self._print_success_line(f"manifest.json ({self._file_size(manifest_path)})")

            # Save settings.json
            settings_path = output_path / "settings.json"
            settings_gen = SettingsGenerator(None)
            settings_gen.save(settings, settings_path)
            self._print_success_line(f"settings.json ({self._file_size(settings_path)})")

            # Save CLAUDE.md
            claude_md_path = output_path / "CLAUDE.md"
            claude_gen = ClaudeMdGenerator(None)
            claude_gen.save(claude_md, claude_md_path)
            self._print_success_line(f"CLAUDE.md ({self._file_size(claude_md_path)})")

            # Save template files
            if templates and templates.total_count > 0:
                if self._write_templates_to_disk(templates, output_path):
                    self._print_success_line(f"templates/ ({templates.total_count} files)")
                else:
                    self._print_warning(f"Failed to write {templates.total_count} template files")

            # TASK-C7A9: Agent files now written in Phase 7 (before CLAUDE.md generation)
            # This ensures ClaudeMdGenerator can scan actual agent files from disk

            return output_path

        except Exception as e:
            self._print_error(f"Package assembly failed: {e}")
            logger.exception("Package assembly error")
            return None

    def _save_analysis_json(self, analysis: Any) -> None:
        """Save analysis to JSON for debugging."""
        try:
            _serializer_module = importlib.import_module('lib.codebase_analyzer.serializer')
            AnalysisSerializer = _serializer_module.AnalysisSerializer

            serializer = AnalysisSerializer()
            path = serializer.save(analysis, filename="template-create-analysis.json")
            self._print_info(f"  Analysis saved to: {path}")

        except Exception as e:
            self._print_warning(f"Failed to save analysis: {e}")

    def _print_dry_run_summary(
        self,
        manifest: Any,
        settings: Any,
        templates: Any,
        agents: List[Any]
    ) -> None:
        """Print summary for dry run mode."""
        self._print_info("\n" + "="*60)
        self._print_info("  DRY RUN - Template Generation Plan")
        self._print_info("="*60)

        self._print_info(f"\nTemplate: {manifest.name}")
        self._print_info(f"Language: {manifest.language} ({manifest.language_version or 'any'})")
        self._print_info(f"Architecture: {manifest.architecture}")
        self._print_info(f"Complexity: {manifest.complexity}/10")

        self._print_info("\nComponents:")
        self._print_success_line("manifest.json (would generate)")
        self._print_success_line("settings.json (would generate)")
        self._print_success_line("CLAUDE.md (would generate)")

        if templates:
            self._print_success_line(f"{templates.total_count} template files (would generate)")

        if agents:
            self._print_success_line(f"{len(agents)} custom agents (would generate)")

        self._print_info("\nNo files written (--dry-run mode)")

    def _create_error_result(self, error: str) -> OrchestrationResult:
        """Create error result."""
        self.errors.append(error)
        return OrchestrationResult(
            success=False,
            template_name="",
            output_path=None,
            manifest_path=None,
            settings_path=None,
            claude_md_path=None,
            template_count=0,
            agent_count=0,
            confidence_score=0,
            errors=self.errors,
            warnings=self.warnings
        )

    def _create_dry_run_result(
        self,
        manifest: Any,
        template_count: int,
        agent_count: int
    ) -> OrchestrationResult:
        """Create dry run result."""
        return OrchestrationResult(
            success=True,
            template_name=manifest.name,
            output_path=None,
            manifest_path=None,
            settings_path=None,
            claude_md_path=None,
            template_count=template_count,
            agent_count=agent_count,
            confidence_score=manifest.confidence_score,
            errors=self.errors,
            warnings=self.warnings
        )

    def _file_size(self, path: Path) -> str:
        """Get human-readable file size."""
        size = path.stat().st_size
        for unit in ['B', 'KB', 'MB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} GB"

    def _print_header(self) -> None:
        """Print main header."""
        print("\n" + "="*60)
        print("  Template Creation - Brownfield (Existing Codebase)")
        print("="*60 + "\n")

    def _print_phase_header(self, phase: str) -> None:
        """Print phase header."""
        print(f"\n{phase}")
        print("-" * 60)

    def _print_success(
        self,
        output_path: Path,
        manifest: Any,
        templates: Any,
        agents: List[Any],
        location_type: str = "personal",
        validation_report_path: Optional[Path] = None
    ) -> None:
        """Print success summary with location-specific messaging (TASK-068, TASK-043)."""
        print("\n" + "="*60)
        print("  ✅ Template Package Created Successfully!")
        print("="*60)

        print(f"\n📁 Location: {output_path}/")

        # TASK-068: Location-specific messaging
        if location_type == "personal":
            print("🎯 Type: Personal use (immediately available)")
        elif location_type == "distribution":
            print("📦 Type: Distribution (requires installation)")
        else:
            print("🔧 Type: Custom location")

        print(f"\n  ├── manifest.json ({self._file_size(output_path / 'manifest.json')})")
        print(f"  ├── settings.json ({self._file_size(output_path / 'settings.json')})")
        print(f"  ├── CLAUDE.md ({self._file_size(output_path / 'CLAUDE.md')})")

        if templates:
            print(f"  ├── templates/ ({templates.total_count} files)")

        if agents:
            agent_prefix = "├──" if validation_report_path else "└──"
            print(f"  {agent_prefix} agents/ ({len(agents)} agents)")

        # TASK-043: Show validation report if generated
        if validation_report_path:
            print(f"  └── validation-report.md ({self._file_size(validation_report_path)})")

        # TASK-068: Location-specific next steps
        print("\n📝 Next Steps:")
        if location_type == "personal":
            print(f"   taskwright init {manifest.name}")
        elif location_type == "distribution":
            print(f"   git add installer/global/templates/{manifest.name}/")
            print(f"   git commit -m \"Add {manifest.name} template\"")
            print(f"   ./installer/scripts/install.sh")
            print(f"   taskwright init {manifest.name}")
        else:
            print(f"1. Review generated files in {output_path}/")
            print(f"2. Test template with: taskwright init {manifest.name}")

    def _print_success_line(self, message: str) -> None:
        """Print success line."""
        print(f"  ✓ {message}")

    def _print_info(self, message: str) -> None:
        """Print info message."""
        print(message)

    def _print_warning(self, message: str) -> None:
        """Print warning message."""
        print(f"  ⚠️  {message}")

    def _print_error(self, message: str) -> None:
        """Print error message."""
        print(f"  ❌ {message}")

    def _print_agent_enhancement_instructions(
        self,
        task_ids: List[str],
        agent_names: List[str],
        template_name: str
    ) -> None:
        """
        Print agent enhancement instructions with Option A/B format (TASK-UX-2F95).
        Includes boundary sections announcement (TASK-DOC-1C5A).

        Displays two clear options:
        - Option A: Fast enhancement using /agent-enhance (2-5 minutes per agent)
        - Option B: Full workflow using /task-work (30-60 minutes per agent)

        Args:
            task_ids: List of created task IDs (for Option B)
            agent_names: List of agent names (for Option A)
            template_name: Name of the template
        """
        print(f"\n{'='*70}")
        print("AGENT ENHANCEMENT OPTIONS")
        print(f"{'='*70}\n")

        # NEW: Boundary sections feature announcement
        print("📋 Enhanced Agents Now Include Boundary Sections (GitHub Best Practices)")
        print("   Automatically generated in all enhanced agents:\n")
        print("   • ALWAYS (5-7 rules): Non-negotiable actions the agent MUST perform")
        print("   • NEVER (5-7 rules): Prohibited actions the agent MUST avoid")
        print("   • ASK (3-5 scenarios): Situations requiring human escalation\n")
        print("   Format: [emoji] [action] ([brief rationale])")
        print("   - ✅ ALWAYS prefix")
        print("   - ❌ NEVER prefix")
        print("   - ⚠️ ASK prefix\n")
        print("   📖 See: installer/global/agents/agent-content-enhancer.md for details")
        print(f"   {'─'*68}\n")

        # Option A: Fast Enhancement (Recommended)
        print("Option A - Fast Enhancement (Recommended): 2-5 minutes per agent")
        print("  Use /agent-enhance for direct AI-powered enhancement\n")

        for agent_name in agent_names:
            print(f"  /agent-enhance {template_name}/{agent_name} --hybrid")

        # Option B: Full Task Workflow (Optional)
        print(f"\nOption B - Full Task Workflow (Optional): 30-60 minutes per agent")
        print("  Use /task-work for complete quality gates\n")

        for task_id in task_ids:
            print(f"  /task-work {task_id}")

        # Enhanced footer note
        print(f"\nBoth approaches use the same AI enhancement logic with boundary validation.")
        print(f"\nExpected Validation:")
        print(f"  ✅ boundary_sections: ['ALWAYS', 'NEVER', 'ASK']")
        print(f"  ✅ boundary_completeness: always_count=5-7, never_count=5-7, ask_count=3-5")
        print(f"{'='*70}\n")

    def _display_enhancement_errors(self, errors: list[str], max_display: int = 3) -> None:
        """Display enhancement errors with optional limit.

        Args:
            errors: List of error messages
            max_display: Maximum number of errors to display (default: 3)
        """
        if errors:
            self._print_warning("  Errors encountered:")
            for error in errors[:max_display]:
                self._print_warning(f"    - {error}")
            if len(errors) > max_display:
                self._print_warning(f"    ... and {len(errors) - max_display} more")

    def _phase9_5_extended_validation(
        self,
        templates: TemplateCollection,
        manifest: Any,
        settings: Any,
        claude_md_path: Path,
        agents: List[Any],
        output_path: Path
    ) -> Tuple[Path, int]:
        """
        Phase 9.5: Extended Validation (TASK-043, TASK-C7A9).

        Runs only if --validate flag set.
        Performs deeper quality checks and generates report.

        Args:
            templates: TemplateCollection to validate
            manifest: Template manifest
            settings: Template settings
            claude_md_path: Path to CLAUDE.md
            agents: List of generated agents
            output_path: Template output directory

        Returns:
            Tuple of (report_path, exit_code)
        """
        self._print_phase_header("Phase 9.5: Extended Validation")

        try:
            # Create validator
            validator = ExtendedValidator()

            # Convert manifest and settings to dicts
            manifest_dict = manifest.to_dict() if hasattr(manifest, 'to_dict') else vars(manifest)
            settings_dict = settings.to_dict() if hasattr(settings, 'to_dict') else vars(settings)

            # Get agent paths
            agent_paths = []
            if agents:
                agents_dir = output_path / "agents"
                for agent in agents:
                    agent_path = agents_dir / f"{agent.name}.md"
                    if agent_path.exists():
                        agent_paths.append(agent_path)

            # Run extended validation
            self._print_info("  Running extended validation checks...")
            validation_report = validator.validate(
                templates=templates,
                manifest=manifest_dict,
                settings=settings_dict,
                claude_md_path=claude_md_path,
                agents=agent_paths,
                phase_5_5_report=self.phase_5_5_report
            )

            # Generate report
            report_generator = ValidationReportGenerator()
            report_path = report_generator.generate_report(
                report=validation_report,
                template_name=manifest_dict['name'],
                output_path=output_path
            )

            # Display summary
            self._print_validation_summary(validation_report)
            self._print_success_line(f"Validation report: {report_path}")

            return report_path, validation_report.get_exit_code()

        except Exception as e:
            self._print_error(f"Extended validation failed: {e}")
            logger.exception("Extended validation error")
            # Don't fail the entire workflow, just warn
            self.warnings.append(f"Extended validation failed: {e}")
            return None, 0

    def _print_validation_summary(self, report: ExtendedValidationReport) -> None:
        """
        Display extended validation summary.

        Args:
            report: ExtendedValidationReport to display
        """
        print(f"\n  Overall Score: {report.overall_score:.1f}/10 (Grade: {report.get_grade()})")
        print(f"  Production Ready: {'✅ Yes' if report.is_production_ready() else '⚠️ No'}")
        print(f"  Exit Code: {report.get_exit_code()}")

        if report.issues:
            print(f"\n  Issues: {len(report.issues)}")
            for issue in report.issues[:3]:
                print(f"    - {issue}")
            if len(report.issues) > 3:
                print(f"    ... and {len(report.issues) - 3} more")

        if report.recommendations:
            print(f"\n  Recommendations: {len(report.recommendations)}")
            for rec in report.recommendations[:3]:
                print(f"    - {rec}")
            if len(report.recommendations) > 3:
                print(f"    ... and {len(report.recommendations) - 3} more")

    # ========== TASK-BRIDGE-002: Checkpoint-Resume Methods ==========

    def _resume_from_checkpoint(self) -> None:
        """
        Restore state from checkpoint (TASK-BRIDGE-002).

        Loads saved orchestrator state and agent response (if available).
        Called during __init__ when config.resume is True.
        """
        print("\n🔄 Resuming from checkpoint...")

        # Load state
        state = self.state_manager.load_state()
        print(f"  Checkpoint: {state.checkpoint}")
        print(f"  Phase: {state.phase}")

        # Restore configuration
        for key, value in state.config.items():
            if hasattr(self.config, key):
                # Convert Path strings back to Path objects
                if key in ('codebase_path', 'output_path') and value is not None:
                    value = Path(value)
                setattr(self.config, key, value)

        # Restore phase data
        phase_data = state.phase_data

        self.qa_answers = phase_data.get("qa_answers")

        # Deserialize analysis (Pydantic model)
        if "analysis" in phase_data and phase_data["analysis"] is not None:
            self.analysis = self._deserialize_analysis(phase_data["analysis"])

        # Restore other phase results
        self.manifest = self._deserialize_manifest(phase_data.get("manifest"))
        self.settings = self._deserialize_settings(phase_data.get("settings"))

        if "templates" in phase_data and phase_data["templates"]:
            self.templates = self._deserialize_templates(phase_data["templates"])

        self.agent_inventory = phase_data.get("agent_inventory")

        if "agents" in phase_data and phase_data["agents"]:
            self.agents = self._deserialize_agents(phase_data["agents"])

        # Load agent response if available
        try:
            response = self.agent_invoker.load_response()
            print(f"  ✓ Agent response loaded successfully")
        except FileNotFoundError:
            print(f"  ⚠️  No agent response found")
            print(f"  → Will fall back to hard-coded detection")
        except Exception as e:
            print(f"  ⚠️  Failed to load agent response: {e}")
            print(f"  → Will fall back to hard-coded detection")

    def _save_checkpoint(self, checkpoint: str, phase: int) -> None:
        """
        Save current state to checkpoint (TASK-BRIDGE-002).

        Called before Phase 6 to enable resume after agent invocation.

        Args:
            checkpoint: Checkpoint name (e.g., "templates_generated")
            phase: Current phase number
        """
        # Serialize phase data
        phase_data = {
            "qa_answers": self.qa_answers,
            "analysis": self._serialize_analysis(self.analysis),
            "manifest": self._serialize_manifest(self.manifest),
            "settings": self._serialize_settings(self.settings),
            "templates": self._serialize_templates(self.templates),
            "agent_inventory": self.agent_inventory,
            "agents": self._serialize_agents(self.agents)
        }

        # Serialize config
        config_dict = {}
        for key, value in self.config.__dict__.items():
            # Convert Path objects to strings for JSON serialization
            if isinstance(value, Path):
                config_dict[key] = str(value)
            else:
                config_dict[key] = value

        # Save state
        self.state_manager.save_state(
            checkpoint=checkpoint,
            phase=phase,
            config=config_dict,
            phase_data=phase_data
        )

        print(f"  💾 State saved (checkpoint: {checkpoint})")

    def _serialize_analysis(self, analysis: Any) -> Optional[dict]:
        """Serialize CodebaseAnalysis to dict."""
        if analysis is None:
            return None
        # Use Pydantic's model_dump for serialization
        if hasattr(analysis, 'model_dump'):
            return analysis.model_dump(mode='json')
        elif hasattr(analysis, '__dict__'):
            return analysis.__dict__
        return None

    def _deserialize_analysis(self, data: dict) -> Any:
        """Deserialize dict back to CodebaseAnalysis."""
        if data is None:
            return None
        # Use Pydantic's model_validate for deserialization
        _models_module = importlib.import_module('lib.codebase_analyzer.models')
        CodebaseAnalysis = _models_module.CodebaseAnalysis
        try:
            return CodebaseAnalysis.model_validate(data)
        except Exception as e:
            self._print_warning(f"Failed to deserialize analysis: {e}")
            return None

    def _serialize_manifest(self, manifest: Any) -> Optional[dict]:
        """Serialize manifest to dict."""
        if manifest is None:
            return None
        if hasattr(manifest, 'to_dict'):
            return manifest.to_dict()
        elif hasattr(manifest, '__dict__'):
            manifest_dict = manifest.__dict__.copy()
            # Convert Path and datetime objects to strings for JSON serialization
            for key, value in manifest_dict.items():
                if isinstance(value, Path):
                    manifest_dict[key] = str(value)
                elif isinstance(value, datetime):
                    manifest_dict[key] = value.isoformat()
            return manifest_dict
        return None

    def _deserialize_manifest(self, data: Optional[dict]) -> Any:
        """Deserialize dict back to manifest."""
        if data is None:
            return None
        # Return as dict for now, actual class reconstruction happens in phases
        return type('Manifest', (), data)()

    def _serialize_settings(self, settings: Any) -> Optional[dict]:
        """Serialize settings to dict."""
        if settings is None:
            return None
        if hasattr(settings, 'to_dict'):
            return settings.to_dict()
        elif hasattr(settings, '__dict__'):
            settings_dict = settings.__dict__.copy()
            # Convert Path and datetime objects to strings for JSON serialization
            for key, value in settings_dict.items():
                if isinstance(value, Path):
                    settings_dict[key] = str(value)
                elif isinstance(value, datetime):
                    settings_dict[key] = value.isoformat()
            return settings_dict
        return None

    def _deserialize_settings(self, data: Optional[dict]) -> Any:
        """Deserialize dict back to settings."""
        if data is None:
            return None
        # Return as dict for now, actual class reconstruction happens in phases
        return type('Settings', (), data)()

    def _serialize_templates(self, templates: Any) -> Optional[dict]:
        """Serialize TemplateCollection to dict."""
        if templates is None:
            return None
        if hasattr(templates, '__dict__'):
            # Serialize TemplateCollection
            result = {
                'total_count': getattr(templates, 'total_count', 0),
                'templates': []
            }

            # Handle generated_at datetime field if present
            if hasattr(templates, 'generated_at'):
                generated_at = getattr(templates, 'generated_at')
                if isinstance(generated_at, datetime):
                    result['generated_at'] = generated_at.isoformat()
                else:
                    result['generated_at'] = generated_at

            # Serialize individual templates
            for tmpl in getattr(templates, 'templates', []):
                tmpl_dict = {}
                if hasattr(tmpl, '__dict__'):
                    tmpl_dict = tmpl.__dict__.copy()
                    # Convert Path and datetime objects to strings for JSON serialization
                    for key, value in tmpl_dict.items():
                        if isinstance(value, Path):
                            tmpl_dict[key] = str(value)
                        elif isinstance(value, datetime):
                            tmpl_dict[key] = value.isoformat()
                result['templates'].append(tmpl_dict)
            return result
        return None

    def _deserialize_templates(self, data: Optional[dict]) -> Any:
        """Deserialize dict back to TemplateCollection."""
        if data is None:
            return None
        # Return as object with attributes
        templates_obj = type('TemplateCollection', (), {
            'total_count': data.get('total_count', 0),
            'templates': []
        })()

        # Reconstruct template objects
        for tmpl_dict in data.get('templates', []):
            tmpl_obj = type('Template', (), tmpl_dict)()
            templates_obj.templates.append(tmpl_obj)

        return templates_obj

    def _serialize_value(self, value: Any, visited: Optional[set] = None) -> Any:
        """
        Recursively serialize a value for JSON storage with cycle detection (DRY principle).

        Architectural Context:
        - Centralizes type conversion logic for checkpoint serialization
        - Handles Path, datetime, Enum, nested structures uniformly
        - Prevents duplication across multiple serialize_* methods
        - Supports deep nesting (dicts, lists, objects)
        - Prevents infinite recursion via cycle detection

        Conversion Rules:
        - Path → str (for JSON compatibility)
        - datetime → ISO 8601 string
        - Enum → value attribute
        - Object with to_dict() → dict (Pydantic models)
        - Object with __dict__ → dict (regular classes)
        - dict → recursively serialize values
        - list → recursively serialize items
        - Circular references → string representation
        - Other → pass through unchanged

        Args:
            value: Value to serialize
            visited: Set of object IDs already visited (for cycle detection)

        Returns:
            JSON-serializable value

        TASK-PHASE-7-5-FIX-FOUNDATION: DRY improvement (+6 SOLID points)
        """
        from enum import Enum as EnumType

        # Initialize visited set on first call
        if visited is None:
            visited = set()

        # Handle None
        if value is None:
            return None

        # Handle primitives (str, int, float, bool) - pass through unchanged
        if isinstance(value, (str, int, float, bool)):
            return value

        # Cycle detection for complex objects
        obj_id = id(value)
        if obj_id in visited:
            # Return string representation for circular references
            logger.debug(f"Circular reference detected for {type(value).__name__}")
            return f"<circular-ref-{type(value).__name__}>"

        # Add to visited set for complex types (not primitives or collections)
        if not isinstance(value, (list, dict, tuple, set)):
            visited.add(obj_id)

        # Handle Path objects
        if isinstance(value, Path):
            return str(value)

        # Handle datetime objects
        if isinstance(value, datetime):
            return value.isoformat()

        # Handle Enum objects
        if isinstance(value, EnumType):
            return value.value

        # Handle Mock objects explicitly (BEFORE to_dict check)
        # NOTE: Mock objects from unittest.mock have complex internal structure
        # and respond to hasattr() calls, so check for them early.
        # Return string representation instead of attempting serialization.
        if type(value).__module__ == 'unittest.mock':
            # Extract mock name if available for better debugging
            mock_name = getattr(value, '_mock_name', None) or 'unnamed'
            return f"<Mock:{mock_name}>"

        # Handle objects with to_dict() method (Pydantic models)
        if hasattr(value, 'to_dict') and callable(getattr(value, 'to_dict')):
            return self._serialize_value(value.to_dict(), visited)

        # Handle objects with __dict__ attribute (regular classes)
        if hasattr(value, '__dict__'):
            result = {}
            for key, val in value.__dict__.items():
                # Skip private attributes (start with _)
                # This avoids Mock framework internals and reduces serialization overhead
                if key.startswith('_'):
                    continue
                result[key] = self._serialize_value(val, visited)
            return result

        # Handle dictionaries (recursively serialize values)
        if isinstance(value, dict):
            result = {}
            for key, val in value.items():
                result[key] = self._serialize_value(val, visited)
            return result

        # Handle lists (recursively serialize items)
        if isinstance(value, list):
            return [self._serialize_value(item, visited) for item in value]

        # Handle tuples (convert to list, recursively serialize)
        if isinstance(value, tuple):
            return [self._serialize_value(item, visited) for item in value]

        # Handle sets (convert to list, recursively serialize)
        if isinstance(value, set):
            return [self._serialize_value(item, visited) for item in value]

        # Fallback: convert to string (don't recurse on unknown types)
        logger.debug(f"Unknown type {type(value)}, converting to string")
        return str(value)

    def _serialize_agents(self, agents: List[Any]) -> Optional[dict]:
        """
        Serialize agents list to dict.

        Now uses _serialize_value() for consistent type handling.

        TASK-PHASE-7-5-FIX-FOUNDATION: DRY improvement
        """
        if not agents:
            return None

        return {
            'agents': [self._serialize_value(agent) for agent in agents]
        }

    def _deserialize_agents(self, data: Optional[dict]) -> List[Any]:
        """Deserialize dict back to agents list."""
        if data is None:
            return []

        agents_list = []

        # Reconstruct agent objects
        for agent_dict in data.get('agents', []):
            agent_obj = type('Agent', (), agent_dict)()
            agents_list.append(agent_obj)

        return agents_list


# Convenience function for command usage
def run_template_create(
    codebase_path: Optional[Path] = None,
    output_path: Optional[Path] = None,  # DEPRECATED: Use output_location instead
    output_location: str = 'global',  # TASK-068: 'global' or 'repo'
    skip_qa: bool = False,  # DEPRECATED (TASK-9039): Now always uses smart defaults
    config_file: Optional[Path] = None,  # TASK-9039: Optional config file path
    max_templates: Optional[int] = None,
    dry_run: bool = False,
    save_analysis: bool = False,
    no_agents: bool = False,
    validate: bool = False,
    create_agent_tasks: bool = True,  # TASK-UX-3A8D: Default ON (opt-out via --no-create-agent-tasks)
    resume: bool = False,  # TASK-BRIDGE-002: Resume from checkpoint
    custom_name: Optional[str] = None,  # TASK-FDB2: Custom template name override
    verbose: bool = False
) -> OrchestrationResult:
    """
    Convenience function to run template creation.

    Args:
        codebase_path: Path to codebase to analyze
        output_path: DEPRECATED - Output directory for template package (use output_location)
        output_location: 'global' (default, ~/.agentecflow/templates/) or 'repo' (installer/global/templates/)
        skip_qa: DEPRECATED (TASK-9039) - Now always uses smart defaults
        config_file: Optional path to config file (TASK-9039)
        max_templates: Maximum template files to generate
        dry_run: Analyze and show plan without saving
        save_analysis: Save analysis JSON for debugging
        no_agents: Skip agent generation
        validate: Run extended validation and generate quality report
        create_agent_tasks: Create individual enhancement tasks for each agent (TASK-PHASE-8-INCREMENTAL)
        custom_name: Custom template name (overrides AI-generated name)
        verbose: Show detailed progress

    Returns:
        OrchestrationResult

    Example (personal use with smart defaults):
        result = run_template_create(
            codebase_path=Path("~/projects/my-app")
        )
        # Creates in ~/.agentecflow/templates/ (immediately available)
        # Uses smart defaults from project detection

    Example (with config file):
        result = run_template_create(
            codebase_path=Path("~/projects/my-app"),
            config_file=Path(".template-create-config.json")
        )
        # Uses config file to override defaults

    Example (distribution):
        result = run_template_create(
            codebase_path=Path("~/projects/my-app"),
            output_location='repo'
        )
        # Creates in installer/global/templates/ (for version control)

        if result.success:
            print(f"Template created: {result.output_path}")
        else:
            print(f"Failed: {result.errors}")
    """
    # TASK-51B2: skip_qa and config_file removed (AI-native workflow)
    # skip_qa parameter kept for backward compatibility but ignored
    # config_file parameter kept for backward compatibility but ignored
    config = OrchestrationConfig(
        codebase_path=codebase_path,
        output_path=output_path,
        output_location=output_location,
        max_templates=max_templates,
        dry_run=dry_run,
        save_analysis=save_analysis,
        no_agents=no_agents,
        validate=validate,
        create_agent_tasks=create_agent_tasks,  # TASK-PHASE-8-INCREMENTAL
        resume=resume,  # TASK-BRIDGE-002
        custom_name=custom_name,  # TASK-FDB2
        verbose=verbose
    )

    orchestrator = TemplateCreateOrchestrator(config)
    return orchestrator.run()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Template creation orchestrator")
    parser.add_argument("--path", type=str, help="Codebase path")
    parser.add_argument("--name", type=str,
                        help="Custom template name (overrides AI-generated name)")
    parser.add_argument("--output-location", choices=['global', 'repo'], default='global',
                        help="Output location: 'global' (~/.agentecflow/templates/) or 'repo' (installer/global/templates/)")
    parser.add_argument("--skip-qa", action="store_true",
                        help="DEPRECATED: Now always uses smart defaults")
    parser.add_argument("--config", type=str,
                        help="Path to config file (TASK-9039)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Analyze and show plan without saving")
    parser.add_argument("--validate", action="store_true",
                        help="Run extended validation and generate quality report")
    parser.add_argument("--max-templates", type=int,
                        help="Maximum template files to generate")
    parser.add_argument("--no-agents", action="store_true",
                        help="Skip agent generation")
    parser.add_argument("--create-agent-tasks", action="store_true", default=True,
                        dest="create_agent_tasks",
                        help="Create individual enhancement tasks for each agent (default: enabled)")
    parser.add_argument("--no-create-agent-tasks", action="store_false",
                        dest="create_agent_tasks",
                        help="Skip agent task creation (opt-out from default behavior)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from checkpoint after agent invocation")
    parser.add_argument("--verbose", action="store_true",
                        help="Show detailed progress")

    args = parser.parse_args()

    result = run_template_create(
        codebase_path=Path(args.path) if args.path else None,
        output_location=args.output_location,
        skip_qa=args.skip_qa,
        config_file=Path(args.config) if args.config else None,  # TASK-9039
        dry_run=args.dry_run,
        validate=args.validate,
        max_templates=args.max_templates,
        no_agents=args.no_agents,
        create_agent_tasks=args.create_agent_tasks,
        resume=args.resume,
        custom_name=args.name,  # TASK-FDB2
        verbose=args.verbose
    )

    sys.exit(result.exit_code if not result.success else 0)
