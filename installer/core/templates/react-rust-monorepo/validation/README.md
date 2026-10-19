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

Template 1.0.1 (2026-10-18) moves `vitest` from 4.0.15 to **4.1.11** (with `@vitest/mocker` 4.1.11 resolved in the lockfile). 4.0.15 carried the critical [GHSA-5xrq-8626-4rwp](https://osv.dev/GHSA-5xrq-8626-4rwp) (CVE-2026-47429, CVSS 9.8, fixed in 4.1.0: arbitrary file read and execution while the Vitest UI server listens) and the moderate [GHSA-82fw-gwwq-j7x9](https://osv.dev/GHSA-82fw-gwwq-j7x9) (CVE-2026-84373, CVSS 5.9, fixed in 4.1.11: path traversal through an `@vitest/mocker` redirect mock). 4.1.11 (published 2026-08-18) is the newest 4.x release at least 14 days old; 4.1.12 was three days old. Vitest 4.1 accepts Vite 8, so the lockfile no longer carries the nested Vite 7.3.7, Rollup and esbuild that 4.0.15 needed. The lockfile was regenerated inside the `node:22.23.2-bookworm-slim` container with npm 11.21.0, because Node 22.23.2's npm 10.9.8 (and 10.9.9) stops with `Cannot read properties of null (reading 'edgesOut')` when resolving Vitest 4.1.x beside Vite 8; `npm ci` with npm 10.9.8 reads the result and leaves it byte-identical. OSV-Scanner 2.7.0 reported three advisories in the old lockfile and none in the new one on 2026-10-18. On the same day `tests/integration/verify_react_rust_template.py` passed on linux arm64 inside the official `rust:1.99.0` image with rustfmt, Clippy and the official Node 22.23.2 build added (npm 10.9.8): Cargo format, locked check, Clippy, two Rust tests, TypeScript, ESLint, Prettier, two Vitest tests, the production build and all four deliberate-defect controls; both lockfiles were unchanged afterwards.

The root `package.json` carries `"overrides": {"@vitejs/devtools-vitest": {"vitest": "4.1.11"}}` (added 2026-10-18). Without it, npm 10.9.8 (the npm bundled with Node 22.23.2) crashes with `edgesOut` on `npm update` and when a lockfile is rebuilt from scratch, because Vite's optional devtools add-on accepts any vitest and npm tries vitest 5 beside 4.1. Adding, removing and installing packages work with or without it. A later vitest upgrade must change the `vitest` pins and this override together, and regenerate the lockfile with npm 11 or later; npm 10.9.8 crashes on the upgrade itself even with the override. Since release 2026.10.18-4 (19 October 2026) the factory image carries npm 11.21.0, where every one of these steps works with or without the override; the override stays for anyone building with Node 22.23.2's bundled npm.
