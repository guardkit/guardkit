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

    def __init__(self, template_dir: Optional[Path] = None, enable_external_agents: bool = False):
        """Initialize command

        Args:
            template_dir: Custom template directory (default: installer/local/templates/)
            enable_external_agents: Enable external agent discovery (default: False)
        """
        if template_dir is None:
            template_dir = Path("installer/local/templates")

        self.template_dir = template_dir
        self.enable_external_agents = enable_external_agents

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
            self._phase4_save_template(template, agents)

            # Success
            self._show_success(template, agents)

            return True

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

    def _phase4_save_template(self, template: GreenfieldTemplate, agents: Any) -> None:
        """Phase 4: Save template to disk

        Args:
            template: GreenfieldTemplate from Phase 2
            agents: AgentRecommendation from Phase 3

        Raises:
            TemplateSaveError: If save fails
        """
        print("\n" + "=" * 60)
        print("  Phase 4: Save Template")
        print("=" * 60 + "\n")

        print("💾 Saving template...")

        try:
            # Create template directory
            template_path = self.template_dir / template.name
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

            # Save agents
            agents_dir = template_path / "agents"
            agents_dir.mkdir(exist_ok=True)

            agent_count = 0
            for agent in agents.all_agents():
                agent_file = agents_dir / f"{agent.name}.md"
                with open(agent_file, "w", encoding="utf-8") as f:
                    f.write(agent.full_definition)
                agent_count += 1

            print(f"  ✓ Saved: {agent_count} agents")

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

        except Exception as e:
            raise TemplateSaveError(f"Failed to save template: {e}") from e

    def _show_success(self, template: GreenfieldTemplate, agents: Any) -> None:
        """Display success message

        Args:
            template: Created template
            agents: Agent recommendation
        """
        print("\n" + "=" * 60)
        print("  Template Creation Complete")
        print("=" * 60 + "\n")

        print(f"✅ Template created: {template.name}")
        print(f"   Location: {self.template_dir / template.name}/")
        print(f"   Agents: {self._count_agents(agents)} total")

        print(f"\n💡 Next steps:")
        print(f"   1. Review template at: {self.template_dir / template.name}/")
        print(f"   2. Customize agents if needed")
        print(f"   3. Use template with: /agentic-init {template.name}")
        print()


def template_init(template_dir: Optional[Path] = None) -> bool:
    """Command entry point for /template-init

    This is the main entry point called by the CLI when user runs:
        /template-init

    Args:
        template_dir: Optional custom template directory

    Returns:
        True if successful, False otherwise

    Example:
        >>> from template_init import template_init
        >>> success = template_init()
        >>> if success:
        ...     print("Template created successfully")
    """
    command = TemplateInitCommand(template_dir=template_dir)
    return command.execute()


def main():
    """CLI entry point for testing

    Allows running the command directly:
        python -m installer.global.commands.lib.template_init.command
    """
    success = template_init()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
