# Compile validation — 2026-10-11

Verified on macOS arm64 using Rust 1.99.0 and Node 22.23.2. The adjacent Cargo and npm lockfiles belong to the neutral sample fixture, not a generated product.

Reproduce from the GuardKit root with its Python dependencies installed:

```sh
python tests/integration/verify_react_rust_template.py /path/to/new-scratch-directory
```

The fixture requires the pinned toolchains and network access or populated dependency caches. It refuses an existing output directory and fails on missing tools, a mismatched Node version or failed checks. It uses the shipped literal renderer and layout.

Passed: Cargo format, locked check, Clippy with warnings denied, two Rust tests, TypeScript typecheck, typed ESLint and Hooks rules, Prettier, two Vitest tests and Vite production build. All four deliberate-defect controls failed as required: Rust type mismatch, TypeScript type mismatch, Rust panic, and floating promise. The fixture restores scratch files after each control.

The focused GuardKit regression suite passed 145 tests: mixed-stack default Player context, opt-in v2 selection, installation, pattern loading, Rust parsing and coverage registration. Native compilation found and corrected an incompatible Utoipa major version pairing; typed linting found and corrected a promise test stub.

This evidence does not establish PostgreSQL query execution/schema compatibility, Keycloak authentication/authorization, browser journeys, container operation, deployment or factory sandbox runtime. Those are required foundation acceptance gates before product use. No cloud resources or shared development services were provisioned.
