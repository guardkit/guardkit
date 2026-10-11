# React + Rust monorepo template

This GuardKit template supplies one combined manifest, scoped rules, two specialist agent guides and a small pattern library. `guardkit init react-rust-monorepo` copies the guidance and manifest into a project; it **does not create the React app, Rust API, native manifests or infrastructure**. A foundation task can materialise the patterns using `templates/layout.json` and GuardKit's literal `.template` renderer. This release does not automate that foundation task.

The neutral notes endpoint is an **unauthenticated demonstration** of validation, safe public errors and a bound SQLx transaction. It is not an auth-ready production service. Before product use, add Keycloak OIDC code+PKCE on the web and JWT plus application authorization on the API, separate app/identity databases, per-run isolated Compose services, and browser/database/container acceptance. Source and compile checks cannot establish those runtime properties.

## Exact materialisation layout

`templates/layout.json` is the authoritative source-to-target map. Every entry below is a literal renderer file mapping; no business names or hidden render logic are needed.

| Pattern source under `templates/` | Materialised target |
| --- | --- |
| `api/error.rs.template` | `apps/api/src/error.rs` |
| `api/routes.rs.template` | `apps/api/src/routes.rs` |
| `api/store.rs.template` | `apps/api/src/store.rs` |
| `web/api.ts.template` | `apps/web/src/api.ts` |
| `web/App.tsx.template` | `apps/web/src/App.tsx` |
| `config/Cargo.toml.template` | `Cargo.toml` |
| `config/rust-toolchain.toml.template` | `rust-toolchain.toml` |
| `config/api-Cargo.toml.template` | `apps/api/Cargo.toml` |
| `config/api-lib.rs.template` | `apps/api/src/lib.rs` |
| `config/api-main.rs.template` | `apps/api/src/main.rs` |
| `config/api-test.rs.template` | `apps/api/tests/api.rs` |
| `config/api-0001_create_notes.sql.template` | `apps/api/migrations/0001_create_notes.sql` |
| `config/package.json.template` | `package.json` |
| `config/node-version.template` | `.nvmrc` |
| `config/web-package.json.template` | `apps/web/package.json` |
| `config/web-tsconfig.json.template` | `apps/web/tsconfig.json` |
| `config/web-eslint.config.mjs.template` | `apps/web/eslint.config.mjs` |
| `config/web-vite.config.ts.template` | `apps/web/vite.config.ts` |
| `config/web-index.html.template` | `apps/web/index.html` |
| `config/web-main.tsx.template` | `apps/web/src/main.tsx` |
| `config/web-api.test.ts.template` | `apps/web/src/api.test.ts` |
| `scripts/check.sh.template` | `scripts/check.sh` |

The primary Player library is exactly three Rust files and two React/TypeScript files under `templates/api` and `templates/web`. Config, glue and test templates live outside those fallback directories so the default five-file Player context can show both stacks. `templates/patterns-manifest.json` records v2 priorities and pairs; selection v2 remains opt-in.

## Native checks after materialisation

Use Rust **1.99.0** and Node **22.23.2**. The validation fixture supplies committed `Cargo.lock` and `package-lock.json`; a product foundation must resolve and commit its own lockfiles before running `npm ci` and `npm run check` at the materialised root. The script fails if Cargo/npm are absent, and runs Rust format, locked compilation, Clippy with warning denial and tests, then web typecheck, type-aware ESLint plus Hooks, Prettier check, Vitest and production build. A first `cargo check` does not need PostgreSQL because the sample uses a bound **runtime** SQLx query. SQL syntax and schema compatibility therefore still require a migrated PostgreSQL integration test in the later foundation. Checked SQLx macros would instead require maintained `.sqlx` metadata and `cargo sqlx prepare --check`.

The sample API requires `DATABASE_URL` when started, listens on `127.0.0.1:3000`, and exposes `/api/health`, `POST /api/notes`, and `/openapi.json`. The Vite dev server proxies `/api` to that local listener. No Compose or Keycloak service is supplied by this template. Production listener, CORS/proxy, authentication, migrations and runtime lifecycle are foundation choices and gates.

See [source-provenance.md](source-provenance.md) for source URLs, licences and the chosen dependency boundary.

## Reproduce the compile evidence

From a GuardKit checkout with its Python dependencies installed, run `python tests/integration/verify_react_rust_template.py /path/to/new-scratch-directory` with the pinned Rust and Node toolchains available. The directory must not exist. This test fixture renders the layout, copies the committed validation locks, installs npm dependencies and runs the aggregate checks plus four deliberate-defect controls. See [validation/README.md](validation/README.md) for the tested scope.
