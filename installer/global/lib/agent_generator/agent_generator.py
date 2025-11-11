"""
AI Agent Generator

Generates project-specific AI agents based on codebase analysis and
fills capability gaps by comparing needed capabilities with existing agents.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Any, Protocol
import frontmatter
import json


@dataclass
class CapabilityNeed:
    """Identified capability need from codebase analysis"""
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


class AgentInvoker(Protocol):
    """Protocol for AI agent invocation (Dependency Inversion Principle)"""

    def invoke(self, agent_name: str, prompt: str) -> str:
        """Invoke an AI agent with a prompt"""
        ...


class DefaultAgentInvoker:
    """Default agent invoker (placeholder for actual implementation)"""

    def invoke(self, agent_name: str, prompt: str) -> str:
        """Invoke agent - this is a placeholder that should be replaced"""
        raise NotImplementedError(
            "Agent invoker must be provided or implemented"
        )


class AIAgentGenerator:
    """Generate AI agents based on codebase analysis"""

    def __init__(
        self,
        inventory: Any,  # AgentInventory from agent_scanner
        ai_invoker: Optional[AgentInvoker] = None
    ):
        """
        Initialize generator

        Args:
            inventory: Existing agent inventory (from TASK-003)
            ai_invoker: AI agent invoker (for DIP compliance)
        """
        self.inventory = inventory
        self.ai_invoker = ai_invoker or DefaultAgentInvoker()

    def generate(self, analysis: Any) -> List[GeneratedAgent]:
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

    def _identify_capability_needs(self, analysis: Any) -> List[CapabilityNeed]:
        """
        Analyze codebase to identify needed agent capabilities.

        Uses AI-powered analysis by default, with fallback to hard-coded
        detection if AI fails.

        Args:
            analysis: Codebase analysis

        Returns:
            List of capability needs
        """
        # Try AI-powered detection first
        try:
            needs = self._ai_identify_all_agents(analysis)
            if needs:  # AI successfully identified agents
                print(f"  ✓ AI identified {len(needs)} capability needs")
                return needs
        except Exception as e:
            print(f"  ⚠️  AI detection failed: {e}")
            print("  → Falling back to hard-coded detection")

        # Fallback to hard-coded detection
        return self._fallback_to_hardcoded(analysis)

    def _ai_identify_all_agents(self, analysis: Any) -> List[CapabilityNeed]:
        """
        Use AI to comprehensively analyze codebase and identify ALL agent needs.

        This eliminates hard-coded pattern detection by having AI analyze:
        - Architecture patterns
        - Code layers and their patterns
        - Frameworks and technologies
        - Quality patterns (ErrorOr, Result, etc.)
        - Testing frameworks

        Args:
            analysis: Codebase analysis from TASK-002

        Returns:
            List of comprehensive capability needs (7-12 for complex projects)

        Raises:
            Exception: If AI invocation fails or returns invalid JSON
        """
        # Build comprehensive prompt for AI analysis
        prompt = self._build_ai_analysis_prompt(analysis)

        # Invoke AI to analyze codebase and identify all agents
        response = self.ai_invoker.invoke(
            agent_name="architectural-reviewer",
            prompt=prompt
        )

        # Parse AI response and convert to CapabilityNeed objects
        needs = self._parse_ai_agent_response(response, analysis)

        return sorted(needs, key=lambda n: n.priority, reverse=True)

    def _build_ai_analysis_prompt(self, analysis: Any) -> str:
        """
        Build comprehensive AI prompt for agent identification.

        Token budget: 3000-5000 tokens (phase-appropriate for planning)

        Args:
            analysis: Codebase analysis

        Returns:
            Formatted prompt string
        """
        # Extract analysis data
        language = getattr(analysis, 'language', 'Unknown')
        architecture_pattern = getattr(analysis, 'architecture_pattern', 'Unknown')
        frameworks = getattr(analysis, 'frameworks', [])
        patterns = getattr(analysis, 'patterns', [])
        layers = getattr(analysis, 'layers', [])
        testing_framework = getattr(analysis, 'testing_framework', None)
        quality_assessment = getattr(analysis, 'quality_assessment', '')

        # Build layers description
        layers_desc = []
        for layer in layers:
            layer_name = getattr(layer, 'name', str(layer))
            layer_patterns = getattr(layer, 'patterns', [])
            layer_dirs = getattr(layer, 'directories', [])
            layers_desc.append(
                f"- {layer_name}: {', '.join(layer_patterns)} "
                f"({len(layer_dirs)} directories)"
            )
        layers_text = '\n'.join(layers_desc) if layers_desc else "No layers identified"

        prompt = f"""Analyze this codebase and identify ALL specialized AI agents needed for template creation.

**Project Context:**
- Language: {language}
- Architecture: {architecture_pattern}
- Frameworks: {', '.join(frameworks) if frameworks else 'None'}
- Patterns Detected: {', '.join(patterns) if patterns else 'None'}
- Testing Framework: {testing_framework or 'None'}
- Quality Patterns: {quality_assessment or 'None'}

**Code Layers:**
{layers_text}

**Requirements:**
1. Generate an agent for EACH architectural pattern listed (MVVM, Repository, Service, etc.)
2. Generate an agent for EACH layer (Domain, Application, Infrastructure, etc.)
3. Generate an agent for EACH major framework (MAUI, React, FastAPI, etc.)
4. Generate specialist agents for patterns (ErrorOr, CQRS, Mediator, etc.)
5. Include validation agents if architecture patterns are detected
6. Include database-specific agents if database frameworks are detected
7. Include testing agents if testing frameworks are detected

**Output Format (STRICT JSON ARRAY ONLY - NO MARKDOWN WRAPPERS):**
[
  {{
    "name": "repository-pattern-specialist",
    "description": "Repository pattern with ErrorOr and thread-safety",
    "reason": "Project uses Repository pattern in Infrastructure layer",
    "technologies": ["C#", "Repository Pattern", "ErrorOr"],
    "priority": 9
  }},
  {{
    "name": "engine-pattern-specialist",
    "description": "Business logic engines with orchestration",
    "reason": "Project has Application layer with Engines subdirectory",
    "technologies": ["C#", "Engine Pattern"],
    "priority": 9
  }}
]

**Critical Instructions:**
- Return ONLY the JSON array, NO markdown code blocks (```json)
- Include minimum 1 agent per major pattern/layer/framework identified
- For complex projects (3+ layers, 4+ patterns), return 7-12 agents
- Priority scale: 10=critical, 7-9=high, 4-6=medium, 1-3=low
- Use descriptive names with hyphens: "mvvm-viewmodel-specialist"

Return comprehensive JSON array of ALL agents this project needs:"""

        return prompt

    def _parse_ai_agent_response(self, response: str, analysis: Any) -> List[CapabilityNeed]:
        """
        Parse AI-generated agent specifications from JSON response.

        Handles various response formats:
        - Pure JSON array
        - JSON with markdown wrappers (```json)
        - Partial JSON with trailing text

        Args:
            response: AI response containing JSON array
            analysis: Codebase analysis (for file mapping)

        Returns:
            List of CapabilityNeed objects

        Raises:
            json.JSONDecodeError: If response is not valid JSON
            KeyError: If required fields are missing
        """
        # Clean response - remove markdown wrappers if present
        cleaned = response.strip()

        # Remove ```json wrapper if present
        if cleaned.startswith("```json"):
            cleaned = cleaned.split("```json\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]
        elif cleaned.startswith("```"):
            cleaned = cleaned.split("```\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            cleaned = cleaned.rsplit("```", 1)[0]

        cleaned = cleaned.strip()

        # Parse JSON array
        try:
            agents_data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            # Try to find JSON array in response
            import re
            json_match = re.search(r'\[[\s\S]*\]', cleaned)
            if json_match:
                agents_data = json.loads(json_match.group(0))
            else:
                raise ValueError(f"No valid JSON array found in AI response: {str(e)}")

        if not isinstance(agents_data, list):
            raise ValueError(f"AI response must be JSON array, got {type(agents_data)}")

        # Convert to CapabilityNeed objects
        needs = []
        example_files = getattr(analysis, 'example_files', [])

        for agent_spec in agents_data:
            need = self._create_capability_need_from_spec(agent_spec, example_files)
            needs.append(need)

        return needs

    def _create_capability_need_from_spec(
        self,
        spec: dict,
        example_files: List[Path]
    ) -> CapabilityNeed:
        """
        Create CapabilityNeed from AI-generated specification.

        Args:
            spec: Agent specification dict from AI
            example_files: Available example files from analysis

        Returns:
            CapabilityNeed object

        Raises:
            KeyError: If required fields are missing from spec
        """
        # Validate required fields
        required_fields = ['name', 'description', 'reason', 'technologies']
        missing = [f for f in required_fields if f not in spec]
        if missing:
            raise KeyError(f"Missing required fields in agent spec: {missing}")

        # Map example files to this agent based on technologies
        agent_files = []
        technologies = spec['technologies']

        # Simple keyword matching for file relevance
        for example_file in example_files[:10]:  # Limit to 10 files
            file_path = example_file if isinstance(example_file, Path) else getattr(example_file, 'path', None)
            if file_path:
                file_str = str(file_path).lower()
                # Check if any technology keyword appears in file path
                if any(tech.lower().replace(' ', '').replace('-', '') in file_str.replace('_', '').replace('-', '')
                       for tech in technologies):
                    agent_files.append(file_path)

        return CapabilityNeed(
            name=spec['name'],
            description=spec['description'],
            reason=spec['reason'],
            technologies=spec['technologies'],
            example_files=agent_files,
            priority=spec.get('priority', 7)  # Default to medium-high priority
        )

    def _fallback_to_hardcoded(self, analysis: Any) -> List[CapabilityNeed]:
        """
        Hard-coded pattern detection (FALLBACK ONLY).

        This is the original implementation preserved as a fallback
        when AI detection fails. Kept for backward compatibility.

        Args:
            analysis: Codebase analysis

        Returns:
            List of capability needs
        """
        needs = []

        # Get example files (handle both list and attribute access)
        example_files = getattr(analysis, 'example_files', [])
        language = getattr(analysis, 'language', 'Unknown')
        architecture_pattern = getattr(analysis, 'architecture_pattern', None)
        layers = getattr(analysis, 'layers', [])
        quality_assessment = getattr(analysis, 'quality_assessment', '')
        testing_framework = getattr(analysis, 'testing_framework', None)

        # Analyze architecture pattern
        if architecture_pattern == "MVVM":
            viewmodel_files = [
                f for f in example_files
                if "ViewModel" in str(getattr(f, 'path', f))
            ]
            needs.append(CapabilityNeed(
                name="mvvm-viewmodel-specialist",
                description="MVVM ViewModel patterns and INotifyPropertyChanged",
                reason=f"Project uses {architecture_pattern} architecture",
                technologies=[language, "MVVM"],
                example_files=viewmodel_files,
                priority=9
            ))

        # Analyze navigation patterns
        for layer in layers:
            layer_name = getattr(layer, 'name', str(layer)).lower()
            layer_patterns = getattr(layer, 'patterns', [])

            if "navigation" in layer_patterns or "appshell" in layer_name:
                nav_files = [
                    f for f in example_files
                    if any(
                        p.lower() in str(getattr(f, 'path', f)).lower()
                        for p in layer_patterns
                    )
                ]
                needs.append(CapabilityNeed(
                    name="navigation-specialist",
                    description=f"{language} navigation patterns",
                    reason=f"Project uses {', '.join(layer_patterns)} for navigation",
                    technologies=[language] + layer_patterns,
                    example_files=nav_files,
                    priority=8
                ))

        # Analyze error handling patterns
        if "ErrorOr" in quality_assessment or "Result" in quality_assessment:
            error_files = []
            for f in example_files:
                try:
                    file_path = getattr(f, 'path', f)
                    if isinstance(file_path, Path) and file_path.exists():
                        content = file_path.read_text()
                        if "ErrorOr" in content or "Result" in content:
                            error_files.append(file_path)
                except Exception:
                    continue

            if error_files:
                needs.append(CapabilityNeed(
                    name="error-pattern-specialist",
                    description="Error handling pattern specialist",
                    reason="Project uses ErrorOr<T> or Result<T> pattern",
                    technologies=[language, "ErrorOr"],
                    example_files=error_files,
                    priority=7
                ))

        # Analyze domain operations
        for layer in layers:
            layer_name = getattr(layer, 'name', str(layer)).lower()
            if layer_name == "domain":
                layer_patterns = getattr(layer, 'patterns', [])
                layer_dirs = getattr(layer, 'directories', [])

                domain_files = [
                    f for f in example_files
                    if "domain" in str(getattr(f, 'path', f)).lower()
                ]
                needs.append(CapabilityNeed(
                    name="domain-operations-specialist",
                    description=f"Domain operations following {', '.join(layer_patterns)}",
                    reason=f"Project has domain layer with {len(layer_dirs)} directories",
                    technologies=[language] + layer_patterns,
                    example_files=domain_files,
                    priority=8
                ))

        # Analyze testing frameworks
        if testing_framework:
            test_files = [
                f for f in example_files
                if "test" in str(getattr(f, 'path', f)).lower()
            ]
            needs.append(CapabilityNeed(
                name=f"{testing_framework.lower()}-specialist",
                description=f"{testing_framework} testing patterns",
                reason=f"Project uses {testing_framework}",
                technologies=[language, testing_framework],
                example_files=test_files,
                priority=7
            ))

        return sorted(needs, key=lambda n: n.priority, reverse=True)

    def _find_capability_gaps(self, needs: List[CapabilityNeed]) -> List[CapabilityNeed]:
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
            if any(tech.lower() in [tag.lower() for tag in agent.tags] for tech in need.technologies):
                # Check description for key terms
                if any(
                    keyword in agent.description.lower()
                    for keyword in ["viewmodel", "mvvm", "navigation", "testing", "domain", "error"]
                ):
                    return True

        return False

    def _generate_agent(self, gap: CapabilityNeed, analysis: Any) -> Optional[GeneratedAgent]:
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

    def _build_generation_prompt(self, gap: CapabilityNeed, analysis: Any) -> str:
        """Build AI prompt for agent generation"""

        # Read example files
        examples = []
        for example_file in gap.example_files[:3]:  # Max 3 examples
            try:
                file_path = example_file if isinstance(example_file, Path) else getattr(example_file, 'path', None)
                if file_path and file_path.exists():
                    content = file_path.read_text()
                    examples.append(f"File: {file_path}\n```\n{content[:500]}\n```")
            except Exception:
                continue

        examples_text = "\n\n".join(examples) if examples else "No example files available"

        language = getattr(analysis, 'language', 'Unknown')
        architecture_pattern = getattr(analysis, 'architecture_pattern', 'Unknown')
        frameworks = getattr(analysis, 'frameworks', [])

        prompt = f"""
Create an AI agent definition for this project.

**Agent Name**: {gap.name}
**Purpose**: {gap.description}
**Why Needed**: {gap.reason}

**Project Context**:
- Language: {language}
- Architecture: {architecture_pattern}
- Frameworks: {', '.join(frameworks)}
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

    def _parse_generated_agent(self, response: str, gap: CapabilityNeed) -> GeneratedAgent:
        """Parse AI-generated agent definition"""

        # Extract markdown (may have ```markdown wrapper)
        markdown = response.strip()
        if markdown.startswith("```markdown"):
            markdown = markdown.split("```markdown\n", 1)[1]
            markdown = markdown.rsplit("```", 1)[0]
        elif markdown.startswith("```"):
            # Handle plain ``` wrapper
            markdown = markdown.split("```\n", 1)[1] if "\n" in markdown else markdown[3:]
            markdown = markdown.rsplit("```", 1)[0]

        # Parse frontmatter
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

    def _is_reusable(self, gap: CapabilityNeed, metadata: dict) -> bool:
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
                print(
                    f"\n  {agent.name}:\n"
                    f"  This agent is reusable across similar projects.\n"
                    f"  Would save to .claude/agents/ for future use."
                )
                # Note: Actual user prompt would be interactive
                # For now, this is informational only

    def save_agent_to_custom(self, agent: GeneratedAgent) -> Path:
        """
        Save agent to .claude/agents/

        Args:
            agent: Generated agent to save

        Returns:
            Path to saved agent file
        """
        custom_dir = Path(".claude/agents")
        custom_dir.mkdir(parents=True, exist_ok=True)

        agent_file = custom_dir / f"{agent.name}.md"
        agent_file.write_text(agent.full_definition, encoding='utf-8')

        return agent_file
