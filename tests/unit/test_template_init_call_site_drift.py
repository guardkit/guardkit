"""Guard against call-site drift in the /template-init command.

WHAT THIS PROTECTS AGAINST, in plain words
------------------------------------------
One part of the code calls another part, passing an argument the receiving
function does not accept, or asking for a method that no longer exists. Python
only notices at the moment the line actually runs, so a mistake like this can
sit in the codebase for months and only surface in front of a user.

That is exactly what happened here. The command that creates a new project
template from a questionnaire (``/template-init``) delegated two jobs to the
interactive questionnaire class:

  * working out which folder to save the finished template into, and
  * scoring the finished template for quality.

That class was later rewritten and lost both abilities, along with the two
constructor arguments the command was passing it. The calls were left behind.
Both would have raised an error the moment they ran, and one of them was
wrapped in a catch-everything handler that quietly reported the failure as a
poor quality score — so the command appeared to work while doing nothing.

These tests read the command's source without running it and check every such
call against the real class, so the same drift cannot return silently.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from greenfield_qa_session import TemplateInitQASession

COMMAND_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "installer"
    / "core"
    / "commands"
    / "lib"
    / "template_init"
    / "command.py"
)


@pytest.fixture(scope="module")
def command_tree() -> ast.Module:
    assert COMMAND_SOURCE.is_file(), f"missing source file: {COMMAND_SOURCE}"
    return ast.parse(COMMAND_SOURCE.read_text(encoding="utf-8"), str(COMMAND_SOURCE))


def _accepted_parameters() -> set[str]:
    params = inspect.signature(TemplateInitQASession.__init__).parameters
    return {name for name in params if name != "self"}


def test_every_qa_session_construction_passes_accepted_arguments(command_tree):
    """No call may name a constructor argument the class does not accept.

    The original defect: two lines built the questionnaire object with
    ``output_location=...`` and ``validate=...``. It accepts neither, so both
    raised TypeError as soon as they were reached.
    """
    accepted = _accepted_parameters()
    offenders = []

    for node in ast.walk(command_tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = getattr(func, "id", None) or getattr(func, "attr", None)
        if name != "TemplateInitQASession":
            continue
        for kw in node.keywords:
            if kw.arg is not None and kw.arg not in accepted:
                offenders.append((node.lineno, kw.arg))

    assert not offenders, (
        "TemplateInitQASession is constructed with arguments it does not accept "
        f"(accepted: {sorted(accepted)}). Offending call sites: "
        + ", ".join(f"line {line} passes {arg!r}" for line, arg in offenders)
    )


def _known_session_surface() -> set[str]:
    """Every name a TemplateInitQASession instance legitimately has.

    That is the class surface (methods, class attributes) plus the instance
    attributes the class assigns to ``self`` in its own body — the latter do
    not exist on the class object, so ``hasattr`` alone would report them
    missing.
    """
    surface = set(dir(TemplateInitQASession))

    source = Path(inspect.getfile(TemplateInitQASession)).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.ClassDef) and node.name == "TemplateInitQASession"):
            continue
        for sub in ast.walk(node):
            targets = []
            if isinstance(sub, ast.Assign):
                targets = sub.targets
            elif isinstance(sub, ast.AnnAssign):
                targets = [sub.target]
            for target in targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    surface.add(target.attr)
    return surface


def _runtime_guarded_names(tree: ast.Module) -> set[str]:
    """Names the command explicitly checks for with hasattr() before using.

    A call site wrapped in ``hasattr(TemplateInitQASession, "x")`` cannot
    crash, because the code has asked whether the capability is present. Those
    are deliberate, and this test treats them as safe rather than as drift.
    """
    guarded = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "hasattr"):
            continue
        if len(node.args) != 2:
            continue
        subject, attr = node.args
        subject_name = getattr(subject, "id", None) or getattr(subject, "attr", None)
        if subject_name == "TemplateInitQASession" and isinstance(attr, ast.Constant):
            if isinstance(attr.value, str):
                guarded.add(attr.value)
    return guarded


def test_every_qa_session_attribute_used_actually_exists(command_tree):
    """Every ``session.<name>`` the command reaches for must really exist.

    The original defect: the command called ``session._get_template_path``,
    ``session._display_location_guidance`` and ``session._run_level2_validation``.
    None of the three survived the rewrite of the questionnaire class, so each
    would have raised AttributeError on the line that used it.

    Within this module the local variable ``session`` is only ever bound to a
    ``TemplateInitQASession``, which is what makes this check sound.

    A name the command guards with ``hasattr`` first is not drift — that code
    has already asked whether the capability exists. See the note in
    ``_phase5_extended_validation``, where the quality-scoring routine is
    called only if it is present.
    """
    surface = _known_session_surface() | _runtime_guarded_names(command_tree)
    missing = []

    for node in ast.walk(command_tree):
        if not isinstance(node, ast.Attribute):
            continue
        value = node.value
        if not isinstance(value, ast.Name) or value.id != "session":
            continue
        if node.attr not in surface:
            missing.append((node.lineno, node.attr))

    assert not missing, (
        "The command reaches for attributes that TemplateInitQASession does not "
        "have, and does not guard with hasattr(): "
        + ", ".join(f"line {line} uses session.{attr}" for line, attr in missing)
    )
