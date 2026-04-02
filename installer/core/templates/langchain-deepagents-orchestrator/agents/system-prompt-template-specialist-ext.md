# System Prompt Template Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **system-prompt-template-specialist** agent.

**Core documentation**: See [system-prompt-template-specialist.md](./system-prompt-template-specialist.md)

---

## Related Templates

### `templates/other/prompts/orchestrator_prompts.py.template`
Defines `ORCHESTRATOR_SYSTEM_PROMPT` as a typed string constant with two runtime placeholders: `{date}` (ISO date injected at agent creation time) and `{domain_prompt}` (domain-specific instructions loaded from `domains/{domain}/DOMAIN.md`). This is the canonical example of a multi-placeholder domain-agnostic prompt.

### `templates/other/prompts/evaluator_prompts.py.template`
Demonstrates the two-phase prompt construction technique required when a prompt body contains literal JSON braces (e.g. a verdict schema). Phase 1 injects the schema via `%`-formatting; Phase 2 escapes all remaining braces then restores the `{date}` placeholder so `str.format(date=...)` works at runtime without colliding with JSON syntax.

### `templates/other/prompts/__init__.py.template`
Provides the re-export shim that surfaces all four prompt constants (`ORCHESTRATOR_SYSTEM_PROMPT`, `IMPLEMENTER_SYSTEM_PROMPT`, `EVALUATOR_SYSTEM_PROMPT`, `EVALUATOR_VERDICT_SCHEMA`) through a single `from prompts import ...` import. The `__all__` list is the authoritative public API for the prompts package.

### `templates/other/agents/agents.py.template`
Shows exactly how prompt constants are consumed: `datetime.date.today().isoformat()` provides the `date` value, `ORCHESTRATOR_SYSTEM_PROMPT.format(date=today, domain_prompt=domain_prompt)` performs injection, and the resolved string is passed as `system_prompt=` to `create_deep_agent()` or `SubAgent()`.

### `templates/other/other/agent.py.template`
The entrypoint that wires YAML config to model selection and `_load_domain_prompt()` to domain context loading, then calls `_build_agent()` to produce the module-level `agent` variable referenced by `langgraph.json`.

## Code Examples

### Example 1: Standard single-placeholder prompt (DO)

For prompts whose body contains no literal JSON braces, define a typed string constant directly and use a single `str.format()` call at agent creation time.

```python
# templates/other/prompts/implementer_prompts.py.template
IMPLEMENTER_SYSTEM_PROMPT: str = """\
You are the **Implementer** — a focused execution agent responsible for
producing high-quality outputs based on the plan and instructions provided by
the Orchestrator.

Today's date: {date}

## Quality Standards

- All code outputs must be syntactically valid.
- All functions and classes must include docstrings.
- Error handling must be present for any I/O or external operations.
- No hardcoded secrets, credentials, or environment-specific paths.
"""

# At agent creation time (templates/other/agents/agents.py.template):
today = datetime.date.today().isoformat()
prompt = IMPLEMENTER_SYSTEM_PROMPT.format(date=today)
return SubAgent(
    name="implementer",
    system_prompt=prompt,
    model=model,
    tools=list(_ORCHESTRATOR_TOOLS),
)
```

**Why**: The constant stays domain-agnostic; the date is always fresh; `str.format()` raises `KeyError` immediately if a placeholder is missing, making errors visible at startup rather than silently producing wrong prompts.

---

### Example 2: Two-phase construction for prompts with embedded JSON (DO)

When the prompt body must contain literal JSON braces (e.g. a verdict schema), use `%`-formatting to inject the schema first, then escape all remaining braces before restoring the runtime `{date}` placeholder.

```python
# templates/other/prompts/evaluator_prompts.py.template
EVALUATOR_VERDICT_SCHEMA: str = """\
{
  "decision": "accept|revise|reject",
  "score": "<integer 1-5>",
  "issues": ["<list of specific issues found, empty if none>"],
  "criteria_met": "<boolean>",
  "quality_assessment": "high|adequate|needs_revision"
}\
"""

def _build_evaluator_prompt() -> str:
    # Phase 1: inject schema via %-formatting (no curly-brace conflict).
    raw = """\
You are the **Evaluator** — an objective quality-assurance agent.

Today's date: __DATE_PLACEHOLDER__

## Verdict Schema

\\n""" % EVALUATOR_VERDICT_SCHEMA

    # Phase 2: escape ALL remaining curly braces, then restore the date placeholder.
    escaped = raw.replace("{", "{{").replace("}", "}}")
    prompt = escaped.replace("__DATE_PLACEHOLDER__", "{date}")
    return prompt

EVALUATOR_SYSTEM_PROMPT: str = _build_evaluator_prompt()
```

**Why**: If you used `str.format()` directly on a string containing `{"decision": ...}`, Python raises `KeyError: 'decision'`. The two-phase approach keeps the schema readable in source while making the final constant safe for `str.format(date=...)`.

**DON'T do this** — it will raise `KeyError` at runtime:

```python
# WRONG: raw JSON braces collide with str.format() placeholders
BAD_PROMPT = """
Verdict: {"decision": "accept"}  # KeyError: 'decision'
Date: {date}
"""
prompt = BAD_PROMPT.format(date="2026-03-30")  # crashes
```

---

### Example 3: Re-export shim with typed `__all__` (DO)

Organise per-role prompt modules under a package and expose a clean import surface via `__init__.py`.

```python
# templates/other/prompts/__init__.py.template
"""
Prompt constants for all three agent roles.
Domain-specific instructions are injected at runtime via placeholders.
"""

from {{ProjectName}}.orchestrator_prompts import ORCHESTRATOR_SYSTEM_PROMPT
from {{ProjectName}}.implementer_prompts import IMPLEMENTER_SYSTEM_PROMPT
from {{ProjectName}}.evaluator_prompts import EVALUATOR_SYSTEM_PROMPT, EVALUATOR_VERDICT_SCHEMA

__all__ = [
    "ORCHESTRATOR_SYSTEM_PROMPT",
    "IMPLEMENTER_SYSTEM_PROMPT",
    "EVALUATOR_SYSTEM_PROMPT",
    "EVALUATOR_VERDICT_SCHEMA",
]
```

Consumers then import with a single line:

```python
from prompts import ORCHESTRATOR_SYSTEM_PROMPT, IMPLEMENTER_SYSTEM_PROMPT
```

**Why**: Centralising exports in `__init__.py` decouples consumers from internal module layout. Adding or renaming a module only requires updating the shim, not every import site.

---

### Example 4: Orchestrator prompt with dual placeholders (DO)

For prompts that accept both a runtime date and a runtime domain context, declare both placeholders explicitly and document them in the module docstring.

```python
# templates/other/prompts/orchestrator_prompts.py.template
ORCHESTRATOR_SYSTEM_PROMPT: str = """\
You are the **Orchestrator** — the top-level reasoning and coordination agent.

Today's date: {date}

## Domain-Specific Instructions

{domain_prompt}
"""

# Injection in templates/other/agents/agents.py.template:
today = datetime.date.today().isoformat()
system_prompt = ORCHESTRATOR_SYSTEM_PROMPT.format(
    date=today,
    domain_prompt=domain_prompt,  # loaded from domains/{domain}/DOMAIN.md
)
graph = create_deep_agent(
    model=reasoning_model,
    system_prompt=system_prompt,
    subagents=subagents,
    memory=["./AGENTS.md"],
)
```

**Why**: Keeping both placeholders in the constant (not hard-coded at call sites) means the full prompt is readable in one place and every injection point is explicit and auditable.

---

## Verdict Schema Reference

The Evaluator returns structured JSON matching this schema (from `evaluator_prompts.py.template`):

```json
{
  "decision": "accept|revise|reject",
  "score": "<integer 1-5>",
  "issues": ["<list of specific issues found>"],
  "criteria_met": "<boolean>",
  "quality_assessment": "high|adequate|needs_revision"
}
```

The orchestrator should validate the verdict before acting on it:

```python
import json

def validate_verdict(raw_verdict: str) -> dict:
    """Parse and validate an evaluator verdict JSON string."""
    verdict = json.loads(raw_verdict)
    assert verdict["decision"] in ("accept", "revise", "reject")
    assert isinstance(verdict["score"], int) and 1 <= verdict["score"] <= 5
    assert isinstance(verdict["issues"], list)
    assert isinstance(verdict["criteria_met"], bool)
    assert verdict["quality_assessment"] in ("high", "adequate", "needs_revision")
    return verdict
```

## Testing Prompts

Validate that all placeholders resolve without `KeyError`:

```python
def test_orchestrator_prompt_resolves():
    from prompts import ORCHESTRATOR_SYSTEM_PROMPT
    result = ORCHESTRATOR_SYSTEM_PROMPT.format(
        date="2026-01-15",
        domain_prompt="Test domain guidelines."
    )
    assert "2026-01-15" in result
    assert "Test domain guidelines." in result
    assert "{date}" not in result
    assert "{domain_prompt}" not in result

def test_evaluator_prompt_resolves():
    from prompts import EVALUATOR_SYSTEM_PROMPT
    result = EVALUATOR_SYSTEM_PROMPT.format(date="2026-01-15")
    assert "2026-01-15" in result
    assert "{date}" not in result
    # Verify JSON braces in schema are preserved (not consumed by .format)
    assert '"decision"' in result
```

*This extended documentation is part of GuardKit's progressive disclosure system.*
