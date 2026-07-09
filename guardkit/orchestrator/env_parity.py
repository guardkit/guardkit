"""ENVTAMPER-a — post-bootstrap skip-guard dependency parity probe (§5.1).

Half (a) of ENVTAMPER01: remove the *motive* for the ABL-001 self-mock. After
bootstrap installs complete, this probe finds every module guarded by a
``pytest.importorskip``/``find_spec`` skip-guard, checks whether it actually
imports in the worktree venv, and — the load-bearing RENV-1 fix — checks WHERE
it resolves:

* **missing** (skip-guarded module not importable) → advisory ``ENV_PARITY_GAP``
  naming the mapped extra (so the Player sees the sanctioned fix — declare the
  extra — before the tamper temptation).
* **vendored stub** (RENV-1): an external-distribution-named module that imports
  but resolves to a path *inside the worktree* rather than site-packages → the
  Player planted a fake package DIRECTORY (``nats_core/__init__.py``) as ordinary
  product files.  A naive importability probe would *succeed* and suppress the
  advisory — a false green.  The resolution-origin check inverts that to a signal:
  ``vendored_stub_suspected``.  This also backstops import-hook substitution
  (RENV-4) — it observes where a module resolved, regardless of how.

Advisory only — NEVER a hard bootstrap failure (AC-003).  The import probe runs
the **worktree-venv interpreter** in a subprocess with clean worktree-only
PYTHONPATH (AC-002; ``namespace-hygiene`` — guardkit's own env must not mask a
missing worktree dep).
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Common import-name ≠ dist-name cases where PEP-503 normalization fails.
_STDLIB_HINT = frozenset(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else frozenset()


@dataclass
class EnvParityFinding:
    kind: str  # ENV_PARITY_GAP | vendored_stub_suspected
    module: str
    detail: str
    mapped_extra: Optional[str] = None
    guard_sites: List[str] = field(default_factory=list)
    severity: str = "advisory"

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "module": self.module,
            "detail": self.detail,
            "mapped_extra": self.mapped_extra,
            "guard_sites": self.guard_sites,
            "severity": self.severity,
        }


@dataclass
class EnvParityResult:
    ran: bool = False
    findings: List[EnvParityFinding] = field(default_factory=list)
    skip_reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "ran": self.ran,
            "skip_reason": self.skip_reason,
            "findings": [f.to_dict() for f in self.findings],
        }


def _normalize_dist(name: str) -> str:
    """PEP 503 normalize a distribution / module name for comparison."""
    return name.lower().replace("_", "-").replace(".", "-").strip()


def _extras_map(pyproject_path: Path) -> Dict[str, List[str]]:
    """``{normalized_dist_name: [extra_group, ...]}`` from optional-dependencies."""
    out: Dict[str, List[str]] = {}
    if not pyproject_path.exists():
        return out
    try:
        try:
            import tomllib  # py311+
        except ImportError:  # pragma: no cover
            import tomli as tomllib  # type: ignore
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return out
    groups = (data.get("project") or {}).get("optional-dependencies") or {}
    for group, reqs in groups.items():
        if not isinstance(reqs, list):
            continue
        for req in reqs:
            if not isinstance(req, str):
                continue
            # strip version/extras: "nats-core>=0.4,<1" → "nats-core"
            dist = req.split(";")[0].split("[")[0]
            for sep in ("<", ">", "=", "!", "~", " ", "@"):
                dist = dist.split(sep)[0]
            norm = _normalize_dist(dist)
            if norm:
                out.setdefault(norm, [])
                if group not in out[norm]:
                    out[norm].append(group)
    return out


def _run_resolution_probe(
    modules: List[str], venv_python: str, worktree: Path
) -> Dict[str, dict]:
    """One subprocess (worktree venv, clean PYTHONPATH) resolving each candidate."""
    script = (
        "import importlib, json\n"
        f"cands = {modules!r}\n"
        "out = {}\n"
        "for name in cands:\n"
        "    e = {}\n"
        "    try:\n"
        "        m = importlib.import_module(name)\n"
        "        e['imported'] = True\n"
        "        e['file'] = getattr(m, '__file__', None)\n"
        "        e['path'] = list(getattr(m, '__path__', []) or [])\n"
        "    except BaseException as ex:\n"
        "        e['imported'] = False\n"
        "        e['error'] = type(ex).__name__\n"
        "    out[name] = e\n"
        "print(json.dumps(out))\n"
    )
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONPATH"] = str(worktree)
    try:
        proc = subprocess.run(
            [venv_python, "-c", script],
            cwd=str(worktree), env=env, capture_output=True, text=True, timeout=120,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout.strip().splitlines()[-1])
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        logger.debug("resolution probe failed: %s", exc)
    return {}


def _resolves_inside_worktree(entry: dict, worktree: Path) -> bool:
    wt = str(worktree.resolve())
    for loc in [entry.get("file")] + list(entry.get("path") or []):
        if loc:
            try:
                if str(Path(loc).resolve()).startswith(wt):
                    return True
            except (OSError, ValueError):
                continue
    return False


def analyze_env_parity(
    worktree_path: Path,
    venv_python: Optional[str] = None,
    *,
    pyproject_rel: str = "pyproject.toml",
) -> EnvParityResult:
    """Run the skip-guard parity + resolution-origin probe (advisory).

    Returns an :class:`EnvParityResult`; empty findings when no skip-guards or
    the factory extractor is unavailable (absent — never a hard failure).
    """
    worktree = Path(worktree_path)
    python = venv_python or sys.executable
    try:
        from guardkitfactory.wiring.skip_guards import extract_skip_guard_modules
    except ImportError:
        return EnvParityResult(ran=False, skip_reason="guardkitfactory unavailable")

    guards = extract_skip_guard_modules(worktree)
    if not guards:
        return EnvParityResult(ran=True, skip_reason="no skip-guards found")

    # Probe top-level module names (importorskip("nats_core.events") → nats_core).
    top_levels = sorted({m.split(".")[0] for m in guards})
    probe = _run_resolution_probe(top_levels, python, worktree)
    extras = _extras_map(worktree / pyproject_rel)

    findings: List[EnvParityFinding] = []
    for mod in top_levels:
        entry = probe.get(mod, {})
        guard_sites = sorted({s for m, sites in guards.items()
                              if m.split(".")[0] == mod for s in sites})
        norm = _normalize_dist(mod)
        mapped = (extras.get(norm) or [None])[0]
        if not entry.get("imported"):
            # Missing skip-guarded module → env parity gap.
            n = len(guard_sites)
            if mapped:
                detail = (
                    f"extra '{mapped}' not bootstrapped (provides {norm} → module "
                    f"{mod}); {n} test(s) carry skip-guards on it and will skip. "
                    f"Declare bootstrap_extras: [{mapped}] in the feature YAML, or "
                    f"set GUARDKIT_ENV_PARITY_AUTOADD=1 to auto-add mapped extras."
                )
            else:
                detail = (
                    f"module '{mod}' missing; no mapped extra found — declare "
                    f"manually. {n} test(s) will skip."
                )
            findings.append(EnvParityFinding(
                kind="ENV_PARITY_GAP", module=mod, detail=detail,
                mapped_extra=mapped, guard_sites=guard_sites,
            ))
        elif _resolves_inside_worktree(entry, worktree) and mod not in _STDLIB_HINT:
            # RENV-1: an external-named, skip-guarded module resolving to a
            # worktree-local directory is a suspected vendored stub.
            findings.append(EnvParityFinding(
                kind="vendored_stub_suspected", module=mod,
                detail=(
                    f"'{mod}' resolves to a worktree-local directory "
                    f"({entry.get('file') or (entry.get('path') or [''])[0]}), not "
                    f"an installed distribution — vendored stub suspected. A "
                    f"skip-guarded external dep should install into the venv, not "
                    f"be vendored as product files."
                ),
                mapped_extra=(extras.get(norm) or [None])[0], guard_sites=guard_sites,
            ))
    return EnvParityResult(ran=True, findings=findings)
