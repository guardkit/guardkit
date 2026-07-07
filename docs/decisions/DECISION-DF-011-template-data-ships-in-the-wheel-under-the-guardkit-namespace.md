# DECISION-DF-011 — Template data ships inside the wheel, under the guardkit namespace

**Status:** CANDIDATE — drafted 2026-07-08 for Rich's curation (P11 modernization-review follow-up, Fable). **NOT filed in REGISTER.md**; number tentative (DF-005 reserved, DF-010 = the A2A candidate ahead in the queue). Accept/amend/decline at the register.
**Scope:** guardkit distribution/packaging only. Additive; no pinned byte changes; integration seam v1/v1.1 preserved (this is the packaging change Session C's design names as the wheel-install remediation, not a seam change).
**Consumer:** Session C template loader (specialist-agent, `importlib.resources` over the installed distribution), `guardkit init` / `qa_scaffold` / `conftest_bridge` resolution, any future non-editable (container/wheel) deployment of guardkit.
**Companions:** DF-007 (unchanged — qa/ *instances* remain repo-owned; this ships stubs/templates only), namespace-hygiene rule (`.claude/rules/namespace-hygiene.md` — binding constraint §2.2), WS3 calibrated baseline (untouched — exclusion §2.4).
**Reasoning trail:** `docs/reviews/guardkit-modernization-review-2026-07-08.md` §4 DIM3-F1 + §2 DIM1-F2 (skeptic-verified, incl. an empirical wheel build); `specialist-agent/docs/design/ws1-session-c-mode-registry-and-template-loader-2026-07-07.md` §4.1 (verified packaging facts + documented remediation).

---

## Summary

The guardkit wheel ships the code but none of the data the code needs: `pyproject.toml`
`[tool.hatch.build.targets.wheel] packages = ["guardkit"]` omits `installer/` entirely, while
the F1–F5 *validator* code ships — so a plain pip install has enforcement code with nothing to
scaffold, and the qa scaffold fails **silently** (info-level log). This record packages the
`installer/core` template data into the wheel **under the guardkit namespace** and resolves it
via `importlib.resources`, making the installed distribution the single canonical source for
every consumer — the same mechanism Session C's loader already standardises.

## 1 · Context — why now

1. **Verified empirically (P11 skeptic):** a wheel built from main (199 files) contains zero
   `installer/` entries. A clean-venv `pip install <wheel> && guardkit-py init default`
   produces **no qa/ directory** — WS2-B1's scaffold (23ae2ddb) is inert on the standard
   install path, and the miss is a silent `logger.info` skip (`qa_scaffold.py:41-43`), the
   absence-of-failure shape applied to distribution.
2. **The resolver's fallback is a dead end:** `guardkit/templates/resolver.py:33-43` falls back
   to `~/.guardkit/templates`, which **no installer ever populates** (install.sh writes
   `~/.agentecflow`). Both resolution paths fail on a wheel install.
3. **Session C names editable install as the v1 prerequisite** for the specialist-agent seam
   and documents this exact remediation, wired to fail with instructions
   (`TemplateSourceError` names the fix). The loader is the intended consumer of this change.
4. **The drift record:** two confirmed drift sites (repo `.claude/commands` stale since
   2026-02-22; `~/.agentecflow` stale ~7 weeks undetected) are both copy-generation artifacts.
   Reading from the installed distribution removes a whole drift generation for programmatic
   consumers.

## 2 · Decision

1. **Package the template data in the wheel** via hatch `force-include`, mapping
   `installer/core` → a guardkit-namespaced package (e.g. `guardkit/_installer_core`, or a
   `guardkit.templates.data` subpackage — implementer's choice, one location). `installer/core`
   stays where it is in the repo as the authoring source; the mapping happens at build time —
   no second in-repo copy.
2. **Binding constraint — never a top-level `installer` package.** `packages = ["guardkit",
   "installer"]` is rejected: top-level `installer` collides with PyPI `pypa/installer` 1.0.1 —
   the same externally-defined-namespace class as the `mcp` shadowing incident
   (namespace-hygiene rule). Any implementation PR violating this is wrong by construction.
3. **Resolver switches to `importlib.resources`** over the guardkit-namespaced package for
   `init`, `qa_scaffold`, `conftest_bridge`, and template listing. Editable installs keep
   working (resources resolve to the repo checkout). The `~/.guardkit/templates` fallback is
   **dispositioned in the same PR**: either documented as the explicit user-override directory
   or removed — not left as a third, never-populated namespace.
4. **Exclusion (WS3-frozen):** the `bin-entries.txt` **runtime** read stays worktree-relative
   (`autobuild.py:943-952`) — it is part of the calibrated direct-mode evidence gate
   (`direct-mode-relaxed-gates-require-positive-evidence.md`) and is explicitly out of scope
   for the resolver migration. Only *install-time* resolution moves.
5. **Failure gets loud:** the qa-scaffold miss path is promoted from info to WARNING minimum;
   a wheel-install container that somehow lacks the data fails with the named remediation, not
   a mystery (per Session C's `TemplateSourceError` design).
6. **Acceptance gate (CI-pinned):** clean venv → build wheel → install → `guardkit-py init
   default` produces qa/ stubs and resolves a stack template; runs in CI so the gap cannot
   silently reopen. Also exercised via the ephemeral-consumer path (`uvx --from <wheel>
   guardkit-py init` or pipx equivalent) — the harshest consumer: no install.sh, no
   `~/.agentecflow`, no repo checkout, so it proves the wheel is fully self-contained.
   (Consumer tooling stays the user's choice — pip/uv/uvx all consume the same wheel; this
   record decides the wheel's contents, not the consumer.)

## 3 · Consequences

**Positive:** `pip install` becomes a real distribution channel (wheel size cost: a few hundred
KB of markdown); the specialist container loses its editable-install prerequisite; the F1–F5
enforcement code and its data ship together; one canonical programmatic source ends the
copy-generation drift class for installed consumers.
**Negative / accepted:** the resolver change touches 3–4 call sites and needs its fallback-order
test matrix updated; `installer/scripts/*.sh` may ride into the wheel (harmless; excludable);
`install.sh` remains the attended-surface installer short-term — the commands-manifest/prune
work (review PB-3) is a separate, compatible task, and the manifest should be designed once to
serve both prune and packaging include-list.
**Contract impact: none.** Template bytes are unchanged, so the FEAT-SPL-007/008 sha256
TemplatePins (`79a6c306…`/`cb440952…`) do not change. No re-pin, no G2b re-freeze.

## 4 · Companion edits (on acceptance)

- `REGISTER.md`: file DF-011 row (guardkit-scoped; body at this path).
- `specialist-agent` Session C doc §4.1: dated note that the wheel remediation landed (the
  loader's `TemplateSourceError` message can drop "editable install required").
- Review backlog: PB-1 → owned task; note the PB-3 manifest interplay.

## 5 · Revisit conditions

1. Hatch force-include proves unable to express the mapping cleanly → fall back to physically
   relocating `installer/core` under `guardkit/` (a bigger move; take it back through the
   register).
2. The fleet formally standardises on editable/source installs forever (unlikely; contradicts
   the container path) → this record's urgency drops but its hygiene value stands.

---

*Drafted 2026-07-08 (P11 follow-up). "The code and the data it enforces travel together."*
