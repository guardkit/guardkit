# `api_test/` — a pinned, sanitised copy of the pilot repository

Used only by `tests/conformance/test_api_test_repo.py`, the architecture checker's
acceptance test. Do not edit it except as described here.

## Where it came from

Taken with `git archive` from the api_test repository (`guardkit/api_test`), commit
`50e4120e5e7fc9df689cbe1a8c32860a8e6ceca7` (31 August 2026, "ADR-001 amended"). That is
the last commit where the planted search-router problem was still in the code and the
rules file's `expected_current_finding` annotations were true.

Only the three things the checker reads were copied:

- `src/` (43 files)
- `pyproject.toml`
- `docs/architecture-rules.yaml`

## What was changed from the original

The copy is not byte-for-byte identical. On 16 October 2026 three lines in
`docs/architecture-rules.yaml` were changed to remove personal attribution, because
GuardKit is a public repository:

| Line | Original wording | Now |
|---|---|---|
| 6 (comment) | the ADRs *[owner's first name]* read and ruled | the ADRs the owner read and ruled |
| 48 | `record_ruled_by:` *[owner's first name, lower case]* | `record_ruled_by: owner` |
| 126 (comment) | (*[owner's first name]*'s word) | (the owner's word) |

The checker does not read `record_ruled_by` or comments, and the line count is unchanged,
so every finding, line number and expectation is the same as in the original. Nothing in
`src/` or `pyproject.toml` was changed.

## Inert test data in the copy

These are placeholders in api_test's example application, not real credentials or
people:

- `src/core/config.py:24` — default database address
  `postgresql+asyncpg://postgres:test@localhost:5432/test` (local test database).
- `src/core/config.py:39` — contact address `support@example.com`.
- `src/users/router.py:38` — `AUTH_TOKEN = "dev-token"`, a development token for the
  example endpoints.
- `src/users/schemas.py` (lines 24-25 and the other schema examples) — the made-up user
  "John Doe" with `john.doe@example.com`, used in OpenAPI examples.

## Moving to a newer api_test

Replace the whole `api_test/` folder from one api_test commit, repeat the attribution
check above, and update the commit named here and in the test module's docstring.
