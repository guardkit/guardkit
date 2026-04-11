---
agent: railway-result-pipeline-specialist
---

# Railway Result Pipeline Specialist - Quick Reference

## Purpose

Implements Railway-Oriented Programming pipelines using CSharpFunctionalExtensions Result<TError, TSuccess> with BindAsync, MapAsync, MapErrorAsync, and TapAsync chains. Enforces the rule that no mid-chain IsSuccess checks appear. Responsible for ResultExtensions, BaseError abstract record hierarchy, and enum-discriminated error types with static factory methods..

## When to Use

- Implementing features related to this agent's specialty
- Need expert guidance in this specific domain

## Full Documentation

For detailed examples and best practices, see:
- Agent: `agents/railway-result-pipeline-specialist.md`
- Extended: `agents/railway-result-pipeline-specialist-ext.md`