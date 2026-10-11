# React + Go monorepo

Use `apps/web` for React/Vite/strict TypeScript and `apps/api` for the Go `net/http` API. Keep the HTTP contract explicit: TypeScript types do not validate network JSON. Add a Go package or interface only when a real feature or consumer needs it. Read the scoped rules for the files you edit, then run the relevant native checks.

`guardkit init react-go-monorepo` installs guidance and metadata. Source files under this GuardKit template's `templates/` directory are literal patterns for a later foundation task; init does not generate an app.
