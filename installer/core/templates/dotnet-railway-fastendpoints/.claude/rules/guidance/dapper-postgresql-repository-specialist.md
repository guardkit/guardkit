---
agent: dapper-postgresql-repository-specialist
---

# Dapper Postgresql Repository Specialist - Quick Reference

## Purpose

Implements Dapper + Npgsql repositories wrapping every public method in try/catch that converts exceptions to domain-specific RepositoryUnavailable error variants. Uses DefaultTypeMap.MatchNamesWithUnderscores = true for snake_case column mapping. Returns Result<TDomainError, T> from every method..

## When to Use

- Implementing features related to this agent's specialty
- Need expert guidance in this specific domain

## Full Documentation

For detailed examples and best practices, see:
- Agent: `agents/dapper-postgresql-repository-specialist.md`
- Extended: `agents/dapper-postgresql-repository-specialist-ext.md`