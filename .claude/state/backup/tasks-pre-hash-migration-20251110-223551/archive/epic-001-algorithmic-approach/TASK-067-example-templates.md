---
id: TASK-067
title: Create example templates for distribution
status: backlog
created: 2025-11-01T16:37:00Z
priority: medium
complexity: 4
estimated_hours: 4
tags: [examples, templates, documentation]
epic: EPIC-001
feature: testing-documentation
dependencies: [TASK-047]
blocks: []
---

# TASK-067: Create Example Templates

## Objective

Create example templates to demonstrate capabilities:
- Example mycompany-react template
- Example mycompany-python-api template
- Example mycompany-maui template
- Include in distribution

## Acceptance Criteria

- [ ] mycompany-react template created
  - React 18 + TypeScript + Vite
  - Functional components pattern
  - Custom hooks
  - Testing with Vitest + Playwright
- [ ] mycompany-python-api template created
  - FastAPI + pytest
  - Clean Architecture
  - Domain pattern
  - ErrorOr pattern
- [ ] mycompany-maui template created
  - .NET MAUI + MVVM
  - AppShell navigation
  - Domain pattern
  - ErrorOr pattern
- [ ] All templates include README with usage
- [ ] All templates validated
- [ ] All templates compile successfully

## Implementation

Create three example templates in `examples/templates/`:

```bash
examples/templates/
├── mycompany-react/
│   ├── manifest.json
│   ├── settings.json
│   ├── CLAUDE.md
│   ├── README.md
│   ├── agents/
│   │   ├── react-state-specialist.md
│   │   └── typescript-domain-modeler.md
│   └── templates/
│       ├── component/functional-component.tsx.template
│       ├── hook/custom-hook.ts.template
│       └── test/component-test.tsx.template
├── mycompany-python-api/
│   └── ...
└── mycompany-maui/
    └── ...
```

Each template should:
- Be fully functional (validated, compiles)
- Include company-specific customizations as examples
- Demonstrate pattern extraction capabilities
- Include 2-3 relevant agents
- Have comprehensive README

**Estimated Time**: 4 hours | **Complexity**: 4/10 | **Priority**: MEDIUM
