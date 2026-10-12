---
paths:
  - "apps/api/**"
---

# Go API

- Keep one Go module with a small `cmd/api` composition root and feature-local `internal` packages. Use `net/http` handlers and method-aware routes; add frameworks and interfaces only for demonstrated needs.
- Bound and decode untrusted JSON strictly. Validate and normalize before persistence. Carry `r.Context()` into I/O; give database operations explicit deadlines. Use bound SQL parameters and migrations; `go build` does not verify SQL against PostgreSQL.
- Check returned errors. Add context with `%w` only when exposing the underlying error is an intended contract. Close rows and check `Rows.Err()` when using multi-row queries. Handle transaction rollback failure. Keep database details out of public errors and omit credentials, tokens, request bodies and personal data from logs.
- Run `gofmt`, `go vet`, pinned Staticcheck, `go test -race -count=1` (never a cached result) and `go build`. Race tests only cover executed paths. HTTP fake-store tests validate the handler contract but do not prove migrated database behavior.
