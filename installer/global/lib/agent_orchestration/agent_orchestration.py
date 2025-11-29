"""
Agent System Orchestration

Orchestrates the complete agent system flow:
1. Scan existing agents (user, template, global)
2. Analyze codebase for needs
3. Generate missing agents
4. Optionally discover external agents
5. Return final agent recommendations

This module coordinates between the agent scanner, agent generator, and
external discovery (Phase 2) to provide a unified agent recommendation
for template creation.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import importlib

# Import using importlib to avoid 'global' keyword issue
_agent_scanner_module = importlib.import_module('installer.global.lib.agent_scanner.agent_scanner')
_agent_generator_module = importlib.import_module('installer.global.lib.agent_generator.agent_generator')
_analyzer_models_module = importlib.import_module('installer.global.lib.codebase_analyzer.models')

AgentDefinition = _agent_scanner_module.AgentDefinition
AgentInventory = _agent_scanner_module.AgentInventory
MultiSourceAgentScanner = _agent_scanner_module.MultiSourceAgentScanner

AIAgentGenerator = _agent_generator_module.AIAgentGenerator
GeneratedAgent = _agent_generator_module.GeneratedAgent

CodebaseAnalysis = _analyzer_models_module.CodebaseAnalysis


@dataclass
class DiscoveredAgent:
    """External agent discovered from community sources (Phase 2)"""
    name: str
    description: str
    source_url: str
    tags: List[str]
    relevance_score: float  # 0-100


@dataclass
class AgentRecommendation:
    """Final agent recommendation"""
    # Existing agents to use
    use_custom: List[AgentDefinition]  # User's custom agents
    use_template: List[AgentDefinition]  # Template agents
    use_global: List[AgentDefinition]  # Global built-in agents

    # Newly generated agents
    generated: List[GeneratedAgent]  # AI-created agents

    # Optional external suggestions (Phase 2)
    external_suggestions: List[DiscoveredAgent]  # From external discovery

    def all_agents(self) -> List:
        """Return all agents (existing + generated)"""
        return (
            self.use_custom +
            self.use_template +
            self.use_global +
            self.generated
        )

    def total_count(self) -> int:
        """Total number of agents"""
        return len(self.all_agents())

    def summary(self) -> str:
        """Human-readable summary"""
        lines = []
        lines.append(f"Total: {self.total_count()} agents")

        if self.use_custom:
            lines.append(f"  • Custom: {len(self.use_custom)}")
        if self.use_template:
            lines.append(f"  • Template: {len(self.use_template)}")
        if self.use_global:
            lines.append(f"  • Global: {len(self.use_global)}")
        if self.generated:
            lines.append(f"  • Generated: {len(self.generated)}")
        if self.external_suggestions:
            lines.append(f"  • Suggestions: {len(self.external_suggestions)} (optional)")

        return "\n".join(lines)


class AgentOrchestrator:
    """Orchestrate complete agent system workflow"""

    def __init__(
        self,
        template_path: Optional[Path] = None,
        enable_external_discovery: bool = False
    ):
        """
        Initialize orchestrator

        Args:
            template_path: Path to template/agents/ if using template
            enable_external_discovery: Whether to enable external discovery (Phase 2)
        """
        self.template_path = template_path
        self.enable_external_discovery = enable_external_discovery

    def recommend_agents(
        self,
        analysis: CodebaseAnalysis
    ) -> AgentRecommendation:
        """
        Complete agent recommendation flow

        Args:
            analysis: Codebase analysis from TASK-002

        Returns:
            AgentRecommendation with all agents
        """
        print("\n" + "="*60)
        print("  Agent System")
        print("="*60)

        try:
            # Phase 1: Inventory existing agents
            inventory = self._phase1_inventory()

            # Phase 2: Generate missing agents
            generated = self._phase2_generate(analysis, inventory)

            # Phase 3: External discovery (optional, Phase 2)
            external = self._phase3_external_discovery(analysis, inventory, generated)

            # Phase 4: Build recommendation
            recommendation = self._phase4_build_recommendation(
                inventory,
                generated,
                external
            )

            # Phase 5: Display summary
            self._phase5_display_summary(recommendation)

            return recommendation

        except Exception as e:
            print(f"\n⚠️  Agent system error: {e}")
            print("  → Continuing with minimal agent set")

            # Fallback: Return minimal recommendation
            return self._fallback_recommendation()

    def _phase1_inventory(self) -> AgentInventory:
        """Phase 1: Scan existing agents"""

        scanner = MultiSourceAgentScanner(
            custom_path=Path(".claude/agents"),
            template_path=self.template_path,
            global_path=None  # Auto-detect
        )

        inventory = scanner.scan()

        return inventory

    def _phase2_generate(
        self,
        analysis: CodebaseAnalysis,
        inventory: AgentInventory
    ) -> List[GeneratedAgent]:
        """Phase 2: Generate missing agents"""

        generator = AIAgentGenerator(inventory=inventory)

        generated = generator.generate(analysis)

        return generated

    def _phase3_external_discovery(
        self,
        analysis: CodebaseAnalysis,
        inventory: AgentInventory,
        generated: List[GeneratedAgent]
    ) -> List[DiscoveredAgent]:
        """Phase 3: External agent discovery (optional, Phase 2)"""

        # Only if enabled and user opts in
        if not self.enable_external_discovery:
            return []

        # Ask user
        discover = input("\n🌐 Discover community agents? [y/N] ")

        if discover.lower() != 'y':
            print("  ℹ️  Skipping external discovery")
            return []

        try:
            _external_discovery_module = importlib.import_module('installer.global.lib.agent_orchestration.external_discovery')
            suggest_external_agents = _external_discovery_module.suggest_external_agents

            print("\n📡 Searching external sources...")

            external = suggest_external_agents(
                analysis=analysis,
                existing_agents=inventory,
                generated_agents=generated
            )

            if external:
                print(f"  ✓ Found {len(external)} suggestions")
            else:
                print("  ℹ️  No unique external agents found")

            return external

        except ImportError:
            print("  ℹ️  External discovery not yet implemented (Phase 2)")
            return []
        except Exception as e:
            print(f"  ⚠️  External discovery failed: {e}")
            print("  → Continuing without external agents")
            return []

    def _phase4_build_recommendation(
        self,
        inventory: AgentInventory,
        generated: List[GeneratedAgent],
        external: List[DiscoveredAgent]
    ) -> AgentRecommendation:
        """Phase 4: Build final recommendation"""

        return AgentRecommendation(
            use_custom=inventory.custom_agents,
            use_template=inventory.template_agents,
            use_global=inventory.global_agents,
            generated=generated,
            external_suggestions=external
        )

    def _phase5_display_summary(self, recommendation: AgentRecommendation):
        """Phase 5: Display summary to user"""

        print("\n" + "="*60)
        print("  Agent Setup Complete")
        print("="*60 + "\n")

        print(recommendation.summary())

        # Show which agents are being used
        if recommendation.use_custom:
            print("\n💡 Using your custom agents:")
            for agent in recommendation.use_custom:
                print(f"  • {agent.name}")

        if recommendation.generated:
            print("\n✨ Generated project-specific agents:")
            for agent in recommendation.generated:
                print(f"  • {agent.name}")

        if recommendation.external_suggestions:
            print(f"\n📦 External suggestions available: {len(recommendation.external_suggestions)}")
            print("  (Review and optionally add during template finalization)")

        print()

    def _fallback_recommendation(self) -> AgentRecommendation:
        """Fallback recommendation if orchestration fails"""

        # Try to at least load global agents
        try:
            scanner = MultiSourceAgentScanner()
            inventory = scanner.scan()

            return AgentRecommendation(
                use_custom=inventory.custom_agents,
                use_template=inventory.template_agents,
                use_global=inventory.global_agents,
                generated=[],
                external_suggestions=[]
            )

        except Exception:
            # Complete fallback: Empty recommendation
            return AgentRecommendation(
                use_custom=[],
                use_template=[],
                use_global=[],
                generated=[],
                external_suggestions=[]
            )


# Convenience function for template creation
def get_agents_for_template(
    analysis: CodebaseAnalysis,
    template_path: Optional[Path] = None,
    enable_external: bool = False
) -> AgentRecommendation:
    """
    Get complete agent recommendation for template

    Args:
        analysis: Codebase analysis
        template_path: Path to template/agents/ if using existing template
        enable_external: Enable external discovery (Phase 2)

    Returns:
        AgentRecommendation with all agents

    Usage:
        # In /template-create command
        analysis = analyzer.analyze(project_root)
        agents = get_agents_for_template(analysis)

        # Save agents to template
        for agent in agents.all_agents():
            save_agent_to_template(agent, template_dir)
    """
    orchestrator = AgentOrchestrator(
        template_path=template_path,
        enable_external_discovery=enable_external
    )

    return orchestrator.recommend_agents(analysis)
