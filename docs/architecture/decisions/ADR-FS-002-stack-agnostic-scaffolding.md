# ADR-FS-002: Stack-Agnostic Scaffolding with Pluggable Language Support

- **Date**: 2026-02
- **Status**: Accepted

## Context

GuardKit targets projects in multiple languages. Generated test scaffolding (step definitions, runner config, fixtures) must adapt to the target project's stack. The core specification format must remain universal.

## Decision

Auto-detect technology stack from codebase signals (`pyproject.toml`, `go.mod`, `package.json`, etc.) using priority-based rules — earlier signals win. Generate stack-appropriate BDD step definition skeletons. The Gherkin `.feature` file is universal; scaffolding is a convenience layer.

Priority order: `pyproject.toml` (Python) > `requirements.txt`/`setup.py` (Python) > `go.mod` (Go) > `Cargo.toml` (Rust) > `package.json` (TypeScript, only if no Python signals present).

## Rationale

Gherkin itself is language-neutral. The step definitions that bind Gherkin to executable code are necessarily language-specific. By detecting the stack and using templates, we generate useful scaffolding without coupling the core specification format to any particular language.

## Alternatives Rejected

- **Python-only** — Excludes non-Python projects, contradicts stack-agnostic principle
- **No scaffolding** — Player writes all boilerplate from scratch, error-prone for local models

## Consequences

**Positive:**
- Adding support for a new language requires only a new template module
- Stack detection heuristics are extensible
- Polyglot repos handled correctly (Python wins when both `pyproject.toml` and `package.json` exist)

**Negative:**
- Stack detection heuristics need extending as new project types are encountered
- Deferred to v2 — v1 generates Gherkin only with inline generation guidance in the slash command prompt

## Implementation Note

v1 defers formatter modules to v2. When implemented, BDD templates go in `guardkit/formatters/templates/` — NOT `guardkit/templates/bdd/` (that directory holds Jinja2 `.j2` system templates).

## Related

- Uses [ADR-SP-004](ADR-SP-004-progressive-disclosure.md) — scaffolding loaded on demand, not always
