"""
Template Create Orchestrator

Orchestrates complete template creation workflow from existing codebases.
Coordinates Q&A, AI analysis, and component generation phases.

TASK-010: /template-create Command Orchestrator
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import json
import logging

# Import component modules using importlib to avoid 'global' keyword issue
import importlib
_template_qa_module = importlib.import_module('installer.global.commands.lib.template_qa_session')
_codebase_analyzer_module = importlib.import_module('installer.global.lib.codebase_analyzer.ai_analyzer')
_manifest_gen_module = importlib.import_module('installer.global.lib.template_creation.manifest_generator')
_settings_gen_module = importlib.import_module('installer.global.lib.settings_generator.generator')
_claude_md_gen_module = importlib.import_module('installer.global.lib.template_generator.claude_md_generator')
_template_gen_module = importlib.import_module('installer.global.lib.template_generator.template_generator')
_agent_gen_module = importlib.import_module('installer.global.lib.agent_generator.agent_generator')

TemplateQASession = _template_qa_module.TemplateQASession
CodebaseAnalyzer = _codebase_analyzer_module.CodebaseAnalyzer
ManifestGenerator = _manifest_gen_module.ManifestGenerator
SettingsGenerator = _settings_gen_module.SettingsGenerator
ClaudeMdGenerator = _claude_md_gen_module.ClaudeMdGenerator
TemplateGenerator = _template_gen_module.TemplateGenerator
AIAgentGenerator = _agent_gen_module.AIAgentGenerator

# TASK-BRIDGE-002: Agent Bridge Integration
_agent_bridge_invoker_module = importlib.import_module('installer.global.lib.agent_bridge.invoker')
_agent_bridge_state_module = importlib.import_module('installer.global.lib.agent_bridge.state_manager')
AgentBridgeInvoker = _agent_bridge_invoker_module.AgentBridgeInvoker
StateManager = _agent_bridge_state_module.StateManager
TemplateCreateState = _agent_bridge_state_module.TemplateCreateState

# TASK-040: Phase 5.5 Completeness Validation
_validator_module = importlib.import_module('installer.global.lib.template_generator.completeness_validator')
_models_module = importlib.import_module('installer.global.lib.template_generator.models')
CompletenessValidator = _validator_module.CompletenessValidator
ValidationReport = _models_module.ValidationReport
TemplateCollection = _models_module.TemplateCollection

# TASK-043: Phase 5.7 Extended Validation
_extended_validator_module = importlib.import_module('installer.global.lib.template_generator.extended_validator')
_report_generator_module = importlib.import_module('installer.global.lib.template_generator.report_generator')
ExtendedValidator = _extended_validator_module.ExtendedValidator
ExtendedValidationReport = _extended_validator_module.ExtendedValidationReport
ValidationReportGenerator = _report_generator_module.ValidationReportGenerator


logger = logging.getLogger(__name__)


@dataclass
class OrchestrationConfig:
    """Configuration for template creation orchestration"""
    codebase_path: Optional[Path] = None
    output_path: Optional[Path] = None  # DEPRECATED: Use output_location instead
    output_location: str = 'global'  # TASK-068: 'global' or 'repo'
    skip_qa: bool = False
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
    7. CLAUDE.md generation (TASK-007) [REORDERED - was Phase 5]
       ↑ NOW agents exist and can be documented accurately
    8. Template package assembly

    Phase Reordering (TASK-019A):
    - Agents are now created BEFORE CLAUDE.md generation
    - Eliminates AI hallucinations about non-existent agents
    - CLAUDE.md now scans and documents actual agent files

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
            phase=6,
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
        If config.resume is True, skips to Phase 6 (agent generation).
        Otherwise, executes all phases 1-8 from start.

        Returns:
            OrchestrationResult with success status and generated artifacts
        """
        try:
            # If resuming, skip to Phase 6
            if self.config.resume:
                return self._run_from_phase_6()

            # Normal execution: Phases 1-8
            return self._run_all_phases()

        except KeyboardInterrupt:
            self._print_info("\n\nTemplate creation interrupted.")
            return self._create_error_result("User interrupted")
        except Exception as e:
            logger.exception("Unexpected error in orchestration")
            return self._create_error_result(f"Unexpected error: {e}")

    def _run_all_phases(self) -> OrchestrationResult:
        """
        Execute phases 1-8 from start (TASK-BRIDGE-002).

        Saves checkpoint before Phase 6 to enable resume after agent invocation.

        Returns:
            OrchestrationResult with success status and generated artifacts
        """
        self._print_header()

        # Phase 1: Q&A Session
        self.qa_answers = self._phase1_qa_session()
        if not self.qa_answers:
            return self._create_error_result("Q&A session cancelled or failed")

        # Phase 2: AI Analysis
        self.analysis = self._phase2_ai_analysis(self.qa_answers)
        if not self.analysis:
            return self._create_error_result("AI analysis failed")

        # Save analysis if requested
        if self.config.save_analysis:
            self._save_analysis_json(self.analysis)

        # Phase 3: Manifest Generation
        self.manifest = self._phase3_manifest_generation(self.analysis)
        if not self.manifest:
            return self._create_error_result("Manifest generation failed")

        # Phase 4: Settings Generation
        self.settings = self._phase4_settings_generation(self.analysis)
        if not self.settings:
            return self._create_error_result("Settings generation failed")

        # Phase 5: Template File Generation (reordered - was Phase 6)
        self.templates = self._phase5_template_generation(self.analysis)
        if not self.templates:
            self.warnings.append("No template files generated")

        # ===== Phase 5.5: Completeness Validation (TASK-040) =====
        if not self.config.skip_validation and self.templates:
            self.templates = self._phase5_5_completeness_validation(
                templates=self.templates,
                analysis=self.analysis
            )

        # IMPORTANT: Save state before Phase 6
        # (Phase 6 may exit with code 42 to request agent invocation)
        self._save_checkpoint("templates_generated", phase=5)

        # Phase 6: Agent Recommendation (may exit with code 42)
        self.agents = []
        if not self.config.no_agents:
            self.agents = self._phase6_agent_recommendation(self.analysis)

        # Phase 7-8: Complete workflow
        return self._complete_workflow()

    def _run_from_phase_6(self) -> OrchestrationResult:
        """
        Continue from Phase 6 after agent invocation (TASK-BRIDGE-002).

        State has been restored in __init__, now complete the workflow.

        Returns:
            OrchestrationResult with success status and generated artifacts
        """
        self._print_header()
        print("  (Resuming from checkpoint)")

        # Phase 6: Complete agent generation with loaded response
        self.agents = []
        if not self.config.no_agents:
            self.agents = self._phase6_agent_recommendation(self.analysis)

        # Phase 7-8: Complete workflow
        return self._complete_workflow()

    def _complete_workflow(self) -> OrchestrationResult:
        """
        Complete phases 7-8 (TASK-BRIDGE-002).

        Shared by both _run_all_phases and _run_from_phase_6.

        Returns:
            OrchestrationResult with success status and generated artifacts
        """
        # Phase 7: CLAUDE.md Generation (reordered - was Phase 5)
        # NOW agents exist and can be documented accurately
        self.claude_md = self._phase7_claude_md_generation(self.analysis, self.agents)
        if not self.claude_md:
            return self._create_error_result("CLAUDE.md generation failed")

        # Phase 8: Template Package Assembly
        if self.config.dry_run:
            self._print_dry_run_summary(self.manifest, self.settings, self.templates, self.agents)
            return self._create_dry_run_result(self.manifest, len(self.templates.templates if self.templates else []), len(self.agents))

        output_path = self._phase8_package_assembly(
            manifest=self.manifest,
            settings=self.settings,
            claude_md=self.claude_md,
            templates=self.templates,
            agents=self.agents
        )

        if not output_path:
            return self._create_error_result("Package assembly failed")

        # ===== Phase 5.7: Extended Validation (TASK-043) =====
        # Run after package assembly when all files are in place
        validation_report_path = None
        exit_code = 0
        if self.config.validate and self.templates:
            validation_report_path, exit_code = self._phase5_7_extended_validation(
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

    def _phase1_qa_session(self) -> Optional[Dict[str, Any]]:
        """
        Phase 1: Run Q&A session to gather context.

        Returns:
            Dictionary with Q&A answers or None if cancelled
        """
        self._print_phase_header("Phase 1: Q&A Session")

        try:
            qa_session = TemplateQASession(skip_qa=self.config.skip_qa)
            answers = qa_session.run()

            if not answers:
                self._print_error("Q&A session cancelled")
                return None

            self._print_success_line("Q&A complete")

            # Convert to dictionary for downstream use
            return answers.to_dict() if hasattr(answers, 'to_dict') else vars(answers)

        except Exception as e:
            self._print_error(f"Q&A session failed: {e}")
            logger.exception("Q&A session error")
            return None

    def _phase2_ai_analysis(self, qa_answers: Dict[str, Any]) -> Optional[Any]:
        """
        Phase 2: Analyze codebase with AI.

        Args:
            qa_answers: Answers from Q&A session

        Returns:
            CodebaseAnalysis or None if failed
        """
        self._print_phase_header("Phase 2: AI Codebase Analysis")

        try:
            # Get codebase path from config or Q&A
            codebase_path = self.config.codebase_path or Path(qa_answers.get('codebase_path', '.'))

            if not codebase_path.exists():
                self._print_error(f"Codebase path does not exist: {codebase_path}")
                return None

            # Build template context from Q&A
            template_context = {
                'name': qa_answers.get('template_name', 'unknown'),
                'language': qa_answers.get('primary_language', 'unknown'),
                'framework': qa_answers.get('framework', ''),
                'architecture': qa_answers.get('architecture_pattern', ''),
                'purpose': qa_answers.get('template_purpose', '')
            }

            # Run analyzer
            analyzer = CodebaseAnalyzer(max_files=10)

            self._print_info(f"  Analyzing: {codebase_path}")
            analysis = analyzer.analyze_codebase(
                codebase_path=codebase_path,
                template_context=template_context,
                save_results=False
            )

            self._print_success_line(f"Analysis complete (confidence: {analysis.overall_confidence.percentage}%)")

            return analysis

        except Exception as e:
            self._print_error(f"Analysis failed: {e}")
            logger.exception("Analysis error")
            return None

    def _phase3_manifest_generation(self, analysis: Any) -> Optional[Any]:
        """
        Phase 3: Generate manifest.json.

        Args:
            analysis: CodebaseAnalysis from phase 2

        Returns:
            TemplateManifest or None if failed
        """
        self._print_phase_header("Phase 3: Manifest Generation")

        try:
            generator = ManifestGenerator(analysis)
            manifest = generator.generate()

            self._print_success_line(f"Template: {manifest.name}")
            self._print_info(f"  Language: {manifest.language} ({manifest.language_version or 'any version'})")
            self._print_info(f"  Architecture: {manifest.architecture}")
            self._print_info(f"  Complexity: {manifest.complexity}/10")

            return manifest

        except Exception as e:
            self._print_error(f"Manifest generation failed: {e}")
            logger.exception("Manifest generation error")
            return None

    def _phase4_settings_generation(self, analysis: Any) -> Optional[Any]:
        """
        Phase 4: Generate settings.json.

        Args:
            analysis: CodebaseAnalysis from phase 2

        Returns:
            TemplateSettings or None if failed
        """
        self._print_phase_header("Phase 4: Settings Generation")

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

    def _phase5_template_generation(self, analysis: Any) -> Optional[Any]:
        """
        Phase 5: Generate .template files (reordered - was Phase 6).

        Args:
            analysis: CodebaseAnalysis from phase 2

        Returns:
            TemplateCollection or None if failed
        """
        self._print_phase_header("Phase 5: Template File Generation")

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

    def _phase6_agent_recommendation(self, analysis: Any) -> List[Any]:
        """
        Phase 6: Recommend and generate custom agents (reordered - was Phase 7).

        TASK-BRIDGE-002: Modified to pass AgentBridgeInvoker to generator.
        May exit with code 42 if agent invocation needed.

        Args:
            analysis: CodebaseAnalysis from phase 2

        Returns:
            List of GeneratedAgent objects
        """
        self._print_phase_header("Phase 6: Agent Recommendation")

        try:
            # Import agent scanner to get inventory
            _agent_scanner_module = importlib.import_module('installer.global.lib.agent_scanner')
            scan_agents = _agent_scanner_module.scan_agents

            inventory = scan_agents()

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

    def _phase7_claude_md_generation(self, analysis: Any, agents: List[Any]) -> Optional[Any]:
        """
        Phase 7: Generate CLAUDE.md (reordered - was Phase 5).

        NOW runs AFTER agents are generated, so it can document actual agents
        instead of hallucinating non-existent ones.

        Args:
            analysis: CodebaseAnalysis from phase 2
            agents: List of GeneratedAgent objects from phase 6

        Returns:
            TemplateClaude or None if failed
        """
        self._print_phase_header("Phase 7: CLAUDE.md Generation")

        try:
            # Pass agents to generator for accurate documentation
            generator = ClaudeMdGenerator(analysis, agents=agents)
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

    def _phase5_5_completeness_validation(
        self,
        templates: TemplateCollection,
        analysis: Any
    ) -> TemplateCollection:
        """
        Phase 5.5: Completeness Validation (TASK-040).

        Validates template completeness and optionally auto-fixes issues.

        Args:
            templates: TemplateCollection to validate
            analysis: CodebaseAnalysis for context

        Returns:
            Updated TemplateCollection (possibly with auto-generated templates)
        """
        self._print_phase_header("Phase 5.5: Completeness Validation")

        try:
            # Create validator
            validator = CompletenessValidator()

            # Run validation
            self._print_info("  Validating template completeness...")
            validation_report = validator.validate(templates, analysis)

            # TASK-043: Store Phase 5.5 report for Phase 5.7 extended validation
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

    def _phase8_package_assembly(
        self,
        manifest: Any,
        settings: Any,
        claude_md: Any,
        templates: Any,
        agents: List[Any]
    ) -> Optional[Path]:
        """
        Phase 8: Assemble complete template package.

        Args:
            manifest: TemplateManifest
            settings: TemplateSettings
            claude_md: TemplateClaude
            templates: TemplateCollection
            agents: List of GeneratedAgent

        Returns:
            Path to output directory or None if failed
        """
        self._print_phase_header("Phase 8: Package Assembly")

        try:
            # TASK-068: Determine output path based on output_location
            if self.config.output_path:
                # Legacy support: if output_path is explicitly set, use it
                output_path = self.config.output_path
                location_type = "custom"
            elif self.config.output_location == 'repo':
                # Write to repository location for distribution
                output_path = Path("installer/global/templates") / manifest.name
                location_type = "distribution"
            else:
                # Default: Write to global location for immediate use
                output_path = Path.home() / ".agentecflow" / "templates" / manifest.name
                location_type = "personal"

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
                template_gen = TemplateGenerator(None, None)
                template_gen.save_templates(templates, output_path)
                self._print_success_line(f"templates/ ({templates.total_count} files)")

            # Save agent files
            if agents:
                agents_dir = output_path / "agents"
                agents_dir.mkdir(exist_ok=True)

                for agent in agents:
                    agent_path = agents_dir / f"{agent.name}.md"
                    agent_path.write_text(agent.full_definition, encoding='utf-8')

                self._print_success_line(f"agents/ ({len(agents)} agents)")

            return output_path

        except Exception as e:
            self._print_error(f"Package assembly failed: {e}")
            logger.exception("Package assembly error")
            return None

    def _save_analysis_json(self, analysis: Any) -> None:
        """Save analysis to JSON for debugging."""
        try:
            _serializer_module = importlib.import_module('installer.global.lib.codebase_analyzer.serializer')
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

    def _phase5_7_extended_validation(
        self,
        templates: TemplateCollection,
        manifest: Any,
        settings: Any,
        claude_md_path: Path,
        agents: List[Any],
        output_path: Path
    ) -> Tuple[Path, int]:
        """
        Phase 5.7: Extended Validation (TASK-043).

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
        self._print_phase_header("Phase 5.7: Extended Validation")

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
            "agent_inventory": self.agent_inventory
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
        _models_module = importlib.import_module('installer.global.lib.codebase_analyzer.models')
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
            return manifest.__dict__
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
            return settings.__dict__
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
            # Serialize individual templates
            for tmpl in getattr(templates, 'templates', []):
                tmpl_dict = {}
                if hasattr(tmpl, '__dict__'):
                    tmpl_dict = tmpl.__dict__.copy()
                    # Convert Path objects to strings
                    for key, value in tmpl_dict.items():
                        if isinstance(value, Path):
                            tmpl_dict[key] = str(value)
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


# Convenience function for command usage
def run_template_create(
    codebase_path: Optional[Path] = None,
    output_path: Optional[Path] = None,  # DEPRECATED: Use output_location instead
    output_location: str = 'global',  # TASK-068: 'global' or 'repo'
    skip_qa: bool = False,
    max_templates: Optional[int] = None,
    dry_run: bool = False,
    save_analysis: bool = False,
    no_agents: bool = False,
    validate: bool = False,
    resume: bool = False,  # TASK-BRIDGE-002: Resume from checkpoint
    verbose: bool = False
) -> OrchestrationResult:
    """
    Convenience function to run template creation.

    Args:
        codebase_path: Path to codebase to analyze
        output_path: DEPRECATED - Output directory for template package (use output_location)
        output_location: 'global' (default, ~/.agentecflow/templates/) or 'repo' (installer/global/templates/)
        skip_qa: Skip interactive Q&A
        max_templates: Maximum template files to generate
        dry_run: Analyze and show plan without saving
        save_analysis: Save analysis JSON for debugging
        no_agents: Skip agent generation
        validate: Run extended validation and generate quality report
        verbose: Show detailed progress

    Returns:
        OrchestrationResult

    Example (personal use):
        result = run_template_create(
            codebase_path=Path("~/projects/my-app")
        )
        # Creates in ~/.agentecflow/templates/ (immediately available)

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
    config = OrchestrationConfig(
        codebase_path=codebase_path,
        output_path=output_path,
        output_location=output_location,
        skip_qa=skip_qa,
        max_templates=max_templates,
        dry_run=dry_run,
        save_analysis=save_analysis,
        no_agents=no_agents,
        validate=validate,
        resume=resume,  # TASK-BRIDGE-002
        verbose=verbose
    )

    orchestrator = TemplateCreateOrchestrator(config)
    return orchestrator.run()
