# React + Rust monorepo

Use `apps/web` for React/Vite/TypeScript and `apps/api` for the Axum API. The HTTP contract is explicit; TypeScript types alone do not validate network JSON. Keep a feature's route, validation, service and persistence code close together before adding crates or services. Read the scoped rules for the files you edit.

`guardkit init react-rust-monorepo` installs guidance and the manifest. Native files in the GuardKit source template's `templates/` directory are patterns for a later foundation task and are not installed by init.
