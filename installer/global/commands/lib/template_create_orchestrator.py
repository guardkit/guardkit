"""
Template Create Orchestrator

Orchestrates complete template creation workflow from existing codebases.
Coordinates Q&A, AI analysis, and component generation phases.

TASK-010: /template-create Command Orchestrator
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import logging

# Import component modules
from installer.global.commands.lib.template_qa_session import TemplateQASession
from installer.global.lib.codebase_analyzer.ai_analyzer import CodebaseAnalyzer
from installer.global.lib.template_creation.manifest_generator import ManifestGenerator
from installer.global.lib.settings_generator.generator import SettingsGenerator
from installer.global.lib.template_generator.claude_md_generator import ClaudeMdGenerator
from installer.global.lib.template_generator.template_generator import TemplateGenerator
from installer.global.lib.agent_generator.agent_generator import AIAgentGenerator

# TASK-040: Phase 5.5 Completeness Validation
import importlib
_validator_module = importlib.import_module('installer.global.lib.template_generator.completeness_validator')
_models_module = importlib.import_module('installer.global.lib.template_generator.models')
CompletenessValidator = _validator_module.CompletenessValidator
ValidationReport = _models_module.ValidationReport
TemplateCollection = _models_module.TemplateCollection


logger = logging.getLogger(__name__)


@dataclass
class OrchestrationConfig:
    """Configuration for template creation orchestration"""
    codebase_path: Optional[Path] = None
    output_path: Optional[Path] = None
    skip_qa: bool = False
    max_templates: Optional[int] = None
    dry_run: bool = False
    save_analysis: bool = False
    no_agents: bool = False
    verbose: bool = False
    skip_validation: bool = False  # TASK-040: Skip Phase 5.5 validation
    auto_fix_templates: bool = True  # TASK-040: Auto-fix completeness issues
    interactive_validation: bool = True  # TASK-040: Prompt user for validation decisions


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

        # Configure logging
        if config.verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

    def run(self) -> OrchestrationResult:
        """
        Execute complete template creation workflow.

        Returns:
            OrchestrationResult with success status and generated artifacts
        """
        try:
            self._print_header()

            # Phase 1: Q&A Session
            qa_answers = self._phase1_qa_session()
            if not qa_answers:
                return self._create_error_result("Q&A session cancelled or failed")

            # Phase 2: AI Analysis
            analysis = self._phase2_ai_analysis(qa_answers)
            if not analysis:
                return self._create_error_result("AI analysis failed")

            # Save analysis if requested
            if self.config.save_analysis:
                self._save_analysis_json(analysis)

            # Phase 3: Manifest Generation
            manifest = self._phase3_manifest_generation(analysis)
            if not manifest:
                return self._create_error_result("Manifest generation failed")

            # Phase 4: Settings Generation
            settings = self._phase4_settings_generation(analysis)
            if not settings:
                return self._create_error_result("Settings generation failed")

            # Phase 5: Template File Generation (reordered - was Phase 6)
            templates = self._phase5_template_generation(analysis)
            if not templates:
                self.warnings.append("No template files generated")

            # ===== Phase 5.5: Completeness Validation (TASK-040) =====
            if not self.config.skip_validation and templates:
                templates = self._phase5_5_completeness_validation(
                    templates=templates,
                    analysis=analysis
                )

            # Phase 6: Agent Recommendation (reordered - was Phase 7)
            agents = []
            if not self.config.no_agents:
                agents = self._phase6_agent_recommendation(analysis)

            # Phase 7: CLAUDE.md Generation (reordered - was Phase 5)
            # NOW agents exist and can be documented accurately
            claude_md = self._phase7_claude_md_generation(analysis, agents)
            if not claude_md:
                return self._create_error_result("CLAUDE.md generation failed")

            # Phase 8: Template Package Assembly
            if self.config.dry_run:
                self._print_dry_run_summary(manifest, settings, templates, agents)
                return self._create_dry_run_result(manifest, len(templates.templates if templates else []), len(agents))

            output_path = self._phase8_package_assembly(
                manifest=manifest,
                settings=settings,
                claude_md=claude_md,
                templates=templates,
                agents=agents
            )

            if not output_path:
                return self._create_error_result("Package assembly failed")

            # Success!
            self._print_success(output_path, manifest, templates, agents)

            return OrchestrationResult(
                success=True,
                template_name=manifest.name,
                output_path=output_path,
                manifest_path=output_path / "manifest.json",
                settings_path=output_path / "settings.json",
                claude_md_path=output_path / "CLAUDE.md",
                template_count=len(templates.templates) if templates else 0,
                agent_count=len(agents),
                confidence_score=manifest.confidence_score,
                errors=self.errors,
                warnings=self.warnings
            )

        except KeyboardInterrupt:
            self._print_info("\n\nTemplate creation interrupted.")
            return self._create_error_result("User interrupted")
        except Exception as e:
            logger.exception("Unexpected error in orchestration")
            return self._create_error_result(f"Unexpected error: {e}")

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

        Args:
            analysis: CodebaseAnalysis from phase 2

        Returns:
            List of GeneratedAgent objects
        """
        self._print_phase_header("Phase 6: Agent Recommendation")

        try:
            # Import agent scanner to get inventory
            from installer.global.lib.agent_scanner import scan_agents

            inventory = scan_agents()
            generator = AIAgentGenerator(inventory)

            agents = generator.generate(analysis)

            if agents:
                self._print_info(f"  Generated {len(agents)} custom agents")
            else:
                self._print_info("  All capabilities covered by existing agents")

            return agents

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
            # Determine output path
            if self.config.output_path:
                output_path = self.config.output_path
            else:
                output_path = Path("./templates") / manifest.name

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
            from installer.global.lib.codebase_analyzer.serializer import AnalysisSerializer

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
        agents: List[Any]
    ) -> None:
        """Print success summary."""
        print("\n" + "="*60)
        print("  ✅ Template Package Created Successfully!")
        print("="*60)

        print(f"\nOutput: {output_path}/")
        print(f"  ├── manifest.json ({self._file_size(output_path / 'manifest.json')})")
        print(f"  ├── settings.json ({self._file_size(output_path / 'settings.json')})")
        print(f"  ├── CLAUDE.md ({self._file_size(output_path / 'CLAUDE.md')})")

        if templates:
            print(f"  ├── templates/ ({templates.total_count} files)")

        if agents:
            print(f"  └── agents/ ({len(agents)} agents)")

        print("\nNext steps:")
        print(f"1. Review generated files in {output_path}/")
        print(f"2. Test template with: taskwright init {manifest.name}")
        print("3. Share template with team or contribute to global library")

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


# Convenience function for command usage
def run_template_create(
    codebase_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    skip_qa: bool = False,
    max_templates: Optional[int] = None,
    dry_run: bool = False,
    save_analysis: bool = False,
    no_agents: bool = False,
    verbose: bool = False
) -> OrchestrationResult:
    """
    Convenience function to run template creation.

    Args:
        codebase_path: Path to codebase to analyze
        output_path: Output directory for template package
        skip_qa: Skip interactive Q&A
        max_templates: Maximum template files to generate
        dry_run: Analyze and show plan without saving
        save_analysis: Save analysis JSON for debugging
        no_agents: Skip agent generation
        verbose: Show detailed progress

    Returns:
        OrchestrationResult

    Example:
        result = run_template_create(
            codebase_path=Path("~/projects/my-app"),
            output_path=Path("./templates/my-template")
        )

        if result.success:
            print(f"Template created: {result.output_path}")
        else:
            print(f"Failed: {result.errors}")
    """
    config = OrchestrationConfig(
        codebase_path=codebase_path,
        output_path=output_path,
        skip_qa=skip_qa,
        max_templates=max_templates,
        dry_run=dry_run,
        save_analysis=save_analysis,
        no_agents=no_agents,
        verbose=verbose
    )

    orchestrator = TemplateCreateOrchestrator(config)
    return orchestrator.run()
