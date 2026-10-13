"""Every git command GuardKit runs in a project goes through ``project_git``.

Reads the source of ``guardkit/`` and ``installer/`` and fails on:

* a ``subprocess``, ``asyncio`` subprocess or ``os`` process call whose command
  is git, anywhere other than ``guardkit/lib/project_git.py``. A command counts
  as git when it is a literal list or tuple starting with ``"git"``, a
  ``["git"] + args`` sum, a name assigned one of those, or a string starting
  with ``"git "``;
* a git command that reaches another repository (``fetch``, ``push`` and the
  rest), written anywhere, whether it goes to ``subprocess`` or to
  ``run_git()`` or an executor;
* a production executor that does not hand its command to ``run_git()`` (or,
  for the evidence capture's bounded runner, ``prepare_git()``).

The one named exception is ``installer/core/commands/lib/distribution_helpers.py``:
it publishes a template repository when an operator asks for it (add, commit,
tag, push), nothing in GuardKit imports it, and it never runs inside a project
the factory builds.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ("guardkit", "installer")
HELPER = Path("guardkit/lib/project_git.py")
EXCEPTION = Path("installer/core/commands/lib/distribution_helpers.py")

NETWORK = {"fetch", "pull", "push", "clone", "ls-remote", "fetch-pack", "send-pack",
           "credential", "submodule"}
NETWORK_REMOTE = {"update", "show", "prune", "set-head"}

PROCESS_CALLS = {
    ("subprocess", "run"), ("subprocess", "Popen"), ("subprocess", "call"),
    ("subprocess", "check_call"), ("subprocess", "check_output"),
    ("subprocess", "getoutput"), ("subprocess", "getstatusoutput"),
    ("asyncio", "create_subprocess_exec"), ("asyncio", "create_subprocess_shell"),
    ("os", "system"), ("os", "popen"), ("os", "execv"), ("os", "execvp"),
    ("os", "execvpe"), ("os", "execl"), ("os", "execlp"), ("os", "spawnv"),
    ("os", "spawnvp"), ("os", "posix_spawn"), ("os", "posix_spawnp"),
}

#: Production executors, and the helper function each must hand its command to.
EXECUTORS: Tuple[Tuple[str, str], ...] = (
    ("guardkit/orchestrator/worktree_checkpoints.py", "SubprocessGitExecutor.execute"),
    ("guardkit/worktrees/manager.py", "SubprocessExecutor.run"),
    ("installer/core/lib/orchestrator/worktrees.py", "SubprocessExecutor.run"),
    ("guardkit/qa/diff_ingest.py", "_default_git"),
    ("guardkit/qa/enforcement.py", "_default_git"),
    ("guardkit/orchestrator/run_evidence.py", "_git_runner"),
)


def _python_files() -> Iterator[Path]:
    for top in SOURCES:
        for path in sorted((ROOT / top).rglob("*.py")):
            rel = path.relative_to(ROOT)
            if "__pycache__" in rel.parts or rel.parts[:3] == ("installer", "core", "templates"):
                continue
            yield rel


def _const(node: ast.AST) -> Optional[str]:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _list_items(node: ast.AST) -> Optional[List[ast.AST]]:
    if isinstance(node, (ast.List, ast.Tuple)):
        return list(node.elts)
    return None


class _Scanner(ast.NodeVisitor):
    def __init__(self) -> None:
        self.process_aliases: Dict[str, Tuple[str, str]] = {}
        self.module_aliases: Dict[str, str] = {}
        self.assigned: Dict[str, ast.AST] = {}
        #: Names holding git commands (``cmds.append(["git", ...])``).
        self.git_collections: set = set()
        self.direct: List[int] = []
        self.network: List[int] = []

    # -- what names mean --------------------------------------------------

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.module_aliases[alias.asname or alias.name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            key = (node.module or "", alias.name)
            if key in PROCESS_CALLS:
                self.process_aliases[alias.asname or alias.name] = key
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.assigned[target.id] = node.value
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        source = node.iter
        holds_git = isinstance(source, ast.Name) and source.id in self.git_collections
        items = _list_items(source)
        if items and any(self._is_git_command(i) for i in items):
            holds_git = True
        if holds_git and isinstance(node.target, ast.Name):
            self.assigned[node.target.id] = ast.List(elts=[ast.Constant("git")])
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name) and node.value is not None:
            self.assigned[node.target.id] = node.value
        self.generic_visit(node)

    # -- is this a git command? -------------------------------------------

    def _is_git_word(self, node: ast.AST) -> bool:
        value = _const(node)
        if value is None and isinstance(node, ast.Name):
            bound = self.assigned.get(node.id)
            value = _const(bound) if bound is not None else None
        return value is not None and (value == "git" or value.endswith("/git"))

    def _is_git_command(self, node: ast.AST, depth: int = 0) -> bool:
        if depth > 5:
            return False
        if isinstance(node, ast.Starred):
            return self._is_git_command(node.value, depth + 1)
        items = _list_items(node)
        if items:
            return self._is_git_word(items[0])
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return self._is_git_command(node.left, depth + 1)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in (
            "list", "tuple"
        ) and node.args:
            return self._is_git_command(node.args[0], depth + 1)
        if isinstance(node, ast.Name) and node.id in self.assigned:
            return self._is_git_command(self.assigned[node.id], depth + 1)
        text = _const(node)
        if text is not None:
            return text.startswith("git ")
        if isinstance(node, ast.JoinedStr) and node.values:
            first = _const(node.values[0])
            return first is not None and first.startswith("git ")
        return False

    def _process_call(self, node: ast.Call) -> bool:
        func = node.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            module = self.module_aliases.get(func.value.id, func.value.id)
            return (module, func.attr) in PROCESS_CALLS
        if isinstance(func, ast.Name):
            return func.id in self.process_aliases
        return False

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if (isinstance(func, ast.Attribute) and func.attr in ("append", "extend", "insert")
                and isinstance(func.value, ast.Name) and node.args
                and any(self._is_git_command(a) for a in node.args)):
            self.git_collections.add(func.value.id)
        if self._process_call(node):
            command = node.args[0] if node.args else next(
                (k.value for k in node.keywords if k.arg in ("args", "cmd", "command")), None
            )
            if command is not None and self._is_git_command(command):
                self.direct.append(node.lineno)
        # A network command handed to anything whose name says git.
        func_name = (
            node.func.attr if isinstance(node.func, ast.Attribute)
            else node.func.id if isinstance(node.func, ast.Name) else ""
        )
        if node.args and "git" in func_name.lower():
            items = _list_items(node.args[0])
            if items and _const(items[0]) in NETWORK:
                self.network.append(node.lineno)
        self.generic_visit(node)

    def visit_List(self, node: ast.List) -> None:
        self._check_network_literal(node)
        self.generic_visit(node)

    def visit_Tuple(self, node: ast.Tuple) -> None:
        self._check_network_literal(node)
        self.generic_visit(node)

    def _check_network_literal(self, node: ast.AST) -> None:
        items = _list_items(node) or []
        words = [_const(i) for i in items[:3]]
        if len(words) >= 2 and words[0] == "git":
            if words[1] in NETWORK or (
                words[1] == "remote" and len(words) > 2 and words[2] in NETWORK_REMOTE
            ):
                self.network.append(node.lineno)


def _scan(rel: Path) -> _Scanner:
    scanner = _Scanner()
    scanner.visit(ast.parse((ROOT / rel).read_text(encoding="utf-8"), filename=str(rel)))
    return scanner


def test_no_direct_git_process_calls() -> None:
    found = []
    for rel in _python_files():
        if rel in (HELPER, EXCEPTION):
            continue
        for line in _scan(rel).direct:
            found.append(f"{rel}:{line}")
    assert found == [], (
        "git is run directly instead of through guardkit.lib.project_git.run_git: "
        + ", ".join(found)
    )


def test_no_network_git_commands() -> None:
    found = []
    for rel in _python_files():
        if rel == EXCEPTION:
            continue
        for line in _scan(rel).network:
            found.append(f"{rel}:{line}")
    assert found == [], "git commands that reach another repository: " + ", ".join(found)


def _function_source(rel: str, qualified: str) -> Optional[str]:
    source = (ROOT / rel).read_text(encoding="utf-8")
    tree = ast.parse(source)
    parts = qualified.split(".")
    body = tree.body
    found = None
    for part in parts:
        found = next(
            (n for n in body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                                               ast.ClassDef)) and n.name == part),
            None,
        )
        if found is None:
            return None
        body = found.body
    return ast.get_source_segment(source, found)


def test_every_production_executor_hands_its_command_to_the_helper() -> None:
    missing = []
    for rel, qualified in EXECUTORS:
        body = _function_source(rel, qualified)
        if body is None or not ("run_git(" in body or "prepare_git(" in body):
            missing.append(f"{rel}::{qualified}")
    assert missing == [], "executors that do not hand git to the helper: " + ", ".join(missing)


def test_the_source_check_recognises_each_shape() -> None:
    """The scanner itself: each recognised shape, and one it must not flag."""
    sample = '''
import subprocess, os, asyncio
from subprocess import run as sprun
GIT = "git"
CMD = ["git", "status"]
def f(args):
    subprocess.run(["git", "status"])
    subprocess.run(["git"] + args)
    subprocess.run(CMD)
    os.system("git status")
    sprun([GIT, "diff"])
    asyncio.create_subprocess_exec(*["git", "log"])
    subprocess.run(["ls"])
    run_git(["fetch", "origin"])
    x = ["git", "push", "origin"]
    cmds = []
    cmds.append(["git", "rev-parse", "HEAD"])
    for c in cmds:
        subprocess.run(c)
'''
    scanner = _Scanner()
    scanner.visit(ast.parse(sample))
    assert scanner.direct == [7, 8, 9, 10, 11, 12, 19]
    assert sorted(scanner.network) == [14, 15]
