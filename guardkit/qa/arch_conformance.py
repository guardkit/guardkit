"""Reports where a repository's code sits relative to that repository's own written architecture rules.

PLAIN-LANGUAGE SUMMARY
----------------------
A repository can describe how it is meant to be built — "database queries live in
crud.py", "one feature does not import another feature" — and the code can then
drift away from that description without anybody noticing, because the tests still
pass and the description is prose that nothing reads.

This module reads a small YAML file in the target repository that states four or
five of those rules in a form a machine can apply, walks the repository's Python
source as a syntax tree, and writes down every place the code sits somewhere the
rule did not say it would.

It does not decide whether that is wrong. It writes down what it saw, what the
rule says, which line of which document the rule came from, and where every other
place in the repository that matches the same pattern lives. A person, or a code
generator being given feedback, reads those and draws the conclusion.

WHAT THIS MODULE DOES NOT DO — read this before adding anything to it
--------------------------------------------------------------------
* **No score, no confidence number.** The only calibration this estate has ever
  run on a local reviewer measured 19% catch and 74% over-flag. A number from an
  uncalibrated instrument is a decoration.
* **No verdict.** Nothing here says "aligned", "misaligned", "violation" or
  "pass". The word used throughout is *site*: a place in the code where a pattern
  named by a rule occurs.
* **No severity.** Severity is a judgement about consequence and this module
  cannot see consequence. If severity is ever added it comes from the rules file,
  where a human put it, never from here.
* **No model, no network, no subprocess.** Python's standard library only. What
  it does can be proved by reading it, which is the entire reason it exists in
  this form.
* **It changes nothing and blocks nothing.** It is a command that prints. It is
  not wired into any build.

WHAT IT CANNOT SEE — stated up front, not buried
-------------------------------------------------
* Only Python, only files that parse. A file with a syntax error is reported as
  unparsed and skipped, never silently dropped.
* Only the three mechanical shapes below. Any rule needing judgement — "is this
  business logic?", "does this module duplicate that one?" — cannot be expressed
  here and must not be forced into it.
* Only what a single file's syntax tree shows. It does not resolve names across
  files, does not follow call graphs, and does not know what a function does.
* Only what the rules file states. A repository with no rules file gets no
  findings, and that is reported as "no rules file", never as "clean".

THE THREE SHAPES A RULE CAN TAKE
---------------------------------
``call-site-home-file``
    A named kind of call belongs in a file with a given name. A bare call such as
    ``select(...)`` counts only if that name was imported in that file from a
    module the rule names; a method call such as ``db.execute(...)`` counts only
    if the receiver is named as, or annotated as, a type the rule names.

``module-import-boundary``
    A feature module does not import another feature module. Imports to the
    modules the rule lists as infrastructure are not reported, and the
    composition root is out of scope because wiring features together is its job.

``class-definition-home-file``
    A class with a given base class belongs in a file with a given name.

WHY A SYNTAX TREE AND NOT A TEXT SEARCH
----------------------------------------
Because a text search cannot tell code from prose. ``api_test`` contains
``users = await db.execute(select(User))`` inside a docstring — an example in a
comment, not a query. A text search reports it. A syntax tree does not see it at
all, because a docstring is a string constant. Any run of this module can be
checked against that one line to confirm the instrument is reading code.

RUNNING IT
----------
::

    python -m guardkit.qa.arch_conformance --repo /path/to/repo
    python -m guardkit.qa.arch_conformance --repo /path/to/repo --json
    python -m guardkit.qa.arch_conformance --repo /path/to/repo \
        --rules /path/to/architecture-rules.yaml

The exit code is 0 whatever it finds. It is an observer.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_RULES_PATH = "docs/architecture-rules.yaml"
SKIP_DIR_NAMES = {
    "__pycache__", ".git", ".venv", "venv", "node_modules", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "build", "dist", ".tox", ".eggs",
}
SKIP_DIR_SUFFIXES = (".egg-info", ".dist-info")


def _skip_dir(name: str) -> bool:
    return name in SKIP_DIR_NAMES or name.endswith(SKIP_DIR_SUFFIXES)


def repo_identity(repo: Path) -> tuple[str, str]:
    """The name of the repository at ``repo``, and how that name was established.

    Reads ``.git`` as a file, never runs git. A ``git worktree`` checkout carries a
    ``.git`` FILE pointing back at the main repository, so a lane worktree named
    ``at-arch`` still identifies as ``api_test`` — which is the whole point: a
    rules file is ruled for a repository, not for a directory.
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

# --------------------------------------------------------------------------
# What a site is
# --------------------------------------------------------------------------


@dataclass
class Site:
    """One place in the code where a pattern named by a rule occurs.

    ``placement`` is one of:
      ``at_home``  - the file is the one the rule names as the pattern's home.
      ``excepted`` - the file/line is named in the rule's own exceptions list.
      ``elsewhere``- neither. This is what gets reported.
    """

    rule_id: str
    path: str                # repo-relative
    line: int
    col: int
    observed: str            # what is there, in words
    how_observed: str        # the syntax-tree fact that established it
    placement: str
    enclosing: str | None = None
    exception_reason: str | None = None


@dataclass
class Report:
    repo: str
    rules_path: str | None
    rules_source_document: str | None = None
    rules_withheld: str | None = None
    files_scanned: int = 0
    files_unparsed: list[dict[str, Any]] = field(default_factory=list)
    rules: list[dict[str, Any]] = field(default_factory=list)
    sites: list[Site] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------


class Layout:
    """What the rules file says this repository's directories mean."""

    def __init__(self, repo: Path, cfg: dict[str, Any]):
        self.repo = repo
        self.source_root = cfg.get("source_root", "src")
        self.infrastructure = {p.strip("/") for p in cfg.get("infrastructure_modules", [])}
        self.composition_root = {p.strip("/") for p in cfg.get("composition_root", [])}
        root = repo / self.source_root
        self.feature_names = sorted(
            d.name
            for d in (root.iterdir() if root.is_dir() else [])
            if d.is_dir()
            and not _skip_dir(d.name)
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


# --------------------------------------------------------------------------
# Reading one file's syntax tree
# --------------------------------------------------------------------------


class FileFacts:
    """Everything the three detectors need from one file, gathered in one walk."""

    def __init__(self, tree: ast.AST):
        self.imported_from: dict[str, str] = {}   # local name -> module it came from
        self.imports: list[tuple[str, int, str, int]] = []  # (module, line, text, relative-level)
        self.calls: list[tuple[ast.Call, str | None, dict[str, str]]] = []
        self.classes: list[ast.ClassDef] = []
        self._collect_imports(tree)
        self._walk(tree, enclosing=None, annotations={})

    def _collect_imports(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    self.imported_from[alias.asname or alias.name] = mod
                text = (f"from {'.' * node.level}{mod} import "
                        + ", ".join(a.name for a in node.names))
                self.imports.append((mod, node.lineno, text, node.level))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self.imported_from[alias.asname or alias.name.split(".")[0]] = alias.name
                    self.imports.append((alias.name, node.lineno, f"import {alias.name}", 0))

    def _walk(self, node: ast.AST, enclosing: str | None, annotations: dict[str, str]) -> None:
        """Recurse, carrying the enclosing function name and its parameter types."""
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            annotations = dict(annotations)
            args = node.args
            for a in [*args.posonlyargs, *args.args, *args.kwonlyargs,
                      *( [args.vararg] if args.vararg else []),
                      *( [args.kwarg] if args.kwarg else [])]:
                if a is not None and a.annotation is not None:
                    t = _name_of(a.annotation)
                    if t:
                        annotations[a.arg] = t
            enclosing = node.name
        elif isinstance(node, ast.ClassDef):
            self.classes.append(node)
        if isinstance(node, ast.Call):
            self.calls.append((node, enclosing, annotations))
        for child in ast.iter_child_nodes(node):
            self._walk(child, enclosing, annotations)


def _name_of(node: ast.AST | None) -> str | None:
    """The trailing identifier of a Name / Attribute / Subscript, if there is one."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return _name_of(node.value)
    return None


# --------------------------------------------------------------------------
# The three detectors
# --------------------------------------------------------------------------


def detect_call_sites(rule: dict, rel: str, facts: FileFacts) -> list[Site]:
    chk = rule["check"]
    fns = chk.get("functions") or {}
    meths = chk.get("methods") or {}
    fn_names = set(fns.get("names") or [])
    fn_from = tuple(fns.get("imported_from") or [])
    m_names = set(meths.get("names") or [])
    recv_names = set(meths.get("receiver_names") or [])
    recv_types = set(meths.get("receiver_types") or [])
    out: list[Site] = []
    for call, enclosing, annos in facts.calls:
        f = call.func
        if isinstance(f, ast.Name) and f.id in fn_names:
            src = facts.imported_from.get(f.id)
            if src and (not fn_from or src.split(".")[0] in fn_from):
                out.append(Site(
                    rule["id"], rel, call.lineno, call.col_offset,
                    f"a call to {f.id}(), the name this file imports from {src}",
                    f"python ast: Call(func=Name({f.id!r})) at line {call.lineno}; "
                    f"ImportFrom({src!r}) binds that name in this file",
                    "", enclosing))
        elif isinstance(f, ast.Attribute) and f.attr in m_names:
            recv = f.value
            why = None
            if isinstance(recv, ast.Name):
                if recv.id in recv_names:
                    why = f"receiver is named {recv.id!r}, which the rule lists as a database session"
                elif annos.get(recv.id) in recv_types:
                    why = (f"receiver {recv.id!r} is annotated {annos[recv.id]} in the signature of "
                           f"{enclosing or '<module>'}(), which the rule lists as a database session")
            elif isinstance(recv, ast.Attribute) and recv.attr in recv_names:
                why = f"receiver attribute is named {recv.attr!r}, which the rule lists as a database session"
            if why:
                out.append(Site(
                    rule["id"], rel, call.lineno, call.col_offset,
                    f"a call to .{f.attr}() on a database session",
                    f"python ast: Call(func=Attribute(attr={f.attr!r})) at line {call.lineno}; {why}",
                    "", enclosing))
    return out


def detect_class_sites(rule: dict, rel: str, facts: FileFacts) -> list[Site]:
    """Classes whose base is one the rule names — including through a base declared
    in the same file. ``class UserCreate(UserBase)`` where ``UserBase(BaseModel)``
    sits ten lines above counts, and the chain that established it is reported.
    Bases declared in OTHER files are not followed: this checker reads one syntax
    tree at a time and does not resolve names across files."""
    wanted = set(rule["check"].get("base_names") or [])
    local: dict[str, list[str]] = {
        c.name: [b for b in (_name_of(x) for x in c.bases) if b] for c in facts.classes}

    def chain(name: str, seen: set[str]) -> list[str] | None:
        for b in local.get(name, []):
            if b in wanted:
                return [b]
            if b not in seen:
                deeper = chain(b, seen | {b})
                if deeper is not None:
                    return [b, *deeper]
        return None

    out: list[Site] = []
    for cls in facts.classes:
        path = chain(cls.name, {cls.name})
        if path is None:
            continue
        via = (f" via {' -> '.join(path[:-1])} declared in this same file"
               if len(path) > 1 else "")
        out.append(Site(
            rule["id"], rel, cls.lineno, cls.col_offset,
            f"class {cls.name} declared here, with base {path[-1]}{via}",
            f"python ast: ClassDef(name={cls.name!r}) at line {cls.lineno}; base chain "
            f"{' -> '.join([cls.name, *path])}",
            "", None))
    return out


def detect_import_boundary(rule: dict, rel: str, facts: FileFacts, layout: Layout) -> list[Site]:
    allowed = {m.replace("/", ".") for m in (rule["check"].get("allowed_target_modules") or [])}
    own = layout.module_of(rel)
    pkg_parts = rel.split("/")[:-1]
    out: list[Site] = []
    for mod, line, text, level in facts.imports:
        target = mod
        if level:
            base = pkg_parts[: len(pkg_parts) - (level - 1)] if level > 1 else pkg_parts
            target = ".".join([*base, *(mod.split(".") if mod else [])])
        parts = target.split(".")
        if len(parts) < 2 or parts[0] != layout.source_root:
            continue
        if ".".join(parts[:2]) in allowed:
            continue
        tgt_feature = parts[1]
        if tgt_feature not in layout.feature_names or tgt_feature == own:
            continue
        out.append(Site(
            rule["id"], rel, line, 0,
            f"an import of {target}, which is in feature module "
            f"{layout.source_root}/{tgt_feature}, written in feature module "
            f"{layout.source_root}/{own}",
            f"python ast: {'ImportFrom' if text.startswith('from') else 'Import'} "
            f"resolving to {target!r} at line {line}  ({text})",
            "", None))
    return out


DETECTORS = {
    "call-site-home-file": "call",
    "class-definition-home-file": "class",
    "module-import-boundary": "import",
}


# --------------------------------------------------------------------------
# Placement
# --------------------------------------------------------------------------


def place(site: Site, rule: dict) -> None:
    home = rule["check"].get("home_file")
    if home and Path(site.path).name == home:
        site.placement = "at_home"
        return
    for exc in rule.get("exceptions") or []:
        if exc.get("path", "").strip("/") != site.path:
            continue
        lines = exc.get("lines")
        if lines is None or site.line in lines:
            site.placement = "excepted"
            site.exception_reason = " ".join((exc.get("why") or "").split())
            return
    site.placement = "elsewhere"


# --------------------------------------------------------------------------
# The run
# --------------------------------------------------------------------------


def run(repo: Path, rules_path: Path | None, rules_are_for_another_repo: bool = False) -> Report:
    import yaml  # only import; the rules file is YAML because the rest of this estate is

    rp = rules_path or (repo / DEFAULT_RULES_PATH)
    rep = Report(repo=str(repo), rules_path=str(rp) if rp.exists() else None)
    if not rp.exists():
        rep.notes.append(
            f"No rules file at {rp}. This repository has not stated any architecture rules "
            f"a machine can apply, so nothing was checked. That is not the same as clean."
        )
        return rep

    cfg = yaml.safe_load(rp.read_text())

    # A rules file states the repository it was ruled for. Applying api_test's
    # rules to another repository was measured on 2026-08-22 across seven estate
    # repositories and produced 15 to 85 observations per repository, every one of
    # them an artefact of a layout the rules never described. So a mismatch
    # withholds the observations rather than printing them: a checker that cries
    # wolf gets switched off, and the noise would be the checker's fault, not the
    # code's. --rules-are-for-another-repo prints them anyway, for exactly that
    # experiment.
    declared = cfg.get("repo")
    actual, how = repo_identity(repo)
    if declared and declared != actual and not rules_are_for_another_repo:
        rep.rules_withheld = (
            f"These rules were ruled for the repository {declared!r}. The repository "
            f"at {repo} identifies as {actual!r} ({how}). Nothing is reported. "
            f"Architecture rules describe one repository's layout and mean nothing "
            f"in another: forced onto seven other estate repositories on 2026-08-22 "
            f"these same four rules produced 15 to 85 observations each, all of them "
            f"noise. Pass --rules-are-for-another-repo to print them anyway."
        )
        rep.notes.append(rep.rules_withheld)
        return rep
    rep.notes.append(f"Repository identified as {actual!r} ({how}); the rules file "
                     f"names {declared!r}."
                     + ("  THESE RULES WERE NOT WRITTEN FOR THIS REPOSITORY — printed "
                        "because --rules-are-for-another-repo was passed."
                        if declared and declared != actual else ""))

    layout = Layout(repo, cfg.get("layout") or {})
    rep.rules_source_document = cfg.get("source_document")
    rep.notes.append(
        f"Rules: {len(cfg.get('rules') or [])} from {rp}, derived from "
        f"{cfg.get('source_document')}, ruled_by={cfg.get('ruled_by')}."
    )
    rep.notes.append(
        f"Feature modules found under {layout.source_root}/: "
        + (", ".join(layout.feature_names) or "(none)")
        + ". Infrastructure: " + (", ".join(sorted(layout.infrastructure)) or "(none)")
        + ". Composition root: " + (", ".join(sorted(layout.composition_root)) or "(none)")
    )

    src_root = repo / layout.source_root
    files: list[tuple[str, FileFacts]] = []
    for path in sorted(src_root.rglob("*.py")) if src_root.is_dir() else []:
        if any(_skip_dir(p) for p in path.relative_to(repo).parts):
            continue
        rel = path.relative_to(repo).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except (SyntaxError, UnicodeDecodeError) as exc:
            rep.files_unparsed.append({"path": rel, "reason": type(exc).__name__ + ": " + str(exc)})
            continue
        files.append((rel, FileFacts(tree)))
    rep.files_scanned = len(files)

    for rule in cfg.get("rules") or []:
        kind = rule["check"]["kind"]
        if kind not in DETECTORS:
            rep.notes.append(f"Rule {rule['id']}: check kind {kind!r} is not one this "
                             f"checker implements. Nothing was checked for it.")
            continue
        scope = rule["check"].get("scope", "all")
        rep.rules.append({
            "id": rule["id"], "says": rule["says"], "kind": kind, "scope": scope,
            "source": rule.get("source"),
            "exceptions": [{"path": e.get("path"), "lines": e.get("lines"),
                            "why": " ".join((e.get("why") or "").split())}
                           for e in (rule.get("exceptions") or [])],
        })
        for rel, facts in files:
            if not layout.in_scope(rel, scope):
                continue
            if kind == "module-import-boundary" and rel in layout.composition_root:
                continue
            if kind == "call-site-home-file":
                found = detect_call_sites(rule, rel, facts)
            elif kind == "class-definition-home-file":
                found = detect_class_sites(rule, rel, facts)
            else:
                found = detect_import_boundary(rule, rel, facts, layout)
            for s in found:
                place(s, rule)
            rep.sites.extend(found)
    return rep


# --------------------------------------------------------------------------
# Saying what was seen
# --------------------------------------------------------------------------


def to_json(rep: Report) -> dict[str, Any]:
    out: dict[str, Any] = {
        "repo": rep.repo, "rules_file": rep.rules_path,
        "rules_withheld": rep.rules_withheld,
        "rules_derived_from": rep.rules_source_document,
        "files_scanned": rep.files_scanned, "files_unparsed": rep.files_unparsed,
        "notes": rep.notes, "findings": [], "rules": [],
    }
    for r in rep.rules:
        mine = [s for s in rep.sites if s.rule_id == r["id"]]
        counts = {p: sum(1 for s in mine if s.placement == p)
                  for p in ("at_home", "excepted", "elsewhere")}
        out["rules"].append({**r, "sites_matched": len(mine), "sites_by_placement": counts,
                             "all_sites": [{"at": f"{s.path}:{s.line}", "placement": s.placement}
                                           for s in mine]})
        for s in mine:
            if s.placement != "elsewhere":
                continue
            out["findings"].append({
                "rule_id": r["id"], "rule_says": r["says"],
                "rule_source": r["source"],
                "observed_at": f"{s.path}:{s.line}",
                "observed": s.observed,
                "enclosing_function": s.enclosing,
                "how_observed": s.how_observed,
                "same_repo_comparison": {
                    "sites_matching_this_pattern": len(mine),
                    "sites_in_the_file_the_rule_names": counts["at_home"],
                    "sites_named_as_exceptions_in_the_rules_file": counts["excepted"],
                    "sites_in_neither": counts["elsewhere"],
                    "where_the_other_sites_are": sorted({
                        s2.path for s2 in mine if s2.placement == "at_home"}),
                },
            })
    return out


def to_text(rep: Report) -> str:
    L: list[str] = []
    L.append(f"Architecture rules check — {rep.repo}")
    if not rep.rules_path or rep.rules_withheld:
        L += ["", *(f"  {n}" for n in rep.notes)]
        return "\n".join(L)
    L.append(f"Rules file: {rep.rules_path}")
    L.append(f"Files read as Python syntax trees: {rep.files_scanned}"
             + (f"; {len(rep.files_unparsed)} would not parse" if rep.files_unparsed else ""))
    for u in rep.files_unparsed:
        L.append(f"  did not parse: {u['path']} — {u['reason']}")
    for n in rep.notes:
        L.append(f"  {n}")
    total = 0
    for r in rep.rules:
        mine = [s for s in rep.sites if s.rule_id == r["id"]]
        elsewhere = [s for s in mine if s.placement == "elsewhere"]
        at_home = [s for s in mine if s.placement == "at_home"]
        excepted = [s for s in mine if s.placement == "excepted"]
        total += len(elsewhere)
        L.append("")
        L.append("=" * 78)
        L.append(f"RULE  {r['id']}   ({r['kind']}, scope: {r['scope']})")
        L.append(f"  says:   {r['says']}")
        src = r.get("source") or {}
        L.append(f"  source: {src.get('file')} line {src.get('line')} — "
                 f"\"{' '.join((src.get('quote') or '').split())}\"")
        L.append(f"  matched {len(mine)} site(s) in this repository: "
                 f"{len(at_home)} in the file the rule names, "
                 f"{len(excepted)} named as exceptions in the rules file, "
                 f"{len(elsewhere)} in neither.")
        for s in elsewhere:
            L.append("")
            L.append(f"  {s.path}:{s.line}")
            L.append(f"      observed:     {s.observed}"
                     + (f", inside {s.enclosing}()" if s.enclosing else ""))
            L.append(f"      how observed: {s.how_observed}")
            L.append(f"      the rule {r['id']} says: {r['says']}")
        if elsewhere:
            L.append("")
            L.append("  Where every other site matching this pattern lives:")
            for s in at_home:
                L.append(f"      {s.path}:{s.line}   (the file the rule names)")
            for s in excepted:
                L.append(f"      {s.path}:{s.line}   (named as an exception: {s.exception_reason})")
            if not at_home and not excepted:
                L.append("      there are none.")
    L.append("")
    L.append("=" * 78)
    L.append(f"{total} site(s) reported across {len(rep.rules)} rule(s). "
             f"This is a list of observations. It is not a verdict, a score, or a "
             f"count of defects; whether any of these should change is not something "
             f"this checker can see.")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="arch_conformance",
        description="Report where a repository's code sits relative to its own "
                    "written architecture rules. Observes; decides nothing.")
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--rules", type=Path, default=None,
                    help=f"default: <repo>/{DEFAULT_RULES_PATH}")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--rules-are-for-another-repo", action="store_true",
                    help="print observations even though the rules file names a "
                         "different repository. For experiments, not for use.")
    a = ap.parse_args(argv)
    rep = run(a.repo.resolve(), a.rules.resolve() if a.rules else None,
              a.rules_are_for_another_repo)
    print(json.dumps(to_json(rep), indent=2) if a.json else to_text(rep))
    return 0    # an observer. Always 0.


if __name__ == "__main__":
    sys.exit(main())
