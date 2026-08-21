"""
Template Init Command - Main Orchestrator

Implements the /template-init command that orchestrates greenfield template
creation from user's technology choices (no existing codebase required).

Phases:
1. Q&A Session (TASK-001B)
2. AI Template Generation
3. Agent Setup (TASK-009)
4. Save Template
"""

import json
import sys
from pathlib import Path
from typing import Optional, Any

try:
    from .models import GreenfieldTemplate
    from .errors import (
        TemplateInitError,
        QASessionCancelledError,
        TemplateGenerationError,
        TemplateSaveError,
        AgentSetupError,
    )
    from .ai_generator import AITemplateGenerator
except ImportError:
    from models import GreenfieldTemplate
    from errors import (
        TemplateInitError,
        QASessionCancelledError,
        TemplateGenerationError,
        TemplateSaveError,
        AgentSetupError,
    )
    from ai_generator import AITemplateGenerator


class TemplateInitCommand:
    """Orchestrate greenfield template creation

    This command implements the complete workflow for creating a new template
    from scratch based on user's technology choices gathered through Q&A.

    Workflow:
        1. Phase 1: Run Q&A session (TASK-001B)
        2. Phase 2: AI generates template structure
        3. Phase 3: Set up agent system (TASK-009)
        4. Phase 4: Save template to disk

    Attributes:
        template_dir: Directory where templates are saved
        enable_external_agents: Enable external agent discovery (Phase 1: False)
    """

    def __init__(self, template_dir: Optional[Path] = None, enable_external_agents: bool = False, no_create_agent_tasks: bool = False, validate: bool = False, output_location: str = 'global', no_rules_structure: bool = False, claude_md_size_limit: int = 5000):
        """Initialize command

        Args:
            template_dir: Custom template directory (default: installer/local/templates/)
            enable_external_agents: Enable external agent discovery (default: False)
            no_create_agent_tasks: Skip agent enhancement task creation (default: False)
            validate: Run extended validation (Level 2) (default: False)
            output_location: Where to save template ('global' or 'repo')
            no_rules_structure: Skip rules structure generation (default: False)
            claude_md_size_limit: Maximum size for core CLAUDE.md in bytes (default: 5000)
        """
        # Regression fix 2026-08-21 (originally TASK-INIT-007, "two-location
        # output"): `template_dir` and `output_location` are two different ways
        # of saying where the finished template goes, and after that port they
        # disagreed. Remember whether the caller NAMED a directory, because an
        # explicitly named directory is the more specific instruction and wins;
        # otherwise the save path comes from `output_location`. See
        # _get_template_path().
        self._template_dir_explicit = template_dir is not None

        if template_dir is None:
            template_dir = Path("installer/local/templates")

        self.template_dir = template_dir
        self.enable_external_agents = enable_external_agents
        self.no_create_agent_tasks = no_create_agent_tasks
        self.validate = validate
        self.output_location = output_location
        self.no_rules_structure = no_rules_structure
        self.claude_md_size_limit = claude_md_size_limit

    def execute(self) -> bool:
        """Execute /template-init command

        Returns:
            True if template created successfully, False otherwise
        """
        try:
            self._show_header()

            # Phase 1: Q&A Session (TASK-001B)
            answers = self._phase1_qa_session()

            if not answers:
                print("\n⚠️  Template creation cancelled.\n")
                return False

            # Phase 2: AI Template Generation
            template = self._phase2_ai_generation(answers)

            # Phase 3: Agent Setup (TASK-009)
            agents = self._phase3_agent_setup(template)

            # Phase 4: Save Template
            template_path = self._phase4_save_template(template, agents)

            # Phase 4.5: Rules Structure Generation
            if not self.no_rules_structure:
                self._phase4_5_rules_structure_generation(template_path, answers)

            # Phase 5: Level 2 Extended Validation (Optional)
            exit_code = 0
            if self.validate:
                exit_code = self._phase5_extended_validation(template, template_path)

            # Phase 6: Create Agent Enhancement Tasks
            self._phase6_create_agent_tasks(template, template_path)

            # Success
            self._show_success(template, agents)

            return exit_code == 0 if self.validate else True

        except KeyboardInterrupt:
            print("\n\n⚠️  Template creation cancelled by user.\n")
            return False

        except QASessionCancelledError:
            print("\n\n⚠️  Q&A session cancelled.\n")
            return False

        except TemplateGenerationError as e:
            print(f"\n\n❌ Template generation failed: {e}\n")
            return False

        except TemplateSaveError as e:
            print(f"\n\n❌ Failed to save template: {e}\n")
            return False

        except AgentSetupError as e:
            print(f"\n\n❌ Agent setup failed: {e}\n")
            return False

        except Exception as e:
            print(f"\n\n❌ Template creation failed: {e}\n")
            import traceback
            traceback.print_exc()
            return False

    def _show_header(self) -> None:
        """Display command header"""
        print("\n" + "=" * 60)
        print("  /template-init - Greenfield Template Creation")
        print("=" * 60 + "\n")

    def _phase1_qa_session(self) -> Optional[Any]:
        """Phase 1: Run Q&A session (TASK-001B)

        Returns:
            GreenfieldAnswers if successful, None if cancelled

        Raises:
            QASessionCancelledError: If user cancels Q&A
        """
        print("=" * 60)
        print("  Phase 1: Q&A Session")
        print("=" * 60 + "\n")

        print("📋 Starting Q&A session...\n")

        try:
            # Import Q&A session from TASK-001B
            from ..template_qa_session import TemplateQASession

            qa = TemplateQASession()
            answers = qa.run()

            if not answers:
                raise QASessionCancelledError("User cancelled Q&A session")

            print("\n✅ Q&A session completed successfully\n")
            return answers

        except ImportError as e:
            # Fallback if Q&A session not available
            print(f"⚠️  Q&A session module not found: {e}")
            print("Using minimal Q&A for testing...\n")
            answers = self._minimal_qa_fallback()
            if not answers:
                raise QASessionCancelledError("User cancelled Q&A session")
            return answers

        except KeyboardInterrupt:
            raise QASessionCancelledError("User interrupted Q&A session")

    def _minimal_qa_fallback(self) -> Optional[Any]:
        """Minimal Q&A fallback for testing when full Q&A not available

        This is a temporary fallback for development/testing.
        Production should always use full TemplateQASession from TASK-001B.

        Returns:
            Minimal GreenfieldAnswers-like object
        """
        print("⚠️  Using minimal Q&A fallback (for testing only)")
        print("In production, full Q&A session from TASK-001B will be used.\n")

        # Minimal questions
        template_name = input("Template name: ").strip()
        if not template_name:
            return None

        template_purpose = input("Template purpose: ").strip()
        if not template_purpose:
            return None

        primary_language = input("Primary language (Python/TypeScript/C#): ").strip()
        if not primary_language:
            return None

        framework = input("Framework (FastAPI/NestJS/.NET): ").strip()
        if not framework:
            return None

        architecture_pattern = input("Architecture pattern (MVVM/Clean/Layered): ").strip()
        if not architecture_pattern:
            return None

        unit_testing_framework = input("Testing framework (pytest/vitest/xUnit): ").strip()
        if not unit_testing_framework:
            return None

        error_handling = input("Error handling (Result/ErrorOr/Exceptions): ").strip()
        if not error_handling:
            return None

        # Create minimal answer object
        class MinimalAnswers:
            def __init__(self):
                self.template_name = template_name
                self.template_purpose = template_purpose
                self.primary_language = primary_language
                self.framework = framework
                self.architecture_pattern = architecture_pattern
                self.unit_testing_framework = unit_testing_framework
                self.error_handling = error_handling

        return MinimalAnswers()

    def _phase2_ai_generation(self, answers: Any) -> GreenfieldTemplate:
        """Phase 2: AI generates template from Q&A answers

        Args:
            answers: GreenfieldAnswers from Phase 1

        Returns:
            GreenfieldTemplate with all components

        Raises:
            TemplateGenerationError: If generation fails
        """
        print("\n" + "=" * 60)
        print("  Phase 2: AI Template Generation")
        print("=" * 60 + "\n")

        print("🤖 Generating template structure...")

        try:
            generator = AITemplateGenerator(greenfield_context=answers)
            template = generator.generate(answers)

            print(f"  ✓ Manifest generated")
            print(f"  ✓ Settings generated")
            print(f"  ✓ CLAUDE.md generated")
            print(f"  ✓ Project structure defined")
            print(f"  ✓ Code templates created")

            return template

        except Exception as e:
            raise TemplateGenerationError(f"Template generation failed: {e}") from e

    def _phase3_agent_setup(self, template: GreenfieldTemplate) -> Any:
        """Phase 3: Generate agents for template (TASK-009)

        Args:
            template: GreenfieldTemplate from Phase 2

        Returns:
            AgentRecommendation with all agents

        Raises:
            AgentSetupError: If agent setup fails
        """
        print("\n" + "=" * 60)
        print("  Phase 3: Agent System")
        print("=" * 60 + "\n")

        print("🤖 Setting up agent system...")

        try:
            # Try to import agent orchestration from TASK-009
            # If not available, use fallback
            try:
                # Future import when TASK-009 is implemented
                # from ..agent_orchestration import AgentOrchestrator
                #
                # orchestrator = AgentOrchestrator()
                # agents = orchestrator.recommend_agents(
                #     analysis=template.inferred_analysis,
                #     enable_external=self.enable_external_agents
                # )

                # Fallback for now (TASK-009 not yet implemented)
                agents = self._fallback_agent_setup(template)

            except ImportError:
                # Fallback if TASK-009 not available
                agents = self._fallback_agent_setup(template)

            print(f"  ✓ Agent system configured")
            print(f"  ✓ {self._count_agents(agents)} agents ready")

            return agents

        except Exception as e:
            raise AgentSetupError(f"Agent setup failed: {e}") from e

    def _fallback_agent_setup(self, template: GreenfieldTemplate) -> Any:
        """Fallback agent setup when TASK-009 not available

        This creates a minimal agent recommendation using only global agents.

        Args:
            template: GreenfieldTemplate from Phase 2

        Returns:
            Minimal agent recommendation
        """
        print("  ℹ️  Using minimal agent setup (TASK-009 not yet implemented)")

        # Create minimal recommendation with global agents
        class MinimalAgentRecommendation:
            def __init__(self):
                self.use_global = []
                self.use_template = []
                self.use_custom = []
                self.generated = []
                self.external_suggestions = []

            def all_agents(self):
                return (
                    self.use_global
                    + self.use_template
                    + self.use_custom
                    + self.generated
                )

        recommendation = MinimalAgentRecommendation()

        # Add references to global agents (these will be copied later)
        # For now, just track that they should be included
        global_agent_names = [
            "architectural-reviewer",
            "task-manager",
            "test-verifier",
            "code-reviewer",
        ]

        # Create minimal agent definitions
        class MinimalAgent:
            def __init__(self, name: str):
                self.name = name
                self.full_definition = f"# {name}\n\nGlobal agent for {name}"

        for agent_name in global_agent_names:
            recommendation.use_global.append(MinimalAgent(agent_name))

        return recommendation

    def _count_agents(self, agents: Any) -> int:
        """Count total agents in recommendation

        Args:
            agents: AgentRecommendation or minimal fallback

        Returns:
            Total number of agents
        """
        try:
            return len(agents.all_agents())
        except AttributeError:
            # Fallback if all_agents() not available
            return (
                len(getattr(agents, "use_global", []))
                + len(getattr(agents, "use_template", []))
                + len(getattr(agents, "use_custom", []))
                + len(getattr(agents, "generated", []))
            )

    def _get_template_path(self, template_name: str) -> Path:
        """Work out which directory this template will be written to.

        This calculation used to live on the interactive Q&A session class and
        was lost when that class was rewritten; the call to it survived and
        crashed. It belongs here, on the command that already owns both
        `template_dir` and `output_location`.

        Resolution order:

        1. A directory the caller named explicitly (``template_dir=``) wins.
           It is the most specific instruction available.
        2. Otherwise ``output_location`` decides:

           * ``'repo'``   -> ``<cwd>/installer/core/templates/<name>`` — the
             in-repository home, meant for sharing with the team.
           * ``'global'`` -> ``~/.agentecflow/templates/<name>`` — the
             per-user home. This is the default.
        """
        if self._template_dir_explicit:
            return self.template_dir / template_name

        if self.output_location == 'repo':
            return Path.cwd() / "installer" / "core" / "templates" / template_name

        return Path.home() / ".agentecflow" / "templates" / template_name

    def _display_location_guidance(self, template_path: Path) -> None:
        """Tell the user where the template landed, and what to do next."""
        print("\n" + "=" * 70)
        print("  Template Saved")
        print("=" * 70 + "\n")

        if self.output_location == 'repo' and not self._template_dir_explicit:
            print(f"\u2705 Repository template: {template_path}")
            print()
            print("This one is meant to be shared with the team:")
            print("  1. Review the generated template")
            print("  2. Add it to git:  git add installer/core/templates/")
            print("  3. Push it")
        else:
            print(f"\u2705 Template saved: {template_path}")
            print()
            print("This template is available to you locally.")
            print("To create one for team distribution instead, re-run with:")
            print("  /template-init --output-location=repo")

        print()
        print("Use it with:")
        print(f"  /agentic-init {template_path.name}")

    def _phase4_save_template(self, template: GreenfieldTemplate, agents: Any) -> Path:
        """Phase 4: Save template to disk

        Args:
            template: GreenfieldTemplate from Phase 2
            agents: AgentRecommendation from Phase 3

        Returns:
            Path to saved template directory

        Raises:
            TemplateSaveError: If save fails
        """
        print("\n" + "=" * 60)
        print("  Phase 4: Save Template")
        print("=" * 60 + "\n")

        print("💾 Saving template...")

        try:
            # Where the template goes is decided by this command itself.
            # This used to be delegated to the interactive Q&A session class,
            # which (a) has never accepted an `output_location` argument, so the
            # call raised TypeError the moment it ran, and (b) no longer has the
            # path helper the next line called. Building an interactive Q&A
            # object just to do path arithmetic also dragged the `inquirer`
            # input library into a save that needs no input at all.
            template_path = self._get_template_path(template.name)
            template_path.mkdir(parents=True, exist_ok=True)

            # Save manifest.json
            manifest_file = template_path / "manifest.json"
            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(template.manifest, f, indent=2)
            print(f"  ✓ Saved: manifest.json")

            # Save settings.json
            settings_file = template_path / "settings.json"
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(template.settings, f, indent=2)
            print(f"  ✓ Saved: settings.json")

            # Save CLAUDE.md
            claude_file = template_path / "CLAUDE.md"
            with open(claude_file, "w", encoding="utf-8") as f:
                f.write(template.claude_md)
            print(f"  ✓ Saved: CLAUDE.md")

            # Save agents (split into core and extended files)
            from installer.core.lib.agent_generator.agent_splitter import (
                split_agent_content,
                validate_split_sizes
            )

            agents_dir = template_path / "agents"
            agents_dir.mkdir(exist_ok=True)

            agent_count = 0
            warnings = []
            for agent in agents.all_agents():
                # Split agent into core and extended parts
                try:
                    core_content, extended_content = split_agent_content(agent.full_definition)

                    # Save core file
                    agent_file = agents_dir / f"{agent.name}.md"
                    with open(agent_file, "w", encoding="utf-8") as f:
                        f.write(core_content)

                    # Save extended file
                    extended_file = agents_dir / f"{agent.name}-ext.md"
                    with open(extended_file, "w", encoding="utf-8") as f:
                        f.write(extended_content)

                    # Validate sizes
                    size_warnings = validate_split_sizes(core_content, extended_content)
                    if size_warnings:
                        warnings.extend([f"  ⚠️ {agent.name}: {w}" for w in size_warnings])

                    agent_count += 1
                except Exception as e:
                    print(f"  ⚠️ Failed to split agent {agent.name}: {e}")
                    # Fallback: save unsplit agent
                    agent_file = agents_dir / f"{agent.name}.md"
                    with open(agent_file, "w", encoding="utf-8") as f:
                        f.write(agent.full_definition)
                    agent_count += 1

            print(f"  ✓ Saved: {agent_count} agents (core + extended)")

            # Show size warnings if any
            if warnings:
                print("\n  Size Warnings:")
                for warning in warnings:
                    print(warning)

            # Save code templates (if any)
            if template.code_templates:
                templates_dir = template_path / "templates"
                templates_dir.mkdir(exist_ok=True)

                for name, content in template.code_templates.items():
                    template_file = templates_dir / name
                    template_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(template_file, "w", encoding="utf-8") as f:
                        f.write(content)

                print(f"  ✓ Saved: {len(template.code_templates)} code templates")

            print(f"\n✅ Template saved to: {template_path}")

            # Display location-specific guidance
            self._display_location_guidance(template_path)

            # Ensure /template-validate compatibility (TASK-INIT-005).
            # These two helpers DO still exist on the Q&A session class, so the
            # session is built here, inside the guard: constructing it needs the
            # interactive `inquirer` package, and a non-interactive save must not
            # hard-require it.
            try:
                from ..greenfield_qa_session import TemplateInitQASession
                session = TemplateInitQASession()
                session.ensure_validation_compatibility(template_path)
                session.display_validation_guidance(template_path)
            except Exception as e:
                # Non-fatal - just warn if validation compatibility setup fails
                print(f"⚠️  Warning: Could not set up validation compatibility: {e}")

            return template_path

        except Exception as e:
            raise TemplateSaveError(f"Failed to save template: {e}") from e

    def _phase4_5_rules_structure_generation(self, template_path: Path, qa_answers: Any) -> None:
        """Phase 4.5: Rules Structure Generation

        Generates modular .claude/rules/ directory structure based on Q&A session answers.

        Args:
            template_path: Path to saved template directory
            qa_answers: Q&A session answers containing language, framework, architecture choices

        Raises:
            TemplateSaveError: If rules generation fails
        """
        print("\n" + "=" * 60)
        print("  Phase 4.5: Rules Structure Generation")
        print("=" * 60 + "\n")

        print("📐 Generating rules structure...")

        try:
            from installer.core.lib.rules_generator import generate_rules_structure

            # Extract Q&A answers into dict format
            answers_dict = {}
            if hasattr(qa_answers, 'language'):
                answers_dict['language'] = qa_answers.language
            elif hasattr(qa_answers, '__dict__'):
                # Convert object to dict
                answers_dict = vars(qa_answers)
            else:
                # Already a dict
                answers_dict = qa_answers

            # Generate rules structure
            generate_rules_structure(
                template_dir=str(template_path),
                qa_answers=answers_dict,
                claude_md_size_limit=self.claude_md_size_limit
            )

            print("  ✓ Generated code-style.md")
            print("  ✓ Generated testing.md")
            print("  ✓ Generated patterns/")

            print(f"\n✅ Rules structure generated successfully")

        except ValueError as e:
            # Size limit violation
            print(f"\n⚠️  Warning: {e}")
            print("Consider increasing --claude-md-size-limit or moving content to rules/")
            # Non-fatal - continue without rules structure
        except Exception as e:
            print(f"\n⚠️  Warning: Failed to generate rules structure: {e}")
            print("Template creation will continue without rules structure.")
            # Non-fatal - template still usable

    def _phase5_extended_validation(self, template: GreenfieldTemplate, template_path: Path) -> int:
        """Phase 5: Level 2 Extended Validation (Optional)

        Runs extended validation checks on generated template and produces quality report.

        Args:
            template: GreenfieldTemplate from Phase 2
            template_path: Path to saved template directory

        Returns:
            Exit code (0 = A grade, 1 = B-C grade, 2 = D-F grade)
        """
        print("\n" + "=" * 70)
        print("  Level 2: Extended Validation")
        print("=" * 70 + "\n")

        # ------------------------------------------------------------------
        # FLAGGED FOR REVIEW (2026-08-21) — extended validation cannot run.
        #
        # The scoring routine this phase calls, `_run_level2_validation`, used
        # to live on the greenfield Q&A session class. That class was rewritten
        # and the routine went with it; this call site was left behind. It was
        # broken twice over: the session has never accepted a `validate`
        # argument either, so building it raised TypeError before the missing
        # method was even reached. The blanket `except Exception` further down
        # then turned that into a bland "validation failed" warning — so
        # `--template-init --validate` has been reporting on a score it never
        # computed.
        #
        # A surviving extended validator does exist, at
        # installer/core/lib/template_generator/extended_validator.py, but it
        # scores a TemplateCollection of fully described CodeTemplate records
        # (file type, language, purpose, patterns). The greenfield path only
        # ever holds a plain {filename: content} dictionary. Connecting the two
        # would mean inventing those fields, which would yield a
        # confident-looking grade with nothing behind it.
        #
        # So: the original body is kept below, unchanged in intent, behind an
        # explicit capability check. If the scoring routine is ever restored,
        # this phase starts working again with no further edit. Until then it
        # says plainly that no score was produced instead of inventing one.
        # Deciding whether to rebuild Level 2 scoring for greenfield templates,
        # or to retire the `--validate` flag, is a design call for Rich.
        # ------------------------------------------------------------------
        try:
            from ..greenfield_qa_session import TemplateInitQASession
            _level2_available = hasattr(TemplateInitQASession, "_run_level2_validation")
        except Exception:  # noqa: BLE001 - import shape varies by entry point
            TemplateInitQASession = None  # type: ignore[assignment]
            _level2_available = False

        if not _level2_available:
            print("⚠️  Extended validation did NOT run — no quality score was produced.")
            print()
            print("    The Level 2 scoring routine for greenfield templates is not")
            print("    present in this build, so there is nothing to grade against.")
            print(f"    The template itself saved correctly to: {template_path}")
            print()
            print("    To check the saved template, run:  /template-validate")
            print()
            return 1

        try:
            # Create temporary session instance for validation
            session = TemplateInitQASession()

            # Prepare template data for validation
            template_data = {
                'architecture_pattern': getattr(template, 'architecture_pattern', 'unknown'),
                'layers': getattr(template, 'layers', []),
                'agents': []  # Could be populated from agents if needed
            }

            # Prepare Level 1 results (minimal defaults since Level 1 validation may not exist yet)
            level1_results = {
                'crud_completeness': {
                    'passes': True,
                    'coverage': 1.0,
                    'threshold': 0.75,
                    'covered_operations': [],
                    'missing_operations': []
                },
                'layer_symmetry': {
                    'is_symmetric': True,
                    'found_layers': []
                }
            }

            # Run Level 2 validation
            level2_results = session._run_level2_validation(
                template_path,
                template_data,
                level1_results
            )

            # Display quality summary
            scores = level2_results['quality_scores']
            print(f"\n📊 Quality Assessment:")
            print(f"  Overall Score: {scores['overall_score']}/10 (Grade: {scores['grade']})")
            print(f"  Production Ready: {'✅ Yes' if scores['production_ready'] else '❌ No'}")

            # Determine exit code based on score
            if scores['overall_score'] >= 8:
                return 0  # A grade
            elif scores['overall_score'] >= 6:
                return 1  # B-C grade
            else:
                return 2  # D-F grade

        except Exception as e:
            print(f"⚠️ Warning: Extended validation failed: {e}")
            import traceback
            traceback.print_exc()
            return 1  # Return warning exit code on failure

    def _phase6_create_agent_tasks(self, template: GreenfieldTemplate, template_path: Path) -> None:
        """Phase 6: Create agent enhancement tasks

        Creates one enhancement task per generated agent for incremental improvement.

        Args:
            template: GreenfieldTemplate from Phase 2
            template_path: Path to saved template directory

        Raises:
            AgentSetupError: If task creation fails (non-fatal - just warns)
        """
        if self.no_create_agent_tasks:
            return

        print("\n" + "=" * 60)
        print("  Phase 5: Agent Enhancement Tasks")
        print("=" * 60 + "\n")

        try:
            # Find agent files in template directory
            agents_dir = template_path / "agents"
            if not agents_dir.exists():
                print("⚠️ No agents directory found, skipping task creation")
                return

            agent_files = list(agents_dir.glob("*.md"))
            if not agent_files:
                print("⚠️ No agents generated, skipping task creation")
                return

            # Import greenfield Q&A session for task creation methods
            from ..greenfield_qa_session import TemplateInitQASession

            # Create temporary session instance for task creation
            session = TemplateInitQASession(no_create_agent_tasks=True)
            # Set template name in session data for task metadata
            session._session_data = {'template_name': template.name}

            # Create enhancement tasks
            print(f"📋 Creating enhancement tasks for {len(agent_files)} agents...")
            task_ids = session._create_agent_enhancement_tasks(
                template.name,
                agent_files
            )

            if task_ids:
                print(f"  ✓ Created {len(task_ids)} enhancement tasks")

                # Display enhancement options to user
                session._display_enhancement_options(task_ids, template.name)
            else:
                print("⚠️ No enhancement tasks created")

        except Exception as e:
            print(f"⚠️ Warning: Agent task creation failed: {e}")
            # Don't fail entire workflow, just warn
            import traceback
            traceback.print_exc()

    def _show_success(self, template: GreenfieldTemplate, agents: Any) -> None:
        """Display success message

        Args:
            template: Created template
            agents: Agent recommendation
        """
        print("\n" + "=" * 60)
        print("  Template Creation Complete")
        print("=" * 60 + "\n")

        # Report the path the template was ACTUALLY written to. This used to
        # print `self.template_dir / name` unconditionally, which disagreed with
        # where Phase 4 saves when `--output-location` is in play — so the
        # success message could name a directory that does not exist.
        saved_at = self._get_template_path(template.name)

        print(f"✅ Template created: {template.name}")
        print(f"   Location: {saved_at}/")
        print(f"   Agents: {self._count_agents(agents)} total")

        print(f"\n💡 Next steps:")
        print(f"   1. Review template at: {saved_at}/")
        print(f"   2. Customize agents if needed")
        print(f"   3. Use template with: /agentic-init {template.name}")
        print()


def template_init(template_dir: Optional[Path] = None, no_create_agent_tasks: bool = False, validate: bool = False, output_location: str = 'global') -> bool:
    """Command entry point for /template-init

    This is the main entry point called by the CLI when user runs:
        /template-init

    Args:
        template_dir: Optional custom template directory
        no_create_agent_tasks: Skip agent enhancement task creation (default: False)
        validate: Run extended validation (Level 2) (default: False)
        output_location: Where to save template ('global' or 'repo')

    Returns:
        True if successful, False otherwise

    Example:
        >>> from template_init import template_init
        >>> success = template_init()
        >>> if success:
        ...     print("Template created successfully")

        >>> success = template_init(validate=True)
        >>> # Generates validation-report.md with quality scores

        >>> success = template_init(output_location='repo')
        >>> # Saves template to repository location
    """
    command = TemplateInitCommand(template_dir=template_dir, no_create_agent_tasks=no_create_agent_tasks, validate=validate, output_location=output_location)
    return command.execute()


def main():
    """CLI entry point for testing

    Allows running the command directly:
        python -m installer.core.commands.lib.template_init.command
    """
    success = template_init()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
