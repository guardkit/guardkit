# Source provenance

Reviewed 2026-10-11. The source patterns were written for this template; no third-party starter source was copied. Version pins below identify the compile fixture verified on 2026-10-11 with the committed lockfiles and native checks.

| Guidance | Use in this template | Licence / caution |
| --- | --- | --- |
| [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/) | Naming, public errors and typed boundaries. Its authors describe guidance, not a mandatory checklist. | [MIT or Apache-2.0](https://github.com/rust-lang/api-guidelines) |
| [Microsoft Pragmatic Rust Guidelines v2026.6](https://microsoft.github.io/rust-guidelines/) and [project guidance](https://microsoft.github.io/rust-guidelines/guidelines/project/index.html) | Cargo workspace config and modest crate boundaries. | [MIT](https://github.com/microsoft/rust-guidelines) |
| [Cargo workspaces](https://doc.rust-lang.org/cargo/reference/workspaces.html) and [Clippy CI](https://doc.rust-lang.org/clippy/continuous_integration/index.html) | Shared workspace lock/toolchain/lints and native failure gates. | Official documentation |
| [Axum Router/State docs](https://docs.rs/axum/latest/axum/) and [maintainer examples](https://github.com/tokio-rs/axum) | Typed state, handler composition and released Axum 0.8 line. `main` is moving toward 0.9. | [MIT](https://github.com/tokio-rs/axum/blob/main/LICENSE) |
| [Tokio tracing](https://tokio.rs/tokio/topics/tracing) | Structured diagnostics with no client-side database detail. | Official documentation |
| [SQLx query docs](https://docs.rs/sqlx/latest/sqlx/macro.query.html) and [CLI](https://github.com/transact-rs/sqlx/blob/main/sqlx-cli/README.md) | Explicit distinction between runtime bound SQL and build-time checked queries requiring a DB or `.sqlx`. | No SQLx source copied |
| [Utoipa Axum integration](https://docs.rs/utoipa-axum/latest/utoipa_axum/) | Annotated handler and generated OpenAPI document. | [MIT](https://github.com/juhaku/utoipa/blob/master/LICENSE-MIT) |
| [Apollo Rust best-practices skill](https://github.com/apollographql/skills/blob/main/skills/rust-best-practices/SKILL.md) | Optional reading about ownership, errors and tests; not installed or treated as a gate. | Skill declares MIT; [repository calls its skills experimental reference material](https://github.com/apollographql/skills/blob/main/README.md) |
| [launchbadge RealWorld Axum/SQLx](https://github.com/launchbadge/realworld-axum-sqlx) | Conceptual comparison only. Last listed update was 2023-12-30; source was not copied. | AGPL-3.0, unsuitable as a generic copied starter |

Validated pinned fixture: Rust 1.99.0; Axum 0.8.9; SQLx 0.8.6; Tokio 1.53.2; Utoipa 6.0.0 and utoipa-axum 0.3.0; Node 22.23.2; React/React DOM 19.3.0; TypeScript 6.0.3; typescript-eslint 8.71.1; ESLint 10.12.0; React Hooks plugin 7.1.1; Vite 8.3.3; Vitest 4.0.15; Prettier 3.6.2. TypeScript 7 is outside typescript-eslint 8.71.1's declared peer range, so the fixture stays on 6.0.3. An initial native build found that utoipa-axum 0.3 depends on Utoipa 6; pinning Utoipa 5 caused duplicate trait types and was corrected. Lockfiles and native execution, rather than this prose, establish the tested resolution.
