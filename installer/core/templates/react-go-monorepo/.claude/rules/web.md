---
paths:
  - "apps/web/**"
---

# React web

- Keep UI and data access close to the feature. Validate unknown network JSON at the HTTP boundary; introduce a generated OpenAPI client when the product contract and drift check exist.
- Use strict TypeScript, typed event handlers, checked promises and React Hooks rules. Preserve loading, error and success states. Keep effects cancellable.
- For product identity, use OIDC authorization code with PKCE. Do not put a client secret in browser code or use the password grant. Decide token storage and refresh from the product threat model.
- Avoid adding state libraries, component suites or plugins before a feature needs them.
- Smoke gates use `bash scripts/check.sh`. Browser journeys are the project's declared `feature_check` (`bash scripts/check-feature.sh`), which starts and stops the isolated stack and which GuardKit runs itself after the last wave with its own long limit (`feature_check_timeout: 1800`). Do not put browser journeys in `smoke_gates`, whose default limit is 120 s; if a plan must, it sets `timeout: 600`. Never run `npx playwright test` directly.
