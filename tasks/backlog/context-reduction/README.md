# Feature: Context Reduction via Graphiti Migration

## Problem

Static CLAUDE.md and .claude/rules/ files load ~15,800 tokens into every conversation, contributing to weekly token usage limits. Graphiti is operational (163 episodes) but underutilized.

## Solution

Phased reduction through editorial trimming, path-gating, and selective Graphiti migration. Target: ~8,000 tokens always-loaded (49% reduction).

## Subtasks

| Task ID | Title | Mode | Wave | Status |
|---------|-------|------|------|--------|
| TASK-CR-001 | Trim root CLAUDE.md to lean version | task-work | 1 | backlog |
| TASK-CR-002 | Trim .claude/CLAUDE.md remove duplicates | task-work | 1 | backlog |
| TASK-CR-003 | Add path gate to graphiti-knowledge.md | direct | 1 | backlog |
| TASK-CR-004 | Trim graphiti-knowledge.md content | task-work | 1 | backlog |
| TASK-CR-005 | Seed Graphiti project_overview + architecture | direct | 2 | backlog |
| TASK-CR-006 | Seed Graphiti patterns with code examples | direct | 2 | backlog |
| TASK-CR-007 | Trim orchestrators.md | task-work | 3 | backlog |
| TASK-CR-008 | Trim dataclasses + pydantic patterns | task-work | 3 | backlog |
| TASK-CR-009 | Trim 5 remaining path-gated files | task-work | 3 | backlog |
| TASK-CR-010 | Regression test workflows | task-work | 3 | backlog |

## Parent Review

TASK-REV-5F19 - Full analysis at [.claude/reviews/TASK-REV-5F19-review-report.md](../../../.claude/reviews/TASK-REV-5F19-review-report.md)

## Key Decisions

1. **Wave 1 first**: No Graphiti dependency, immediate savings (~4,400 tokens)
2. **Code example migration is conditional**: If Graphiti can't preserve Python formatting, pattern files stay static (path-gated)
3. **Root CLAUDE.md becomes a quick reference card**: Command syntax + quality gates + task states only
