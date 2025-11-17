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

# TASK-PHASE-7-5-BATCH-PROCESSING: Import WorkflowPhase from constants to avoid circular import
import importlib
_constants_module = importlib.import_module('installer.global.lib.template_creation.constants')
WorkflowPhase = _constants_module.WorkflowPhase

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
        self._templates_written_to_disk: bool = False

    def enhance_all_agents(self, template_dir: Path) -> Dict[str, Any]:
        """
        Enhance all agent files in a template directory using batch processing.

        ARCHITECTURAL CHANGE (TASK-PHASE-7-5-BATCH-PROCESSING):
        - Replaced loop-based enhancement with single batch invocation
        - Eliminates checkpoint-resume cycles within Phase 7.5
        - Processes all agents in one AI invocation for consistency

        Args:
            template_dir: Root directory of template

        Returns:
            Dict with:
                - status: 'success', 'skipped', or 'failed'
                - enhanced_count: Number of agents successfully enhanced
                - failed_count: Number of agents that failed enhancement
                - total_count: Total number of agents
                - success_rate: Percentage of successful enhancements
                - errors: List of error messages
        """
        self.template_root = template_dir
        agents_dir = template_dir / "agents"
        templates_dir = template_dir / "templates"

        if not agents_dir.exists():
            logger.warning(f"No agents directory in {template_dir}")
            return self._create_skip_result([], [])

        # Get all agent files
        agent_files = list(agents_dir.glob("*.md"))

        # Get all template files
        all_templates = list(templates_dir.rglob("*.template")) if templates_dir.exists() else []

        logger.info(f"Phase {WorkflowPhase.PHASE_7_5}: Found {len(agent_files)} agents and {len(all_templates)} templates")
        print(f"\n{'='*60}")
        print(f"Agent Enhancement (Batch Processing)")
        print(f"{'='*60}")
        print(f"Found {len(agent_files)} agents and {len(all_templates)} templates")

        # Check if we have templates to enhance with
        if not all_templates:
            logger.warning("No templates available for agent enhancement")
            return self._create_skip_result(agent_files, all_templates)

        # CRITICAL: Ensure templates are written to disk before batch enhancement
        # This allows agent-content-enhancer to read actual template files
        self._ensure_templates_on_disk(template_dir)

        # BATCH PROCESSING - Single invocation for all agents
        batch_result = self._batch_enhance_agents(agent_files, all_templates, template_dir)

        return batch_result

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

    # ========================================================================
    # BATCH PROCESSING IMPLEMENTATION (TASK-PHASE-7-5-BATCH-PROCESSING)
    # ========================================================================

    def _ensure_templates_on_disk(self, output_path: Path) -> None:
        """
        Ensure templates are written to disk before Phase 7.5.

        Phase 7.5 (agent enhancement) requires templates on disk so that
        agent-content-enhancer can read actual template files for accurate
        content generation.

        This method is idempotent - safe to call multiple times.

        Args:
            output_path: Template output directory

        Note:
            This is a placeholder for orchestrator integration.
            In the actual workflow, the orchestrator calls this method
            before Phase 7.5 runs.
        """
        if self._templates_written_to_disk:
            logger.debug("Templates already on disk, skipping write")
            return

        templates_dir = output_path / "templates"
        if templates_dir.exists() and list(templates_dir.rglob("*.template")):
            logger.debug(f"Templates found on disk: {templates_dir}")
            self._templates_written_to_disk = True
        else:
            logger.warning(f"No templates found on disk at {templates_dir}")

    def _batch_enhance_agents(
        self,
        agent_files: List[Path],
        all_templates: List[Path],
        output_path: Path
    ) -> Dict[str, Any]:
        """
        Process all agents in a single batch invocation.

        ARCHITECTURAL RATIONALE:
        - Single AI invocation for all agents ensures consistency
        - Eliminates checkpoint-resume cycles within Phase 7.5
        - Reduces total workflow time by ~60 seconds
        - Better token efficiency (shared context)

        Args:
            agent_files: List of agent markdown files
            all_templates: List of all template file paths
            output_path: Template output directory

        Returns:
            Dict with status, counts, success_rate, and errors
        """
        if self.bridge_invoker is None:
            logger.warning("No bridge invoker available - skipping enhancement")
            return self._create_skip_result(agent_files, all_templates)

        # Build batch request with all agent metadata and template catalog
        batch_request = self._build_batch_enhancement_request(agent_files, all_templates)

        # Single bridge invocation for all agents
        logger.info(
            f"Phase {WorkflowPhase.PHASE_7_5}: Invoking agent-content-enhancer "
            f"for {len(agent_files)} agents (batch mode)"
        )
        print(f"\nInvoking agent-content-enhancer for batch enhancement...")

        try:
            # Invoke agent bridge with structured batch request
            batch_response = self.bridge_invoker.invoke(
                agent_name="agent-content-enhancer",
                prompt=self._build_batch_prompt(batch_request),
                timeout_seconds=180,  # Longer timeout for batch processing
                context={
                    "mode": "batch",
                    "phase": WorkflowPhase.PHASE_7_5,
                    "agent_count": len(agent_files),
                    "template_count": len(all_templates),
                    "output_path": str(output_path)
                }
            )

        except SystemExit as e:
            # Propagate SystemExit(42) for checkpoint-resume pattern
            if e.code == 42:
                logger.info("Bridge invocation triggered checkpoint (exit code 42)")
                raise
            # Other exit codes are errors
            logger.error(f"Bridge invocation failed with exit code {e.code}")
            return self._create_error_result(f"Bridge exit code {e.code}", agent_files)

        except Exception as e:
            logger.error(f"Batch enhancement failed: {e}", exc_info=True)
            return self._create_error_result(str(e), agent_files)

        # Parse and apply batch response
        return self._apply_batch_enhancements(agent_files, batch_response, output_path)

    def _build_batch_enhancement_request(
        self,
        agent_files: List[Path],
        all_templates: List[Path]
    ) -> Dict[str, Any]:
        """
        Build structured batch request for all agents.

        Request Structure:
        - agents: List of agent metadata (name, technologies, current content)
        - template_catalog: Compact listing of all templates
        - enhancement_instructions: Standardized guidelines

        Token Budget:
        - Target: 8,000-10,000 tokens (input)
        - Strategy: Use metadata instead of full content for efficiency

        Args:
            agent_files: List of agent markdown files
            all_templates: List of template file paths

        Returns:
            Structured batch request dict
        """
        # Build agent metadata list
        agents = []
        for agent_file in agent_files:
            try:
                metadata = self._read_frontmatter(agent_file)
                agents.append({
                    "name": metadata.name,
                    "technologies": metadata.technologies,
                    "description": metadata.description,
                    "file_path": str(agent_file.relative_to(self.template_root))
                })
            except Exception as e:
                logger.warning(f"Failed to read {agent_file.name}: {e}")
                continue

        # Build compact template catalog
        template_catalog = self._build_template_catalog(all_templates)

        return {
            "agents": agents,
            "template_catalog": template_catalog,
            "enhancement_instructions": self._get_enhancement_instructions()
        }

    def _build_template_catalog(self, all_templates: List[Path]) -> List[Dict[str, str]]:
        """
        Build compact template catalog for batch prompt.

        Includes only essential metadata to minimize token usage:
        - Template path (relative to template root)
        - Category (inferred from directory structure)
        - File extension (indicates technology)

        Args:
            all_templates: List of template file paths

        Returns:
            List of template metadata dicts
        """
        catalog = []

        for template_path in all_templates:
            rel_path = template_path.relative_to(self.template_root)
            parts = rel_path.parts

            # Infer category from directory structure
            category = parts[1] if len(parts) > 1 else "other"

            catalog.append({
                "path": str(rel_path),
                "category": category,
                "name": template_path.stem
            })

        return catalog

    def _get_enhancement_instructions(self) -> str:
        """
        Return standardized enhancement instructions for batch processing.

        Returns:
            Enhancement guidelines as string
        """
        return """
For each agent, enhance the agent file with:

1. **Template References** (2-3 primary templates)
   - List most relevant templates from catalog
   - Explain when to use each template
   - Include actual file paths

2. **Best Practices** (3-5 practices)
   - Extract patterns from template code
   - Base on actual template implementations
   - Include specific examples

3. **Code Examples** (1-2 realistic examples)
   - Show key patterns from templates
   - Use proper syntax for agent's technologies
   - Include placeholders with {{syntax}}

4. **Constraints** (what NOT to do)
   - Scope limitations based on templates
   - Anti-patterns to avoid
   - Technology-specific warnings

**Quality Standards:**
- Target: 150-250 lines per agent
- Preserve original frontmatter (YAML)
- Use markdown formatting (##, ```, lists)
- Base ALL content on provided templates (no invention)

**Output Format:**
Return JSON with this structure:
{
  "enhancements": [
    {
      "agent_name": "agent-file-name",
      "enhanced_content": "full enhanced markdown content including frontmatter"
    }
  ]
}
"""

    def _build_batch_prompt(self, batch_request: Dict[str, Any]) -> str:
        """
        Build AI prompt for batch enhancement.

        Args:
            batch_request: Structured batch request

        Returns:
            Complete prompt string
        """
        agents = batch_request["agents"]
        template_catalog = batch_request["template_catalog"]
        instructions = batch_request["enhancement_instructions"]

        agents_list = "\n".join([
            f"- **{a['name']}**: {a['description']} (Technologies: {', '.join(a['technologies'])})"
            for a in agents
        ])

        templates_by_category = {}
        for template in template_catalog:
            category = template["category"]
            if category not in templates_by_category:
                templates_by_category[category] = []
            templates_by_category[category].append(template["path"])

        catalog_text = ""
        for category, paths in sorted(templates_by_category.items()):
            catalog_text += f"\n**{category.title()}:**\n"
            catalog_text += "\n".join([f"  - {path}" for path in paths])

        return f"""You are enhancing AI agent documentation files with template-specific content.

**Agents to Enhance ({len(agents)} total):**
{agents_list}

**Available Templates ({len(template_catalog)} total):**
{catalog_text}

**Enhancement Instructions:**
{instructions}

**Important:**
- Process ALL agents in this batch
- Ensure each enhancement is 150-250 lines
- Base content ONLY on templates provided
- Return valid JSON with all enhancements

Generate the enhancements now:"""

    def _apply_batch_enhancements(
        self,
        agent_files: List[Path],
        batch_response: str,
        output_path: Path
    ) -> Dict[str, Any]:
        """
        Parse batch response and apply enhancements to agent files.

        Args:
            agent_files: List of agent markdown files
            batch_response: AI response (JSON string)
            output_path: Template output directory

        Returns:
            Dict with status, counts, success_rate, and errors
        """
        enhanced_count = 0
        failed_count = 0
        errors = []

        # Parse JSON response
        try:
            response_data = self._parse_batch_response(batch_response)
            enhancements = response_data.get("enhancements", [])

            if not enhancements:
                logger.error("Batch response contains no enhancements")
                return self._create_error_result("No enhancements in batch response", agent_files)

        except Exception as e:
            logger.error(f"Failed to parse batch response: {e}")
            return self._create_error_result(f"Response parsing failed: {e}", agent_files)

        # Map enhancements to agent files
        enhancement_map = {e["agent_name"]: e for e in enhancements}

        # Apply enhancements to each agent file
        for agent_file in agent_files:
            agent_name = agent_file.stem
            enhancement = enhancement_map.get(agent_name)

            if not enhancement:
                logger.warning(f"No enhancement found for {agent_name}")
                failed_count += 1
                errors.append(f"Missing enhancement for {agent_name}")
                print(f"  ⚠ No enhancement for {agent_name}")
                continue

            try:
                success = self._apply_single_enhancement(agent_file, enhancement)
                if success:
                    enhanced_count += 1
                    print(f"  ✓ Enhanced {agent_name}")
                else:
                    failed_count += 1
                    errors.append(f"Validation failed for {agent_name}")
                    print(f"  ⚠ Validation failed for {agent_name}")

            except Exception as e:
                logger.error(f"Error applying enhancement for {agent_name}: {e}")
                failed_count += 1
                errors.append(f"{agent_name}: {str(e)}")
                print(f"  ✗ Error: {e}")

        # Create result summary
        return self._create_batch_result(enhanced_count, failed_count, errors)

    def _parse_batch_response(self, response: str) -> Dict[str, Any]:
        """
        Parse AI batch response JSON.

        Handles markdown wrappers and malformed JSON gracefully.

        Args:
            response: AI response string

        Returns:
            Parsed response dict

        Raises:
            json.JSONDecodeError: If response is not valid JSON
        """
        # Try direct JSON parsing
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass

        # Try stripping markdown wrappers
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned.split("```json\n", 1)[1] if "\n" in cleaned else cleaned[7:]
            cleaned = cleaned.rsplit("```", 1)[0]
        elif cleaned.startswith("```"):
            cleaned = cleaned.split("```\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            cleaned = cleaned.rsplit("```", 1)[0]

        return json.loads(cleaned.strip())

    def _apply_single_enhancement(
        self,
        agent_file: Path,
        enhancement: Dict[str, Any]
    ) -> bool:
        """
        Apply enhancement content to single agent file.

        Args:
            agent_file: Agent markdown file path
            enhancement: Enhancement data dict with 'enhanced_content' key

        Returns:
            True if successful, False otherwise
        """
        try:
            enhanced_content = enhancement.get("enhanced_content", "")

            if not enhanced_content:
                logger.warning(f"No enhanced content for {agent_file.name}")
                return False

            # Validate enhancement quality
            if not self._validate_enhancement(enhanced_content):
                logger.warning(f"Enhancement validation failed for {agent_file.name}")
                return False

            # Write enhanced content to file
            agent_file.write_text(enhanced_content, encoding="utf-8")

            logger.info(
                f"Enhanced {agent_file.name} "
                f"({len(enhanced_content)} chars, {len(enhanced_content.splitlines())} lines)"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to apply enhancement: {e}")
            return False

    def _validate_enhancement(self, content: str) -> bool:
        """
        Validate enhanced agent content meets quality standards.

        Quality Gates:
        - Minimum length: 150 lines
        - Maximum length: 250 lines (warning, not blocking)
        - Required sections: Template References, Best Practices, Code Examples, Constraints

        Args:
            content: Enhanced markdown content

        Returns:
            True if valid, False otherwise
        """
        lines = content.split("\n")
        line_count = len(lines)

        # Minimum length check
        if line_count < 150:
            logger.warning(f"Enhancement too short: {line_count} lines (expected ≥150)")
            return False

        # Maximum length warning (not blocking)
        if line_count > 250:
            logger.warning(f"Enhancement longer than expected: {line_count} lines (target 150-250)")

        # Required sections check
        required_sections = [
            "Template References",
            "Best Practices",
            "Code Examples",
            "Constraints"
        ]

        for section in required_sections:
            if section not in content:
                logger.warning(f"Missing required section: {section}")
                return False

        return True

    # ========================================================================
    # RESULT CREATION METHODS
    # ========================================================================

    def _create_batch_result(
        self,
        enhanced_count: int,
        failed_count: int,
        errors: List[str]
    ) -> Dict[str, Any]:
        """
        Create structured batch enhancement result.

        Args:
            enhanced_count: Number of successfully enhanced agents
            failed_count: Number of failed agents
            errors: List of error messages

        Returns:
            Result dict with status, counts, success_rate, errors
        """
        total = enhanced_count + failed_count
        success_rate = (enhanced_count / total * 100) if total > 0 else 0

        result = {
            "status": "success" if enhanced_count > 0 else "failed",
            "enhanced_count": enhanced_count,
            "failed_count": failed_count,
            "total_count": total,
            "success_rate": success_rate,
            "errors": errors
        }

        # Log summary
        print(f"\n{'='*60}")
        print(f"Enhancement Summary")
        print(f"{'='*60}")
        print(f"  Enhanced: {enhanced_count}/{total} agents ({success_rate:.1f}%)")
        if errors:
            print(f"  Errors: {len(errors)}")
            for error in errors[:3]:  # Show first 3 errors
                print(f"    - {error}")
        print(f"{'='*60}")

        logger.info(
            f"Phase {WorkflowPhase.PHASE_7_5} completed: "
            f"{enhanced_count}/{total} agents enhanced ({success_rate:.1f}%)"
        )

        return result

    def _create_skip_result(
        self,
        agent_files: List[Path],
        all_templates: List[Path]
    ) -> Dict[str, Any]:
        """
        Create result when enhancement is skipped.

        Args:
            agent_files: List of agent files
            all_templates: List of template files

        Returns:
            Skip result dict
        """
        logger.info("Agent enhancement skipped - agents remain in basic form")
        print(f"\n⚠ Agent enhancement skipped (no templates or bridge invoker)")

        return {
            "status": "skipped",
            "enhanced_count": 0,
            "failed_count": 0,
            "total_count": len(agent_files),
            "success_rate": 0,
            "errors": [],
            "reason": f"No templates ({len(all_templates)}) or bridge invoker unavailable"
        }

    def _create_error_result(
        self,
        error_message: str,
        agent_files: List[Path]
    ) -> Dict[str, Any]:
        """
        Create result when enhancement fails completely.

        Args:
            error_message: Error description
            agent_files: List of agent files

        Returns:
            Error result dict
        """
        logger.error(f"Agent enhancement failed: {error_message}")
        print(f"\n✗ Agent enhancement failed: {error_message}")

        return {
            "status": "failed",
            "enhanced_count": 0,
            "failed_count": len(agent_files),
            "total_count": len(agent_files),
            "success_rate": 0,
            "errors": [error_message]
        }
