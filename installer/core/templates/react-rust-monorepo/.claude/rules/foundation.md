# Monorepo foundation obligations

- The API must validate Keycloak JWT signature against trusted JWKS plus issuer, audience, expiry and accepted algorithm. Authentication does not replace feature-level authorization; check roles or ownership in the API. Reject invalid or missing credentials with safe responses.
- Keep application PostgreSQL and Keycloak identity data in separate databases. Use migrations for application schema. Credentials come from secret management or local ignored environment files, never source-controlled values.
- Isolate PostgreSQL, Keycloak and browser/service lifetimes per test run. Provide readiness checks, cleanup and unique ports or network names. Preview requires actual browser and API evidence, not a successful compile alone.
- Later foundation acceptance must exercise a real browser, Keycloak login/logout, authorized and rejected API calls, migrated PostgreSQL, and container startup/readiness/teardown. The shipped patterns establish only source and compile-tier behavior.
