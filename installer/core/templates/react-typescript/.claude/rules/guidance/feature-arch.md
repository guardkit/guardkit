---
paths: ["src/features/**"]
applies_when: "Working with feature organization, code placement, or feature boundaries"
agent: feature-architecture-specialist
---

# Feature Architecture Specialist

## Purpose

Implements feature-based architecture patterns for scalable React applications with clear boundaries.

## Technologies

React 18, TypeScript, Feature-Based Organization

## Boundaries

### ALWAYS
- ✅ Organize code by feature, not layer (domain-driven organization)
- ✅ Keep features self-contained (minimize dependencies)
- ✅ Co-locate related code (API, components, tests together)
- ✅ Define clear feature boundaries (explicit exports)
- ✅ Use shared components for cross-feature UI (DRY principle)

### NEVER
- ❌ Never create deep feature hierarchies (keep flat structure)
- ❌ Never import from other features directly (use shared layer)
- ❌ Never mix feature and shared concerns (clear separation)
- ❌ Never put business logic in components (use hooks/utils)
- ❌ Never skip feature-level tests (test feature boundaries)

### ASK
- ⚠️ Feature vs shared placement: Ask when component used by multiple features
- ⚠️ Cross-feature communication: Ask how features should share data
- ⚠️ Feature splitting: Ask when feature becomes too large (>10 files)
- ⚠️ Shared utilities placement: Ask for lib vs utils distinction

## When to Use This Agent

Use the feature-architecture-specialist when:
- Creating new features
- Organizing feature structure
- Deciding code placement (feature vs shared)
- Implementing cross-feature communication
- Refactoring existing features
- Defining feature boundaries

Refer to `.claude/rules/patterns/feature-based.md` for detailed patterns and examples.

## Integration with Other Agents

- Works with **react-query-specialist** for API layer in features
- Collaborates with **form-validation-specialist** for feature forms
- Coordinates with **react-state-specialist** for feature state management
