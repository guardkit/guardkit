#!/usr/bin/env bash
#
# Direct-to-main CI guard (pre-push hook) — TASK-FIX-CIGUARD01.
#
# Why this exists
#   The `Tests` workflow (.github/workflows/tests.yml) runs on every push to
#   main, but `main` has no branch protection and the owner pushes DIRECTLY to
#   main. A required-PR-status-check never applies to a direct push, so CI is
#   advisory-only: on 2026-06-12 a real import-time `ImportError`
#   (`map_bdd_run_result`) interrupted pytest COLLECTION for the whole tree,
#   the `Tests` run went red, and nothing stopped the broken commit from
#   landing and sticking. See:
#     - tasks/.../TASK-FIX-CIGUARD01-*.md  (full root cause, Part B)
#     - tasks/completed/TASK-INFRA-CIGREEN/ (the "gate merges" framing this
#       corrects to "gate merges AND direct pushes")
#
# What it does
#   Before a push that updates refs/heads/main, runs the fast pytest COLLECTION
#   check — the exact oracle that catches the CIGUARD01 defect class (import /
#   collection errors that red the whole suite). Collection-only is deliberate:
#   it is ~2-3s (a full `pytest tests/` is >4 min and would just get bypassed),
#   and the defect this guard exists to stop is a *collection* error, not a
#   per-test failure. Per-test pass/fail remains the CI workflow's job.
#
#   On a non-zero collection exit the push is ABORTED at the source — no PR,
#   no remote round-trip required. This is the only Part-B guard that blocks a
#   broken direct-to-main push BEFORE it reaches main.
#
# Install (one-time, per clone)
#   ./scripts/install-git-hooks.sh
#   (symlinks .git/hooks/pre-push -> scripts/pre-push.sh; see CONTRIBUTING.md)
#
# Bypass (use sparingly, and know you are pushing unverified collection)
#   git push --no-verify          # git skips the hook entirely
#   GUARDKIT_SKIP_PREPUSH=1 git push
#
set -euo pipefail

# --- explicit opt-out ------------------------------------------------------
if [[ "${GUARDKIT_SKIP_PREPUSH:-}" == "1" ]]; then
  echo "pre-push: GUARDKIT_SKIP_PREPUSH=1 — skipping collection guard (unverified push)." >&2
  exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# --- decide whether this push touches main ---------------------------------
# Git feeds the pre-push hook one line per ref on stdin:
#   <local ref> <local sha> <remote ref> <remote sha>
# A branch deletion has an all-zero local sha (nothing to test). If stdin is
# empty or unreadable we FAIL SAFE and run the check anyway.
ZERO="0000000000000000000000000000000000000000"
push_touches_main=0
saw_any_ref=0

while read -r local_ref local_sha remote_ref remote_sha; do
  saw_any_ref=1
  # Skip deletions (local sha all zeros => nothing being pushed).
  if [[ "$local_sha" == "$ZERO" ]]; then
    continue
  fi
  if [[ "$remote_ref" == "refs/heads/main" ]]; then
    push_touches_main=1
  fi
done

# No ref lines on stdin (e.g. invoked manually without piping) => fail safe.
if [[ "$saw_any_ref" -eq 0 ]]; then
  push_touches_main=1
fi

if [[ "$push_touches_main" -eq 0 ]]; then
  echo "pre-push: push does not update refs/heads/main — collection guard skipped." >&2
  exit 0
fi

# --- pick an interpreter ---------------------------------------------------
# Prefer an active venv, then the repo's .venv, then python3/python.
if [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
  PY="${VIRTUAL_ENV}/bin/python"
elif [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  PY="${REPO_ROOT}/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PY="$(command -v python)"
else
  echo "pre-push: no python interpreter found — cannot run collection guard." >&2
  echo "          install deps or bypass with 'git push --no-verify' (unverified)." >&2
  exit 1
fi

# --- run the fast collection check -----------------------------------------
# Mirrors .github/workflows/tests.yml's collection surface: clear repo addopts
# (--cov etc.) and disable the cache so this is a clean structural probe.
echo "pre-push: running pytest collection guard (refs/heads/main)…" >&2
if "$PY" -m pytest tests/ -o addopts="" -p no:cacheprovider --co -q >/tmp/guardkit-prepush-collect.$$ 2>&1; then
  rm -f "/tmp/guardkit-prepush-collect.$$"
  echo "pre-push: collection OK — push allowed." >&2
  exit 0
fi

# Non-zero collection exit (import/collection error) => abort the push.
echo "" >&2
echo "═══════════════════════════════════════════════════════════════════════" >&2
echo "❌ pre-push BLOCKED: pytest collection failed — push aborted." >&2
echo "   A direct push to main with a broken collection would red the Tests" >&2
echo "   gate (see TASK-FIX-CIGUARD01). Fix the import/collection error below," >&2
echo "   or bypass with 'git push --no-verify' if you KNOW it is safe." >&2
echo "───────────────────────────────────────────────────────────────────────" >&2
tail -n 25 "/tmp/guardkit-prepush-collect.$$" >&2 || true
echo "═══════════════════════════════════════════════════════════════════════" >&2
rm -f "/tmp/guardkit-prepush-collect.$$"
exit 1
