"""One function per shape of check. The rules file drives every one of them.

A check knows a *shape* — "a named kind of call belongs in a file with a given
name", "a feature module does not import another feature module". It does not know
any rule id, file name, method name or module name: those all arrive from the
``signals`` block of the rule it is handed. That is why a rule can be added to a
repository's rules file without touching this module, and why a rule naming a shape
that is not in the table at the bottom raises ``Unsupported`` instead of quietly
reporting nothing.

Ten shapes are implemented, which is every shape api_test's rules file uses:

===============================  ==========================================================
``call-site-home-file``          a kind of call belongs in a file with a given name
``module-import-boundary``       a feature module does not import another feature module
``file-layout``                  a directory must not exist / a file must be present
``handler-shape``                a route handler must be async, or must declare its return
``forbidden-imports``            named modules must not be imported, named calls not made
``forbidden-method-call``        a named method must not be called on a named receiver
``class-definition-home-file``   a marked class belongs in a file, with a given base class
``config-file-fact``             a TOML config file must state something
``annotation-completeness``      every function annotates its arguments and its return
``forbidden-construction``       a named thing must not be constructed outside given places
===============================  ==========================================================
"""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path
from typing import Any, Callable

from guardkit.conformance.facts import (
    Assignment,
    FileFacts,
    annotation_text,
    dotted_of,
    name_of,
    unwrap,
)
from guardkit.conformance.model import ELSEWHERE, EXCEPTED, Site, Tally, Unsupported
from guardkit.conformance.rules import Layout, Rule, as_list

# --------------------------------------------------------------------------
# Shared: is this call's receiver a database session, and how do we know?
# --------------------------------------------------------------------------


def _receiver_reason(func: ast.Attribute, annotations: dict[str, str],
                     receiver_names: set[str], receiver_types: set[str]) -> str | None:
    """Why the thing this method was called on counts as what the rule named."""
    recv = func.value
    if isinstance(recv, ast.Name):
        if recv.id in receiver_names:
            return f"the receiver is named {recv.id!r}, which the rule lists"
        t = annotations.get(recv.id)
        if t and t in receiver_types:
            return (f"the receiver {recv.id!r} is annotated {t} in the enclosing "
                    f"signature, and the rule lists {t}")
    elif isinstance(recv, ast.Attribute) and recv.attr in receiver_names:
        return f"the receiver attribute is named {recv.attr!r}, which the rule lists"
    return None


# --------------------------------------------------------------------------
# call-site-home-file
# --------------------------------------------------------------------------


def check_call_site_home_file(rule: Rule, rel: str, facts: FileFacts,
                              layout: Layout, tally: Tally) -> list[Site]:
    """A named kind of call belongs in a file with a given name.

    Two ways a call counts, and both conditions are needed, because without them any
    project function called ``update()`` would match:

    * a bare call — ``select(...)`` — counts only when this file imported that name
      from a module the rule names;
    * a method call — ``db.execute(...)`` — counts only when the receiver is named,
      or annotated, as something the rule lists.

    **Granularity.** The rules file settles this and this code obeys it: one site per
    query, anchored at the line where the query is *built*. A line that only runs a
    query built earlier — ``result = await db.execute(stmt)`` — is folded into that
    site and named inside it, rather than counted a second time. So the two queries in
    api_test's search router occupy four lines and are two sites, not four.
    """
    fns = rule.signal("functions") or {}
    meths = rule.signal("methods") or {}
    fn_names = set(fns.get("names") or [])
    fn_from = tuple(fns.get("imported_from") or [])
    m_names = set(meths.get("names") or [])
    recv_names = set(meths.get("receiver_names") or [])
    recv_types = set(meths.get("receiver_types") or [])
    if not fn_names and not m_names:
        raise Unsupported(
            "the rule names neither a function nor a method to look for, so there is "
            "nothing for this shape of check to match")

    tally.add("calls read", len(facts.calls))
    builds: dict[int, Site] = {}          # id(Call node) -> the site it produced
    runs: list[tuple[Site, ast.Call, str | None]] = []

    for call in facts.calls:
        f = call.node.func
        if isinstance(f, ast.Name) and f.id in fn_names:
            src = facts.imported_from.get(f.id)
            if src and (not fn_from or src.split(".")[0] in fn_from):
                site = Site(
                    rule.id, rel, call.node.lineno,
                    f"a call to {f.id}(), the name this file imports from {src}",
                    f"python ast: Call(func=Name({f.id!r})) at line {call.node.lineno}; "
                    f"ImportFrom({src!r}) binds that name in this file",
                    enclosing=call.enclosing)
                builds[id(call.node)] = site
        elif isinstance(f, ast.Attribute) and f.attr in m_names:
            why = _receiver_reason(f, call.annotations, recv_names, recv_types)
            if why:
                site = Site(
                    rule.id, rel, call.node.lineno,
                    f"a call to .{f.attr}() on {name_of(f.value) or 'the receiver'}",
                    f"python ast: Call(func=Attribute(attr={f.attr!r})) at line "
                    f"{call.node.lineno}; {why}",
                    enclosing=call.enclosing)
                runs.append((site, call.node, call.enclosing))

    return _fold_runs_into_builds(builds, runs, facts)


def _fold_runs_into_builds(builds: dict[int, Site],
                           runs: list[tuple[Site, ast.Call, str | None]],
                           facts: FileFacts) -> list[Site]:
    """Attach every run of an already-counted query to the line that built it."""
    out: list[Site] = list(builds.values())
    for site, call, enclosing in runs:
        parent = _built_by(call, enclosing, builds, facts.assignments)
        if parent is not None:
            parent.also_at.append(f"line {site.line}: {site.observed}")
        else:
            out.append(site)
    out.sort(key=lambda s: (s.line, s.observed))
    return out


def _built_by(call: ast.Call, enclosing: str | None, builds: dict[int, Site],
              assignments: list[Assignment]) -> Site | None:
    """The site that built what this call is running, if this call is only running one."""
    args: list[ast.AST] = [*call.args, *(k.value for k in call.keywords)]
    for arg in args:
        arg = unwrap(arg)
        # `db.execute(select(User))` — built inline, on the same line.
        if isinstance(arg, ast.Call):
            for node in ast.walk(arg):
                if id(node) in builds:
                    return builds[id(node)]
        # `stmt = select(User)` ... `db.execute(stmt)` — built earlier, same function.
        if isinstance(arg, ast.Name):
            candidates = [a for a in assignments
                          if a.target == arg.id and a.enclosing == enclosing
                          and a.line <= call.lineno]
            for a in sorted(candidates, key=lambda a: a.line, reverse=True):
                for node in ast.walk(a.value):
                    if id(node) in builds:
                        return builds[id(node)]
                break   # the nearest earlier assignment is the one that binds the name
    return None


# --------------------------------------------------------------------------
# module-import-boundary
# --------------------------------------------------------------------------


def check_module_import_boundary(rule: Rule, rel: str, facts: FileFacts,
                                 layout: Layout, tally: Tally) -> list[Site]:
    """A feature module does not import another feature module.

    Imports towards the modules the rule lists as infrastructure are the intended
    direction and are not reported. Imports within the same feature are not reported.
    The composition root — the file whose job is joining the features together — is
    excluded by the engine before this is called.

    **The public read interface**, when the rule names one. A rule may list
    ``public_modules`` — file basenames such as ``[crud, schemas]``. An import that
    resolves to ``src.<other feature>.<one of those>`` is then the sanctioned way for one
    feature to read another's data, and is not reported. Two things are still reported
    even so: a name in that import starting with an underscore, which is that feature's
    private helper wearing a public file's address; and an import of the feature package
    itself, with no file named after it, which reaches every file in it.

    A rule that names no ``public_modules`` behaves exactly as it did before this signal
    existed — every import into another feature is reported, in the same words.
    """
    allowed = {str(m).replace("/", ".") for m in (rule.signal("allowed_target_modules") or [])}
    public_order = [str(m).removesuffix(".py") for m in (rule.signal("public_modules") or [])]
    public = set(public_order)
    interface = ", ".join(f"{m}.py" for m in public_order)
    own = layout.module_of(rel)
    pkg_parts = rel.split("/")[:-1]
    tally.add("imports read", len(facts.imports))
    out: list[Site] = []
    for imp in facts.imports:
        target = imp.module
        if imp.level:
            base = pkg_parts[: len(pkg_parts) - (imp.level - 1)] if imp.level > 1 else pkg_parts
            target = ".".join([*base, *(imp.module.split(".") if imp.module else [])])
        parts = target.split(".")
        if len(parts) < 2 or parts[0] != layout.source_root:
            continue
        if ".".join(parts[:2]) in allowed:
            continue
        other = parts[1]
        if other not in layout.feature_names or other == own:
            continue

        observed = (f"an import of {target}, which is in feature module "
                    f"{layout.source_root}/{other}, written in feature module "
                    f"{layout.source_root}/{own}")
        if public:
            leaf = parts[2] if len(parts) > 2 else None
            if leaf is None:
                observed = (
                    f"an import of {target}, the whole of feature module "
                    f"{layout.source_root}/{other}, which reaches every file in it, "
                    f"written in feature module {layout.source_root}/{own}; only that "
                    f"feature's public read interface is importable: {interface}")
            elif leaf in public:
                private_names = [n for n in imp.names if n.startswith("_")]
                if not private_names:
                    continue      # the sanctioned way to read another feature's data
                observed = (
                    f"an import of {', '.join(private_names)} from {target}, "
                    f"{'names' if len(private_names) > 1 else 'a name'} starting with an "
                    f"underscore and so private to feature module "
                    f"{layout.source_root}/{other}, written in feature module "
                    f"{layout.source_root}/{own}")
            else:
                observed = (
                    f"an import of {target}, which is a private file of feature module "
                    f"{layout.source_root}/{other}, written in feature module "
                    f"{layout.source_root}/{own}; that feature's public read interface "
                    f"is {interface}")

        out.append(Site(
            rule.id, rel, imp.line, observed,
            f"python ast: {'ImportFrom' if imp.is_from else 'Import'} resolving to "
            f"{target!r} at line {imp.line}  ({imp.text})"))
    return out


# --------------------------------------------------------------------------
# file-layout
# --------------------------------------------------------------------------


def check_file_layout(rule: Rule, repo: Path, layout: Layout,
                      files: list[tuple[str, FileFacts]], tally: Tally) -> list[Site]:
    """Facts about the file tree: a directory that must not exist, a file that must.

    No parsing at all. ``src/schemas.py`` is a file and ``src/schemas/`` is a
    directory; the rules file forbids the directory and sanctions the file, so both
    are looked at and the sanctioned file is recorded as an exception rather than
    passed over in silence.
    """
    forbidden = [str(d).strip("/") for d in (rule.signal("forbidden_directories") or [])]
    required = [str(f) for f in (rule.signal("required_files") or [])]
    allowed_files = {str(f).strip("/") for f in (rule.signal("allowed_files") or [])}
    if not forbidden and not required:
        raise Unsupported(
            "the rule names neither a forbidden directory nor a required file, so there "
            "is nothing for this shape of check to look at")

    out: list[Site] = []
    tally.add("directories checked", len(forbidden))
    for d in forbidden:
        if (repo / d).is_dir():
            out.append(Site(
                rule.id, d, 0,
                f"the directory {d}/ exists",
                f"file tree: {d} is a directory under the repository root"))
        near = f"{d}.py"
        if near in allowed_files and (repo / near).is_file():
            out.append(Site(
                rule.id, near, 0,
                f"the file {near} exists — a file, not the forbidden directory {d}/",
                f"file tree: {near} is a file under the repository root",
                placement=EXCEPTED,
                exception_reason=f"the rules file lists {near} as allowed"))

    if required:
        scope = rule.scope
        modules = ([f"{layout.source_root}/{m}" for m in layout.feature_names]
                   if scope == "feature_modules" else [layout.source_root])
        tally.add("modules checked", len(modules))
        for mod in modules:
            for name in required:
                if not (repo / mod / name).is_file():
                    out.append(Site(
                        rule.id, mod, 0,
                        f"the module {mod}/ contains no {name}",
                        f"file tree: no file named {name} in {mod}/"))
    return out


# --------------------------------------------------------------------------
# handler-shape
# --------------------------------------------------------------------------


def _handler_decorator(fn: ast.FunctionDef | ast.AsyncFunctionDef,
                       http_methods: set[str]) -> str | None:
    """The decorator that makes this function a route handler, as written.

    The SHAPE is matched, not a list of receiver names: any attribute call whose
    attribute is an HTTP method name. A checker hardcoding ``router`` and ``app``
    would miss api_test's ``@recent_router.get``, scan nineteen of twenty handlers
    and report nothing about the twentieth.
    """
    for dec in fn.decorator_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(target, ast.Attribute) and target.attr in http_methods:
            recv = name_of(target.value) or "?"
            return f"@{recv}.{target.attr}"
    return None


def check_handler_shape(rule: Rule, rel: str, facts: FileFacts, layout: Layout,
                        tally: Tally) -> list[Site]:
    """How a route handler must be declared: async, and/or declaring what it returns."""
    http = {str(m).lower() for m in (rule.signal("http_method_names") or [])}
    if not http:
        raise Unsupported("the rule names no HTTP method names, so no route handler "
                          "can be identified")
    forbidden_annotations = {str(a) for a in (rule.signal("forbidden_annotations") or [])}
    requires = [r.strip().lower() for r in as_list(rule.signal("require"))]

    want_async = False
    want_return = False
    for req in requires:
        if req in ("asyncfunctiondef", "async def", "asyncfunctiondef required"):
            want_async = True
        elif req in ("return annotation present", "return annotation"):
            want_return = True
        else:
            raise Unsupported(
                f"the rule requires {req!r}, which this shape of check does not know "
                f"how to test")
    if not want_async and not want_return and not forbidden_annotations:
        raise Unsupported("the rule requires nothing this shape of check can test")

    out: list[Site] = []
    tally.add("functions read", len(facts.functions))
    for f in facts.functions:
        dec = _handler_decorator(f.node, http)
        if dec is None:
            continue
        tally.add("route handlers found", 1)
        if want_async and not f.is_async:
            out.append(Site(
                rule.id, rel, f.node.lineno,
                f"the route handler {f.node.name}() is declared 'def', not 'async def'",
                f"python ast: FunctionDef(name={f.node.name!r}) at line {f.node.lineno} "
                f"decorated {dec}(...), and it is not an AsyncFunctionDef",
                enclosing=f.node.name))
        if want_return and f.node.returns is None:
            out.append(Site(
                rule.id, rel, f.node.lineno,
                f"the route handler {f.node.name}() declares no return type",
                f"python ast: {type(f.node).__name__}(name={f.node.name!r}) at line "
                f"{f.node.lineno} decorated {dec}(...) has returns=None",
                enclosing=f.node.name))
        elif forbidden_annotations and f.node.returns is not None:
            written = annotation_text(f.node.returns)
            if name_of(f.node.returns) in forbidden_annotations:
                out.append(Site(
                    rule.id, rel, f.node.lineno,
                    f"the route handler {f.node.name}() declares its return type as "
                    f"{written}, which the rule lists as not a type",
                    f"python ast: {type(f.node).__name__}(name={f.node.name!r}) at line "
                    f"{f.node.lineno} decorated {dec}(...) returns {written}",
                    enclosing=f.node.name))
    return out


# --------------------------------------------------------------------------
# forbidden-imports
# --------------------------------------------------------------------------


def _module_matches(imported: str, forbidden: str) -> bool:
    """``urllib.request`` matches itself and ``urllib.request.x``, never ``urllib``
    and never ``requests_mock``. Whole dotted segments only."""
    return imported == forbidden or imported.startswith(forbidden + ".")


def check_forbidden_imports(rule: Rule, rel: str, facts: FileFacts, layout: Layout,
                            tally: Tally) -> list[Site]:
    """Named modules must not be imported here, and named calls must not be made."""
    modules = [str(m) for m in (rule.signal("modules") or [])]
    calls = [str(c) for c in (rule.signal("calls") or [])]
    if not modules and not calls:
        raise Unsupported("the rule names no module and no call to look for")

    out: list[Site] = []
    tally.add("imports read", len(facts.imports))
    tally.add("calls read", len(facts.calls))
    for imp in facts.imports:
        for m in modules:
            if _module_matches(imp.module, m):
                out.append(Site(
                    rule.id, rel, imp.line,
                    f"an import of {m}, which the rule names",
                    f"python ast: {'ImportFrom' if imp.is_from else 'Import'} of "
                    f"{imp.module!r} at line {imp.line}  ({imp.text})"))
                break

    for call in facts.calls:
        dotted = dotted_of(call.node.func)
        for c in calls:
            head, _, tail = c.rpartition(".")
            matched = None
            if dotted == c and facts.imported_from.get(c.split(".")[0]) == head:
                # `import time` then `time.sleep(...)`
                matched = (f"python ast: Call to {c} at line {call.node.lineno}; "
                           f"'{c.split('.')[0]}' is bound in this file by 'import {head}'")
            elif (isinstance(call.node.func, ast.Name)
                  and call.node.func.id == tail
                  and facts.imported_from.get(tail) == head):
                # `from time import sleep` then `sleep(...)`
                matched = (f"python ast: Call(func=Name({tail!r})) at line "
                           f"{call.node.lineno}; ImportFrom({head!r}) binds that name here")
            if matched:
                out.append(Site(
                    rule.id, rel, call.node.lineno,
                    f"a call to {c}, which the rule names",
                    matched, enclosing=call.enclosing))
                break
    out.sort(key=lambda s: (s.line, s.observed))
    return out


# --------------------------------------------------------------------------
# forbidden-method-call
# --------------------------------------------------------------------------


def check_forbidden_method_call(rule: Rule, rel: str, facts: FileFacts,
                                layout: Layout, tally: Tally) -> list[Site]:
    """A named method must not be called on a receiver of a named kind."""
    m_names = {str(m) for m in (rule.signal("methods") or [])}
    recv_names = {str(r) for r in (rule.signal("receiver_names") or [])}
    recv_types = {str(r) for r in (rule.signal("receiver_types") or [])}
    if not m_names:
        raise Unsupported("the rule names no method to look for")

    out: list[Site] = []
    tally.add("method calls read",
              sum(1 for c in facts.calls if isinstance(c.node.func, ast.Attribute)))
    for call in facts.calls:
        f = call.node.func
        if not isinstance(f, ast.Attribute) or f.attr not in m_names:
            continue
        why = _receiver_reason(f, call.annotations, recv_names, recv_types)
        if why:
            out.append(Site(
                rule.id, rel, call.node.lineno,
                f"a call to .{f.attr}() on {name_of(f.value) or 'the receiver'}",
                f"python ast: Call(func=Attribute(attr={f.attr!r})) at line "
                f"{call.node.lineno}; {why}",
                enclosing=call.enclosing))
    return out


# --------------------------------------------------------------------------
# class-definition-home-file
# --------------------------------------------------------------------------


def check_class_definition_home_file(rule: Rule, rel: str, facts: FileFacts,
                                     layout: Layout, tally: Tally) -> list[Site]:
    """A class marked as a database table belongs in a named file, with a named base.

    A class counts when its body carries one of the marks the rule names — an
    assignment to ``__tablename__``, or a call to ``mapped_column(...)``. Two separate
    things can then be wrong about it, so they are reported separately: it is in the
    wrong file, and it does not inherit the base the rule names. Bases declared in the
    same file are followed one step at a time; bases in other files are not, because
    this reads one syntax tree at a time and does not resolve names across files.
    """
    marks = {str(m) for m in (rule.signal("class_marks") or [])}
    required_bases = {str(b) for b in (rule.signal("required_base_names") or [])}
    home = rule.signal("home_file")
    if not marks:
        raise Unsupported("the rule names no mark that identifies the classes it is about")

    local: dict[str, list[str]] = {c.node.name: c.base_names for c in facts.classes}

    def base_chain(name: str, seen: set[str]) -> list[str] | None:
        for b in local.get(name, []):
            if b in required_bases:
                return [b]
            if b not in seen:
                deeper = base_chain(b, seen | {b})
                if deeper is not None:
                    return [b, *deeper]
        return None

    out: list[Site] = []
    tally.add("classes read", len(facts.classes))
    for cls in facts.classes:
        hit = [m for m in cls.marks if m in marks]
        if not hit:
            continue
        tally.add("database table classes found", 1)
        node = cls.node
        out.append(Site(
            rule.id, rel, node.lineno,
            f"class {node.name} is a database table class ({', '.join(hit)} in its body), "
            f"declared in {Path(rel).name}",
            f"python ast: ClassDef(name={node.name!r}) at line {node.lineno}; "
            f"body carries {', '.join(hit)}",
            enclosing=node.name))
        if required_bases:
            chain = base_chain(node.name, {node.name})
            if chain is None:
                out.append(Site(
                    rule.id, rel, node.lineno,
                    f"class {node.name} is a database table class but none of its base "
                    f"classes is {' or '.join(sorted(required_bases))}; it has "
                    + (f"base {', '.join(cls.base_names)}" if cls.base_names else "no bases"),
                    f"python ast: ClassDef(name={node.name!r}) at line {node.lineno}; "
                    f"bases {cls.base_names}",
                    enclosing=node.name, always_a_finding=True))
    return out


# --------------------------------------------------------------------------
# config-file-fact
# --------------------------------------------------------------------------

_TABLE_EXISTS = re.compile(r"^table\s+\[([A-Za-z0-9_.\-]+)\]\s+exists$", re.I)
_VALUE_IS = re.compile(r"^([A-Za-z0-9_.\-]+)\s+is\s+(.+)$", re.I)


def _toml_get(data: dict[str, Any], dotted: str) -> tuple[bool, Any]:
    cur: Any = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def _literal(text: str) -> Any:
    t = text.strip()
    low = t.lower()
    if low in ("true", "false"):
        return low == "true"
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        return t[1:-1]
    try:
        return int(t)
    except ValueError:
        raise Unsupported(
            f"the rule requires a value {text!r}, and this shape of check only compares "
            f"against true, false, a quoted string, or a whole number")


def _header_line(raw: str, dotted: str) -> int:
    """The line a TOML table header sits on, so a finding can point at something real."""
    pattern = re.compile(r"^\s*\[\s*" + re.escape(dotted) + r"\s*\]", re.M)
    m = pattern.search(raw)
    return raw[: m.start()].count("\n") + 1 if m else 0


def check_config_file_fact(rule: Rule, repo: Path, layout: Layout,
                           files: list[tuple[str, FileFacts]], tally: Tally) -> list[Site]:
    """A configuration file must state something. Read as TOML; nothing is run.

    Only that the configuration is present is checked. Neither mypy nor ruff is
    executed by this checker, and a finding here says the setting is missing or
    different, never that the code fails type checking.
    """
    rel = str(rule.signal("file") or "")
    if not rel:
        raise Unsupported("the rule names no configuration file to read")
    requires = as_list(rule.signal("require"))
    if not requires:
        raise Unsupported("the rule states no requirement about the configuration file")

    path = repo / rel
    if not path.is_file():
        return [Site(rule.id, rel, 0,
                     f"there is no {rel} in this repository",
                     f"file tree: {rel} is not a file under the repository root")]
    raw = path.read_text(encoding="utf-8")
    try:
        data = tomllib.loads(raw)
    except tomllib.TOMLDecodeError as exc:
        raise Unsupported(f"{rel} could not be read as TOML ({exc}), so nothing about "
                          f"it was checked")

    out: list[Site] = []
    tally.add("requirements checked", len(requires))
    for req in requires:
        req = req.strip()
        m = _TABLE_EXISTS.match(req)
        if m:
            dotted = m.group(1)
            present, value = _toml_get(data, dotted)
            if not (present and isinstance(value, dict)):
                out.append(Site(
                    rule.id, rel, 0,
                    f"{rel} has no [{dotted}] table",
                    f"toml: no table at {dotted} in {rel}"))
            continue
        m = _VALUE_IS.match(req)
        if m:
            dotted, wanted_text = m.group(1), m.group(2)
            wanted = _literal(wanted_text)
            present, value = _toml_get(data, dotted)
            line = _header_line(raw, dotted.rpartition(".")[0])
            if not present:
                out.append(Site(
                    rule.id, rel, line,
                    f"{rel} does not set {dotted}; the rule wants it {wanted_text.strip()}",
                    f"toml: no key at {dotted} in {rel}"))
            elif value != wanted:
                out.append(Site(
                    rule.id, rel, line,
                    f"{rel} sets {dotted} to {value!r}; the rule wants "
                    f"{wanted_text.strip()}",
                    f"toml: {dotted} = {value!r} in {rel}"))
            continue
        raise Unsupported(
            f"the rule states its requirement as {req!r}, and this shape of check only "
            f"understands 'table [x.y] exists' and 'x.y is <value>'")
    return out


# --------------------------------------------------------------------------
# annotation-completeness
# --------------------------------------------------------------------------


def check_annotation_completeness(rule: Rule, rel: str, facts: FileFacts,
                                  layout: Layout, tally: Tally) -> list[Site]:
    """Every function annotates its arguments and its return.

    One site per function, listing everything missing from it, so a function that is
    missing three annotations is one place to go and fix, not three. An explicit
    ``Any`` is not reported: "implicit Any" means the absence of an annotation, which
    is what this looks for. Lambdas cannot carry annotations and are not looked at.
    """
    requires = [r.strip().lower() for r in as_list(rule.signal("require"))]
    ignore = {str(a) for a in (rule.signal("ignore_args") or [])}
    want_return = False
    want_args = False
    for req in requires:
        if req in ("return annotation", "return annotation present"):
            want_return = True
        elif req in ("annotation on every argument", "argument annotations"):
            want_args = True
        else:
            raise Unsupported(
                f"the rule requires {req!r}, which this shape of check does not know "
                f"how to test")
    if not want_return and not want_args:
        raise Unsupported("the rule requires nothing this shape of check can test")

    out: list[Site] = []
    tally.add("functions read", len(facts.functions))
    for f in facts.functions:
        node = f.node
        missing: list[str] = []
        if want_args:
            a = node.args
            for arg in [*a.posonlyargs, *a.args, *a.kwonlyargs,
                        *([a.vararg] if a.vararg else []),
                        *([a.kwarg] if a.kwarg else [])]:
                if arg is None or arg.arg in ignore:
                    continue
                if arg.annotation is None:
                    missing.append(f"the argument {arg.arg!r}")
        if want_return and node.returns is None:
            missing.append("the return")
        if missing:
            out.append(Site(
                rule.id, rel, node.lineno,
                f"{node.name}() has no type annotation on " + ", ".join(missing),
                f"python ast: {type(node).__name__}(name={node.name!r}) at line "
                f"{node.lineno}; {len(missing)} annotation(s) absent",
                enclosing=node.name))
    return out


# --------------------------------------------------------------------------
# forbidden-construction
# --------------------------------------------------------------------------


def check_forbidden_construction(rule: Rule, rel: str, facts: FileFacts,
                                 layout: Layout, tally: Tally) -> list[Site]:
    """A named thing must not be constructed here.

    A call is a construction; a ``def`` of the same name is not, and an annotation
    that merely mentions the name is not, because only ``ast.Call`` nodes are looked
    at. The directories where the thing legitimately does get built are excluded by
    the engine before this is called.
    """
    calls = {str(c) for c in (rule.signal("calls") or [])}
    if not calls:
        raise Unsupported("the rule names nothing whose construction it forbids")
    out: list[Site] = []
    tally.add("calls read", len(facts.calls))
    for call in facts.calls:
        n = name_of(call.node.func)
        if n in calls:
            written = dotted_of(call.node.func) or n
            out.append(Site(
                rule.id, rel, call.node.lineno,
                f"a call to {written}(), which builds one of the things the rule names",
                f"python ast: Call(func -> {n!r}) at line {call.node.lineno}",
                enclosing=call.enclosing))
    return out


# --------------------------------------------------------------------------
# The table. A rule naming a kind that is not here is reported as unsupported.
# --------------------------------------------------------------------------

FileCheck = Callable[[Rule, str, FileFacts, Layout, Tally], list[Site]]
RepoCheck = Callable[[Rule, Path, Layout, list[tuple[str, FileFacts]], Tally], list[Site]]

PER_FILE_CHECKS: dict[str, FileCheck] = {
    "call-site-home-file": check_call_site_home_file,
    "module-import-boundary": check_module_import_boundary,
    "handler-shape": check_handler_shape,
    "forbidden-imports": check_forbidden_imports,
    "forbidden-method-call": check_forbidden_method_call,
    "class-definition-home-file": check_class_definition_home_file,
    "annotation-completeness": check_annotation_completeness,
    "forbidden-construction": check_forbidden_construction,
}

PER_REPO_CHECKS: dict[str, RepoCheck] = {
    "file-layout": check_file_layout,
    "config-file-fact": check_config_file_fact,
}

KNOWN_KINDS = sorted([*PER_FILE_CHECKS, *PER_REPO_CHECKS])
