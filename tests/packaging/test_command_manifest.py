"""PB-3: command-distribution manifest generator + doctor drift check.

The manifest (installer/core/commands/MANIFEST.json) is the single provenance
source for install.sh's prune list, `guardkit doctor`'s drift report, and the
packaging include set. These tests pin: (1) the committed manifest is current
(the CI --check contract), (2) the version is the single source
guardkit/__init__.py, (3) the tombstones are declared, (4) the doctor drift
check classifies current / modified / missing / retired-present correctly and
is report-only.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MANIFEST_PATH = _REPO_ROOT / "installer" / "core" / "commands" / "MANIFEST.json"
_GENERATOR = _REPO_ROOT / "scripts" / "generate_command_manifest.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location("_gen_cmd_manifest", _GENERATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestManifestGenerator:
    def test_committed_manifest_is_current(self) -> None:
        """CI --check contract: the committed manifest matches the repo."""
        gen = _load_generator()
        assert gen.main(["--check"]) == 0

    def test_version_derives_from_init_py(self) -> None:
        """Manifest version == guardkit/__init__.py __version__ (single source)."""
        gen = _load_generator()
        manifest = json.loads(_MANIFEST_PATH.read_text())
        assert manifest["version"] == gen._read_version()

    def test_tombstones_declared(self) -> None:
        """The two retired command names are declared with retirement commits."""
        manifest = json.loads(_MANIFEST_PATH.read_text())
        names = {t["name"] for t in manifest["tombstones"]}
        assert {"impact-analysis.md", "system-overview.md"} <= names
        for t in manifest["tombstones"]:
            assert t.get("retired_in"), f"tombstone missing retired_in: {t}"

    def test_every_command_hash_matches_disk(self) -> None:
        """Manifest sha256 is the true content hash of each command markdown."""
        manifest = json.loads(_MANIFEST_PATH.read_text())
        commands_dir = _MANIFEST_PATH.parent
        for name, entry in manifest["commands"].items():
            data = (commands_dir / name).read_bytes()
            assert hashlib.sha256(data).hexdigest() == entry["sha256"], name

    def test_manifest_is_hash_of_content_only(self) -> None:
        """No file CONTENT is embedded — only hashes (never a second source)."""
        manifest = json.loads(_MANIFEST_PATH.read_text())
        for entry in manifest["commands"].values():
            assert set(entry) <= {"sha256", "source_commit"}


class TestDoctorDriftCheck:
    def _install(self, tmp_path: Path, names, tombstones=()) -> Path:
        """Build a fake installed commands dir + manifest under tmp_path."""
        commands = tmp_path / ".agentecflow" / "commands"
        commands.mkdir(parents=True)
        entries = {}
        for name, content in names.items():
            (commands / name).write_text(content)
            entries[name] = {
                "sha256": hashlib.sha256(content.encode()).hexdigest(),
                "source_commit": "abc1234",
            }
        manifest = {
            "schema_version": 1,
            "package": "guardkit-py",
            "version": "9.9.9",
            "commands": entries,
            "tombstones": [{"name": t, "retired_in": "deadbeef"} for t in tombstones],
        }
        (commands / "MANIFEST.json").write_text(json.dumps(manifest))
        return commands

    def _run(self, tmp_path: Path, monkeypatch):
        from guardkit.cli.doctor import CheckStatus, CommandManifestDriftCheck

        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        # cwd without a .claude/commands so only the global dir is scanned.
        monkeypatch.chdir(tmp_path)
        return CommandManifestDriftCheck().run(), CheckStatus

    def test_all_current_passes(self, tmp_path, monkeypatch) -> None:
        self._install(tmp_path, {"feature-plan.md": "PLAN", "task-work.md": "WORK"})
        result, CheckStatus = self._run(tmp_path, monkeypatch)
        assert result.status == CheckStatus.PASS
        assert "current" in result.message

    def test_modified_reports_warning(self, tmp_path, monkeypatch) -> None:
        commands = self._install(tmp_path, {"feature-plan.md": "PLAN"})
        (commands / "feature-plan.md").write_text("TAMPERED")
        result, CheckStatus = self._run(tmp_path, monkeypatch)
        assert result.status == CheckStatus.WARNING
        assert "1 modified" in result.message

    def test_retired_present_reports_warning(self, tmp_path, monkeypatch) -> None:
        commands = self._install(
            tmp_path, {"feature-plan.md": "PLAN"}, tombstones=("impact-analysis.md",)
        )
        (commands / "impact-analysis.md").write_text("stale")
        result, CheckStatus = self._run(tmp_path, monkeypatch)
        assert result.status == CheckStatus.WARNING
        assert "retired-present" in result.message
        assert "re-run install.sh to prune" in (result.details or "")

    def test_missing_global_reports_warning(self, tmp_path, monkeypatch) -> None:
        commands = self._install(tmp_path, {"feature-plan.md": "PLAN"})
        (commands / "feature-plan.md").unlink()
        result, CheckStatus = self._run(tmp_path, monkeypatch)
        assert result.status == CheckStatus.WARNING
        assert "1 missing" in result.message

    def test_report_only_never_required(self, tmp_path, monkeypatch) -> None:
        """The drift check is optional — it never blocks doctor's exit code."""
        commands = self._install(tmp_path, {"feature-plan.md": "PLAN"})
        (commands / "feature-plan.md").write_text("TAMPERED")
        result, _ = self._run(tmp_path, monkeypatch)
        assert result.required is False
