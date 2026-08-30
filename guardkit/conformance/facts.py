"""What one Python file's syntax tree shows, gathered in a single walk.

Everything the checks need comes from here, so no check ever reads the raw text of
a source file. That is deliberate: a text search cannot tell code from prose, and
``api_test`` carries ``await db.execute(select(User))`` inside a docstring at
``src/db/dependencies.py:29``. A syntax tree cannot see it, because a docstring is
a string constant. Any run can be checked against that one line to confirm the
instrument is reading code and not text.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field


def name_of(node: ast.AST | None) -> str | None:
    """The trailing identifier of a Name / Attribute / Subscript, if there is one."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return name_of(node.value)
    return None


def dotted_of(node: ast.AST | None) -> str | None:
    """``"time.sleep"`` for ``time.sleep``; None when the chain is not plain dotted names."""
    parts: list[str] = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    return None


def unwrap(node: ast.AST | None) -> ast.AST | None:
    """Strip ``await`` so ``await db.execute(stmt)`` presents as the call it is."""
    while isinstance(node, ast.Await):
        node = node.value
    return node


def annotation_text(node: ast.AST | None) -> str | None:
    """The annotation as written, close enough for a report to quote."""
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:  # pragma: no cover - ast.unparse handles every node we parse
        return name_of(node)


@dataclass
class ImportSite:
    module: str          # dotted module path as written ("" for `from . import x`)
    line: int
    text: str            # the import as a reader would write it
    level: int           # 0 for absolute, 1+ for relative
    is_from: bool


@dataclass
class CallSite:
    node: ast.Call
    enclosing: str | None            # name of the function the call sits in
    annotations: dict[str, str]      # parameter name -> annotation, from enclosing signatures


@dataclass
class Assignment:
    enclosing: str | None
    target: str
    line: int
    value: ast.AST


@dataclass
class FunctionSite:
    node: ast.FunctionDef | ast.AsyncFunctionDef
    is_async: bool
    enclosing_class: str | None


@dataclass
class ClassSite:
    node: ast.ClassDef
    marks: list[str] = field(default_factory=list)   # e.g. ["__tablename__", "mapped_column"]
    base_names: list[str] = field(default_factory=list)


class FileFacts:
    """One walk of one file, keeping what every check kind needs."""

    def __init__(self, rel: str, tree: ast.Module) -> None:
        self.rel = rel
        self.tree = tree
        self.imported_from: dict[str, str] = {}     # local name -> module it came from
        self.imports: list[ImportSite] = []
        self.calls: list[CallSite] = []
        self.assignments: list[Assignment] = []
        self.classes: list[ClassSite] = []
        self.functions: list[FunctionSite] = []
        self._collect_imports(tree)
        self._walk(tree, enclosing=None, annotations={}, in_class=None)

    # -- imports ---------------------------------------------------------

    def _collect_imports(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    self.imported_from[alias.asname or alias.name] = mod
                text = (f"from {'.' * node.level}{mod} import "
                        + ", ".join(a.name for a in node.names))
                self.imports.append(ImportSite(mod, node.lineno, text, node.level, True))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    # `import a.b.c` binds `a`; `import a.b as ab` binds `ab`.
                    bound = alias.asname or alias.name.split(".")[0]
                    self.imported_from[bound] = alias.name
                    self.imports.append(
                        ImportSite(alias.name, node.lineno, f"import {alias.name}", 0, False))

    # -- the walk --------------------------------------------------------

    def _walk(self, node: ast.AST, enclosing: str | None,
              annotations: dict[str, str], in_class: str | None) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.functions.append(
                FunctionSite(node, isinstance(node, ast.AsyncFunctionDef), in_class))
            annotations = dict(annotations)
            a = node.args
            for arg in [*a.posonlyargs, *a.args, *a.kwonlyargs,
                        *([a.vararg] if a.vararg else []),
                        *([a.kwarg] if a.kwarg else [])]:
                if arg is not None and arg.annotation is not None:
                    t = name_of(arg.annotation)
                    if t:
                        annotations[arg.arg] = t
            enclosing = node.name
        elif isinstance(node, ast.ClassDef):
            self.classes.append(ClassSite(
                node,
                marks=self._class_marks(node),
                base_names=[b for b in (name_of(x) for x in node.bases) if b],
            ))
            in_class = node.name
        elif isinstance(node, ast.Assign):
            value = unwrap(node.value)
            for target in node.targets:
                if isinstance(target, ast.Name) and value is not None:
                    self.assignments.append(
                        Assignment(enclosing, target.id, node.lineno, value))
        elif isinstance(node, ast.AnnAssign):
            value = unwrap(node.value)
            if isinstance(node.target, ast.Name) and value is not None:
                self.assignments.append(
                    Assignment(enclosing, node.target.id, node.lineno, value))

        if isinstance(node, ast.Call):
            self.calls.append(CallSite(node, enclosing, annotations))

        for child in ast.iter_child_nodes(node):
            self._walk(child, enclosing, annotations, in_class)

    @staticmethod
    def _class_marks(cls: ast.ClassDef) -> list[str]:
        """The names in a class body that mark it as a database table class.

        Two marks are recognised because the rules file names two: an assignment to
        ``__tablename__``, and a call to ``mapped_column(...)`` anywhere in the body.
        """
        marks: list[str] = []
        for node in ast.walk(cls):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id == "__tablename__":
                        marks.append("__tablename__")
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and node.target.id == "__tablename__":
                    marks.append("__tablename__")
            elif isinstance(node, ast.Call):
                n = name_of(node.func)
                if n == "mapped_column":
                    marks.append("mapped_column")
        # keep order, drop duplicates
        seen: set[str] = set()
        return [m for m in marks if not (m in seen or seen.add(m))]
