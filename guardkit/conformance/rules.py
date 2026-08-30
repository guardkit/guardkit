"""Reading a repository's ``docs/architecture-rules.yaml``.

The shape read here is the one api_test's rules file uses, derived from that
repository's ruled architecture record on 2026-08-30: each rule carries ``id``,
``rule`` (the sentence in ordinary words), ``source_document`` / ``source_section``
/ ``source_sentence`` (where the sentence came from, quoted), and a ``signals``
block whose ``kind`` says which shape of check applies and which names drive it.

Nothing about a rule is hardcoded here. The ids, the file names, the method names,
the allowed directions of an import — all of them come out of the yaml. The engine
only knows *shapes*, and a rule naming a shape it does not have is reported as
unsupported rather than passed over.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_RULES_PATH = "docs/architecture-rules.yaml"

# Directories never walked, whatever the rules file says. Build and tool output is
# not source, and __pycache__ in particular would otherwise be read as a ninth
# feature module on any machine that has run the tests.
SKIP_DIR_NAMES = {
    "__pycache__", ".git", ".venv", "venv", "node_modules", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "build", "dist", ".tox", ".eggs",
}
SKIP_DIR_SUFFIXES = (".egg-info", ".dist-info")


def skip_dir(name: str) -> bool:
    return (name in SKIP_DIR_NAMES
            or name.startswith(".")
            or name.endswith(SKIP_DIR_SUFFIXES))


def as_list(value: Any) -> list[str]:
    """``require: AsyncFunctionDef`` and ``require: [a, b]`` both arrive as a list."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value]


def squash(text: str | None) -> str:
    """A YAML folded block on one line, for printing."""
    return " ".join((text or "").split())


@dataclass
class Rule:
    id: str
    says: str
    source: dict[str, Any]
    kind: str
    signals: dict[str, Any]
    exceptions: list[dict[str, Any]] = field(default_factory=list)
    checked_by: str = ""
    expected_current_finding: dict[str, Any] | None = None
    inherited: list[str] = field(default_factory=list)   # signals borrowed from another rule

    @property
    def scope(self) -> str:
        return str(self.signals.get("scope", "all"))

    def signal(self, name: str, default: Any = None) -> Any:
        return self.signals.get(name, default)


@dataclass
class RulesFile:
    path: Path
    repo: str | None
    source_record: str | None
    layout_cfg: dict[str, Any]
    rules: list[Rule]
    raw: dict[str, Any]


def load(path: Path) -> RulesFile:
    """Read the rules file. Raises ValueError with a plain sentence if it cannot."""
    import yaml   # the rest of this estate writes YAML; this is the only import

    try:
        cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"{path} could not be read as YAML: {exc}") from exc
    if not isinstance(cfg, dict):
        raise ValueError(f"{path} does not contain a mapping at the top level.")

    rules: list[Rule] = []
    for i, entry in enumerate(cfg.get("rules") or []):
        if not isinstance(entry, dict) or not entry.get("id"):
            raise ValueError(f"{path}: rule number {i + 1} has no id.")
        signals = entry.get("signals")
        source = {
            "document": entry.get("source_document"),
            "section": entry.get("source_section"),
            "sentence": squash(entry.get("source_sentence")),
        }
        rules.append(Rule(
            id=str(entry["id"]),
            says=squash(entry.get("rule")),
            source=source,
            # A rule with no signals block names no shape at all; the engine reports
            # that as unsupported rather than guessing one.
            kind=str((signals or {}).get("kind", "")) if isinstance(signals, dict) else "",
            signals=signals if isinstance(signals, dict) else {},
            exceptions=[
                {"path": str(e.get("path", "")).strip("/"),
                 "lines": e.get("lines"),
                 "why": squash(e.get("why"))}
                for e in (entry.get("exceptions") or [])
            ],
            checked_by=squash(entry.get("checked_by")),
            expected_current_finding=entry.get("expected_current_finding"),
        ))

    _resolve_same_as(rules)

    return RulesFile(
        path=path,
        repo=cfg.get("repo"),
        source_record=cfg.get("source_record"),
        layout_cfg=cfg.get("layout") or {},
        rules=rules,
        raw=cfg,
    )


SAME_AS = re.compile(r"same as\s+([A-Za-z0-9_.\-]+)", re.I)


def _resolve_same_as(rules: list[Rule]) -> None:
    """Let one rule say its signal is "same as R-OTHER" and mean it.

    api_test's R-ADR003-1 writes its decorator test as "same as R-ADR002-1 — match the
    shape, not a list of names", and then does not repeat the list of HTTP method
    names. Rather than the engine quietly inventing that list — a checker holding a
    list no rules file states is a checker nobody can audit — the reference is
    followed: any signal the named rule has and this one does not is borrowed from it,
    and every borrowed name is recorded on the rule so the report can say so.
    """
    by_id = {r.id: r for r in rules}
    for rule in rules:
        referenced: list[Rule] = []
        for value in rule.signals.values():
            if not isinstance(value, str):
                continue
            for match in SAME_AS.finditer(value):
                other = by_id.get(match.group(1))
                if other is not None and other is not rule:
                    referenced.append(other)
        for other in referenced:
            for key, value in other.signals.items():
                if key in ("kind", "scope") or key in rule.signals:
                    continue
                rule.signals[key] = value
                rule.inherited.append(f"{key} (from {other.id})")


class Layout:
    """What the rules file says this repository's directories mean."""

    def __init__(self, repo: Path, cfg: dict[str, Any]):
        self.repo = repo
        self.source_root = str(cfg.get("source_root", "src"))
        self.infrastructure = {str(p).strip("/") for p in (cfg.get("infrastructure_modules") or [])}
        self.composition_root = {str(p).strip("/") for p in (cfg.get("composition_root") or [])}
        # The rules file also names directories that are never a feature module. Two
        # of its entries are a name (__pycache__) and a description (anything starting
        # with a dot); both are already covered by skip_dir, and any further literal
        # name given is honoured here.
        self.never_a_feature = {str(p) for p in (cfg.get("never_a_feature_module") or [])}
        root = repo / self.source_root
        self.feature_names = sorted(
            d.name
            for d in (sorted(root.iterdir()) if root.is_dir() else [])
            if d.is_dir()
            and not skip_dir(d.name)
            and d.name not in self.never_a_feature
            and f"{self.source_root}/{d.name}" not in self.infrastructure
        )

    def module_of(self, rel: str) -> str | None:
        """The feature module a repo-relative file belongs to, or None."""
        parts = rel.split("/")
        if len(parts) < 3 or parts[0] != self.source_root:
            return None
        return parts[1] if parts[1] in self.feature_names else None

    def in_scope(self, rel: str, scope: str) -> bool:
        if scope == "feature_modules":
            return self.module_of(rel) is not None
        return rel.split("/")[0] == self.source_root


def repo_identity(repo: Path) -> tuple[str, str]:
    """The name of the repository at ``repo``, and how that name was established.

    Reads ``.git`` as a file; never runs git. A ``git worktree`` checkout carries a
    ``.git`` FILE pointing back at the main repository, so a lane worktree named
    ``at-arch`` still identifies as ``api_test`` — which is the point: a rules file
    is ruled for a repository, not for a directory.
    """
    dotgit = repo / ".git"
    try:
        if dotgit.is_file():
            txt = dotgit.read_text(encoding="utf-8").strip()
            if txt.startswith("gitdir:"):
                g = Path(txt.split(":", 1)[1].strip())
                for parent in g.parents:
                    if parent.name == ".git":
                        return parent.parent.name, f"git worktree of {parent.parent}"
        if dotgit.is_dir():
            return repo.name, f"git working tree at {repo}"
    except OSError:
        pass
    return repo.name, "directory name (no .git found)"
