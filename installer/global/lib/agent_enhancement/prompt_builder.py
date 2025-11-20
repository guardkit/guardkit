"""
Enhancement Prompt Builder

Builds prompts for AI-powered agent enhancement.

TASK-PHASE-8-INCREMENTAL: Shared module for agent enhancement
"""

from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class EnhancementPromptBuilder:
    """Builds AI prompts for agent enhancement."""

    def build(
        self,
        agent_metadata: Dict[str, Any],
        templates: List[Path],
        template_dir: Path
    ) -> str:
        """
        Build enhancement prompt for AI agent.

        Args:
            agent_metadata: Agent metadata from frontmatter
            templates: List of template file paths
            template_dir: Template root directory

        Returns:
            Formatted prompt string for agent-content-enhancer

        Example Output:
            ```
            Enhance the following agent with template-specific content:

            Agent Name: testing-specialist
            Agent Description: Provides guidance on testing strategies

            Available Templates (15):
            - templates/tests/unit/ComponentTest.tsx.template
            - templates/tests/integration/ApiTest.tsx.template
            ...

            Please provide enhancement in JSON format:
            {
                "sections": ["related_templates", "examples", "best_practices"],
                "related_templates": "## Related Templates\\n\\n...",
                "examples": "## Code Examples\\n\\n...",
                "best_practices": "## Best Practices\\n\\n..."
            }
            ```
        """
        agent_name = agent_metadata.get("name", "unknown")
        agent_description = agent_metadata.get("description", "No description available")

        # Format template list
        template_list = []
        for template in templates[:20]:  # Limit to first 20 to avoid token overflow
            rel_path = template.relative_to(template_dir)
            template_list.append(f"- {rel_path}")

        if len(templates) > 20:
            template_list.append(f"... and {len(templates) - 20} more templates")

        prompt = f"""Enhance the following agent with template-specific content:

**Agent Name**: {agent_name}
**Agent Description**: {agent_description}

**Available Templates** ({len(templates)} total):
{chr(10).join(template_list)}

**Task**: Generate enhancement content for this agent including:
1. Related templates that this agent should reference
2. Code examples from the templates that demonstrate best practices
3. Best practices for using this agent with these templates
4. Anti-patterns to avoid (if applicable)

**Output Format**: Return a JSON object with the following structure:
```json
{{
    "sections": ["related_templates", "examples", "best_practices"],
    "related_templates": "## Related Templates\\n\\n- template1\\n- template2\\n...",
    "examples": "## Code Examples\\n\\n### Example 1\\n```code```\\n...",
    "best_practices": "## Best Practices\\n\\n1. Practice 1\\n2. Practice 2\\n..."
}}
```

**Important**:
- Use markdown formatting for all sections
- Include actual code snippets in examples
- Be specific and actionable in best practices
- Only reference templates that are actually relevant to this agent
- Ensure all JSON is valid and properly escaped
"""

        return prompt

    def build_minimal(self, agent_name: str, template_count: int) -> str:
        """
        Build minimal prompt for quick enhancement (used for testing).

        Args:
            agent_name: Name of agent to enhance
            template_count: Number of available templates

        Returns:
            Minimal prompt string
        """
        return f"""Enhance agent '{agent_name}' with {template_count} templates.

Return JSON:
{{
    "sections": ["related_templates"],
    "related_templates": "## Related Templates\\n\\n(list templates)"
}}
"""
