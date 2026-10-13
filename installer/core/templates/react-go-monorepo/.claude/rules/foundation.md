# Monorepo foundation obligations

- The API must validate Keycloak JWT signature against trusted JWKS plus issuer, audience, expiry and accepted algorithm. Authentication does not replace feature-level authorization; check roles or ownership in the API. Reject invalid or missing credentials with safe responses.
- Keep application PostgreSQL and Keycloak identity data in separate databases. Test application migrations and queries against a migrated database. Credentials come from secret management or ignored local environment files, never source-controlled values.
- Isolate PostgreSQL, Keycloak and browser/service lifetimes per test run. Provide readiness checks, cleanup, and unique ports or network names. Retained preview needs actual browser and API evidence, not a successful compile.
- Later foundation acceptance must exercise a real browser, Keycloak login/logout, authorized and rejected API calls, migrated PostgreSQL, and container startup/readiness/teardown. The shipped patterns establish source and compile-tier behavior only.
- Browser journeys run ONLY through `bash scripts/check-feature.sh`, which starts and stops the isolated stack. Never run `npx playwright test` directly. A feature plan's smoke gate for browser checks names `bash scripts/check-feature.sh`.
