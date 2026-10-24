"""Cooperating checkout writers and immutable, in-memory task attribution.

The on-disk marker is deny-only crash evidence, never a resume credential.
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
_history = {}
_fresh = {}
_bindings = {}
_selected = {}
# Step 1 (24 October 2026): the last approved commit of each checkout in this
# run, kept when a task's approval completes. A later failure never erases it.
_approved_heads = {}
_local = threading.local()


def register_fresh_checkout(root, source_commit, *, source_root=None):
    """Called only by fresh worktree creation with its resolved source pin.

    The in-memory registration, not a clean tree or a marker, authorizes the
    first admission. Saved files can only refuse subsequent use.
    """
    root, git_dir = identity(root)
    source = _git(root, "rev-parse", str(source_commit) + "^{commit}")
    if _git(root, "rev-parse", "HEAD") != source:
        raise ScopeUnavailable("Fresh worktree does not match admitted source")
    with _registry_lock:
        if str(git_dir) in _history or (git_dir / "guardkit-writer-unsettled").exists():
            raise ScopeUnavailable(
                "Cannot register an old or unsettled checkout as fresh"
            )
        _approved_heads.pop(str(git_dir), None)
        _fresh[str(git_dir)] = {
            "commit": source,
            "source_root": str(Path(source_root or root).resolve()),
            "build_id": uuid.uuid4().hex,
        }


def bind_fresh_footprint(root, source_root, artifact_path, *, kind, expected=None):
    """Bind declared inputs to an immutable source blob, before any task move.

    This selects starting inputs, never approves sibling work. The capability
    is consumed by the first all-footprint lease and cannot be recreated.
    """
    import yaml
    from guardkit.orchestrator.evidence_repos import resolve_evidence_repos

    root, git_dir = identity(root)
    fresh = _fresh.get(str(git_dir))
    if not fresh or str(git_dir) in _history or str(git_dir) in _selected:
        raise ScopeUnavailable(
            "Initial sibling selection requires an unconsumed fresh primary source"
        )
    source_root = Path(source_root).resolve()
    if str(source_root) != fresh["source_root"]:
        raise ScopeUnavailable(
            "Declaration source differs from the fresh checkout producer"
        )
    if artifact_path is None:
        if expected:
            raise ScopeUnavailable(
                "Sibling declaration has no immutable source artifact"
            )
        declared, blob_id = [], ""
    else:
        artifact = Path(artifact_path)
        if not artifact.is_absolute():
            artifact = source_root / artifact
        try:
            artifact = artifact.resolve()
            relative = artifact.relative_to(source_root).as_posix()
            # Git reads the registered source, never the mutable working file.
            blob_id = _git(root, "rev-parse", f"{fresh['commit']}:{relative}")
            content = _git(root, "cat-file", "blob", blob_id)
            if kind == "task":
                if not content.startswith("---"):
                    raise ValueError("Task source has no frontmatter")
                content = content.split("---", 2)[1]
            document = yaml.safe_load(content)
            if not isinstance(document, dict):
                raise ValueError("Declaration source is not a mapping")
            declared = document.get("evidence_repos") or []
            if kind == "task" and artifact.exists():
                current = artifact.read_text()
                current_document = (
                    yaml.safe_load(current.split("---", 2)[1])
                    if current.startswith("---")
                    else {}
                )
                if (
                    not isinstance(current_document, dict)
                    or (current_document.get("evidence_repos") or []) != declared
                ):
                    raise ValueError(
                        "Mutable task sibling declaration differs from admitted source"
                    )

        except Exception as exc:
            raise ScopeUnavailable(
                "Cannot bind sibling declarations to admitted source: " + str(exc)
            ) from exc
        if expected is not None and declared != (expected or []):
            raise ScopeUnavailable(
                "Mutable sibling declaration differs from admitted source"
            )
    if not isinstance(declared, list):
        raise ScopeUnavailable("The complete sibling declaration must be a list")
    resolved = []
    entry_identities = []
    for entry in declared:
        if isinstance(entry, dict):
            if not isinstance(entry.get("path"), str) or not entry["path"].strip():
                raise ScopeUnavailable("Malformed sibling path in complete declaration")
            if any(
                key in entry
                and entry[key] is not None
                and not isinstance(entry[key], str)
                for key in ("test_command", "interpreter")
            ):
                raise ScopeUnavailable(
                    "Malformed sibling command/interpreter in complete declaration"
                )
        elif not isinstance(entry, str) or not entry.strip():
            raise ScopeUnavailable("Malformed entry in complete sibling declaration")
        one = resolve_evidence_repos([entry], source_root)
        if len(one) != 1:
            raise ScopeUnavailable(
                "Complete sibling declaration could not be resolved; no inputs selected"
            )
        sibling = one[0]
        canonical, sibling_git_dir = identity(sibling.root)
        entry_identities.append((canonical, sibling_git_dir))
        if canonical != sibling.root or canonical == root:
            raise ScopeUnavailable(
                "Sibling declaration must name a distinct canonical repository root"
            )
        previous = next(
            (r for r in resolved if r.root == sibling.root or r.name == sibling.name),
            None,
        )
        if previous is not None and previous != sibling:
            raise ScopeUnavailable("Conflicting duplicate sibling declaration")
        if previous is None:
            resolved.append(sibling)
    binding = {
        "repos": tuple(resolved),
        "identities": tuple(identity(r.root) for r in resolved),
        "blob": blob_id,
        "declaration": json.dumps(declared, sort_keys=True),
        "source": dict(fresh),
        "entry_identities": tuple(entry_identities),
    }
    previous = _bindings.get(str(git_dir))
    if previous is not None and previous != binding:
        raise ScopeUnavailable("Fresh declaration binding cannot be replaced")
    _bindings[str(git_dir)] = binding
    return list(resolved)


def _verify_binding(binding):
    from guardkit.orchestrator.evidence_repos import resolve_evidence_repos

    for entry, expected in zip(
        json.loads(binding["declaration"]), binding["entry_identities"]
    ):
        resolved = resolve_evidence_repos(
            [entry], Path(binding["source"]["source_root"])
        )
        if len(resolved) != 1 or identity(resolved[0].root) != expected:
            raise ScopeUnavailable(
                "Declared sibling alias/identity moved after immutable source binding"
            )


def current_lease(root=None):
    lease = getattr(_local, "lease", None)
    if lease and root is not None and str(identity(root)[0]) not in lease.expected:
        return None
    return lease


class CheckoutLease:
    def __init__(self, repositories, input_paths):
        self.repositories = repositories
        self.input_paths = input_paths
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
        self.continuation_snapshot = None
        # GKT-150, step 1 (24 October 2026): a branch or HEAD that moved
        # outside the task's own checkpoints is noted here, never a failure.
        self.notes = []

    def verify(self, scope=None):
        if current_lease() is not self or threading.get_ident() != self.owner:
            raise ScopeUnavailable(
                "No retained checkout ownership; automatic resume refused; work preserved"
            )
        if self.failure:
            raise ScopeUnavailable(self.failure)
        if scope is not None and scope is not self.scope:
            raise ScopeUnavailable("Task scope is not the retained admission object")
        for path, expected in self.input_paths:
            if identity(path) != expected:
                raise ScopeUnavailable(
                    "Writer checkout alias/identity moved; work preserved"
                )
        binding = _bindings.get(str(self.repositories[0][2]))
        if binding:
            _verify_binding(binding)
        for _, root, git_dir in self.repositories:
            if identity(root) != (root, git_dir):
                raise ScopeUnavailable("Checkout identity changed; work preserved")
            branch = _git(root, "symbolic-ref", "--short", "HEAD")
            if branch != self.branches[str(root)]:
                self._note_moved(
                    root, f"branch changed from {self.branches[str(root)]} to {branch}"
                )
                self.branches[str(root)] = branch
            head = _git(root, "rev-parse", "HEAD")
            if head != self.expected[str(root)]:
                self._note_moved(
                    root,
                    f"HEAD moved from {self.expected[str(root)]} to {head} "
                    "outside the task's own checkpoints",
                )
                self.expected[str(root)] = head

    def _note_moved(self, root, what):
        note = f"Checkout {root}: {what}; recorded, the task goes on"
        self.notes.append(note)
        logger.warning(note)

    def checkpoint_completed(self):
        # Only the checkpoint writer calls this after validating the old HEAD.
        self.expected = {
            str(root): _git(root, "rev-parse", "HEAD")
            for _, root, _ in self.repositories
        }
        self.checkpoints.add(tuple(sorted(self.expected.items())))
        self.continuation_snapshot = boundary_snapshot(self)

    def admit(self, task_id, feature_id="", round_id="initial"):
        self.verify()
        if self.scope is not None:
            if self.scope.task_id != task_id:
                raise ScopeUnavailable("A different task already owns this checkout")
            return self.scope
        is_repair = str(round_id) not in {"initial", "1"}
        if is_repair and task_id not in _history.get(
            str(self.repositories[0][2]), {}
        ).get("approved_tasks", ()):
            raise ScopeUnavailable(
                "Repair admission has no retained approval for this task"
            )
        for _, root, _ in self.repositories:
            dirty = _dirty(root)
            if dirty:
                raise ScopeUnavailable(
                    "Inherited product changes preserved; cannot admit task: "
                    + ", ".join(dirty[:12])
                )
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
        self.continuation_snapshot = boundary_snapshot(self)
        return self.scope

    def verify_continuation(self, scope):
        self.verify(scope)
        if scope is None or self.continuation_snapshot != boundary_snapshot(self):
            raise ScopeUnavailable(
                "Tracked/index/untracked state differs from the retained continuation boundary"
            )

    def poison(self, reason):
        self.failure = self.failure or str(reason) or "Writer did not settle; work preserved"
        for _, _, git_dir in self.repositories:
            _history[str(git_dir)] = {"failed": self.failure}


@contextmanager
def checkout_lease(root, evidence_repos=(), cancelled=None):
    primary = identity(root)
    repos = [("", *primary)] + [(r.name, *identity(r.root)) for r in evidence_repos]
    active = current_lease()
    if active:
        if not {str(d) for _, _, d in repos}.issubset(
            {str(d) for _, _, d in active.repositories}
        ):
            raise ScopeUnavailable("Nested writer has an unowned sibling footprint")
        active.verify()
        yield active
        return
    binding = _bindings.get(str(primary[1]))
    if binding is not None:
        if tuple(evidence_repos) != binding["repos"]:
            raise ScopeUnavailable(
                "Writer footprint differs from immutable source declaration"
            )
    elif evidence_repos:
        raise ScopeUnavailable(
            "Sibling writer footprint has no immutable source binding"
        )
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
        if binding:
            _verify_binding(binding)
        if (
            binding
            and tuple(identity(r.root) for r in evidence_repos) != binding["identities"]
        ):
            raise ScopeUnavailable(
                "Sibling identity changed before all-footprint admission"
            )
        selecting = str(primary[1]) in _fresh
        selected_heads = {}
        for _, repository_root, git_dir in repos:
            marker = git_dir / "guardkit-writer-unsettled"
            prior = _history.get(str(git_dir))
            fresh = _fresh.get(str(git_dir))
            head = _git(repository_root, "rev-parse", "HEAD")
            is_initial_input = (
                selecting and binding is not None and git_dir != primary[1]
            )
            if marker.exists() or (prior and prior.get("failed")):
                raise ScopeUnavailable(
                    "Prior writer is unapproved or its termination is unknown; work preserved"
                )
            if not prior and not fresh and not is_initial_input:
                raise ScopeUnavailable(
                    "No retained approved boundary or freshly registered source; automatic resume refused"
                )
            if fresh and not prior and fresh["commit"] != head:
                raise ScopeUnavailable(
                    "Fresh source moved before admission; work preserved"
                )
            if prior and prior["head"] != head:
                raise ScopeUnavailable(
                    "Checkout changed outside the admitted writer; work preserved"
                )
            if selecting and _dirty(repository_root):
                raise ScopeUnavailable(
                    "Initial input has inherited product changes; no inputs selected"
                )
            selected_heads[str(repository_root)] = head
        if selecting:
            # Consume only after every declared input passed under all locks.
            source = _fresh.pop(str(primary[1]))
            _selected[str(primary[1])] = {
                **source,
                "inputs": selected_heads,
                "provenance": "selected starting inputs; not approval",
            }
        lease = CheckoutLease(
            repos,
            [(Path(root).absolute(), primary)]
            + [(r.root, identity(r.root)) for r in evidence_repos],
        )
        _local.lease = lease
        try:
            # Initialization is part of ownership too: a failed marker write
            # must never leave an unlocked, reusable thread-local owner.
            for _, _, git_dir in repos:
                (git_dir / "guardkit-writer-unsettled").write_text(
                    "Writer in progress; never a resume credential\n"
                )
            yield lease
            if not lease.failure:
                lease.verify()
                # Remove every marker before publishing any approved history.
                # A partial removal failure poisons the complete footprint.
                for _, _, git_dir in repos:
                    (git_dir / "guardkit-writer-unsettled").unlink(missing_ok=True)
                for _, root, git_dir in repos:
                    approved = set(
                        _history.get(str(git_dir), {}).get("approved_tasks", ())
                    )
                    if lease.scope:
                        approved.add(lease.scope.task_id)
                        _approved_heads[str(git_dir)] = lease.expected[str(root)]
                    _history[str(git_dir)] = {
                        "head": lease.expected[str(root)],
                        "approved_tasks": sorted(approved),
                        "provenance": (
                            "approved task boundary"
                            if lease.scope
                            else "selected input boundary"
                        ),
                    }
        except BaseException as exc:
            lease.poison(str(exc))
            raise
        finally:
            try:
                if lease.failure:
                    # Best effort persistent denial, including members whose
                    # marker was already removed. In-memory denial is retained
                    # even if the filesystem cannot record it; never mask the
                    # original failure with another marker I/O error.
                    for _, _, git_dir in repos:
                        try:
                            (git_dir / "guardkit-writer-unsettled").write_text(
                                "Writer unsettled; automatic resume refused\n"
                            )
                        except OSError:
                            pass
            finally:
                _local.lease = None


def approved_head(root):
    """The last commit an approved task left in this checkout during this run,
    or ``None`` when no task has been approved here yet."""
    try:
        _, git_dir = identity(root)
    except Exception:  # noqa: BLE001 — absence, never a failure
        return None
    return _approved_heads.get(str(git_dir))


def bootstrap_admitted_checkout(scope):
    """Run the existing product-writing bridge bootstrap under task ownership.

    Preserve the admitted baseline; any bridge written is visible in the same
    inventory/audit/checkpoint as the rest of this task's actual changes.
    """
    lease = current_lease()
    if lease is None or scope is None or scope is not lease.scope:
        raise ScopeUnavailable("Bootstrap requires the retained admitted task scope")
    lease.verify(scope)
    selected = _selected[str(lease.repositories[0][2])]
    if selected.get("bridge_bootstrapped"):
        return
    from guardkit.templates.conftest_bridge import install_features_conftest_bridge

    install_features_conftest_bridge(Path(scope.repositories[0].root))
    selected["bridge_bootstrapped"] = True


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
