---
id: TASK-004A
title: AI Agent Generator
status: backlog
created: 2025-11-01T23:15:00Z
priority: high
complexity: 6
estimated_hours: 8
tags: [ai-generation, agents, context-aware]
epic: EPIC-001
feature: agent-generation
dependencies: [TASK-002, TASK-003]
blocks: [TASK-009, TASK-010]
---

# TASK-004A: AI Agent Generator

## Objective

Generate project-specific AI agents based on codebase analysis, filling capability gaps identified by comparing needed capabilities with existing agents.

**Key Principle**: AI creates tailored agents from actual code examples (not generic templates)

## Context

**From Agent Strategy (Approved)**:
- AI generation is PRIMARY capability (not just discovery)
- Claude Code already creates excellent agents (proven: MAUI, .NET, Python API agents)
- Generated agents are context-aware (learn from project's actual code)
- User can save generated agents to `.claude/agents/` for reuse

## Acceptance Criteria

- [ ] Analyze codebase to determine needed agent capabilities
- [ ] Compare needed capabilities with existing agents (from TASK-003)
- [ ] Identify capability gaps (needed but don't exist)
- [ ] Generate agent definitions using AI
- [ ] Base generation on project's actual code examples
- [ ] Create complete agent markdown (frontmatter + body)
- [ ] Prompt user to save agents for reuse
- [ ] Validate generated agents (markdown syntax, required fields)
- [ ] Unit tests with mock AI responses
- [ ] Integration tests with real codebase analysis

## Implementation

```python
# src/commands/template_create/agent_generator.py

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set
import json

@dataclass
class CapabilityNeed:
    """Identified capability need"""
    name: str  # e.g., "maui-appshell-navigator"
    description: str  # What capability is needed
    reason: str  # Why it's needed
    technologies: List[str]  # Technologies involved
    example_files: List[Path]  # Code examples to learn from
    priority: int  # 1-10 (10=critical)

@dataclass
class GeneratedAgent:
    """AI-generated agent definition"""
    name: str
    description: str
    tools: List[str]
    tags: List[str]
    full_definition: str  # Complete markdown
    confidence: int  # 0-100 (AI's confidence)
    based_on_files: List[Path]  # Source files used for generation
    reuse_recommended: bool  # Whether agent is reusable across projects

class AIAgentGenerator:
    """Generate AI agents based on codebase analysis"""

    def __init__(
        self,
        inventory: 'AgentInventory',
        ai_invoker: 'AgentInvoker' = None
    ):
        """
        Initialize generator

        Args:
            inventory: Existing agent inventory (from TASK-003)
            ai_invoker: AI agent invoker (for DIP compliance)
        """
        self.inventory = inventory
        self.ai_invoker = ai_invoker or DefaultAgentInvoker()

    def generate(self, analysis: 'CodebaseAnalysis') -> List[GeneratedAgent]:
        """
        Generate agents to fill capability gaps

        Args:
            analysis: Codebase analysis from TASK-002

        Returns:
            List of generated agents
        """
        print("\n🤖 Determining agent needs...")

        # Phase 1: Identify needed capabilities
        needs = self._identify_capability_needs(analysis)

        print(f"  ✓ Identified {len(needs)} capability needs")

        # Phase 2: Find gaps (needed but don't exist)
        gaps = self._find_capability_gaps(needs)

        if not gaps:
            print("  ✓ All capabilities covered by existing agents")
            return []

        print(f"  ✓ Found {len(gaps)} gaps to fill")

        # Phase 3: Generate agents for gaps
        print("\n💡 Creating project-specific agents...")

        generated = []
        for gap in gaps:
            print(f"  → Generating: {gap.name}")

            agent = self._generate_agent(gap, analysis)

            if agent:
                print(f"    ✓ Created: {agent.name} (confidence: {agent.confidence}%)")
                generated.append(agent)
            else:
                print(f"    ⚠️  Failed to generate {gap.name}")

        # Phase 4: Offer to save for reuse
        self._offer_save_for_reuse(generated)

        return generated

    def _identify_capability_needs(
        self,
        analysis: 'CodebaseAnalysis'
    ) -> List[CapabilityNeed]:
        """
        Analyze codebase to identify needed agent capabilities

        Args:
            analysis: Codebase analysis

        Returns:
            List of capability needs
        """
        needs = []

        # Analyze architecture pattern
        if analysis.architecture_pattern == "MVVM":
            needs.append(CapabilityNeed(
                name="mvvm-viewmodel-specialist",
                description="MVVM ViewModel patterns and INotifyPropertyChanged",
                reason=f"Project uses {analysis.architecture_pattern} architecture",
                technologies=[analysis.language, "MVVM"],
                example_files=[
                    f for f in analysis.example_files
                    if "ViewModel" in str(f.path)
                ],
                priority=9
            ))

        # Analyze navigation pattern
        for layer in analysis.layers:
            if "navigation" in layer.patterns or "appshell" in str(layer).lower():
                needs.append(CapabilityNeed(
                    name="navigation-specialist",
                    description=f"{analysis.language} navigation patterns",
                    reason=f"Project uses {', '.join(layer.patterns)} for navigation",
                    technologies=[analysis.language] + layer.patterns,
                    example_files=[
                        f for f in analysis.example_files
                        if any(p.lower() in str(f.path).lower() for p in layer.patterns)
                    ],
                    priority=8
                ))

        # Analyze error handling patterns
        if "ErrorOr" in analysis.quality_assessment or "Result" in analysis.quality_assessment:
            needs.append(CapabilityNeed(
                name="error-pattern-specialist",
                description="Error handling pattern specialist",
                reason="Project uses ErrorOr<T> or Result<T> pattern",
                technologies=[analysis.language, "ErrorOr"],
                example_files=[
                    f for f in analysis.example_files
                    if "ErrorOr" in f.path.read_text() or "Result" in f.path.read_text()
                ],
                priority=7
            ))

        # Analyze domain operations
        for layer in analysis.layers:
            if layer.name == "domain":
                needs.append(CapabilityNeed(
                    name="domain-operations-specialist",
                    description=f"Domain operations following {', '.join(layer.patterns)}",
                    reason=f"Project has domain layer with {len(layer.directories)} directories",
                    technologies=[analysis.language] + layer.patterns,
                    example_files=[
                        f for f in analysis.example_files
                        if layer.name.lower() in str(f.path).lower()
                    ],
                    priority=8
                ))

        # Analyze testing frameworks
        if analysis.testing_framework:
            needs.append(CapabilityNeed(
                name=f"{analysis.testing_framework.lower()}-specialist",
                description=f"{analysis.testing_framework} testing patterns",
                reason=f"Project uses {analysis.testing_framework}",
                technologies=[analysis.language, analysis.testing_framework],
                example_files=[
                    f for f in analysis.example_files
                    if "test" in str(f.path).lower()
                ],
                priority=7
            ))

        return sorted(needs, key=lambda n: n.priority, reverse=True)

    def _find_capability_gaps(
        self,
        needs: List[CapabilityNeed]
    ) -> List[CapabilityNeed]:
        """
        Find capability gaps (needed but don't exist)

        Args:
            needs: List of capability needs

        Returns:
            List of gaps to fill
        """
        gaps = []

        for need in needs:
            # Check if agent exists
            if self.inventory.has_agent(need.name):
                agent = self.inventory.find_by_name(need.name)
                print(f"  ✓ {need.name}: Using existing ({agent.source})")
                continue

            # Check if capability is covered by similar agent
            if self._capability_covered(need):
                print(f"  ✓ {need.description}: Covered by existing agent")
                continue

            # Gap identified
            print(f"  ❌ {need.name}: MISSING (will create)")
            gaps.append(need)

        return gaps

    def _capability_covered(self, need: CapabilityNeed) -> bool:
        """Check if capability is covered by existing agents"""

        # Simple keyword matching for now
        # Could use AI for semantic similarity later

        for agent in self.inventory.all_agents():
            # Check tags
            if any(tech.lower() in agent.tags for tech in need.technologies):
                if any(
                    keyword in agent.description.lower()
                    for keyword in ["viewmodel", "mvvm", "navigation", "testing"]
                ):
                    return True

        return False

    def _generate_agent(
        self,
        gap: CapabilityNeed,
        analysis: 'CodebaseAnalysis'
    ) -> Optional[GeneratedAgent]:
        """
        Generate agent definition using AI

        Args:
            gap: Capability gap to fill
            analysis: Codebase analysis for context

        Returns:
            GeneratedAgent if successful, None otherwise
        """
        # Build generation prompt
        prompt = self._build_generation_prompt(gap, analysis)

        try:
            # Invoke AI to generate agent
            response = self.ai_invoker.invoke(
                agent_name="architectural-reviewer",
                prompt=prompt
            )

            # Parse AI response
            agent = self._parse_generated_agent(response, gap)

            return agent

        except Exception as e:
            print(f"    ⚠️  Generation failed: {e}")
            return None

    def _build_generation_prompt(
        self,
        gap: CapabilityNeed,
        analysis: 'CodebaseAnalysis'
    ) -> str:
        """Build AI prompt for agent generation"""

        # Read example files
        examples = []
        for example_file in gap.example_files[:3]:  # Max 3 examples
            try:
                content = example_file.read_text()
                examples.append(f"File: {example_file}\n```\n{content[:500]}\n```")
            except Exception:
                continue

        examples_text = "\n\n".join(examples)

        prompt = f"""
Create an AI agent definition for this project.

**Agent Name**: {gap.name}
**Purpose**: {gap.description}
**Why Needed**: {gap.reason}

**Project Context**:
- Language: {analysis.language}
- Architecture: {analysis.architecture_pattern}
- Frameworks: {', '.join(analysis.frameworks)}
- Technologies: {', '.join(gap.technologies)}

**Code Examples from This Project**:
{examples_text}

**Task**: Generate a complete agent definition in markdown format.

**Output Format**:
```markdown
---
name: {gap.name}
description: {gap.description}
tools: [Read, Write, Edit, Grep, Bash]
tags: [{', '.join(gap.technologies)}]
---

# {gap.name.title().replace('-', ' ')}

[Agent description and capabilities based on this project's patterns]

## Capabilities in This Project

[What this agent can do, based on actual code examples]

## Patterns Used

[Patterns observed in the example files]

## Conventions

[Naming conventions, file structure, etc. from examples]

## Example Usage

[How to use this agent in context of this project]
```

**Important**:
- Base the agent on ACTUAL code examples provided
- Capture project-specific patterns and conventions
- Make the agent context-aware (understands this project's style)
- Include tools: Read, Write, Edit, Grep, Bash (standard set)
- Return ONLY the markdown, no additional commentary

Return the complete agent markdown definition.
"""

        return prompt

    def _parse_generated_agent(
        self,
        response: str,
        gap: CapabilityNeed
    ) -> GeneratedAgent:
        """Parse AI-generated agent definition"""

        # Extract markdown (may have ```markdown wrapper)
        markdown = response.strip()
        if markdown.startswith("```markdown"):
            markdown = markdown.split("```markdown\n", 1)[1]
            markdown = markdown.rsplit("```", 1)[0]

        # Parse frontmatter
        import frontmatter
        post = frontmatter.loads(markdown)

        metadata = post.metadata

        return GeneratedAgent(
            name=metadata.get('name', gap.name),
            description=metadata.get('description', gap.description),
            tools=metadata.get('tools', ['Read', 'Write', 'Edit', 'Grep']),
            tags=metadata.get('tags', gap.technologies),
            full_definition=markdown,
            confidence=85,  # AI-generated agents have high confidence
            based_on_files=gap.example_files,
            reuse_recommended=self._is_reusable(gap, metadata)
        )

    def _is_reusable(
        self,
        gap: CapabilityNeed,
        metadata: dict
    ) -> bool:
        """Determine if agent is reusable across projects"""

        # Agents for general patterns are reusable
        reusable_patterns = [
            "mvvm", "clean-architecture", "hexagonal",
            "testing", "error-handling", "domain"
        ]

        agent_name = gap.name.lower()

        return any(pattern in agent_name for pattern in reusable_patterns)

    def _offer_save_for_reuse(self, generated: List[GeneratedAgent]):
        """Offer to save generated agents for reuse"""

        if not generated:
            return

        print("\n💾 Save agents for reuse?")

        for agent in generated:
            if agent.reuse_recommended:
                save = input(
                    f"\n  {agent.name}:\n"
                    f"  This agent is reusable across similar projects.\n"
                    f"  Save to .claude/agents/ for future use? [y/N] "
                )

                if save.lower() == 'y':
                    self._save_to_custom_agents(agent)
                    print(f"    ✓ Saved to .claude/agents/{agent.name}.md")

    def _save_to_custom_agents(self, agent: GeneratedAgent):
        """Save agent to .claude/agents/"""

        custom_dir = Path(".claude/agents")
        custom_dir.mkdir(parents=True, exist_ok=True)

        agent_file = custom_dir / f"{agent.name}.md"
        agent_file.write_text(agent.full_definition, encoding='utf-8')
```

## Usage Examples

### Example 1: Generate Agents for MAUI Project

```python
# After codebase analysis
analysis = analyzer.analyze(project_root)

# Scan existing agents
scanner = MultiSourceAgentScanner()
inventory = scanner.scan()

# Generate agents
generator = AIAgentGenerator(inventory=inventory)
generated = generator.generate(analysis)

# Output:
# 🤖 Determining agent needs...
#   ✓ Identified 5 capability needs
#   ✓ architectural-reviewer: Using existing (global)
#   ✓ code-reviewer: Using existing (global)
#   ❌ maui-appshell-navigator: MISSING (will create)
#   ❌ errror-pattern-specialist: MISSING (will create)
#   ✓ Found 2 gaps to fill
#
# 💡 Creating project-specific agents...
#   → Generating: maui-appshell-navigator
#     ✓ Created: maui-appshell-navigator (confidence: 85%)
#   → Generating: errror-pattern-specialist
#     ✓ Created: errror-pattern-specialist (confidence: 85%)
#
# 💾 Save agents for reuse?
#   maui-appshell-navigator:
#   This agent is reusable across similar projects.
#   Save to .claude/agents/ for future use? [y/N] y
#     ✓ Saved to .claude/agents/maui-appshell-navigator.md

print(f"Generated {len(generated)} agents")
for agent in generated:
    print(f"  • {agent.name}: {agent.description}")
```

## Testing Strategy

```python
# tests/test_ai_agent_generator.py

def test_identify_capability_needs():
    """Test capability need identification"""
    analysis = CodebaseAnalysis(
        language="C#",
        frameworks=[".NET MAUI"],
        architecture_pattern="MVVM",
        # ...
    )

    inventory = AgentInventory(
        custom_agents=[],
        template_agents=[],
        global_agents=[]
    )

    generator = AIAgentGenerator(inventory=inventory)
    needs = generator._identify_capability_needs(analysis)

    # Should identify MVVM need
    assert any("mvvm" in need.name for need in needs)

    # MVVM need should be high priority
    mvvm_need = next(n for n in needs if "mvvm" in n.name)
    assert mvvm_need.priority >= 8

def test_find_capability_gaps():
    """Test gap finding"""
    needs = [
        CapabilityNeed(
            name="existing-agent",
            description="Test",
            reason="Test",
            technologies=[],
            example_files=[],
            priority=5
        ),
        CapabilityNeed(
            name="missing-agent",
            description="Test",
            reason="Test",
            technologies=[],
            example_files=[],
            priority=5
        )
    ]

    # Inventory has "existing-agent"
    inventory = AgentInventory(
        custom_agents=[],
        template_agents=[],
        global_agents=[
            AgentDefinition(
                name="existing-agent",
                description="Test",
                tools=[],
                tags=[],
                source="global",
                source_path=Path("test.md"),
                priority=1,
                full_definition=""
            )
        ]
    )

    generator = AIAgentGenerator(inventory=inventory)
    gaps = generator._find_capability_gaps(needs)

    # Should only find "missing-agent"
    assert len(gaps) == 1
    assert gaps[0].name == "missing-agent"

def test_generate_agent_with_mock_ai():
    """Test agent generation with mock AI response"""
    mock_response = """---
name: test-specialist
description: Test specialist
tools: [Read, Write]
tags: [test]
---

# Test Specialist

This is a test agent.
"""

    gap = CapabilityNeed(
        name="test-specialist",
        description="Test",
        reason="Test",
        technologies=["test"],
        example_files=[],
        priority=5
    )

    analysis = CodebaseAnalysis(
        language="Python",
        # ...
    )

    # Mock AI invoker
    with patch.object(AIAgentGenerator, '_invoke_ai', return_value=mock_response):
        generator = AIAgentGenerator(inventory=mock_inventory)
        agent = generator._generate_agent(gap, analysis)

        assert agent is not None
        assert agent.name == "test-specialist"
        assert agent.confidence == 85
```

## Definition of Done

- [ ] Capability need identification from codebase analysis
- [ ] Gap finding (compare needs with existing agents)
- [ ] AI-powered agent generation with prompts
- [ ] Agent definition parsing (frontmatter + body)
- [ ] Reuse detection (identify reusable agents)
- [ ] Save-for-reuse prompts (user choice)
- [ ] Validation of generated agents
- [ ] Unit tests with mock AI (>85% coverage)
- [ ] Integration tests with real analysis
- [ ] Documentation for generation prompts

**Estimated Time**: 8 hours | **Complexity**: 6/10 | **Priority**: HIGH

## Benefits

- ✅ Leverages Claude Code's proven agent creation capability
- ✅ Context-aware (learns from actual code)
- ✅ Project-specific (tailored to conventions)
- ✅ Reusable (user can save for future projects)
- ✅ Smart gap detection (doesn't duplicate)
- ✅ High quality (AI-generated, not templates)

---

**Created**: 2025-11-01
**Status**: ✅ **APPROVED** - Ready for implementation
**Dependencies**: TASK-002 (Analysis), TASK-003 (Scanner)
**Blocks**: TASK-009 (Orchestration), TASK-010 (Command)
