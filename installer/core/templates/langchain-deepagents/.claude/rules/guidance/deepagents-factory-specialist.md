---
agent: deepagents-factory-specialist
---

# Deepagents Factory Specialist - Quick Reference

## Purpose

Specialist in the create_deep_agent Factory pattern. Generates agent factory functions that correctly wire model, tools, system_prompt, memory, and backend parameters. Ensures coach factories omit backend and pass empty tools lists, while player factories inject FilesystemBackend and the full tool set..

## When to Use

- Implementing features related to this agent's specialty
- Need expert guidance in this specific domain

## Full Documentation

For detailed examples and best practices, see:
- Agent: `agents/deepagents-factory-specialist.md`
- Extended: `agents/deepagents-factory-specialist-ext.md`