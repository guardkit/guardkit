"""GuardKit - Lightweight AI-Assisted Development Framework."""

__version__ = "0.1.0"

__all__ = ["__version__"]


def _bootstrap_installer_core() -> None:
    """Make ``installer.core.*`` importable when GuardKit is installed as a wheel.

    GuardKit's orchestrator (and ``installer/core``'s own ~24 intra-package
    modules) import the **absolute** name ``installer.core.*`` — a pre-existing
    design that resolves naturally in an editable/source checkout because the
    repo root carries an importable top-level ``installer`` package.

    DF-011 ships that payload inside the wheel under the **guardkit namespace**
    as ``guardkit/_installer_core`` (hatch ``force-include``). The wheel
    deliberately does **not** ship a top-level ``installer`` distribution: that
    would collide with PyPI ``pypa/installer`` — the externally-defined-namespace
    hazard ``.claude/rules/namespace-hygiene.md`` exists to prevent (same class
    as the ``mcp`` shadowing incident).

    Rewriting every ``installer.core.*`` import across guardkit *and* the ~24
    self-referential ``installer/core`` modules is a far larger, higher-risk
    change than DF-011's packaging scope (and would fork the ``install.sh`` /
    ``~/.agentecflow`` import convention). So the wheel keeps the imports as-is
    and this bootstrap grafts the packaged copy onto the ``installer.core`` name
    at runtime, **only when a real ``installer.core`` is not already importable**:

    * **Editable / source install** — the repo's own top-level ``installer`` is
      importable, so ``importlib`` resolves ``installer.core`` on its own and
      this function no-ops. The packaged ``guardkit/_installer_core`` directory
      does not even exist under an editable ``guardkit/`` (it is a build-time
      artefact), which is the primary guard.
    * **Wheel / plain pip install** — ``guardkit/_installer_core`` exists and no
      top-level ``installer.core`` is importable, so ``installer.core`` is
      registered in ``sys.modules`` pointing at the packaged copy. A pre-existing
      ``pypa/installer`` (which provides no ``.core`` submodule) is reused as the
      parent rather than clobbered.

    Idempotent and defensive: any failure leaves imports to fail with their
    natural ``ModuleNotFoundError`` rather than masking the cause.
    """
    import importlib
    import importlib.machinery
    import importlib.util
    import os
    import sys

    # Primary guard: the packaged copy only exists in a built wheel. In an
    # editable/source checkout it is absent, so there is nothing to alias.
    packaged = os.path.join(os.path.dirname(__file__), "_installer_core")
    if not os.path.isdir(packaged):
        return

    if "installer.core" in sys.modules:
        return

    # If a real installer.core is importable (e.g. an editable checkout whose
    # repo root is also on sys.path), prefer it — never shadow the authoring
    # source or a genuinely-installed provider.
    try:
        if importlib.util.find_spec("installer.core") is not None:
            return
    except (ImportError, ModuleNotFoundError, ValueError):
        pass  # find_spec can raise when a partial parent exists; fall through.

    # Establish (or reuse) the top-level `installer` parent package. A real
    # pypa/installer, if present, provides no `.core` — reuse it as parent so we
    # graft rather than replace it; otherwise synthesise a minimal namespace.
    installer_pkg = sys.modules.get("installer")
    if installer_pkg is None:
        try:
            if importlib.util.find_spec("installer") is not None:
                installer_pkg = importlib.import_module("installer")
        except (ImportError, ModuleNotFoundError, ValueError):
            installer_pkg = None
    if installer_pkg is None:
        spec = importlib.machinery.ModuleSpec("installer", loader=None, is_package=True)
        installer_pkg = importlib.util.module_from_spec(spec)
        installer_pkg.__path__ = []  # namespace parent; no filesystem of its own
        sys.modules["installer"] = installer_pkg

    # Load `installer.core` from the packaged copy and register it so every
    # `installer.core.*` absolute import (guardkit's and installer/core's own)
    # resolves under guardkit/_installer_core.
    core_init = os.path.join(packaged, "__init__.py")
    if not os.path.isfile(core_init):
        return
    spec = importlib.util.spec_from_file_location(
        "installer.core",
        core_init,
        submodule_search_locations=[packaged],
    )
    if spec is None or spec.loader is None:
        return
    core = importlib.util.module_from_spec(spec)
    sys.modules["installer.core"] = core
    try:
        spec.loader.exec_module(core)
    except Exception:  # pragma: no cover - defensive; unregister on failure
        sys.modules.pop("installer.core", None)
        return
    setattr(installer_pkg, "core", core)


_bootstrap_installer_core()
