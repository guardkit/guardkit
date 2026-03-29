# Domain-Driven Configuration Pattern

`DOMAIN.md` files inject domain-specific context (generation guidelines, evaluation criteria, output schemas) into agent system prompts at runtime. This makes the adversarial cooperation system domain-agnostic — switch domains by swapping the DOMAIN.md file.

## Core Pattern: _load_domain_prompt()

The entrypoint (`agent.py`) loads domain context at startup and passes it to both agent factories:

```python
def _load_domain_prompt(domain: str) -> str:
    """Read DOMAIN.md for the specified domain."""
    domain_path = pathlib.Path("domains") / domain / "DOMAIN.md"
    if not domain_path.exists():
        raise FileNotFoundError(f"Domain config not found: {domain_path}")
    return domain_path.read_text()

# Module-level wiring
_domain = _get_domain()  # from --domain CLI arg or DOMAIN env var
_domain_prompt = _load_domain_prompt(_domain)

_player = create_player(model=_player_model, domain_prompt=_domain_prompt)
_coach = create_coach(model=_coach_model, domain_prompt=_domain_prompt)
```

Source: `agent.py.template`

## How Domain Context Reaches Agent Prompts

Each factory appends the domain prompt to the role-specific system prompt:

```python
# In create_player()
system_prompt = PLAYER_SYSTEM_PROMPT + "\n\n" + domain_prompt

# In create_coach()
system_prompt = COACH_SYSTEM_PROMPT + "\n\n" + domain_prompt
```

The Player sees domain generation guidelines. The Coach sees domain evaluation criteria. Both come from the same DOMAIN.md file, ensuring consistency.

## DOMAIN.md Structure

Each domain directory contains a `DOMAIN.md` with four required sections:

```markdown
## Domain Description
What this domain is about and what the Player should generate.

## Generation Guidelines
Specific instructions for the Player:
1. Search for relevant information using `search_data`
2. Synthesise into structured content items
3. Include source references for every factual claim

## Evaluation Criteria
Criteria the Coach evaluates against, with scoring rubric:
| Criterion    | Description                              |
|-------------|------------------------------------------|
| Accuracy    | All claims supported by cited sources    |
| Completeness| Content addresses the request fully      |

A content item passes if every criterion scores 3 or above.

## Output Format
JSON schema the Player must produce:
```json
{
  "title": "...",
  "body": "...",
  "sources": [{"reference": "...", "relevance": "..."}]
}
```
```

Source: `example-domain/DOMAIN.md.template`

## Domain Selection

Domains are selected via CLI argument or environment variable:

```python
def _get_domain() -> str:
    """Get domain name from --domain CLI arg or DOMAIN env var."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--domain",
        default=os.environ.get("DOMAIN", "example-domain"),
        help="Domain name (default: example-domain)",
    )
    args, _ = parser.parse_known_args()
    return args.domain
```

Directory structure:
```
domains/
  example-domain/
    DOMAIN.md
  my-custom-domain/
    DOMAIN.md
```

## Relationship to AGENTS.md

| File | Loaded By | Purpose | Scope |
|------|-----------|---------|-------|
| `DOMAIN.md` | `_load_domain_prompt()` in `agent.py` | Domain-specific criteria and guidelines | Per-domain |
| `AGENTS.md` | `MemoryMiddleware` in agent factories | Role boundaries (ALWAYS/NEVER/ASK) | Cross-domain |

Both are injected into agent system prompts, but via different mechanisms:
- `DOMAIN.md` is string-concatenated at factory time
- `AGENTS.md` is loaded via `MemoryMiddleware` at runtime

## When to Use

- Making a multi-agent system work across different content domains
- Separating domain knowledge from agent architecture
- Allowing non-developers to configure agent behavior via markdown
- Any adversarial cooperation system where evaluation criteria change per domain

## When NOT to Use

- Single-domain systems where criteria are fixed (just embed in the prompt)
- Configuration that requires code changes (use Python config instead)
- Operational boundaries that apply across all domains (use AGENTS.md / memory injection pattern)
