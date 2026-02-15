---
id: TASK-SFT-010
title: Add Trophy-model testing guidance to client app templates
task_type: documentation
parent_review: TASK-REV-AC1A
feature_id: FEAT-AC1A
wave: 3
implementation_mode: direct
complexity: 3
dependencies:
  - TASK-SFT-002
priority: medium
---

# Add Trophy-Model Testing Guidance to Client App Templates

## Objective

Update the React TypeScript, FastAPI Python, Next.js Fullstack, and react-fastapi-monorepo templates with Kent C. Dodds' Trophy testing model guidance, distinguishing platform tool testing (Honeycomb) from client app testing (Trophy).

## Acceptance Criteria

- [ ] `installer/core/templates/react-typescript/` updated with Trophy testing guidance
- [ ] `installer/core/templates/fastapi-python/` updated with Trophy testing guidance
- [ ] `installer/core/templates/nextjs-fullstack/` updated with Trophy testing guidance
- [ ] `installer/core/templates/react-fastapi-monorepo/` updated with Trophy testing guidance
- [ ] Each template's testing section includes:
  - Testing distribution: 50% feature/integration, 30% unit, 10% E2E, 10% static
  - "Test behaviour, not implementation" principle
  - What to mock (APIs at HTTP level via MSW/WireMock) vs what NOT to mock (internal functions)
  - When seam tests ARE needed in client apps (third-party integrations, microservice boundaries)
- [ ] Testing requirements checklist in each template:
  - Feature/integration tests for every user story
  - Unit tests for complex business logic only
  - Contract tests for third-party API integrations
  - E2E tests for critical user journeys only
  - Static analysis (TypeScript strict mode, ESLint)

## Implementation Notes

- Do NOT change template structure — add a testing guidance section to existing CLAUDE.md or testing docs in each template
- Reference ADR-SP-009 for architectural justification
- Keep guidance concise (under 50 lines per template)
