# {{ProjectName}} — Pipeline Orchestrator

A pipeline orchestrator agent using DeepAgents two-model architecture.

- **Reasoning model**: Drives decisions, evaluates output quality
- **Implementation model**: Executes tasks, generates artifacts
- **Architecture**: LangGraph with hierarchical subagent composition

## Quick Start

```bash
pip install -r requirements.txt
# Configure models in orchestrator-config.yaml
python -m langgraph dev
```

## Key Patterns

- Two-model orchestration (reasoning + implementation)
- Domain-agnostic prompts with runtime context injection
- SubAgent/AsyncSubAgent factory composition
- @tool(parse_docstring=True) for schema-from-docstrings

## Detailed Guidance

For detailed code style, testing patterns, architecture patterns, and agent-specific
guidance, see the `.claude/rules/` directory. Rules load automatically when you
work on relevant files.

- **Code Style**: `.claude/rules/code-style.md`
- **Testing**: `.claude/rules/testing.md`
- **Patterns**: `.claude/rules/patterns/`
- **Guidance**: `.claude/rules/guidance/`

## Technology Stack

**Language**: Python
**Frameworks**: LangChain, LangGraph, DeepAgents
**Architecture**: Two-Model Pipeline Orchestrator