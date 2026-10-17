# React + Go monorepo template

This GuardKit template supplies one combined manifest, scoped rules, two specialist agent guides and a small pattern library. `guardkit init react-go-monorepo` copies guidance and metadata into a project. It **does not create the React app, Go API, native manifests or infrastructure**. A foundation task can materialise every source in `templates/layout.json` through GuardKit's literal `.template` renderer. This release does not automate that foundation task.

The notes endpoint is an **unauthenticated demonstration** of bounded JSON decoding, validation, safe public errors and a bound pgx transaction. It is not an auth-ready production service. Before product use, add Keycloak OIDC code+PKCE on the web and JWT plus application authorization on the API, separate application and identity databases, isolated services, and browser/database/container acceptance. Source and compile checks cannot establish those runtime properties.

## Exact materialisation layout

`templates/layout.json` is authoritative. Every entry is a literal source-to-target mapping; there is no business-name substitution or hidden render logic. The primary Player library is exactly three Go files in `templates/api` and two React/TypeScript files in `templates/web`. Config, glue and tests sit in flat `templates/config` so the default five-file Player context can show both stacks. `templates/patterns-manifest.json` records v2 priorities and pairs; v2 is opt-in.

| Pattern source under `templates/` | Materialised target |
| --- | --- |
| `api/handler.go.template` | `apps/api/internal/notes/handler.go` |
| `api/store.go.template` | `apps/api/internal/notes/store.go` |
| `api/validation.go.template` | `apps/api/internal/notes/validation.go` |
| `web/api.ts.template` | `apps/web/src/api.ts` |
| `web/App.tsx.template` | `apps/web/src/App.tsx` |
| `config/api-go.mod.template` | `apps/api/go.mod` |
| `config/go-version.template` | `.go-version` |
| `config/api-main.go.template` | `apps/api/cmd/api/main.go` |
| `config/api-handler_test.go.template` | `apps/api/internal/notes/handler_test.go` |
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
| `config/guardkit-config.yaml.template` | `.guardkit/config.yaml` |
| `config/gitignore.template` | `.gitignore` |
| `scripts/require-tools.sh.template` | `scripts/require-tools.sh` |
| `scripts/install.sh.template` | `scripts/install.sh` |
| `scripts/check.sh.template` | `scripts/check.sh` |
| `scripts/coverage.sh.template` | `scripts/coverage.sh` |
| `scripts/check-feature.sh.template` | `scripts/check-feature.sh` |

The fixture copies the committed `validation/go.sum` to `apps/api/go.sum` and `validation/package-lock.json` to the root after rendering. They are not layout entries: every layout source is a contained `.template` under `templates/`, and lockfiles are not rendered. A product foundation should commit its own lockfiles and update them intentionally when dependencies change. The Go module lives at `apps/api`, so Go commands run there. Root npm commands use the web workspace.

## Toolchain declaration

The rendered `.guardkit/config.yaml` tells GuardKit how to install and check the project, using the existing `toolchain:` schema. The exit code is the verdict.

| Declaration | Command | Purpose |
| --- | --- | --- |
| Root `install` | `bash scripts/install.sh` | `npm ci` at the root workspace, then `go mod download`, `go mod verify` and a read-only `go list -deps -test ./...` in `apps/api`, under the same exact version guards as `check.sh` (`scripts/require-tools.sh`). `go list` fails on a missing package hash. Because `go mod download` can quietly re-add a dropped `go.sum` line, the script also fails if `apps/api/go.sum` or `package-lock.json` changed during install: commit the complete files. |
| Root `test` | `bash scripts/check.sh` | The aggregate check: every static check, unit test and build. A clean exit counts only when the output has both a Go `--- PASS:` line and a Vitest `Tests … N passed` line with N at least 1, so neither an all-skipped Go suite nor an all-skipped web suite can pass. A cached Go replay never counts. |
| Root `feature_check` | `bash scripts/check-feature.sh` | The connected browser/API/database journey. |
| Root `coverage` | `bash scripts/coverage.sh` | Runs both suites with coverage and prints the totals. No percentage threshold: exit 0 means the tests passed and coverage was measured. Reports go to the git-ignored `apps/api/coverage/` and `apps/web/coverage/`. |
| Component `web` (`cwd: apps/web`) | `npm run test`; coverage `npm run coverage` (Vitest with `@vitest/coverage-v8`) | Vitest only; a clean exit without a `Tests … N passed` line (N at least 1) counts as not run. |
| Component `api` (`cwd: apps/api`) | `go test -race -count=1 -v ./...` with `GOTOOLCHAIN=local`; coverage writes `coverage/go.out` and prints `go tool cover -func`'s total line | Race-enabled, verbose Go tests; a clean exit counts only with at least one `--- PASS:` line (a test or subtest). Every test skipped, no test files, `[no tests to run]` or a cached replay (`ok … (cached)`, whose reprinted PASS lines are old) count as not run. A parent test whose subtests were all skipped still counts, because Go itself reports that parent as `--- PASS`. |

Every command has an explicit timeout, and the Go and Node pins are recorded under `runtime`. Go tests always run with `-count=1 -v`, here and in `check.sh`: `-count=1` so a cached result is never replayed as a pass, and `-v` because plain `go test` prints the same `ok` line when every test was skipped. A separate top-level `launch` block says what the build shell receives: `settings` names `PLAYWRIGHT_BROWSERS_PATH`, copied from the launching process (the file holds names, never values), and each `scratch` name (`GOPATH`, `GOCACHE`, `npm_config_cache`, `XDG_CONFIG_HOME` for Go's telemetry files, `XDG_CACHE_HOME` for Staticcheck's cache, and `NODE_COMPILE_CACHE` for Node's compile cache) is set to `<worktree scratch folder>/toolchain/<NAME>`, outside the project tree. Applying `scratch` needs a GuardKit/Forge release that reads it. Component installs are not declared because GuardKit runs only the root install. The rendered `.gitignore` keeps installed dependencies and generated output (`node_modules/`, `apps/web/dist/`, coverage, Playwright reports, `*.tsbuildinfo`, and `.cache/` as a backstop for tool caches) out of commits. Smoke gates use `bash scripts/check.sh`. Browser journeys are the declared `feature_check` (`bash scripts/check-feature.sh`), which starts and stops the isolated stack; GuardKit runs it itself after the last wave with its own long limit (`feature_check_timeout: 1800`). Do not put browser journeys in a feature plan's `smoke_gates`: those default to 120 s, and GuardKit reruns them as the baseline probe and the end-of-build re-check. If a plan must, it sets `timeout: 600`. Never run `npx playwright test` directly. The product foundation supplies `scripts/check-feature.sh`. Until it does, the template's stub prints `no connected feature check yet` and fails, so a documentation- or configuration-only change can never claim the app was exercised.

## HTTP contract in the neutral sample

| Request | Response | Meaning |
| --- | --- | --- |
| `GET /api/health` | `200 {"status":"ok"}` | Process liveness only. Database reachability is checked at startup, but health does not continuously test it. |
| `POST /api/notes` with `Content-Type: application/json` and `{"label":" hello "}` | `201 {"id":"<decimal-string>","label":"hello"}` | Trimmed label, 1–80 Unicode code points, one JSON object, no unknown fields or trailing values, body at most 1024 bytes. |
| Invalid content type/body/label on `POST /api/notes` | `400 {"message":"Invalid request"}` | No persistence call. |
| Persistence failure on `POST /api/notes` | `500 {"message":"Service unavailable"}` | No database detail in the response or structured log fields. |
| Unsupported method on a known route | `405` | `net/http` method-aware routing; `404` for unknown paths. |

`apps/web/src/api.ts` validates the network response at runtime and represents `id` as a string. Handler tests assert the contract, invalid-input short circuit, context propagation and safe failure body through a fake persistence consumer. They do not execute PostgreSQL. The migration is an example, and Go compilation does not verify SQL/schema compatibility. A later foundation must migrate a real PostgreSQL instance and test this transaction end to end. Generated OpenAPI clients and sqlc are options only when their generation and drift checks are implemented.

## Native checks and reproduction

Use Go **1.26.9**, Staticcheck **2026.2.1** (module **v0.8.1**), and Node **22.23.2**. From a materialised fixture with locks and dependencies installed, `bash scripts/check.sh` verifies exact tool versions, requires CGO for the race detector, forces `GOTOOLCHAIN=local` and read-only Go modules, then runs `gofmt`, `go mod verify`, `go vet`, Staticcheck, `go test -race -count=1 -v`, `go build`, web typecheck, typed ESLint and Hooks rules, Prettier, Vitest and Vite build. Any missing or mismatched tool, dependency resolution failure or failed check fails the script. `govulncheck` is a separate dated online scan, because its external database changes; see validation notes.

Reproduce from a GuardKit checkout with Python dependencies installed: `python tests/integration/verify_react_go_template.py /path/to/new-scratch-directory`. The directory must not exist. The fixture uses the shipped renderer and layout, copies the locks, runs the declared `scripts/install.sh` and then `scripts/check.sh`, and confirms deliberate defects fail their substantive gates. See [validation/README.md](validation/README.md) for dated evidence. The source and licence boundaries are in [source-provenance.md](source-provenance.md).

Install the pinned analysis tools with the selected Go toolchain before the fixture:

```sh
GOTOOLCHAIN=local go install honnef.co/go/tools/cmd/staticcheck@v0.8.1
GOTOOLCHAIN=local go install golang.org/x/vuln/cmd/govulncheck@v1.9.0
```

Ensure their install directory is on `PATH`. Run the separate vulnerability scan from the rendered `apps/api` directory with `GOTOOLCHAIN=local GOWORK=off GOFLAGS=-mod=readonly govulncheck ./...`. The reproducible compile check does not silently substitute for that online scan.

## Taking in a signed-off prototype

A product may keep a signed-off prototype in a `reference/` folder for builders to read. Nothing here is active until the first sign-off has been recorded in that folder.

- The reuse rules are in `CLAUDE.md` and `.claude/rules/web.md`: copy presentational parts into the product's own folders, never import from `reference/`, replace made-up data and pretend sign-in with the real API client and real sign-in, and never edit `reference/`.
- The web ESLint config already refuses imports from `reference/` and ignores comments that try to switch rules off. Do not name a product folder or import alias `reference`.
- The end of the rendered `.guardkit/config.yaml` has a commented-out example of the settings to switch on after the first sign-off: the `reference` setting, `reference/` as a protected path, `reference/prototype-index.md` as a required document, and a test line that runs `bash reference/check.sh reference/fence.txt` before `bash scripts/check.sh`. The merge accepts only plain test commands, with no `!`, `*`, `$` or `[`.
