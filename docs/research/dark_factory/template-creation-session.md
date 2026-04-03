# Template Creation Session — python-library + nats-asyncio-service

## Instructions

Paste this into Claude Code in the guardkit repo. Create both templates in sequence.

---

## Template 1: python-library

### Source Repo
`/Users/richardwoollcott/Projects/appmilla_github/youtube-transcript-mcp`

### Command
```bash
/template-create --name python-library --path /Users/richardwoollcott/Projects/appmilla_github/youtube-transcript-mcp
```

### Post-Creation Checklist
- [ ] Add `py.typed` (empty file) to package template — PEP 561 marker
- [ ] Remove MCP-specific patterns (FastMCP imports, stdout reserved for MCP protocol, mcp dependency)
- [ ] Set `"category": "library"` in manifest.json (not `"integration"`)
- [ ] Add `_internal/` convention to CLAUDE.md rules
- [ ] Run `/agent-enhance python-library/python-library-specialist --hybrid`
- [ ] Run `/agent-enhance python-library/python-testing-specialist --hybrid`
- [ ] Verify: `guardkit template-validate python-library` passes

### Spec Reference
Full spec at: `docs/research/dark_factory/template-spec-python-library.md`

---

## Template 2: nats-asyncio-service

### Source Repo
`/Users/richardwoollcott/Projects/appmilla_github/nats-asyncio-service-exemplar`

This exemplar was created specifically for template extraction. It encodes:
- FastStream NatsBroker with JetStream
- Handler/Service separation (handlers are thin, services have logic)
- TestNatsBroker for infrastructure-free unit tests
- pydantic-settings configuration
- Lifespan context manager for startup/shutdown
- Pydantic message schemas with extra="ignore"
- Docker Compose with NATS -js flag
- AGENTS.md with ALWAYS/NEVER/ASK boundaries
- Factory function test data pattern
- stderr-only logging
- pytest with asyncio_mode="auto" and -m "not integration" default gate

### Command
```bash
/template-create --name nats-asyncio-service --path /Users/richardwoollcott/Projects/appmilla_github/nats-asyncio-service-exemplar
```

### Post-Creation Checklist
- [ ] Run `/agent-enhance nats-asyncio-service/nats-service-specialist --hybrid`
- [ ] Run `/agent-enhance nats-asyncio-service/nats-testing-specialist --hybrid`
- [ ] Add raw nats-py guidance to rules as fallback for JetStream features FastStream doesn't expose (KV watch, custom stream provisioning)
- [ ] Verify AGENTS.md template is included in generated project files
- [ ] Verify: `guardkit template-validate nats-asyncio-service` passes

### Spec Reference
Full spec at: `docs/research/dark_factory/template-spec-nats-asyncio-service.md`

---

## After Both Templates Are Created

### Review Task: Add All Three New Templates as Built-In

Create a review task to add these templates to the GuardKit installer alongside the existing built-in templates:

1. `langchain-deepagents-orchestrator` (already at `~/.agentecflow/templates/`)
2. `python-library` (just created)
3. `nats-asyncio-service` (just created)

Target location: `guardkit/installer/core/templates/{template-name}/`

This should also update:
- GuardKit help text to list the new templates
- Template documentation
- `guardkit init` to support the new template names

### First Projects From These Templates

Once templates are built-in:

```bash
# nats-core — shared message contract library
cd /Users/richardwoollcott/Projects/appmilla_github/nats-core
guardkit init python-library
# Then: /feature-spec with docs/design/specs/nats-core-system-spec.md

# Jarvis adapters, agents — from nats-asyncio-service template
# (after nats-core is built, since services depend on it)
```
