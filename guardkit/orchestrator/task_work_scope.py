"""Cooperating checkout writers and immutable, in-memory task attribution.

One rule (step 2, 26 October 2026): one writer holds a checkout at a time,
under an exclusive lock. Nothing else about earlier writers refuses the next
one: work a task leaves behind, approved or not, stays for the next task.
Different worktrees have different git directories; sibling writers share locks.
"""

from __future__ import annotations

from contextlib import contextmanager, ExitStack
from dataclasses import dataclass, asdict
import fcntl
import hashlib
import json
import logging
from pathlib import Path
import threading
import uuid

logger = logging.getLogger(__name__)


class ScopeUnavailable(RuntimeError):
    """Work is preserved, but cannot safely be attributed or resumed."""


def _git(root, *args):
    from guardkit.lib.project_git import run_git

    result = run_git(list(args), cwd=Path(root), timeout=30, check=True)
    return result.stdout.rstrip("\n")


def identity(root):
    root = Path(_git(Path(root).resolve(), "rev-parse", "--show-toplevel")).resolve()
    git_dir = Path(_git(root, "rev-parse", "--absolute-git-dir")).resolve()
    return root, git_dir


def _product(path):
    from guardkit.orchestrator.worktree_checkpoints import is_factory_record
    from guardkit.orchestrator.agent_invoker import _is_orchestrator_managed_path

    return not is_factory_record(path) and not _is_orchestrator_managed_path(path)


def _dirty(root):
    paths = _git(root, "diff", "--name-only", "-z", "HEAD").split("\0")
    paths += _git(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
    return sorted({p for p in paths if p and _product(p)})


@dataclass(frozen=True)
class RepositoryScope:
    name: str
    root: str
    git_dir: str
    baseline: str
    branch: str


@dataclass(frozen=True)
class TaskWorkScope:
    task_id: str
    feature_id: str
    scope_id: str
    repositories: tuple[RepositoryScope, ...]
    round_id: str = "initial"
    admission_reason: str = "fresh"
    schema_version: int = 1
    build_id: str = ""
    provenance: str = "retained admission"
    source_declaration: str = ""

    @property
    def baseline_commit(self):
        return self.repositories[0].baseline


_registry_lock = threading.Lock()
_locks = {}
_fresh = {}
_bindings = {}
_selected = {}
# Step 1 (24 October 2026): the last approved commit of each checkout in this
# run, kept when a task's approval completes. A later failure never erases it.
_approved_heads = {}
# Step 2 (26 October 2026): later tasks now run after a task that was not
# approved, on top of what it left. The approved part stays the work before
# the first such task, so the offer never carries unapproved work.
_approval_stopped = set()
_local = threading.local()


def register_fresh_checkout(root, source_commit, *, source_root=None):
    """Called by worktree creation with its resolved source pin: the commit
    whose committed declarations this build reads, and a new build identity."""
    root, git_dir = identity(root)
    source = _git(root, "rev-parse", str(source_commit) + "^{commit}")
    with _registry_lock:
        _selected.pop(str(git_dir), None)
        _bindings.pop(str(git_dir), None)
        _approved_heads.pop(str(git_dir), None)
        _approval_stopped.discard(str(git_dir))
        _fresh[str(git_dir)] = {
            "commit": source,
            "source_root": str(Path(source_root or root).resolve()),
            "build_id": uuid.uuid4().hex,
        }


def adopt_prepared_checkout(root):
    """A checkout another factory process prepared becomes this process's
    starting input, at its current HEAD, with what earlier steps left in it.

    Forge's repair conductor runs each work step as a new ``guardkit
    task-work`` process in a checkout it prepared (build-FEAT-6CE5-20261026132641).
    """
    root, _ = identity(root)
    register_fresh_checkout(root, _git(root, "rev-parse", "HEAD"), source_root=root)


def bind_fresh_footprint(root, source_root, artifact_path, *, kind, expected=None):
    """Bind declared inputs to an immutable source blob, before any task move.

    This selects starting inputs, never approves sibling work.
    """
    import yaml
    from guardkit.orchestrator.evidence_repos import resolve_evidence_repos

    root, git_dir = identity(root)
    source_root = Path(source_root).resolve()
    # Step 2 (26 October 2026): a checkout this process did not register (a
    # resumed or re-run build) reads its declarations at its current HEAD.
    fresh = _fresh.get(str(git_dir)) or _selected.get(str(git_dir))
    if not fresh:
        fresh = _fresh.setdefault(str(git_dir), {
            "commit": _git(root, "rev-parse", "HEAD"),
            "source_root": str(source_root),
            "build_id": uuid.uuid4().hex,
        })

    def _declared(text):
        if kind == "task":
            text = text.split("---", 2)[1] if text.startswith("---") else ""
        document = yaml.safe_load(text)
        return (document.get("evidence_repos") if isinstance(document, dict) else None) or []

    declared, blob_id = list(expected or []), ""
    if artifact_path is not None:
        artifact = Path(artifact_path)
        if not artifact.is_absolute():
            artifact = source_root / artifact
        try:
            artifact = artifact.resolve()
            relative = artifact.relative_to(source_root).as_posix()
            # Git reads the registered source, never the mutable working file.
            blob_id = _git(root, "rev-parse", f"{fresh['commit']}:{relative}")
            declared = _declared(_git(root, "cat-file", "blob", blob_id))
        except Exception:  # noqa: BLE001
            # A declaration file that is not committed (or not readable
            # there) is read as it is on disk.
            blob_id = ""
            try:
                declared = _declared(artifact.read_text())
            except Exception:  # noqa: BLE001
                pass
    if not isinstance(declared, list):
        declared = []
    resolved = resolve_evidence_repos(declared, source_root)
    binding = {
        "repos": tuple(resolved),
        "blob": blob_id,
        "declaration": json.dumps(declared, sort_keys=True),
        "source": {**fresh, "source_root": str(source_root)},
    }
    _bindings[str(git_dir)] = binding
    return list(resolved)


def current_lease(root=None):
    lease = getattr(_local, "lease", None)
    if lease and root is not None and str(identity(root)[0]) not in lease.expected:
        return None
    return lease


class CheckoutLease:
    def __init__(self, repositories):
        self.repositories = repositories
        self.expected = {
            str(root): _git(root, "rev-parse", "HEAD") for _, root, _ in repositories
        }
        self.branches = {
            str(root): _git(root, "symbolic-ref", "--short", "HEAD")
            for _, root, _ in repositories
        }
        self.scope = None
        self.checkpoints = set()
        self.owner = threading.get_ident()
        self.failure = None

    def verify(self, scope=None):
        if current_lease() is not self or threading.get_ident() != self.owner:
            raise ScopeUnavailable(
                "No retained checkout ownership; automatic resume refused; work preserved"
            )
        if scope is not None and scope is not self.scope:
            raise ScopeUnavailable("Task scope is not the retained admission object")
        # The checkout's branch and HEAD as they are now are where this
        # writer goes on from (cull, 27 October 2026).
        # A detached HEAD reads as "HEAD"; the checkpoint's branch checks
        # decide what happens next.
        for _, root, _ in self.repositories:
            self.branches[str(root)] = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
            self.expected[str(root)] = _git(root, "rev-parse", "HEAD")

    def checkpoint_completed(self):
        # Only the checkpoint writer calls this after validating the old HEAD.
        self.expected = {
            str(root): _git(root, "rev-parse", "HEAD")
            for _, root, _ in self.repositories
        }
        self.checkpoints.add(tuple(sorted(self.expected.items())))

    def admit(self, task_id, feature_id="", round_id="initial"):
        self.verify()
        if self.scope is not None:
            if self.scope.task_id != task_id:
                raise ScopeUnavailable("A different task already owns this checkout")
            return self.scope
        is_repair = str(round_id) not in {"initial", "1"}
        # What earlier tasks left in the checkout, approved or not, is this
        # task's starting point.
        self.scope = TaskWorkScope(
            task_id,
            feature_id,
            uuid.uuid4().hex,
            tuple(
                RepositoryScope(
                    name,
                    str(root),
                    str(git_dir),
                    self.expected[str(root)],
                    self.branches[str(root)],
                )
                for name, root, git_dir in self.repositories
            ),
            str(round_id),
            "gate repair" if is_repair else "fresh",
            build_id=_selected.get(str(self.repositories[0][2]), {}).get(
                "build_id", ""
            ),
            provenance="admitted source and selected sibling inputs",
            source_declaration=_bindings.get(str(self.repositories[0][2]), {}).get(
                "blob", ""
            ),
        )
        from guardkit.orchestrator.paths import TaskArtifactPaths

        # Step 1 (24 October 2026): the scope record is bookkeeping. The
        # in-memory scope above is what the task runs on; a failed write is
        # logged and never ends the task.
        try:
            artifact = TaskArtifactPaths.private_artifact_path(
                task_id, f"scope-{self.scope.scope_id}.json", self.repositories[0][1]
            )
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text(json.dumps(asdict(self.scope), indent=2))
        except OSError as exc:
            logger.warning(
                "Scope record for %s could not be written (%s); the task goes on",
                task_id, exc,
            )
        return self.scope

    def poison(self, reason):
        """This writer did not finish approved; it never refuses the next one."""
        self.failure = self.failure or str(reason) or "Writer did not settle; work preserved"


@contextmanager
def checkout_lease(root, evidence_repos=(), cancelled=None):
    primary = identity(root)
    repos = [("", *primary)] + [(r.name, *identity(r.root)) for r in evidence_repos]
    active = current_lease()
    if active:
        yield active
        return
    with ExitStack() as stack:
        for git_dir in sorted({d for _, _, d in repos}, key=str):
            with _registry_lock:
                lock = _locks.setdefault(str(git_dir), threading.Lock())
            while not lock.acquire(timeout=0.1):
                if cancelled and cancelled():
                    raise ScopeUnavailable(
                        "Admission cancelled while prior writer still owns checkout"
                    )
            stack.callback(lock.release)
            handle = stack.enter_context(open(git_dir / "guardkit-writer.lock", "a+"))
            while True:
                try:
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if cancelled and cancelled():
                        raise ScopeUnavailable(
                            "Admission cancelled while another process owns checkout"
                        )
                    threading.Event().wait(0.1)
            stack.callback(fcntl.flock, handle, fcntl.LOCK_UN)
        selecting = str(primary[1]) in _fresh
        selected_heads = {
            str(repository_root): _git(repository_root, "rev-parse", "HEAD")
            for _, repository_root, _ in repos
        }
        if selecting:
            source = _fresh.pop(str(primary[1]))
            _selected[str(primary[1])] = {
                **source,
                "inputs": selected_heads,
                "provenance": "selected starting inputs; not approval",
            }
        lease = CheckoutLease(repos)
        _local.lease = lease
        try:
            yield lease
        except BaseException as exc:
            lease.poison(str(exc))
            raise
        finally:
            _local.lease = None
            if lease.scope is not None:
                # The approved part is the work before the first task that
                # was not approved (step 2, 26 October 2026).
                for _, root_, git_dir in repos:
                    if lease.failure:
                        _approval_stopped.add(str(git_dir))
                    elif str(git_dir) not in _approval_stopped:
                        _approved_heads[str(git_dir)] = lease.expected[str(root_)]


def approved_head(root):
    """The last commit an approved task left in this checkout during this run,
    or ``None`` when no task has been approved here yet."""
    try:
        _, git_dir = identity(root)
    except Exception:  # noqa: BLE001 — absence, never a failure
        return None
    return _approved_heads.get(str(git_dir))


def collect_changes(scope):
    if not isinstance(scope, TaskWorkScope):
        raise ScopeUnavailable(
            "No trusted admitted task scope; attribution unavailable"
        )
    lease = current_lease()
    if lease is None:
        raise ScopeUnavailable("Task writer no longer owns the checkout")
    lease.verify(scope)
    result = {
        "available": True,
        "scope_id": scope.scope_id,
        "baseline_commit": scope.baseline_commit,
        "created": [],
        "modified": [],
        "deleted": [],
    }
    for repo in scope.repositories:
        prefix = repo.name + ":" if repo.name else ""
        before = set(
            _git(repo.root, "ls-tree", "-r", "--name-only", "-z", repo.baseline).split(
                "\0"
            )
        )
        changed = _git(
            repo.root, "diff", "--no-renames", "--name-only", "-z", repo.baseline
        ).split("\0")
        changed += _git(
            repo.root, "ls-files", "--others", "--exclude-standard", "-z"
        ).split("\0")
        for path in sorted(set(changed)):
            if not path or not _product(path):
                continue
            kind = (
                "created"
                if path not in before
                else (
                    "modified"
                    if (Path(repo.root) / path).exists()
                    or (Path(repo.root) / path).is_symlink()
                    else "deleted"
                )
            )
            result[kind].append(prefix + path)
    return result


def boundary_snapshot(lease):
    lease.verify()
    snapshots = []
    for _, root, _ in lease.repositories:
        paths = _dirty(root)
        payload = []
        for path in paths:
            file = root / path
            data = (
                str(file.readlink()).encode()
                if file.is_symlink()
                else (file.read_bytes() if file.is_file() else b"<deleted>")
            )
            mode = file.lstat().st_mode if file.exists() or file.is_symlink() else None
            payload.append((path, mode, hashlib.sha256(data).hexdigest()))
        snapshots.append(
            (
                _git(root, "rev-parse", "HEAD"),
                _git(root, "diff", "--cached", "--binary"),
                payload,
            )
        )
    return snapshots
