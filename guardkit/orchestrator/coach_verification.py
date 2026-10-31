"""Root-level names that mark a worktree as a Python project.

Kept for the work leg's interpreter provisioning (``work_runner``). The
worktree interpreter resolution (``_resolve_venv_python``) and the plain
pytest run under it (``CoachVerifier._run_tests``, used only by state
recovery) were removed on 31 October 2026: state recovery reports what git
shows, and the after-task check of the parts the task changed decides. (27
October 2026: the checks of the Player's claims that lived here were removed.)
"""


# Manifest names that mark a worktree as a Python project. The same
# root-level names ProjectEnvironmentDetector treats as Python stack
# manifests.
_PYTHON_PROJECT_MARKERS = (
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
)
