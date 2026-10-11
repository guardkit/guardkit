# Compile validation — 2026-10-11

The adjacent `go.sum` and npm lockfile belong to the neutral sample fixture, not a generated product. Reproduce from the GuardKit root with its Python dependencies installed:

```sh
python tests/integration/verify_react_go_template.py /path/to/new-scratch-directory
```

The fixture refuses an existing output directory. It requires Go 1.26.9, Staticcheck 2026.2.1, Node 22.23.2 and CGO for race detection. It renders the exact layout, copies both committed locks, installs npm dependencies, runs `scripts/check.sh`, and checks deliberate Go type, vet copylock, TypeScript type and floating-promise defects. It restores scratch files after each control. A missing tool, incompatible version, checksum/dependency failure or failed native gate is a failure.

The deterministic suite covers Go format, module verification, vet, Staticcheck, race-enabled handler tests, build, TypeScript, ESLint, Prettier, Vitest and Vite. `govulncheck` is a separate online scan against a changing vulnerability database; record its version, date and result when run. Do not call an unavailable scan clean.

This verifies source compilation and handler/browser-boundary unit behavior. It does not establish PostgreSQL migration/query execution, Keycloak authentication or authorization, browser journeys, containers, deployment or factory sandbox runtime. Those remain foundation acceptance gates. No shared services are required for this fixture.


Verified on macOS arm64 on 2026-10-11: all native checks passed with Go 1.26.9, Staticcheck 0.8.1 and Node 22.23.2. Four Go handler tests (including invalid-input cases) ran with the race detector; two Vitest tests and the frontend production build passed. All four deliberate-defect controls failed as intended; manifests and checksums stayed unchanged. The focused GuardKit integration/regression suite passed 276 tests, including actual installed-agent discovery and default mixed-stack Player context.

The initial Go 1.27.2 attempt failed inside Staticcheck; the selected supported Go 1.26.9 version runs the full gate. The initial online scan found two reachable x/text advisories. After pinning x/text v0.41.0 and its required x/sync v0.22.0, the final native run passed and govulncheck v1.9.0 reported `No vulnerabilities found` on 2026-10-11. This is a dated known-vulnerability result, not a permanent security guarantee. See source provenance for the advisory and tool-compatibility references.
