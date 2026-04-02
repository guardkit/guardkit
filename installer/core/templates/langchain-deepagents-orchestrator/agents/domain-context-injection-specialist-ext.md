# Domain Context Injection Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **domain-context-injection-specialist** agent.

**Core documentation**: See [domain-context-injection-specialist.md](./domain-context-injection-specialist.md)

---

## Related Templates

### Primary Templates

- **`templates/other/other/agent.py.template`** — Entrypoint that owns the full domain context lifecycle: `_load_domain_prompt()` reads `domains/{domain}/DOMAIN.md` via `pathlib.Path.read_text(encoding="utf-8")`, catches `FileNotFoundError` and `OSError | UnicodeDecodeError`, and returns `_DEFAULT_DOMAIN_PROMPT` on any failure. Also demonstrates CLI `--domain` argument wiring using `argparse.parse_known_args()` so the LangGraph server cannot inject unexpected `sys.argv` values that would raise `SystemExit`. The `_build_agent()` helper keeps wiring logic testable in isolation.

- **`templates/other/agents/agents.py.template`** — Agent factory that injects the loaded domain prompt into `ORCHESTRATOR_SYSTEM_PROMPT` via `.format(date=today, domain_prompt=domain_prompt)` inside `create_orchestrator()`. Passes `memory=["./AGENTS.md"]` to `create_deep_agent()` so boundary rules are loaded at startup. Demonstrates `SubAgent` and `AsyncSubAgent` TypedDict construction and why subagents (implementer, evaluator, builder) carry no `{domain_prompt}` placeholder — domain context flows to them at delegation time through task context strings.

- **`templates/other/prompts/orchestrator_prompts.py.template`** — Contains the `{domain_prompt}` insertion point inside the `## Domain-Specific Instructions` section. The rest of the prompt is fully domain-agnostic: no hardcoded technology stack, language, or framework assumptions. Also shows the `{date}` placeholder pattern used consistently across all three prompt modules.

### Supporting Templates

- **`templates/other/prompts/implementer_prompts.py.template`** — Confirms the domain-agnostic subagent pattern: no `{domain_prompt}` placeholder present. Domain context arrives via the orchestrator's delegation message, not the system prompt.

- **`templates/other/prompts/evaluator_prompts.py.template`** — Shows the two-phase prompt-building technique required when a prompt embeds JSON schema literals (which contain raw `{` and `}` characters). Phase 1 uses `%`-formatting to inject the schema; Phase 2 escapes all curly braces then restores the `__DATE_PLACEHOLDER__` sentinel so `str.format(date=...)` works at runtime without colliding with JSON braces.

- **`templates/other/tools/orchestrator_tools.py.template`** — Demonstrates the consistent defensive I/O pattern used throughout: `pathlib.Path.read_text(encoding="utf-8")` inside a `try/except (OSError, UnicodeDecodeError)` block, all tools returning strings and never raising exceptions, and `@tool(parse_docstring=True)` decoration.

## Code Examples

### Example 1 — Defensive Domain Context Loading (agent.py.template)

This is the canonical pattern for loading `domains/{domain}/DOMAIN.md`. The two-level `except` chain ensures the orchestrator always receives a valid string, even when the domain directory does not exist or the file contains non-UTF-8 bytes.

```python
# DO: two-level defensive fallback — FileNotFoundError first, then broad I/O errors
_DEFAULT_DOMAIN_PROMPT = (
    "No domain-specific guidelines loaded. "
    "Follow general software engineering best practices."
)

def _load_domain_prompt(project_root: Path, domain: str) -> str:
    domain_path = project_root / "domains" / domain / "DOMAIN.md"
    try:
        return domain_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning(
            "Domain file not found at %s — using default prompt.", domain_path
        )
        return _DEFAULT_DOMAIN_PROMPT
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning(
            "Failed to read domain file %s (%s) — using default prompt.",
            domain_path, exc,
        )
        return _DEFAULT_DOMAIN_PROMPT
```

```python
# DON'T: single bare except or no fallback — orchestrator startup fails on missing domain
def _load_domain_prompt_bad(project_root: Path, domain: str) -> str:
    domain_path = project_root / "domains" / domain / "DOMAIN.md"
    return domain_path.read_text()  # raises on missing file, wrong encoding, or permission error
```

**Key points**:
- `FileNotFoundError` is caught separately so the log message is distinct from generic I/O errors.
- `OSError | UnicodeDecodeError` covers permission errors, disk errors, and non-UTF-8 content.
- Always log with the full path so operators can diagnose missing domain directories quickly.
- Return the exact same `_DEFAULT_DOMAIN_PROMPT` constant from both except branches — never an empty string.

---

### Example 2 — Domain Prompt Injection into Orchestrator System Prompt (agents.py.template + orchestrator_prompts.py.template)

The `create_orchestrator()` factory injects domain context at the last possible moment — after the domain file has been successfully loaded — using Python's standard `str.format()`.

```python
# orchestrator_prompts.py — the placeholder lives in its own section
ORCHESTRATOR_SYSTEM_PROMPT: str = """\
...
## Domain-Specific Instructions

{domain_prompt}

---
"""

# agents.py — injection at factory time
def create_orchestrator(
    reasoning_model: str,
    implementation_model: str,
    domain_prompt: str,          # loaded by _load_domain_prompt() in agent.py
) -> CompiledStateGraph:
    today = datetime.date.today().isoformat()
    system_prompt = ORCHESTRATOR_SYSTEM_PROMPT.format(
        date=today,
        domain_prompt=domain_prompt,   # single injection point
    )

    graph = create_deep_agent(
        model=reasoning_model,
        tools=list(_ORCHESTRATOR_TOOLS),
        system_prompt=system_prompt,
        subagents=subagents,
        memory=["./AGENTS.md"],   # boundary rules loaded here
        skills=None,
        context_schema=None,
    )
    return graph
```

```python
# DON'T: inject domain_prompt directly into subagent system prompts
# Subagents are intentionally domain-agnostic — domain context flows at delegation time
def implementer_subagent_bad(model: str, domain_prompt: str) -> SubAgent:
    prompt = IMPLEMENTER_SYSTEM_PROMPT.format(date=today, domain_prompt=domain_prompt)
    # Wrong — the Implementer prompt has no {domain_prompt} placeholder by design
```

**Key points**:
- Only `ORCHESTRATOR_SYSTEM_PROMPT` contains `{domain_prompt}`. Subagent prompts are strictly domain-agnostic.
- `memory=["./AGENTS.md"]` is passed to `create_deep_agent()`, not to subagents.
- Both `{date}` and `{domain_prompt}` are resolved in one `.format()` call inside `create_orchestrator()`.

---

### Example 3 — Two-Phase Evaluator Prompt Building (evaluator_prompts.py.template)

When a prompt string must embed literal JSON, `str.format()` would raise `KeyError` on those braces. The evaluator template solves this with a two-phase build function.

```python
# DO: inject JSON schema via %-formatting first, then escape braces for str.format()
def _build_evaluator_prompt() -> str:
    raw = """\
You are the **Evaluator** ...
Today's date: __DATE_PLACEHOLDER__
...

""" % EVALUATOR_VERDICT_SCHEMA

    escaped = raw.replace("{", "{{").replace("}", "}}"  )
    prompt = escaped.replace("__DATE_PLACEHOLDER__", "{date}")
    return prompt

EVALUATOR_SYSTEM_PROMPT: str = _build_evaluator_prompt()
```

```python
# DON'T: mix JSON literals and str.format() placeholders in the same raw string
BAD_PROMPT = """
{"decision": "accept"}  <- braces cause KeyError in .format(date=today)
Today is {date}
"""
```

---

### Example 4 — CLI Domain Selection with parse_known_args (agent.py.template)

```python
# DO: use parse_known_args() to tolerate unexpected argv from LangGraph server
_arg_parser = argparse.ArgumentParser(description="DeepAgents orchestrator exemplar")
_arg_parser.add_argument(
    "--domain",
    default=DEFAULT_DOMAIN,  # "example-domain"
    help="Domain name to load from domains/{domain}/DOMAIN.md",
)
_parsed_args, _unknown_args = _arg_parser.parse_known_args()

_domain_prompt = _load_domain_prompt(_PROJECT_ROOT, _parsed_args.domain)
agent = _build_agent(_config, _domain_prompt)
```

```python
# DON'T: use parse_args() at module level — LangGraph server injects its own argv
_parsed_args = _arg_parser.parse_args()  # raises SystemExit on unknown LangGraph flags
```

---

## Complete Domain Loading Flow

```
CLI: --domain finance-domain
        │
        ▼
_arg_parser.parse_known_args()
        │  _parsed_args.domain = "finance-domain"
        ▼
_load_domain_prompt(_PROJECT_ROOT, "finance-domain")
        │  Reads: _PROJECT_ROOT / "domains" / "finance-domain" / "DOMAIN.md"
        ├─ [found]        → returns content as string
        ├─ [FileNotFound] → logger.warning + returns _DEFAULT_DOMAIN_PROMPT
        └─ [OSError/UTF8] → logger.warning + returns _DEFAULT_DOMAIN_PROMPT
        │
        ▼
create_orchestrator(..., domain_prompt=_domain_prompt)
        │  ORCHESTRATOR_SYSTEM_PROMPT.format(date=today, domain_prompt=domain_prompt)
        ▼
create_deep_agent(..., memory=["./AGENTS.md"])
```

Domain prompt travels as a plain string from `_load_domain_prompt()` to `ORCHESTRATOR_SYSTEM_PROMPT.format()`. Subagents never receive it — they are domain-agnostic by design.

## DOMAIN.md Example

Example for a finance domain (`domains/finance-domain/DOMAIN.md`):

```markdown
## Domain Description
Financial services data pipelines processing transaction records.

## Technology Stack
- Python 3.12, pandas 2.x, httpx (async), pydantic v2
- Raw SQL via psycopg3 (no ORM)

## Coding Standards
- Currency values: always `Decimal`, never `float`
- Dates: `datetime.date` (UTC); datetimes: `datetime.datetime` with tzinfo
- All public functions must have type annotations
- Max function length: 50 lines

## Project Constraints
- Must pass `ruff check` and `mypy --strict`
- File writes restricted to `output/` directory
```

## AGENTS.md Example

```markdown
# Agent Boundary Rules

## Code Quality
- All generated code must have type annotations
- Tests must use pytest and be named test_*.py
- Never generate code that hardcodes secrets or API keys

## Execution Safety
- Shell commands that delete files require explicit confirmation
- Never run pip install without flagging for review
- Write operations restricted to src/, tests/, and output/
```

---

*This extended documentation is part of GuardKit's progressive disclosure system.*
