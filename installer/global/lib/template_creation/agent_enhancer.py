"""
Agent Enhancer - AI-Powered Agent Documentation Enhancement

Enhances agent files with template-specific content using AI to:
1. Discover relevant templates for each agent
2. Read and analyze template code
3. Generate comprehensive documentation sections
4. Connect agents to actual template files

CRITICAL: This module MUST NOT contain any hard-coded mappings between
agents and templates. All relevance detection is AI-powered.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Any, Protocol
import json
import frontmatter
import logging


logger = logging.getLogger(__name__)


class AgentInvoker(Protocol):
    """Protocol for agent invocation (Dependency Inversion Principle)."""

    def invoke(self, agent_name: str, prompt: str, timeout_seconds: int = 120, context: Optional[dict] = None) -> str:
        """Invoke an agent with a prompt.

        Args:
            agent_name: Name of the agent to invoke
            prompt: Complete prompt text for the agent
            timeout_seconds: Maximum wait time for agent response
            context: Optional context for debugging

        Returns:
            Agent response text
        """
        ...


@dataclass
class AgentMetadata:
    """Agent metadata extracted from frontmatter."""
    name: str
    description: str
    priority: int
    technologies: List[str]
    file_path: Path


@dataclass
class TemplateRelevance:
    """Template relevance to an agent."""
    path: str
    relevance_reason: str
    priority: str  # 'primary', 'secondary', 'tertiary'


@dataclass
class EnhancedContent:
    """AI-generated enhanced content for agent."""
    purpose: str
    when_to_use: str
    related_templates: str
    example_pattern: str
    best_practices: str


class AgentEnhancer:
    """
    Enhance agent files with template references using AI.

    This class implements AI-first architecture:
    - NO hard-coded agent → template mappings
    - NO pattern matching on agent names
    - AI analyzes agent metadata to find relevant templates
    - AI reads template code to generate documentation

    Design Pattern: Orchestrator pattern (Taskwright standard)
    - Coordinates multiple AI analysis steps
    - Manages file I/O and validation
    - Assembles final enhanced agent files
    """

    def __init__(self, bridge_invoker: Optional[AgentInvoker] = None):
        """
        Initialize agent enhancer.

        Args:
            bridge_invoker: Agent bridge invoker for template discovery and content generation.
                           If None, enhancement is skipped gracefully (fallback mode).
        """
        self.bridge_invoker = bridge_invoker
        self.template_root: Optional[Path] = None

    def enhance_all_agents(self, template_dir: Path) -> Dict[str, bool]:
        """
        Enhance all agent files in a template directory.

        Args:
            template_dir: Root directory of template

        Returns:
            {agent_name: success_status}
        """
        self.template_root = template_dir
        agents_dir = template_dir / "agents"
        templates_dir = template_dir / "templates"

        if not agents_dir.exists():
            logger.warning(f"No agents directory in {template_dir}")
            return {}

        # Get all agent files
        agent_files = list(agents_dir.glob("*.md"))

        # Get all template files
        all_templates = list(templates_dir.rglob("*.template")) if templates_dir.exists() else []

        logger.info(f"Found {len(agent_files)} agents and {len(all_templates)} templates")
        print(f"\n{'='*60}")
        print(f"Agent Enhancement")
        print(f"{'='*60}")
        print(f"Found {len(agent_files)} agents and {len(all_templates)} templates")

        results = {}

        for agent_file in agent_files:
            agent_name = agent_file.stem
            print(f"\nEnhancing {agent_name}...")

            try:
                success = self.enhance_agent_file(agent_file, all_templates)
                results[agent_name] = success

                if success:
                    print(f"  ✓ Enhanced successfully")
                else:
                    print(f"  ⚠ No templates found, kept original")

            except Exception as e:
                logger.error(f"Error enhancing {agent_name}: {e}", exc_info=True)
                print(f"  ✗ Error: {e}")
                results[agent_name] = False

        # Summary
        successful = sum(1 for v in results.values() if v)
        print(f"\n{'='*60}")
        print(f"Enhanced {successful}/{len(results)} agents successfully")
        print(f"{'='*60}")

        return results

    def enhance_agent_file(
        self,
        agent_file: Path,
        all_templates: List[Path]
    ) -> bool:
        """
        Enhance a single agent file with template references.

        Args:
            agent_file: Path to agent markdown file
            all_templates: List of all available templates

        Returns:
            True if successful, False otherwise
        """
        # Read existing agent metadata
        agent_metadata = self._read_frontmatter(agent_file)

        # Find relevant templates (AI-powered)
        relevant_templates = self.find_relevant_templates(
            agent_metadata,
            all_templates
        )

        if not relevant_templates:
            logger.info(f"No relevant templates found for {agent_metadata.name}")
            return False

        # Generate enhanced content (AI-powered)
        enhanced_content = self.generate_enhanced_content(
            agent_metadata,
            relevant_templates
        )

        # Validate content references actual templates
        primary_templates = [t for t in relevant_templates if t.priority == 'primary']
        for template in primary_templates:
            if template.path not in enhanced_content:
                logger.warning(
                    f"Primary template {template.path} not referenced in content for {agent_metadata.name}"
                )

        # Build final agent file
        final_content = self._assemble_agent_file(agent_metadata, enhanced_content)

        # Write enhanced file
        agent_file.write_text(final_content, encoding='utf-8')

        return True

    def find_relevant_templates(
        self,
        agent_metadata: AgentMetadata,
        all_templates: List[Path]
    ) -> List[TemplateRelevance]:
        """
        Use AI to find templates relevant to this agent.

        AI-FIRST APPROACH: No hard-coded mappings!

        Args:
            agent_metadata: Agent name, description, technologies
            all_templates: List of all template file paths

        Returns:
            List of relevant templates with priority levels
        """
        # Graceful degradation if no bridge invoker
        if self.bridge_invoker is None:
            logger.warning(f"No bridge invoker available, skipping template discovery for {agent_metadata.name}")
            return []

        if not all_templates:
            logger.info("No templates available for analysis")
            return []

        # Create template listing for AI
        template_list = "\n".join([
            f"- {t.relative_to(self.template_root)}"
            for t in all_templates
        ])

        # Build request payload
        request_payload = {
            "operation": "discover_templates",
            "agent_metadata": {
                "name": agent_metadata.name,
                "description": agent_metadata.description,
                "technologies": agent_metadata.technologies
            },
            "available_templates": [
                str(t.relative_to(self.template_root))
                for t in all_templates
            ]
        }

        # Build AI prompt (token budget: 3000-4000 for planning phase)
        prompt = f"""You are analyzing which code templates are relevant to a specialized AI agent.

**Agent Information:**
- Name: {agent_metadata.name}
- Description: {agent_metadata.description}
- Technologies: {', '.join(agent_metadata.technologies)}

**Available Templates:**
{template_list}

**Your Task:**
Identify which templates are most relevant to this agent's expertise.

**Matching Criteria:**
1. **Technology Match** - Template uses agent's technologies
2. **Pattern Match** - Template demonstrates patterns in agent description
3. **Name Match** - Template name suggests relevance (e.g., "Repository" for repository-pattern agent)
4. **Code Content** - Template would be useful for someone learning this agent's domain

**Priority Levels:**
- "primary" - Perfect example, MUST include in generated content (2-3 templates)
  - Agent name/description directly matches template pattern
  - Template demonstrates core agent functionality
  - REQUIRED: Content must reference all primary templates
- "secondary" - Helpful reference, SHOULD include if space allows (1-3 templates)
  - Template shows related patterns
  - Useful as additional context
  - OPTIONAL: May be mentioned in "See Also" section
- "tertiary" - Tangentially related, MAY mention (0-2 templates)
  - Loosely connected
  - Background context only
  - OPTIONAL: Brief mention only

**Selection Rules:**
- Aim for 2-3 primary templates per agent
- If only 1 primary found, that's acceptable
- If 0 primary found, mark agent as "no enhancement needed"
- Never mark more than 5 templates as primary (too many)

**Response Format:**
Return ONLY valid JSON (no markdown, no explanation):

{{
  "templates": [
    {{
      "path": "templates/other/ConfigurationRepository.cs.template",
      "relevance": "One sentence explaining why this template is relevant",
      "priority": "primary"
    }}
  ]
}}

**Important:**
- Base relevance on ACTUAL template paths provided
- Do NOT invent template paths
- If no templates match, return empty array
- Focus on top 3-5 most relevant templates

Return the JSON now:"""

        try:
            # Invoke agent via bridge (may exit with code 42)
            response = self.bridge_invoker.invoke(
                agent_name="agent-content-enhancer",
                prompt=prompt,
                timeout_seconds=120,
                context=request_payload
            )

            # Parse JSON response
            result = self._parse_template_discovery_response(response)

            logger.info(
                f"AI identified {len(result)} relevant templates for {agent_metadata.name}"
            )

            return result

        except Exception as e:
            logger.error(f"AI template discovery failed for {agent_metadata.name}: {e}")
            return []

    def generate_enhanced_content(
        self,
        agent_metadata: AgentMetadata,
        relevant_templates: List[TemplateRelevance]
    ) -> str:
        """
        Use AI to generate enhanced agent documentation.

        AI-FIRST APPROACH: Content based on actual templates!

        Args:
            agent_metadata: Agent name, description, technologies
            relevant_templates: Templates found in discovery phase

        Returns:
            Enhanced markdown content for agent file
        """
        # Graceful degradation if no bridge invoker
        if self.bridge_invoker is None:
            logger.warning(f"No bridge invoker available, returning minimal content for {agent_metadata.name}")
            return self._get_fallback_content(agent_metadata)

        # Read template contents
        template_paths = [t.path for t in relevant_templates if t.priority == 'primary']
        template_contents = self._read_template_contents(template_paths)

        # Build template summary for AI
        template_summary = "\n".join([
            f"- **{t.path}**: {t.relevance_reason} (Priority: {t.priority})"
            for t in relevant_templates
        ])

        # Build request payload
        template_contents_dict = {}
        for path_str in template_paths[:5]:  # Limit to top 5 templates
            try:
                full_path = self.template_root / path_str
                if full_path.exists():
                    template_contents_dict[path_str] = full_path.read_text(encoding='utf-8')
            except Exception as e:
                logger.warning(f"Could not read template {path_str}: {e}")

        request_payload = {
            "operation": "generate_content",
            "agent_metadata": {
                "name": agent_metadata.name,
                "description": agent_metadata.description,
                "technologies": agent_metadata.technologies
            },
            "relevant_templates": [
                {
                    "path": t.path,
                    "relevance": t.relevance_reason,
                    "priority": t.priority
                }
                for t in relevant_templates
            ],
            "template_contents": template_contents_dict
        }

        # Build AI prompt (token budget: 5000 for implementation phase)
        prompt = f"""You are writing documentation for a specialized AI coding agent.

**Agent Information:**
- Name: {agent_metadata.name}
- Description: {agent_metadata.description}
- Technologies: {', '.join(agent_metadata.technologies)}

**Related Templates:**
{template_summary}

**Template Code Examples:**
{template_contents}

**Your Task:**
Generate comprehensive documentation sections for this agent file.

**Content Length Guidelines:**
- **Purpose**: 1-2 sentences (50-100 words)
- **When to Use**: 3-4 numbered scenarios (150-200 words total)
- **Related Templates**: 2-3 primary templates with explanations (200-300 words total)
- **Example Pattern**: Code snippet + explanation (150-250 words total)
- **Best Practices**: 3-5 practices with examples (200-300 words total)
- **Total Target**: 750-1050 words for all sections combined

**Required Sections:**

1. **Purpose** (1-2 sentences)
   - Concise description of what this agent helps with
   - Should expand on the basic description with more context

2. **When to Use This Agent** (3-4 scenarios)
   - Specific development scenarios when this agent is useful
   - Base scenarios on what the templates demonstrate
   - Format as numbered list with scenario names

3. **Related Templates** (Primary templates section)
   - List primary templates with explanations
   - For each template, explain: what it demonstrates, when to use it, key pattern
   - Use actual template paths provided

4. **Example Pattern** (Code example)
   - Show a key code pattern from the best template
   - Include code snippet with {{{{placeholders}}}}
   - Explain key features

5. **Best Practices** (3-5 practices)
   - Extract best practices from the template code
   - Base on actual patterns in templates, not generic advice
   - Include examples where helpful

**CRITICAL REQUIREMENTS:**
- Base ALL content on the actual templates provided
- Use ONLY the template paths given (don't invent paths)
- Extract patterns from the actual template code
- Be specific and actionable, not generic
- Include code examples with proper placeholders

**Format:**
Return the sections in markdown format, properly formatted for inclusion in agent file.
Use proper markdown headings (##), code blocks with language tags, and lists.

Return the enhanced content now:"""

        try:
            # Invoke agent via bridge (may exit with code 42)
            response = self.bridge_invoker.invoke(
                agent_name="agent-content-enhancer",
                prompt=prompt,
                timeout_seconds=120,
                context=request_payload
            )

            logger.info(
                f"AI generated enhanced content for {agent_metadata.name} "
                f"({len(response)} chars)"
            )

            return response

        except Exception as e:
            logger.error(f"AI content generation failed for {agent_metadata.name}: {e}")
            # Return minimal content on failure
            return self._get_fallback_content(agent_metadata)

    def _get_fallback_content(self, agent_metadata: AgentMetadata) -> str:
        """
        Generate minimal fallback content when AI enhancement fails.

        Args:
            agent_metadata: Agent metadata

        Returns:
            Minimal markdown content
        """
        return f"""## Purpose

{agent_metadata.description}

## When to Use This Agent

Use this agent when working with {', '.join(agent_metadata.technologies)}.

## Technologies

{self._format_bullet_list(agent_metadata.technologies)}

## Usage in Taskwright

This agent is automatically invoked during `/task-work` when the task involves {agent_metadata.name.replace('-', ' ')}."""

    def _read_frontmatter(self, agent_file: Path) -> AgentMetadata:
        """
        Read and parse agent file frontmatter.

        Args:
            agent_file: Path to agent markdown file

        Returns:
            AgentMetadata object
        """
        content = agent_file.read_text(encoding='utf-8')
        post = frontmatter.loads(content)
        metadata = post.metadata

        return AgentMetadata(
            name=metadata.get('name', agent_file.stem),
            description=metadata.get('description', ''),
            priority=metadata.get('priority', 7),
            technologies=metadata.get('technologies', []),
            file_path=agent_file
        )

    def _read_template_contents(
        self,
        template_paths: List[str],
        max_lines_per_template: int = 50
    ) -> str:
        """
        Read template file contents for AI analysis.

        Args:
            template_paths: List of template file paths (relative to template_root)
            max_lines_per_template: Limit lines per template (prevent token overflow)

        Returns:
            Formatted string with template contents
        """
        contents = []

        for path_str in template_paths[:5]:  # Limit to top 5 templates
            try:
                full_path = self.template_root / path_str
                if not full_path.exists():
                    logger.warning(f"Template not found: {path_str}")
                    continue

                lines = full_path.read_text(encoding='utf-8').splitlines()

                # Truncate if too long
                if len(lines) > max_lines_per_template:
                    lines = lines[:max_lines_per_template]
                    lines.append("... (truncated)")

                content = "\n".join(lines)

                contents.append(f"""
**Template: {path_str}**
```
{content}
```
""")
            except Exception as e:
                logger.warning(f"Could not read {path_str}: {e}")
                continue

        return "\n\n".join(contents) if contents else "No template contents available"

    def _parse_template_discovery_response(self, response: str) -> List[TemplateRelevance]:
        """
        Parse AI response for template discovery.

        Args:
            response: AI JSON response

        Returns:
            List of TemplateRelevance objects
        """
        # Try direct JSON parsing
        try:
            data = json.loads(response.strip())
            templates = data.get('templates', [])

            return [
                TemplateRelevance(
                    path=t['path'],
                    relevance_reason=t['relevance'],
                    priority=t['priority']
                )
                for t in templates
            ]
        except json.JSONDecodeError:
            # Try stripping markdown wrappers
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned.split("```json\n", 1)[1] if "\n" in cleaned else cleaned[7:]
                cleaned = cleaned.rsplit("```", 1)[0]
            elif cleaned.startswith("```"):
                cleaned = cleaned.split("```\n", 1)[1] if "\n" in cleaned else cleaned[3:]
                cleaned = cleaned.rsplit("```", 1)[0]

            try:
                data = json.loads(cleaned.strip())
                templates = data.get('templates', [])

                return [
                    TemplateRelevance(
                        path=t['path'],
                        relevance_reason=t['relevance'],
                        priority=t['priority']
                    )
                    for t in templates
                ]
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response: {e}")
                logger.debug(f"Response preview: {response[:200]}")
                return []

    def _assemble_agent_file(
        self,
        agent_metadata: AgentMetadata,
        enhanced_content: str
    ) -> str:
        """
        Assemble final enhanced agent file.

        Args:
            agent_metadata: Agent metadata
            enhanced_content: AI-generated content

        Returns:
            Complete agent file content
        """
        # Format technologies for YAML
        tech_yaml = "\n".join([f"  - {tech}" for tech in agent_metadata.technologies])

        return f"""---
name: {agent_metadata.name}
description: {agent_metadata.description}
priority: {agent_metadata.priority}
technologies:
{tech_yaml}
---

# {self._format_title(agent_metadata.name)}

{enhanced_content}

## Technologies

{self._format_bullet_list(agent_metadata.technologies)}

## Usage in Taskwright

This agent is automatically invoked during `/task-work` when the task involves {agent_metadata.name.replace('-', ' ')}.
"""

    def _format_title(self, name: str) -> str:
        """
        Format agent name as title.

        Args:
            name: Agent name (e.g., 'repository-pattern-specialist')

        Returns:
            Formatted title (e.g., 'Repository Pattern Specialist')
        """
        return name.replace('-', ' ').title()

    def _format_bullet_list(self, items: List[str]) -> str:
        """
        Format list as markdown bullets.

        Args:
            items: List of items

        Returns:
            Markdown bullet list
        """
        return "\n".join([f"- {item}" for item in items])
