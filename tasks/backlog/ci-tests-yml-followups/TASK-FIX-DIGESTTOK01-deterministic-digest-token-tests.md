---
id: TASK-FIX-DIGESTTOK01
title: Make digest token-budget tests deterministic (tiktoken-present vs -absent divergence)
status: backlog
task_type: fix
created: 2026-06-17T00:00:00Z
updated: 2026-06-17T00:00:00Z
priority: low
related: [TASK-HMIG-011]
implementation_mode: task-work
tags: [ci, tests, tokenizer, fidelity, tech-debt]
---

# Task: Deterministic digest token-budget tests

## Why this task exists

`tests/orchestrator/instrumentation/test_digest_content.py::TestDigestTokenBudgets::test_digest_in_target_token_range[router|resolver|player|coach]`
(AC-003: each digest is 300–600 tokens) **passes or fails depending on whether
`tiktoken` is installed** — a latent environment-dependent flake:

- `guardkit/orchestrator/instrumentation/digests.py::count_tokens` uses
  `tiktoken` `cl100k_base` when importable, else a word-based (~0.75 tokens/word)
  approximation.
- **CI (`tests.yml`):** tiktoken is NOT installed → word-based fallback lands
  in 300–600 → **passes**.
- **Local dev / any env with tiktoken:** real `cl100k_base` count → e.g.
  `player.md` = **291 tokens** → **fails** (`assert 300 <= 291`).

So CI currently passes this test *for the wrong reason* (the lower-fidelity
fallback), and the faithful count reveals `player.md` is genuinely just under the
300-token floor. The adversarial review of the CI-green fix called this a "mild
absence-of-fidelity smell." Not caused by, but surfaced during, that work
(commits `4d478818` / `4831563a`).

## Acceptance criteria

- [ ] **AC-001 — pick a source of truth.** Either:
  - (a) declare `tiktoken` in the `[dev]` extra (`pyproject.toml`) so CI counts
    with the real `cl100k_base` encoder, AND adjust the tracked
    `.guardkit/digests/*.md` so each lands in 300–600 under tiktoken (in
    particular bring `player.md` ≥ 300); OR
  - (b) keep tiktoken optional but make `test_digest_in_target_token_range`
    deterministic across BOTH counters (e.g. assert against whichever counter is
    active and document the fallback's looser bound, or skip cleanly when tiktoken
    is absent rather than passing on the approximation).
- [ ] **AC-002 — no environment divergence:** the test must pass deterministically
  whether or not tiktoken is installed — no silent pass-on-fallback / fail-on-real
  split.
- [ ] **AC-003:** if path (a), run with tiktoken present locally and confirm all
  four roles (`router`, `resolver`, `player`, `coach`) are in 300–600.

## Notes

- `count_tokens`: `guardkit/orchestrator/instrumentation/digests.py:60`.
- Tracked digests: `.guardkit/digests/{router,resolver,player,coach}.md` (they ARE
  committed; this is not a missing-file issue).
- This test is currently green in CI; do not destabilise CI — verify the chosen
  path keeps the CI job green.
