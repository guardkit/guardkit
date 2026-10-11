---
paths:
  - "apps/api/**"
---

# Rust API

- Keep a single Axum crate until an actual dependency boundary warrants a workspace sibling. Compose feature routers and give state at the composition root.
- Validate untrusted input before persistence. Bind SQL parameters; never build SQL by concatenating user input. Runtime `sqlx::query` does not check SQL/schema at compile time. If switching to checked macros, maintain `.sqlx` with a migrated database and `cargo sqlx prepare --check` in CI.
- Return stable, minimal public errors. Log diagnostic details with `tracing` while excluding credentials, tokens, secrets and personal data. Do not expose database errors to clients.
- No application `unsafe`; do not use `unwrap` or `expect` on production request paths. Tests may use assertions and explicit `expect` where failure is the test's purpose.
- Keep OpenAPI request/response annotations aligned with handlers and verify the exported contract in the foundation build.
