# React + Go monorepo

Use `apps/web` for React/Vite/strict TypeScript and `apps/api` for the Go `net/http` API. Keep the HTTP contract explicit: TypeScript types do not validate network JSON. Add a Go package or interface only when a real feature or consumer needs it. Read the scoped rules for the files you edit, then run the relevant native checks.

`guardkit init react-go-monorepo` installs guidance and metadata. Source files under this GuardKit template's `templates/` directory are literal patterns for a later foundation task; init does not generate an app.

## When the repository has a `reference/` folder

A `reference/` folder holds a signed-off prototype, kept for reading only. When it exists:

- Copy presentational parts (components, layout, styles, design tokens) from `reference/prototype/` into the product's own folders, adapting them to the product's dependencies.
- Never import from `reference/` or point product code into it.
- Replace made-up data, mock request functions and pretend sign-in with the real API client and real sign-in. Never copy them.
- Delete `eslint-disable` comments when copying a component: they are ignored and fail lint.
- Never edit anything under `reference/`.
