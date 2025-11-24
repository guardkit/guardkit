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
3. Boundaries (ALWAYS/NEVER/ASK framework) for explicit behavior rules
4. Anti-patterns to avoid (if applicable)

**Output Format**: You MUST return a JSON object conforming to this schema:

```json
{{
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["sections", "related_templates", "examples", "boundaries"],
    "properties": {{
        "sections": {{
            "type": "array",
            "items": {{"type": "string"}},
            "minItems": 3,
            "description": "List of section names being provided"
        }},
        "related_templates": {{
            "type": "string",
            "minLength": 50,
            "description": "Markdown section listing relevant templates"
        }},
        "examples": {{
            "type": "string",
            "minLength": 100,
            "description": "Markdown section with code examples from templates"
        }},
        "boundaries": {{
            "type": "string",
            "minLength": 500,
            "pattern": ".*## Boundaries.*### ALWAYS.*### NEVER.*### ASK.*",
            "description": "Markdown section with ALWAYS/NEVER/ASK framework (REQUIRED)"
        }}
    }}
}}
```

**Example Valid Response**:
```json
{{
    "sections": ["related_templates", "examples", "boundaries"],
    "related_templates": "## Related Templates\\n\\n- templates/api/endpoint.ts.template\\n- templates/api/service.ts.template",
    "examples": "## Code Examples\\n\\n### Example 1: API Endpoint\\n```typescript\\napp.get('/api/users', async (req, res) => {{...}})\\n```",
    "boundaries": "## Boundaries\\n\\n### ALWAYS\\n- ✅ Validate input parameters (prevent injection attacks)\\n- ✅ Return typed responses (ensure type safety)\\n- ✅ Handle errors gracefully (improve user experience)\\n- ✅ Log request details (aid debugging)\\n- ✅ Use async/await (prevent callback hell)\\n\\n### NEVER\\n- ❌ Never expose raw database queries (security risk)\\n- ❌ Never return stack traces to client (information leakage)\\n- ❌ Never use synchronous I/O in endpoints (blocks event loop)\\n- ❌ Never skip authentication checks (authorization bypass)\\n- ❌ Never hardcode credentials (credential leakage)\\n\\n### ASK\\n- ⚠️ Rate limiting threshold: Ask if >1000 req/min acceptable\\n- ⚠️ Caching strategy: Ask if Redis vs in-memory for session data\\n- ⚠️ Pagination size: Ask if 50 items/page acceptable for performance"
}}
```

**Critical Notes**:
- The `boundaries` field is **REQUIRED** by schema - responses without it will be rejected
- Boundaries must include all three subsections (ALWAYS/NEVER/ASK) with minimum counts:
  - ALWAYS: 5-7 rules with ✅ prefix
  - NEVER: 5-7 rules with ❌ prefix
  - ASK: 3-5 scenarios with ⚠️ prefix
- Format: "[emoji] [action] ([brief rationale])"
- Minimum 500 characters ensures substantive content
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
