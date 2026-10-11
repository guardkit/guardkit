---
paths:
  - "apps/web/**"
---

# React web

- Keep feature UI and data access together. Prefer a generated OpenAPI client once the product contract is established; validate runtime JSON at an HTTP boundary even when static types exist.
- Use strict TypeScript, typed event handlers, checked promises and React Hooks rules. Keep effects cancellable and preserve loading, error and success states.
- For product identity, use Keycloak OIDC authorization code with PKCE. Never put a client secret in browser code or use the password grant. Keep access tokens out of persistent browser storage when feasible; choose storage and refresh strategy in the product threat model.
- Avoid adding state libraries, component suites or plugins before a feature needs them.
