"""Tests for the boot-smoke gate (WS3-S3 2d).

The POC-006 #1 must-fire fixture: a composition root that constructs a service
missing a required arg → TypeError at composition → boot-smoke construct FAIL.
The clean counterpart passes.  Liveness-at-verdict (R2d-3) covered via serve.
"""

from __future__ import annotations

import sys
from pathlib import Path


from guardkit.orchestrator.boot_smoke import run_boot_smoke
from guardkit.orchestrator.seam_checks import BootSmokeEntry, SeamChecksConfig


def _write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _cfg(*entries: BootSmokeEntry) -> SeamChecksConfig:
    return SeamChecksConfig(present=True, boot_smoke=list(entries))


# --- import kind -----------------------------------------------------------


def test_import_ok(tmp_path: Path) -> None:
    _write(tmp_path, "pkg/__init__.py", "")
    _write(tmp_path, "pkg/mod.py", "x = 1\n")
    cfg = _cfg(BootSmokeEntry(id="imp", kind="import", target="pkg.mod"))
    r = run_boot_smoke(cfg, tmp_path, venv_python=sys.executable)
    assert r.passed and r.aggregate_verdict == "pass"


def test_import_crash_fails(tmp_path: Path) -> None:
    _write(tmp_path, "pkg/__init__.py", "")
    _write(tmp_path, "pkg/mod.py", "import nonexistent_dep_xyz\n")
    cfg = _cfg(BootSmokeEntry(id="imp", kind="import", target="pkg.mod"))
    r = run_boot_smoke(cfg, tmp_path, venv_python=sys.executable)
    assert r.blocking and r.aggregate_verdict == "fail"
    assert r.entries[0].finding_kind == "BOOT_SMOKE_FAIL"


# --- construct kind (POC-006 #1) -------------------------------------------


def test_poc006_construct_missing_required_arg_fails(tmp_path: Path) -> None:
    # VoiceService requires audio_client; the factory omits it → TypeError.
    _write(tmp_path, "app/__init__.py", "")
    _write(tmp_path, "app/service.py",
           "class VoiceService:\n"
           "    def __init__(self, audio_client, cache=None):\n"
           "        self.audio_client = audio_client\n")
    _write(tmp_path, "app/main.py",
           "from app.service import VoiceService\n"
           "def create_service():\n"
           "    return VoiceService(cache=None)\n")  # missing audio_client!
    cfg = _cfg(BootSmokeEntry(
        id="svc", kind="construct", target="app.main:create_service",
        expect_type="app.service:VoiceService",
    ))
    r = run_boot_smoke(cfg, tmp_path, venv_python=sys.executable)
    assert r.blocking and r.aggregate_verdict == "fail"
    assert "TypeError" in r.entries[0].detail or "argument" in r.entries[0].detail


def test_construct_clean_passes(tmp_path: Path) -> None:
    _write(tmp_path, "app/__init__.py", "")
    _write(tmp_path, "app/service.py",
           "class VoiceService:\n"
           "    def __init__(self, audio_client=None):\n"
           "        pass\n")
    _write(tmp_path, "app/main.py",
           "from app.service import VoiceService\n"
           "def create_service():\n"
           "    return VoiceService()\n")
    cfg = _cfg(BootSmokeEntry(
        id="svc", kind="construct", target="app.main:create_service",
        expect_type="app.service:VoiceService",
    ))
    r = run_boot_smoke(cfg, tmp_path, venv_python=sys.executable)
    assert r.passed


def test_construct_expect_type_mismatch_fails(tmp_path: Path) -> None:
    # R2d-4: `def create_app(): return object()` must FAIL against expect_type.
    _write(tmp_path, "app/__init__.py", "")
    _write(tmp_path, "app/service.py", "class App:\n    pass\n")
    _write(tmp_path, "app/main.py", "def create_app():\n    return object()\n")
    cfg = _cfg(BootSmokeEntry(
        id="app", kind="construct", target="app.main:create_app",
        expect_type="app.service:App",
    ))
    r = run_boot_smoke(cfg, tmp_path, venv_python=sys.executable)
    assert r.blocking


# --- serve kind (liveness-at-verdict, R2d-3) -------------------------------


def test_serve_early_ready_late_crash_fails(tmp_path: Path) -> None:
    # print READY then exit non-zero shortly after → must be FAIL, not pass.
    _write(tmp_path, "srv/__init__.py", "")
    _write(tmp_path, "srv/__main__.py",
           "import sys, time\n"
           "print('READY', flush=True)\n"
           "time.sleep(0.2)\n"
           "sys.exit(3)\n")
    cfg = _cfg(BootSmokeEntry(
        id="s", kind="serve", target="srv",
        readiness={"kind": "exit_zero", "timeout_s": 5},
    ))
    r = run_boot_smoke(cfg, tmp_path, venv_python=sys.executable)
    # exit_zero readiness + non-zero exit → FAIL.
    assert r.blocking


def test_serve_port_ready_and_alive_passes(tmp_path: Path) -> None:
    _write(tmp_path, "srv/__init__.py", "")
    _write(tmp_path, "srv/__main__.py",
           "import os, socket, time\n"
           "port = int(os.environ['PORT'])\n"
           "s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)\n"
           "s.bind(('127.0.0.1', port)); s.listen(5)\n"
           "time.sleep(30)\n")
    cfg = _cfg(BootSmokeEntry(
        id="s", kind="serve", target="srv",
        readiness={"kind": "port", "timeout_s": 8},
    ))
    r = run_boot_smoke(cfg, tmp_path, venv_python=sys.executable)
    assert r.passed, [e.to_dict() for e in r.entries]


def test_serve_never_ready_is_ran_and_failed(tmp_path: Path) -> None:
    _write(tmp_path, "srv/__init__.py", "")
    _write(tmp_path, "srv/__main__.py", "import time\ntime.sleep(30)\n")
    cfg = _cfg(BootSmokeEntry(
        id="s", kind="serve", target="srv",
        readiness={"kind": "port", "timeout_s": 2},
    ))
    r = run_boot_smoke(cfg, tmp_path, venv_python=sys.executable)
    assert r.aggregate_verdict == "ran_and_failed"


# --- env arms + absent -----------------------------------------------------


def test_env_absent_is_not_silent(tmp_path: Path) -> None:
    _write(tmp_path, "srv/__init__.py", "")
    _write(tmp_path, "srv/__main__.py", "pass\n")
    cfg = _cfg(BootSmokeEntry(
        id="s", kind="serve", target="srv", env_required=[".env"],
        readiness={"kind": "port", "timeout_s": 2},
    ))
    r = run_boot_smoke(cfg, tmp_path, venv_python=sys.executable)
    assert r.aggregate_verdict == "absent" and r.passed
    assert r.operator_followups  # operator handoff panel, never silent
    assert r.entries[0].finding_kind == "BOOT_SMOKE_ENV_ABSENT"


def test_env_prereq_tamper_is_ran_and_failed(tmp_path: Path) -> None:
    _write(tmp_path, "srv/__init__.py", "")
    _write(tmp_path, "srv/__main__.py", "pass\n")
    cfg = _cfg(BootSmokeEntry(
        id="s", kind="serve", target="srv", env_required=[".env"],
        readiness={"kind": "port", "timeout_s": 2},
    ))
    # .env was satisfied at bootstrap-end but is missing now → tamper.
    r = run_boot_smoke(cfg, tmp_path, venv_python=sys.executable,
                       prereqs_satisfied_at_bootstrap={".env": True})
    assert r.aggregate_verdict == "ran_and_failed"
    assert r.entries[0].finding_kind == "ENV_PREREQ_TAMPER"


def test_no_declaration_is_absent(tmp_path: Path) -> None:
    r = run_boot_smoke(SeamChecksConfig(present=False), tmp_path)
    assert r.ran is False and r.passed


def test_unresolvable_target_is_config_stale(tmp_path: Path) -> None:
    cfg = _cfg(BootSmokeEntry(id="x", kind="import", target="ghost.module"))
    r = run_boot_smoke(cfg, tmp_path, venv_python=sys.executable)
    assert r.entries[0].finding_kind == "CONFIG_STALE"
    assert r.aggregate_verdict == "absent"


def test_command_kind(tmp_path: Path) -> None:
    cfg = _cfg(BootSmokeEntry(id="c", kind="command", target="true", expected_exit=0))
    r = run_boot_smoke(cfg, tmp_path)
    # `true` may not resolve as a worktree target; the command escape-hatch runs argv.
    # Accept pass or config_stale depending on resolvability heuristic.
    assert r.aggregate_verdict in ("pass", "absent")
