"""PB-3: command-distribution manifest generator + doctor drift check.

The manifest (installer/core/commands/MANIFEST.json) is the single provenance
source for install.sh's prune list, `guardkit doctor`'s drift report, and the
packaging include set. These tests pin: (1) the committed manifest is current
(the CI --check contract), (2) the version is the single source
guardkit/__init__.py, (3) the tombstones are declared, (4) the doctor drift
check classifies current / modified / missing / retired-present correctly and
is report-only, and (5) the two-state staleness contract below.

THE TWO STATES (the fix these tests guard)
------------------------------------------
The drift check originally compared installed files against the INSTALL-TIME
manifest only. That answers "has anyone edited these?" and cannot answer "are
these current?" — so a ~7-week-old install of the command markdowns reported a
clean pass. The check now reports two independent states:

* MODIFIED — installed bytes  != manifest sha  (edited locally)
* STALE    — manifest sha     != shipped payload sha  (install is out of date)

A file can be in both. ``guardkit init --update`` refreshes STALE files and
refuses to clobber MODIFIED ones.
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


def _write_install(tmp_path: Path, names, tombstones=()) -> Path:
    """Build a fake installed commands dir + its install-time MANIFEST.json.

    The manifest records the sha256 of exactly the content written, so the
    install starts out unedited (no MODIFIED files).
    """
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


def _write_payload(tmp_path: Path, names) -> Path:
    """Build a fake SHIPPED payload (what the installed package carries).

    Mirrors the real layout — ``<root>/commands/*.md`` plus a MANIFEST.json —
    so ``guardkit init --update`` has a manifest to install alongside the files.
    """
    payload = tmp_path / "payload" / "commands"
    payload.mkdir(parents=True)
    entries = {}
    for name, content in names.items():
        (payload / name).write_text(content)
        entries[name] = {
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
            "source_commit": "ffff999",
        }
    (payload / "MANIFEST.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "package": "guardkit-py",
                "version": "9.9.9",
                "commands": entries,
                "tombstones": [],
            }
        )
    )
    return payload


def _patch_payload(monkeypatch, payload_dir):
    """Point the shared payload resolver at a fake payload dir (or None)."""
    import guardkit.commands.payload as payload_mod

    monkeypatch.setattr(
        payload_mod, "resolve_shipped_commands_dir", lambda: payload_dir
    )


class TestDoctorDriftCheck:
    def _install(self, tmp_path: Path, names, tombstones=()) -> Path:
        return _write_install(tmp_path, names, tombstones)

    def _run(self, tmp_path: Path, monkeypatch, payload=None):
        """Run the drift check against tmp_path as $HOME.

        ``payload`` defaults to a payload IDENTICAL to the installed content,
        i.e. an up-to-date install — so any STALE result in these tests is
        caused by the test, never by ambient repo state.
        """
        from guardkit.cli.doctor import CheckStatus, CommandManifestDriftCheck

        if payload is None:
            installed = tmp_path / ".agentecflow" / "commands"
            payload = _write_payload(
                tmp_path,
                {p.name: p.read_text() for p in installed.glob("*.md")},
            )
        _patch_payload(monkeypatch, payload)
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


class TestStalenessAgainstShippedPayload:
    """The fix: the check must also answer "are these CURRENT?".

    Each test builds an install whose files match their manifest exactly (so the
    OLD, manifest-only check would report a clean pass) and then varies only the
    shipped payload.
    """

    def _run(self, tmp_path: Path, monkeypatch, payload):
        from guardkit.cli.doctor import CheckStatus, CommandManifestDriftCheck

        _patch_payload(monkeypatch, payload)
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        monkeypatch.chdir(tmp_path)
        return CommandManifestDriftCheck().run(), CheckStatus

    def test_current_install_passes(self, tmp_path, monkeypatch) -> None:
        """Install matches manifest AND payload -> PASS, no STALE noise."""
        content = {"feature-plan.md": "v2", "task-work.md": "WORK"}
        _write_install(tmp_path, content)
        payload = _write_payload(tmp_path, content)
        result, CheckStatus = self._run(tmp_path, monkeypatch, payload)
        assert result.status == CheckStatus.PASS
        assert "current" in result.message
        assert "STALE" not in result.message

    def test_edited_file_reports_modified(self, tmp_path, monkeypatch) -> None:
        """A locally edited file is MODIFIED, and is named as such."""
        content = {"feature-plan.md": "v2"}
        commands = _write_install(tmp_path, content)
        payload = _write_payload(tmp_path, content)
        (commands / "feature-plan.md").write_text("HAND EDITED")
        result, CheckStatus = self._run(tmp_path, monkeypatch, payload)
        assert result.status == CheckStatus.WARNING
        assert "1 modified" in result.message
        assert "STALE" not in result.message
        assert "MODIFIED" in (result.details or "")

    def test_behind_payload_reports_stale(self, tmp_path, monkeypatch) -> None:
        """THE REGRESSION GUARD.

        The installed file matches its manifest byte for byte — the old check
        called this "current" — but the package now ships newer content. That
        must be a STALE WARNING naming the remedy, never a silent pass.
        """
        _write_install(tmp_path, {"feature-plan.md": "JULY"})
        payload = _write_payload(tmp_path, {"feature-plan.md": "AUGUST"})
        result, CheckStatus = self._run(tmp_path, monkeypatch, payload)
        assert result.status == CheckStatus.WARNING
        assert "1 STALE" in result.message
        assert "modified" not in result.message
        details = result.details or ""
        assert "feature-plan.md" in details
        assert "guardkit init --update" in details
        assert "guardkit init --update" in result.message

    def test_modified_and_stale_reported_together(self, tmp_path, monkeypatch) -> None:
        """Both states at once are reported as two distinct facts."""
        commands = _write_install(
            tmp_path, {"feature-plan.md": "JULY", "task-work.md": "WORK"}
        )
        payload = _write_payload(
            tmp_path, {"feature-plan.md": "AUGUST", "task-work.md": "WORK"}
        )
        (commands / "task-work.md").write_text("HAND EDITED")
        result, CheckStatus = self._run(tmp_path, monkeypatch, payload)
        assert result.status == CheckStatus.WARNING
        assert "1 modified" in result.message
        assert "1 STALE" in result.message
        details = result.details or ""
        assert "MODIFIED" in details and "task-work.md" in details
        assert "STALE" in details and "feature-plan.md" in details

    def test_stale_is_never_a_silent_pass(self, tmp_path, monkeypatch) -> None:
        """A stale install is a WARNING at minimum — never PASS."""
        _write_install(tmp_path, {"feature-plan.md": "JULY"})
        payload = _write_payload(tmp_path, {"feature-plan.md": "AUGUST"})
        result, CheckStatus = self._run(tmp_path, monkeypatch, payload)
        assert result.status != CheckStatus.PASS

    def test_missing_payload_says_staleness_unknown(self, tmp_path, monkeypatch) -> None:
        """No payload -> the check must SAY it could not check staleness."""
        _write_install(tmp_path, {"feature-plan.md": "JULY"})
        result, CheckStatus = self._run(tmp_path, monkeypatch, None)
        assert result.status == CheckStatus.WARNING
        assert "staleness" in (result.message + (result.details or "")).lower()


class TestInitUpdate:
    """``guardkit init --update`` — the supported way to update an install."""

    def _update(self, tmp_path, monkeypatch, payload, *, force=False):
        from guardkit.cli.init import update_installed_commands

        _patch_payload(monkeypatch, payload)
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        project = tmp_path / "proj"
        project.mkdir(exist_ok=True)
        monkeypatch.chdir(project)
        return update_installed_commands(force=force, project_dir=project)

    def test_update_refreshes_stale_file(self, tmp_path, monkeypatch) -> None:
        """A stale command file is brought up to the shipped content."""
        commands = _write_install(tmp_path, {"feature-plan.md": "JULY"})
        payload = _write_payload(tmp_path, {"feature-plan.md": "AUGUST"})
        assert self._update(tmp_path, monkeypatch, payload) == 0
        assert (commands / "feature-plan.md").read_text() == "AUGUST"

    def test_update_rewrites_manifest_so_check_goes_clean(
        self, tmp_path, monkeypatch
    ) -> None:
        """After --update the manifest describes what is now installed.

        Without the manifest rewrite the refreshed files would be reported as
        MODIFIED on the very next run.
        """
        _write_install(tmp_path, {"feature-plan.md": "JULY"})
        payload = _write_payload(tmp_path, {"feature-plan.md": "AUGUST"})
        self._update(tmp_path, monkeypatch, payload)

        from guardkit.cli.doctor import CheckStatus, CommandManifestDriftCheck

        result = CommandManifestDriftCheck().run()
        assert result.status == CheckStatus.PASS, result.details

    def test_update_refuses_to_clobber_an_edited_file(
        self, tmp_path, monkeypatch
    ) -> None:
        """The never-clobber promise: an edited file survives --update."""
        commands = _write_install(tmp_path, {"feature-plan.md": "JULY"})
        payload = _write_payload(tmp_path, {"feature-plan.md": "AUGUST"})
        (commands / "feature-plan.md").write_text("RICHS OWN EDIT")
        assert self._update(tmp_path, monkeypatch, payload) == 0
        assert (commands / "feature-plan.md").read_text() == "RICHS OWN EDIT"

    def test_edited_file_is_listed_not_silently_skipped(
        self, tmp_path, monkeypatch
    ) -> None:
        """Skipping must be reported by name, not silently."""
        from guardkit.commands.payload import refresh_commands

        commands = _write_install(tmp_path, {"feature-plan.md": "JULY"})
        payload = _write_payload(tmp_path, {"feature-plan.md": "AUGUST"})
        (commands / "feature-plan.md").write_text("RICHS OWN EDIT")
        result = refresh_commands(commands, shipped_dir=payload)
        assert result.skipped_modified == ["feature-plan.md"]
        assert result.updated == []

    def test_force_overwrites_an_edited_file(self, tmp_path, monkeypatch) -> None:
        """--force is the explicit opt-in that discards local edits."""
        commands = _write_install(tmp_path, {"feature-plan.md": "JULY"})
        payload = _write_payload(tmp_path, {"feature-plan.md": "AUGUST"})
        (commands / "feature-plan.md").write_text("RICHS OWN EDIT")
        assert self._update(tmp_path, monkeypatch, payload, force=True) == 0
        assert (commands / "feature-plan.md").read_text() == "AUGUST"

    def test_edited_file_keeps_its_manifest_entry_after_update(
        self, tmp_path, monkeypatch
    ) -> None:
        """A skipped (edited) file keeps its ORIGINAL manifest hash.

        Recomputing it would bless the edit and erase the MODIFIED signal.
        """
        commands = _write_install(
            tmp_path, {"feature-plan.md": "JULY", "task-work.md": "OLD"}
        )
        payload = _write_payload(
            tmp_path, {"feature-plan.md": "AUGUST", "task-work.md": "NEW"}
        )
        (commands / "feature-plan.md").write_text("RICHS OWN EDIT")
        self._update(tmp_path, monkeypatch, payload)
        manifest = json.loads((commands / "MANIFEST.json").read_text())
        assert manifest["commands"]["feature-plan.md"]["sha256"] == (
            hashlib.sha256(b"JULY").hexdigest()
        )
        assert manifest["commands"]["task-work.md"]["sha256"] == (
            hashlib.sha256(b"NEW").hexdigest()
        )

    def test_update_is_idempotent(self, tmp_path, monkeypatch) -> None:
        """Running --update twice changes nothing the second time."""
        from guardkit.commands.payload import refresh_commands

        commands = _write_install(tmp_path, {"feature-plan.md": "JULY"})
        payload = _write_payload(tmp_path, {"feature-plan.md": "AUGUST"})
        self._update(tmp_path, monkeypatch, payload)
        second = refresh_commands(commands, shipped_dir=payload)
        assert second.updated == []
        assert second.skipped_modified == []

    def test_force_without_update_is_refused(self) -> None:
        """--force alone is a user error, refused with a helpful message."""
        from click.testing import CliRunner

        from guardkit.cli.init import init

        result = CliRunner().invoke(init, ["--force"])
        assert result.exit_code != 0
        assert "--update" in str(result.output) + str(result.exception)

    def test_cli_update_flag_refreshes_and_skips_template_init(
        self, tmp_path, monkeypatch
    ) -> None:
        """`guardkit init --update` must be WIRED to the refresh, not to init.

        Guards the flag itself: --update refreshes the installed commands and
        must NOT fall through to a normal init (which would scaffold tasks/ and
        .guardkit/ into the user's cwd as a surprise side effect).
        """
        from click.testing import CliRunner

        from guardkit.cli.init import init

        commands = _write_install(tmp_path, {"feature-plan.md": "JULY"})
        payload = _write_payload(tmp_path, {"feature-plan.md": "AUGUST"})
        _patch_payload(monkeypatch, payload)
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        project = tmp_path / "proj"
        project.mkdir()
        monkeypatch.chdir(project)

        result = CliRunner().invoke(init, ["--update"])
        assert result.exit_code == 0, result.output
        assert (commands / "feature-plan.md").read_text() == "AUGUST"
        assert not (project / "tasks").exists(), "--update must not scaffold a project"
        assert not (project / ".guardkit").exists()
