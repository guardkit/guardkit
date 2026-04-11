---
agent: bounded-context-domain-specialist
---

# Bounded Context Domain Specialist - Quick Reference

## Purpose

Creates domain aggregate roots with static factory methods (Create, Deactivate) for all domain mutations. Defines enum-discriminated error records inheriting BaseError with StatusCode derived via switch expressions. Manages the Contracts project as Anti-Corruption Layer with only lightweight summary DTOs and interface contracts crossing BC boundaries..

## When to Use

- Implementing features related to this agent's specialty
- Need expert guidance in this specific domain

## Full Documentation

For detailed examples and best practices, see:
- Agent: `agents/bounded-context-domain-specialist.md`
- Extended: `agents/bounded-context-domain-specialist-ext.md`