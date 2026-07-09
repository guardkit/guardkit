"""Seam-check declaration config + feature-base anti-tamper (WS3-S3 §1.3).

2b (call-site/composition pins) and 2d (boot-smoke) are driven by a per-repo
declaration file, ``.guardkit/seam-checks.yaml``.  The Player writes to the
repo; a check whose own configuration is Player-writable mid-run is a check the
demonstrated adversary will edit.  Therefore (S2 spec §1.3, invariant 7):

* **The baseline referent is the FEATURE-BASE commit** — the worktree's
  pre-wave-1 creation commit (``<feature_base>``), read via
  ``git show <feature_base>:.guardkit/seam-checks.yaml``.  It is explicitly NOT
  the per-task ``_record_baseline`` HEAD (which advances as waves commit, so a
  wave-1 edit would launder into wave-2's baseline — review R2b-2).
* **CONFIG_TAMPER** compares the working tree AND every wave's committed state
  against the feature-base copy; any divergence is an advisory finding, and the
  **feature-base config governs the run** (the working-tree edit is ignored).

The feature-base commit is captured at worktree creation into
``.guardkit/autobuild/<feature>/feature_base.json`` (composed with L12's
baseline machinery in ``baseline.py`` — the same feature dir), and resolved at
gate time.  When no record exists (older worktree), the resolver falls back to
``git merge-base HEAD <base_branch>`` — the deterministic fork point.

Structural, not prompted (``structural-defence-beats-prompt-instruction``): we
do not ask the Player to leave the file alone; edits simply have no effect and
are surfaced.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_CONFIG_REL = ".guardkit/seam-checks.yaml"
_FEATURE_BASE_FILENAME = "feature_base.json"


# ---------------------------------------------------------------------------
# Feature-base commit pin (composed with baseline.py's feature dir)
# ---------------------------------------------------------------------------


def feature_base_path(state_root: Path, feature_id: str) -> Path:
    """``<state_root>/.guardkit/autobuild/<feature_id>/feature_base.json``."""
    return (
        Path(state_root) / ".guardkit" / "autobuild" / feature_id / _FEATURE_BASE_FILENAME
    )


def _git(args: List[str], cwd: Path) -> Optional[str]:
    """Run a git command, returning stripped stdout or ``None`` on failure."""
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def record_feature_base(
    state_root: Path, feature_id: str, worktree_path: Path, base_branch: str = "main"
) -> Optional[str]:
    """Capture and persist the worktree's pre-wave-1 creation commit.

    Called right after worktree creation (before any wave commits).  Records
    ``git rev-parse HEAD`` in the worktree — the exact commit the worktree was
    branched from.  Persisted atomically; fail-open (returns ``None``).
    """
    sha = _git(["rev-parse", "HEAD"], worktree_path)
    if sha is None:
        return None
    path = feature_base_path(state_root, feature_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(
                {"feature_id": feature_id, "feature_base_commit": sha, "base_branch": base_branch},
                indent=2,
            ),
            encoding="utf-8",
        )
        tmp.replace(path)
    except OSError as exc:
        logger.warning("could not persist feature_base for %s: %s", feature_id, exc)
        return sha
    return sha


def resolve_feature_base(
    worktree_path: Path, feature_id: Optional[str] = None, base_branch: str = "main"
) -> Optional[str]:
    """Resolve the feature-base commit (the §1.3 config referent).

    Order: (1) the recorded ``feature_base.json`` under the worktree, (2) the
    deterministic fork point ``git merge-base HEAD <base_branch>``.  Never the
    per-task ``_record_baseline`` HEAD (which laundering exploits).
    """
    root = Path(worktree_path) / ".guardkit" / "autobuild"
    if root.is_dir():
        try:
            matches = sorted(root.glob(f"*/{_FEATURE_BASE_FILENAME}"))
        except OSError:
            matches = []
        for candidate in matches:
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
                sha = data.get("feature_base_commit")
                if isinstance(sha, str) and sha:
                    return sha
            except (OSError, ValueError):
                continue
    # Fallback: merge-base against the base branch.
    return _git(["merge-base", "HEAD", base_branch], Path(worktree_path))


# ---------------------------------------------------------------------------
# Declaration config
# ---------------------------------------------------------------------------


@dataclass
class BootSmokeEntry:
    """One boot-smoke declaration (§4.2)."""

    id: str
    kind: str  # import | construct | serve | command
    target: str = ""  # module:symbol, or argv string for kind=command
    args: List[Any] = field(default_factory=list)  # explicit literal args for construct
    expect_type: Optional[str] = None  # "pkg.mod:ClassName" for construct
    readiness: Dict[str, Any] = field(default_factory=dict)  # serve/command
    env_required: List[Any] = field(default_factory=list)
    expected_exit: int = 0
    worktree_env: Dict[str, str] = field(default_factory=dict)  # hermetic serve overlay

    @property
    def is_hermetic(self) -> bool:
        """Import/construct always hermetic; serve is hermetic only sans env_required."""
        if self.kind in ("import", "construct"):
            return True
        return self.kind == "serve" and not self.env_required


@dataclass
class SeamChecksConfig:
    """Parsed ``.guardkit/seam-checks.yaml``."""

    version: int = 1
    composition_roots: List[str] = field(default_factory=list)
    exclusions: List[str] = field(default_factory=list)
    boot_smoke: List[BootSmokeEntry] = field(default_factory=list)
    present: bool = False  # False ⇒ absent declaration (silent skip + nudge)
    raw_text: str = ""

    @property
    def has_boot_smoke(self) -> bool:
        return bool(self.boot_smoke)


def _parse_config(text: str) -> SeamChecksConfig:
    try:
        import yaml
    except ImportError:
        logger.debug("seam-checks: PyYAML unavailable; treating as absent")
        return SeamChecksConfig(present=False)
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:  # type: ignore[attr-defined]
        return SeamChecksConfig(present=False)
    if not isinstance(data, dict):
        return SeamChecksConfig(present=False)
    roots: List[str] = []
    for r in data.get("composition_roots") or []:
        if isinstance(r, dict) and r.get("path"):
            roots.append(str(r["path"]))
        elif isinstance(r, str):
            roots.append(r)
    entries: List[BootSmokeEntry] = []
    for e in data.get("boot_smoke") or []:
        if not isinstance(e, dict) or not e.get("kind"):
            continue
        entries.append(BootSmokeEntry(
            id=str(e.get("id", e.get("target", e.get("kind")))),
            kind=str(e["kind"]),
            target=str(e.get("target", "")),
            args=list(e.get("args") or []),
            expect_type=e.get("expect_type"),
            readiness=dict(e.get("readiness") or {}),
            env_required=list(e.get("env_required") or []),
            expected_exit=int(e.get("expected_exit", 0)),
            worktree_env={str(k): str(v) for k, v in (e.get("worktree_env") or {}).items()},
        ))
    return SeamChecksConfig(
        version=int(data.get("version", 1)),
        composition_roots=roots,
        exclusions=[str(x) for x in (data.get("exclusions") or [])],
        boot_smoke=entries,
        present=True,
        raw_text=text,
    )


def load_working_tree_config(worktree_path: Path) -> SeamChecksConfig:
    """Load the working-tree ``.guardkit/seam-checks.yaml`` (may be tampered)."""
    p = Path(worktree_path) / _CONFIG_REL
    if not p.exists():
        return SeamChecksConfig(present=False)
    try:
        return _parse_config(p.read_text(encoding="utf-8"))
    except OSError:
        return SeamChecksConfig(present=False)


def load_feature_base_config(
    worktree_path: Path, feature_base_ref: Optional[str]
) -> SeamChecksConfig:
    """Load the config as it was at the feature-base commit (the governing copy).

    ``git show <ref>:.guardkit/seam-checks.yaml`` — the §1.3 baseline-read.  When
    the ref cannot be resolved or the file did not exist at base, returns an
    absent config (a feature that *introduces* the gate reads absent this run;
    the declaration takes effect next run — the honest one-run lag).
    """
    if not feature_base_ref:
        return SeamChecksConfig(present=False)
    text = _git(["show", f"{feature_base_ref}:{_CONFIG_REL}"], Path(worktree_path))
    if text is None:
        return SeamChecksConfig(present=False)
    return _parse_config(text)


# ---------------------------------------------------------------------------
# CONFIG_TAMPER / CONFIG_STALE
# ---------------------------------------------------------------------------


def _raw_at_commit(worktree_path: Path, ref: str) -> Optional[str]:
    return _git(["show", f"{ref}:{_CONFIG_REL}"], Path(worktree_path))


def detect_config_tamper(
    worktree_path: Path, feature_base_ref: Optional[str]
) -> List[Dict[str, Any]]:
    """Advisory CONFIG_TAMPER findings: working tree AND each wave commit ≠ base.

    Compares the working-tree config and every commit since the feature base
    against the feature-base copy.  Any divergence → one advisory finding
    naming the locus.  The baseline config governs regardless (the caller reads
    ``load_feature_base_config``); this only *surfaces* the edit.
    """
    findings: List[Dict[str, Any]] = []
    base_text = _raw_at_commit(worktree_path, feature_base_ref) if feature_base_ref else None
    # Working-tree divergence (compare content-stripped so a trailing-newline
    # artifact from ``git show`` vs ``read_text`` is not a phantom tamper).
    wt = Path(worktree_path) / _CONFIG_REL
    wt_text = wt.read_text(encoding="utf-8") if wt.exists() else None
    if (base_text or "").strip() != (wt_text or "").strip() and (
        base_text is not None or wt_text is not None
    ):
        findings.append({
            "kind": "CONFIG_TAMPER",
            "pattern": "CONFIG_TAMPER",
            "file": _CONFIG_REL,
            "locus": "working_tree",
            "severity": "warning",
            "why": (
                "seam-checks.yaml diverges from the feature baseline; gate "
                "configuration is human/Coach-at-triage only. The baseline "
                "config governs this run."
            ),
        })
    # Per-wave committed divergence (any commit feature_base..HEAD touching the file).
    if feature_base_ref:
        changed = _git(
            ["log", "--format=%H", f"{feature_base_ref}..HEAD", "--", _CONFIG_REL],
            Path(worktree_path),
        )
        if changed:
            findings.append({
                "kind": "CONFIG_TAMPER",
                "pattern": "CONFIG_TAMPER",
                "file": _CONFIG_REL,
                "locus": "committed_wave",
                "commits": [c for c in changed.splitlines() if c.strip()],
                "severity": "warning",
                "why": (
                    "seam-checks.yaml was modified in a wave commit since the "
                    "feature baseline; the edit is stripped at /feature-complete "
                    "until the 2e merge gate is live (WS3-S5). The baseline "
                    "config governs this run."
                ),
            })
    return findings
