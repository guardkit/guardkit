"""CI lint: no non-localhost credentials or token shapes in tracked run-state
artifacts under ``tasks/`` and ``docs/``.

Seeded by TASK-AB-SECRETSCRUB01 (ABL-001 run-3 credential leak, 2026-07-04).
A failing assertion printed a live DSN; that output travelled the standard
publication path (evidence JSON → task-md turn history → a "land stashed run
state" chore commit → public GitHub). This lint is the standing gate the retro
asked for on such chore commits: any secret-shaped string that reaches a
TRACKED file under ``tasks/`` or ``docs/`` fails CI *before* it can be pushed.

Benign patterns that do NOT fail:

- localhost / 127.0.0.1 fixture DSNs — the documented, legitimate pattern
  (structurally exempt inside ``find_secret_matches``, so no allowlist entry
  is needed for them);
- documentation placeholders (``scheme://user:pass@host`` and friends) —
  filtered by the placeholder heuristic in ``iter_hazards``;
- entries in the explicit allowlist below.

Failure messages mask matched values (file:line + host/prefix only) — a CI
log is also a publication path.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable, List

from guardkit.lib.secret_scrub import iter_hazards

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOTS = ("tasks", "docs")

# Explicit allowlist for known-benign matches the placeholder heuristic cannot
# classify. Entries are ``(relative_path, safe_label)`` pairs — safe_label is
# the SecretMatch.safe_label string, which never contains secret material.
ALLOWLIST: frozenset = frozenset(
    {
        # (currently empty — localhost fixture DSNs are structurally exempt
        # and documentation placeholders are filtered heuristically)
    }
)

# Known-benign literal values: a matched span containing one of these is
# skipped. Each entry needs a justification comment — this set is the
# human-audited record of "yes, that string is deliberately public".
KNOWN_BENIGN_LITERALS: frozenset = frozenset(
    {
        # llama-swap's static shared dev key for the LAN-local inference
        # box — a hardcoded non-secret constant documented across the
        # GB10 run notes; tailnet-only listener, not a credential.
        "llama-swap-local-key",
        # A fixture JWT literal used in template testing docs.
        "mock-jwt-token",
    }
)

# Extensions that are never text artifacts worth scanning.
_SKIP_SUFFIXES = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".ico", ".svg", ".webp"}
)


def _tracked_files(repo_root: Path, roots: Iterable[str]) -> List[Path]:
    """Return TRACKED files under ``roots`` (gitignored evidence is the
    legitimate raw record — the boundary is what leaves it)."""
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-z", "--", *roots],
            cwd=repo_root,
            capture_output=True,
            check=True,
            timeout=60,
        )
        names = [n for n in proc.stdout.decode("utf-8").split("\0") if n]
        return [repo_root / name for name in names]
    except Exception:
        # Fall back to a filesystem walk when git is unavailable — broader
        # than tracked-only, which only errs toward more scanning.
        found: List[Path] = []
        for root in roots:
            base = repo_root / root
            if base.exists():
                found.extend(p for p in base.rglob("*") if p.is_file())
        return found


def scan_files_for_secrets(paths: Iterable[Path], repo_root: Path) -> List[str]:
    """Scan files for secret-shaped hazards; return masked violation lines.

    Exposed as a function (rather than inlined in the test) so the unit
    suite can exercise it against a planted secret in a temp tree.
    """
    violations: List[str] = []
    for path in paths:
        if path.suffix.lower() in _SKIP_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            rel = path.relative_to(repo_root)
        except ValueError:
            rel = path
        for lineno, match in iter_hazards(text):
            if (str(rel), match.safe_label) in ALLOWLIST:
                continue
            span = text[match.start : match.end]
            if any(literal in span for literal in KNOWN_BENIGN_LITERALS):
                continue
            violations.append(f"{rel}:{lineno}  {match.safe_label}")
    return violations


def test_no_secrets_in_tracked_artifacts() -> None:
    files = _tracked_files(REPO_ROOT, SCAN_ROOTS)
    assert files, "expected tracked files under tasks/ and docs/"
    violations = scan_files_for_secrets(files, REPO_ROOT)
    assert not violations, (
        "Secret-shaped strings found in TRACKED run-state artifacts.\n"
        "Anything a test suite prints is one chore commit from public — "
        "scrub the embedded output (guardkit.lib.secret_scrub), replace the "
        "value with a localhost fixture DSN, or (for a verified-benign "
        "match) add an ALLOWLIST entry in this lint.\n"
        "Matched values are masked below (file:line + shape only):\n  "
        + "\n  ".join(violations)
    )
