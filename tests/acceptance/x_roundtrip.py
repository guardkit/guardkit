"""Failing roundtrip oracle — simulates a behavioural regression.

This artefact activates the L4 behavioural-oracle gate by its mere
presence at ``tests/acceptance/*_roundtrip.py`` (no opt-in flag).

When CoachValidator._produce_behavioural_oracle discovers this file
during ``gather_evidence``, it runs it via the worktree venv pytest
interpreter. The test *intentionally fails* so that the guard fires
the hard-RED override (approve $\u2192$ feedback), verifying the
end-to-end red-to-green cycle.

To restore the green path, replace this file with a passing oracle
(e.g. ``assert True``) or remove it entirely (absent $\u2192$ guard
no-ops).
"""

from __future__ import annotations


def test_roundtrip_regression() -> None:
    """Simulated behavioural regression: expected X, got Y."""
    assert False, "Oracle failure: expected X but got Y"
