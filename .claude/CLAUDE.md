# Taskwright - Lightweight Task Workflow System

## Project Context

This is an AI-powered task workflow system with built-in quality gates that prevents broken code from reaching production. The system is technology-agnostic with stack-specific plugins.

## Core Principles

1. **Quality First**: Never compromise on test coverage or architecture
2. **Pragmatic Approach**: Right amount of process for task complexity
3. **Quality Gates**: Automated architectural review and test enforcement
4. **State Tracking**: Transparent progress monitoring through markdown
5. **Technology Agnostic**: Core methodology works across all stacks

## System Philosophy

- Start simple, iterate toward complexity
- Markdown-driven for human and AI readability
- Verification through actual test execution
- Lightweight Architecture Decision Records
- Comprehensive changelogs for traceability

## Workflow Overview

1. **Create Task**: Define what needs to be done
2. **Work on Task**: AI implements with quality gates (Phases 1-5.5)
3. **Review**: Human reviews approved implementation
4. **Complete**: Archive and track

## Technology Stack Detection

The system will detect your project's technology stack and apply appropriate testing strategies:
- React/TypeScript → Playwright + Vitest
- Python API → pytest
- .NET → xUnit/NUnit + platform-specific testing
- Mobile → Platform-specific testing
- Infrastructure → Terraform testing

## Getting Started

Run `/task-create "Your task"` to begin a new task, then use `/task-work TASK-XXX` to implement it with automatic quality gates.
