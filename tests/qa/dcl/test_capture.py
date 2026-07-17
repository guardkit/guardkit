"""Unit tests for the every-run DCL capture lane (W2ab).

Proves the Fallback law on the capture seam:

* **default-OFF** — with the flag absent, ``compile_shadow`` / ``append_brief`` do
  NOTHING: no sink file, no sink dir, no log rows, and ZERO checker invocations
  (the checker is spied to assert it was never called);
* **ON** — one ``compile_shadow`` row per ``.dcl`` with the exact schema; a broken
  ``.dcl`` yields an ``ok: false`` row and never raises;
* **POISON** — a checker that raises leaves ``compile_shadow`` returning normally
  with a ``logger.warning`` and NO row for that file (honest-gates: the fault
  fails loud in this lane's log only);
* **unwritable sink** — swallowed-to-log, never raised.

Node is required only for the real-checker ON tests (``requires_node``); the
default-OFF / poison / unwritable tests spy the checker so they need no runtime.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

import pytest
import yaml

from guardkit.qa.dcl import capture, checker

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "dcl"

requires_node = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node is required to run the vendored WASM DCL checker",
)

#: The exact compile_shadow row schema (build-handoff §3 W2a).
_ROW_KEYS = frozenset(
    {
        "kind",
        "repo",
        "file",
        "sha256",
        "ok",
        "error_count",
        "warning_count",
        "error_codes",
        "run_id",
    }
)


@pytest.fixture(autouse=True)
def _clear_capture_env(monkeypatch):
    """The env override must not leak in from the ambient shell."""
    monkeypatch.delenv(capture.CAPTURE_ENV, raising=False)


def _write_config(repo: Path, **dcl) -> None:
    cfg = repo / ".guardkit"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "config.yaml").write_text(yaml.safe_dump({"dcl": dcl}), encoding="utf-8")


def _write_dcl(repo: Path, rel: str, content: str) -> Path:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _clean_dcl() -> str:
    return (_FIXTURES / "capability.dcl").read_text(encoding="utf-8")


def _broken_dcl() -> str:
    return (_FIXTURES / "broken.dcl").read_text(encoding="utf-8")


def _read_rows(sink: Path) -> list:
    return [json.loads(ln) for ln in sink.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _spy_checker(monkeypatch, *, envelope=None, raises=None):
    """Replace ``checker.check`` with a spy; return the call-log list."""
    calls: list = []

    def _spy(path):
        calls.append(Path(path))
        if raises is not None:
            raise raises
        return envelope or {"ok": True, "errorCount": 0, "warningCount": 0, "diagnostics": []}

    monkeypatch.setattr(checker, "check", _spy)
    return calls


# ===========================================================================
# DEFAULT-OFF: the Fallback law — nothing happens, zero checker calls.
# ===========================================================================


def test_default_off_does_nothing(tmp_path, monkeypatch, caplog):
    """Fresh repo, no flag → no sink, no dir, no rows, ZERO checker invocations."""
    repo = tmp_path
    _write_dcl(repo, "features/x/x.dcl", _clean_dcl())  # artifact PRESENT but flag off
    calls = _spy_checker(monkeypatch)

    with caplog.at_level(logging.INFO, logger="guardkit.qa.dcl.capture"):
        capture.compile_shadow(repo, run_id="run-1")
        capture.append_brief(repo, {"feature": "x"})

    assert calls == []  # checker NEVER invoked
    sink = repo / ".guardkit" / "dcl-capture" / "queue.jsonl"
    assert not sink.exists()
    assert not sink.parent.exists()  # no sink dir created
    assert not any("compile-shadow" in r.message for r in caplog.records)


def test_default_off_explicit_false_flag(tmp_path, monkeypatch):
    """dcl.capture: false is also OFF (and the checker is never touched)."""
    repo = tmp_path
    _write_config(repo, capture=False)
    _write_dcl(repo, "features/x/x.dcl", _clean_dcl())
    calls = _spy_checker(monkeypatch)

    capture.compile_shadow(repo)

    assert calls == []
    assert not (repo / ".guardkit" / "dcl-capture" / "queue.jsonl").exists()


def test_env_falsy_overrides_config_on(tmp_path, monkeypatch):
    """GUARDKIT_DCL_CAPTURE=0 forces OFF even when config says on."""
    repo = tmp_path
    _write_config(repo, capture=True)
    _write_dcl(repo, "features/x/x.dcl", _clean_dcl())
    calls = _spy_checker(monkeypatch)
    monkeypatch.setenv(capture.CAPTURE_ENV, "0")

    capture.compile_shadow(repo)

    assert calls == []


# ===========================================================================
# ON: rows with the exact schema (real vendored checker).
# ===========================================================================


@requires_node
def test_on_two_artifacts_two_rows_exact_schema(tmp_path):
    """ON: one row per .dcl, exact schema; clean → ok True, broken → ok False."""
    repo = tmp_path
    _write_config(repo, capture=True)
    _write_dcl(repo, "features/clean/clean.dcl", _clean_dcl())
    _write_dcl(repo, "features/broken/broken.dcl", _broken_dcl())

    capture.compile_shadow(repo, run_id="run-42")

    sink = repo / ".guardkit" / "dcl-capture" / "queue.jsonl"
    rows = _read_rows(sink)
    assert len(rows) == 2
    by_file = {Path(r["file"]).name: r for r in rows}
    assert set(by_file) == {"clean.dcl", "broken.dcl"}

    for r in rows:
        assert set(r) == _ROW_KEYS
        assert r["kind"] == "compile_shadow"
        assert r["repo"] == str(repo)
        assert r["run_id"] == "run-42"
        assert len(r["sha256"]) == 64

    clean = by_file["clean.dcl"]
    assert clean["ok"] is True
    assert clean["error_count"] == 0
    assert clean["error_codes"] == []

    broken = by_file["broken.dcl"]
    assert broken["ok"] is False
    assert broken["error_count"] > 0


@requires_node
def test_on_broken_only_never_raises(tmp_path):
    """A broken .dcl produces an ok:false row and compile_shadow never raises."""
    repo = tmp_path
    _write_config(repo, capture=True)
    _write_dcl(repo, "features/b/b.dcl", _broken_dcl())

    capture.compile_shadow(repo)  # must not raise

    rows = _read_rows(repo / ".guardkit" / "dcl-capture" / "queue.jsonl")
    assert len(rows) == 1
    assert rows[0]["ok"] is False


@requires_node
def test_on_configured_sink_and_run_id_none(tmp_path):
    """A relative capture_sink is resolved against repo_root; run_id defaults None."""
    repo = tmp_path
    _write_config(repo, capture=True, capture_sink="artifacts/cap.jsonl")
    _write_dcl(repo, "features/clean/clean.dcl", _clean_dcl())

    capture.compile_shadow(repo)

    rows = _read_rows(repo / "artifacts" / "cap.jsonl")
    assert len(rows) == 1
    assert rows[0]["run_id"] is None


@requires_node
def test_on_absolute_sink_honoured(tmp_path):
    """An absolute capture_sink is honoured verbatim (not re-rooted)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    abs_sink = tmp_path / "elsewhere" / "q.jsonl"
    _write_config(repo, capture=True, capture_sink=str(abs_sink))
    _write_dcl(repo, "features/clean/clean.dcl", _clean_dcl())

    capture.compile_shadow(repo)

    assert abs_sink.is_file()
    assert len(_read_rows(abs_sink)) == 1


def test_on_no_features_dir_is_clean(tmp_path, monkeypatch):
    """ON but no features/ dir → no crash, no sink (nothing to compile)."""
    repo = tmp_path
    _write_config(repo, capture=True)
    calls = _spy_checker(monkeypatch)

    capture.compile_shadow(repo)

    assert calls == []
    assert not (repo / ".guardkit" / "dcl-capture" / "queue.jsonl").exists()


# ===========================================================================
# POISON: a checker fault fails loud in the lane's log, never raises, no row.
# ===========================================================================


def test_poison_checker_raises_swallowed_to_log(tmp_path, monkeypatch, caplog):
    """checker.check raising → compile_shadow returns normally, warning fired,
    NO row for that file (honest-gates: loud in the lane's log only)."""
    repo = tmp_path
    _write_config(repo, capture=True)
    _write_dcl(repo, "features/x/x.dcl", _clean_dcl())
    _spy_checker(monkeypatch, raises=RuntimeError("boom in the checker"))

    with caplog.at_level(logging.WARNING, logger="guardkit.qa.dcl.capture"):
        capture.compile_shadow(repo)  # must NOT raise

    assert any("checker fault" in r.message for r in caplog.records)
    # No row was written (append is only reached after a successful compile).
    assert not (repo / ".guardkit" / "dcl-capture" / "queue.jsonl").exists()


# ===========================================================================
# Unwritable sink: swallowed-to-log.
# ===========================================================================


def test_unwritable_sink_swallowed(tmp_path, monkeypatch, caplog):
    """A sink whose parent cannot be created is swallowed-to-log, never raised."""
    repo = tmp_path
    # A regular FILE where the sink's parent dir must be → mkdir(parents=True) fails.
    (repo / "blocker").write_text("i am a file", encoding="utf-8")
    _write_config(repo, capture=True, capture_sink="blocker/queue.jsonl")
    _write_dcl(repo, "features/x/x.dcl", _clean_dcl())
    _spy_checker(monkeypatch)  # clean envelope → append path is reached

    with caplog.at_level(logging.WARNING, logger="guardkit.qa.dcl.capture"):
        capture.compile_shadow(repo)  # must NOT raise

    assert any("unwritable sink" in r.message for r in caplog.records)


def test_append_brief_on_writes_row(tmp_path):
    """append_brief ON → a {kind: brief, **payload} row on the same sink."""
    repo = tmp_path
    _write_config(repo, capture=True)

    capture.append_brief(repo, {"feature": "f1", "task": "TASK-1", "request": "do a thing"})

    rows = _read_rows(repo / ".guardkit" / "dcl-capture" / "queue.jsonl")
    assert rows == [{"kind": "brief", "feature": "f1", "task": "TASK-1", "request": "do a thing"}]


def test_append_brief_unwritable_swallowed(tmp_path, caplog):
    """append_brief swallows an unwritable sink (never raises)."""
    repo = tmp_path
    (repo / "blocker").write_text("file", encoding="utf-8")
    _write_config(repo, capture=True, capture_sink="blocker/queue.jsonl")

    with caplog.at_level(logging.WARNING, logger="guardkit.qa.dcl.capture"):
        capture.append_brief(repo, {"feature": "f1"})  # must NOT raise

    assert any("append_brief" in r.message for r in caplog.records)


# ===========================================================================
# resolve_sink / is_capture_enabled units.
# ===========================================================================


def test_resolve_sink_default(tmp_path):
    assert capture.resolve_sink(tmp_path) == tmp_path / capture.DEFAULT_SINK


def test_is_capture_enabled_env_truthy(tmp_path, monkeypatch):
    monkeypatch.setenv(capture.CAPTURE_ENV, "yes")
    assert capture.is_capture_enabled(tmp_path) is True


def test_is_capture_enabled_default_false(tmp_path):
    assert capture.is_capture_enabled(tmp_path) is False
