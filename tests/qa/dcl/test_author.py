"""W1-S1 — the DCL machine-authoring §10 port (guardkit dcl author).

Every test injects spy seat/probe callables — NO test touches the network (the
single-slot build-lane law). The vendored WASM checker DOES run for real (node is
on PATH); the seat is the only mocked edge.

Layers exercised:

1. Pinned §10 bytes — system prompt sha, vocab delimiter, repair instruction,
   the vendored vocab reference's sha.
2. Prompt composition golden (byte-exact sha of a fixed composed turn).
3. Zero-shot-clean path (1 seat call, artifact + receipt, exit 0).
4. Bounded repair path (EXACTLY 2 seat calls, 2 probes, repaired_clean).
5. POISON dirty-dirty (2 calls, exit 1, artifact NOT written, receipt authored:false).
6. Refusal / probe-failure (exit 2, nothing written, seat never called).
7. Empty-content + vacuous-clean guard (exit 1).
8. Transport retries (4xx no retry -> exit 2; 5xx retries then succeeds).
9. Config precedence (env > config > default).
10. Receipt validates via the qa format machinery; CliRunner smoke of the verb.
"""

from __future__ import annotations

import hashlib
import shutil
import urllib.error
from pathlib import Path

import pytest
import yaml

from guardkit.qa.dcl import author as author_mod
from guardkit.qa.dcl.author import (
    PINNED_SYSTEM_PROMPT,
    PINNED_SYSTEM_PROMPT_SHA256,
    REPAIR_INSTRUCTION,
    VOCAB_DELIM,
    VOCAB_REF,
    VOCAB_REF_SHA256,
    AuthoringInstrumentError,
    author_dcl,
    compose_author_prompt,
    resolve_endpoint_model,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "dcl"
requires_node = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node is required to run the vendored WASM DCL checker",
)

VALID_DCL = (FIXTURES / "capability.dcl").read_text(encoding="utf-8")
BROKEN_DCL = (FIXTURES / "broken.dcl").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Spies — the injected seat/probe edges (no network, ever).
# ---------------------------------------------------------------------------


def _seat(*contents, finish="stop"):
    """A spy seat returning the given contents in order (one per call)."""
    calls: list[dict] = []

    def _call(endpoint, model, system, user):
        idx = len(calls)
        calls.append({"endpoint": endpoint, "model": model, "system": system, "user": user})
        item = contents[idx]
        if isinstance(item, Exception):
            raise item
        return {"choices": [{"message": {"content": item}, "finish_reason": finish}]}

    _call.calls = calls  # type: ignore[attr-defined]
    return _call


def _ok_probe():
    probes: list[dict] = []

    def _probe(endpoint, model):
        rec = {"url": author_mod._probe_base(endpoint) + "/running", "ok": True}
        probes.append(rec)
        return rec

    _probe.probes = probes  # type: ignore[attr-defined]
    return _probe


def _boom_probe():
    def _probe(endpoint, model):
        raise AuthoringInstrumentError("single-slot probe: seat not proven ready")

    return _probe


@pytest.fixture
def repo(tmp_path) -> Path:
    """A minimal target repo with the two required inputs at conventional paths."""
    root = tmp_path / "repo"
    (root / "feature_spec_inputs").mkdir(parents=True)
    (root / "qa").mkdir(parents=True)
    (root / "feature_spec_inputs" / "stats-endpoint.md").write_text(
        "# Request\n\nAdd a GET /stats endpoint returning JSON service statistics.\n",
        encoding="utf-8",
    )
    (root / "qa" / "pass-bar-TASK-STAT-001.yaml").write_text(
        yaml.safe_dump(
            {
                "criteria": [
                    {"id": "C1", "text": "GET /stats returns 200 JSON", "class": "machine", "evidence_kind": "json"},
                ],
                "negative_paths": ["dependency_down_degradation"],
            }
        ),
        encoding="utf-8",
    )
    return root


def _req(repo: Path) -> Path:
    return repo / "feature_spec_inputs" / "stats-endpoint.md"


def _crit(repo: Path) -> Path:
    return repo / "qa" / "pass-bar-TASK-STAT-001.yaml"


def _author(repo: Path, seat, probe, **kw):
    return author_dcl(
        feature="stats-endpoint",
        task="TASK-STAT-001",
        repo_root=repo,
        request_path=_req(repo),
        criteria_path=_crit(repo),
        endpoint="http://127.0.0.1:9000/v1/chat/completions",
        model="qwen36-workhorse",
        seat_call=seat,
        running_probe=probe,
        **kw,
    )


# ===========================================================================
# 1. Pinned §10 bytes.
# ===========================================================================


def test_pinned_system_prompt_sha256() -> None:
    assert PINNED_SYSTEM_PROMPT == (
        "Output ONLY the DCL source. No prose, no explanation, no markdown fences."
    )
    assert hashlib.sha256(PINNED_SYSTEM_PROMPT.encode("utf-8")).hexdigest() == PINNED_SYSTEM_PROMPT_SHA256
    assert PINNED_SYSTEM_PROMPT_SHA256 == (
        "419e455b26af1d3014e28100f6e6520c1fbdba10d05941adbbd0e2d0163d7316"
    )


def test_vocab_delim_and_repair_instruction_bytes() -> None:
    assert VOCAB_DELIM == "\n\n=== DCL v1.0 VERIFIED VOCABULARY REFERENCE ===\n"
    assert REPAIR_INSTRUCTION == (
        "The DCL compiler REJECTED your previous attempt with the diagnostics above. "
        "Fix exactly those errors while preserving the declared semantics, and return "
        "ONLY the corrected, compile-clean DCL source — the full .dcl file, no prose, "
        "no explanation, no markdown fences."
    )


def test_vocab_reference_sha256_pinned() -> None:
    """The vendored vocab reference is byte-identical to the §10 upstream copy."""
    assert VOCAB_REF.is_file()
    got = hashlib.sha256(VOCAB_REF.read_bytes()).hexdigest()
    assert got == VOCAB_REF_SHA256
    assert got == "25121afe7415b15cba161fa2f3e728dad7095675f214a298317b51bb0e8fee2b"


# ===========================================================================
# 2. Prompt composition golden.
# ===========================================================================


def test_compose_prompt_golden() -> None:
    request = "Feature: stats endpoint\n\nExpose GET /stats returning a JSON count.\n"
    criteria = {
        "criteria": [
            {"id": "C1", "text": "GET /stats returns 200 with a JSON body", "class": "machine", "evidence_kind": "json"},
            {"id": "C2", "text": "the count field is a non-negative integer", "class": "machine", "evidence_kind": "json"},
        ],
        "negative_paths": ["dependency_down_degradation"],
    }
    vocab = "STUB VOCAB v1.0\nlanguage dcl 1.0\n"
    system, user, sha = compose_author_prompt(request, criteria, vocab)

    assert system == PINNED_SYSTEM_PROMPT
    # The vocab is appended verbatim at the very END under the delimiter.
    assert user.endswith(VOCAB_DELIM + vocab)
    # prompt_sha256 covers the FULL composed turn (including the vocab).
    assert sha == hashlib.sha256(user.encode("utf-8")).hexdigest()
    # Byte-exact regression lock (computed at build time).
    assert sha == "7e6f35382602d7bc2a7b3852ee998d00100ce03aa83e4d78bc5462942318637c"


# ===========================================================================
# 3. Zero-shot-clean path.
# ===========================================================================


@requires_node
def test_zero_shot_clean(repo) -> None:
    seat = _seat(VALID_DCL)
    probe = _ok_probe()
    result = _author(repo, seat, probe)

    assert result.exit_code == 0
    assert result.authored is True
    assert result.attempts == 1
    assert result.zero_shot_clean is True
    assert result.repaired_clean is None
    assert len(seat.calls) == 1  # exactly one seat call
    assert len(probe.probes) == 1

    artifact = repo / "features" / "stats-endpoint" / "stats-endpoint.dcl"
    assert artifact.is_file()
    body = artifact.read_text(encoding="utf-8")
    assert body.splitlines()[0].startswith("language dcl 1.0")
    assert "// @task:TASK-STAT-001" in body
    assert "capability ReportServiceStatistics" in body

    receipt = repo / "qa" / "dcl" / "authoring-stats-endpoint.yaml"
    assert receipt.is_file()
    data = yaml.safe_load(receipt.read_text(encoding="utf-8"))
    assert data["authored"] is True
    assert data["attempts"] == 1
    assert data["zero_shot_clean"] is True
    assert data["artifact"] == "features/stats-endpoint/stats-endpoint.dcl"
    assert data["prompt"]["system_sha256"] == PINNED_SYSTEM_PROMPT_SHA256
    assert data["vocab_ref"]["sha256"] == VOCAB_REF_SHA256
    assert data["sampling"] == {"temperature": 0.3, "top_p": 0.9, "max_tokens": 16384}
    assert data["envelopes"]["attempt2"] is None


@requires_node
def test_zero_shot_marker_not_duplicated(repo) -> None:
    """A model that already emitted the marker keeps exactly one."""
    already = VALID_DCL.replace(
        "language dcl 1.0\n", "language dcl 1.0\n// @task:TASK-STAT-001\n", 1
    )
    result = _author(repo, _seat(already), _ok_probe())
    assert result.authored is True
    body = (repo / "features" / "stats-endpoint" / "stats-endpoint.dcl").read_text()
    assert body.count("// @task:TASK-STAT-001") == 1


# ===========================================================================
# 4. Bounded repair path — EXACTLY one repair call.
# ===========================================================================


@requires_node
def test_repair_path_exactly_two_calls(repo) -> None:
    seat = _seat(BROKEN_DCL, VALID_DCL)
    probe = _ok_probe()
    result = _author(repo, seat, probe)

    assert result.exit_code == 0
    assert result.authored is True
    assert result.attempts == 2
    assert result.zero_shot_clean is False
    assert result.repaired_clean is True
    assert len(seat.calls) == 2  # exactly two — the structural bound
    assert len(probe.probes) == 2  # single-slot probe before BOTH calls

    # The repair prompt carried the previous attempt + the verbatim diagnostics.
    repair_user = seat.calls[1]["user"]
    assert "REJECTED BY THE DCL COMPILER" in repair_user
    assert "DCL COMPILER DIAGNOSTICS (VERBATIM)" in repair_user
    assert REPAIR_INSTRUCTION in repair_user
    assert BROKEN_DCL.rstrip("\n") in repair_user

    receipt = yaml.safe_load(
        (repo / "qa" / "dcl" / "authoring-stats-endpoint.yaml").read_text()
    )
    assert receipt["attempts"] == 2
    assert receipt["zero_shot_clean"] is False
    assert receipt["repaired_clean"] is True
    assert receipt["envelopes"]["attempt1"]["ok"] is False
    assert receipt["envelopes"]["attempt2"]["ok"] is True
    assert receipt["repair_wall_time_s"] is not None


# ===========================================================================
# 5. POISON — dirty then dirty is a LOUD failure, no artifact written.
# ===========================================================================


@requires_node
def test_poison_dirty_dirty(repo) -> None:
    seat = _seat(BROKEN_DCL, BROKEN_DCL)
    result = _author(repo, seat, _ok_probe())

    assert result.exit_code == 1
    assert result.authored is False
    assert result.attempts == 2
    assert result.repaired_clean is False
    assert result.failure_reason and "did not compile clean" in result.failure_reason
    assert len(seat.calls) == 2

    # Artifact NOT written; receipt written with authored:false.
    assert not (repo / "features" / "stats-endpoint" / "stats-endpoint.dcl").exists()
    receipt = yaml.safe_load(
        (repo / "qa" / "dcl" / "authoring-stats-endpoint.yaml").read_text()
    )
    assert receipt["authored"] is False
    assert receipt["artifact"] is None
    assert receipt["failure_reason"]


@requires_node
def test_poison_leaves_preexisting_artifact_untouched(repo) -> None:
    art = repo / "features" / "stats-endpoint" / "stats-endpoint.dcl"
    art.parent.mkdir(parents=True)
    art.write_text("language dcl 1.0\n// PRIOR ARTIFACT — must survive\n", encoding="utf-8")

    result = _author(repo, _seat(BROKEN_DCL, BROKEN_DCL), _ok_probe())
    assert result.authored is False
    assert art.read_text(encoding="utf-8") == "language dcl 1.0\n// PRIOR ARTIFACT — must survive\n"


# ===========================================================================
# 6. Refusal / probe-failure — exit 2, nothing written, seat never called.
# ===========================================================================


def test_probe_failure_is_exit2_nothing_written(repo) -> None:
    seat = _seat(VALID_DCL)  # must never be invoked
    with pytest.raises(AuthoringInstrumentError):
        _author(repo, seat, _boom_probe())
    assert len(seat.calls) == 0
    assert not (repo / "features").exists()
    assert not (repo / "qa" / "dcl").exists()


def test_missing_inputs_is_exit2(repo) -> None:
    with pytest.raises(AuthoringInstrumentError):
        author_dcl(
            feature="stats-endpoint",
            task="TASK-STAT-001",
            repo_root=repo,
            request_path=repo / "feature_spec_inputs" / "does-not-exist.md",
            criteria_path=_crit(repo),
            endpoint="http://127.0.0.1:9000/v1/chat/completions",
            model="qwen36-workhorse",
            seat_call=_seat(VALID_DCL),
            running_probe=_ok_probe(),
        )
    assert not (repo / "qa" / "dcl").exists()


# ===========================================================================
# 7. Empty-content + vacuous-clean guard — exit 1.
# ===========================================================================


@requires_node
def test_empty_content_guard(repo) -> None:
    # Empty content compiles vacuously clean but is a LOUD authoring failure.
    seat = _seat("", "")
    result = _author(repo, seat, _ok_probe())
    assert result.exit_code == 1
    assert result.authored is False
    assert result.failure_reason and "empty" in result.failure_reason
    assert not (repo / "features" / "stats-endpoint" / "stats-endpoint.dcl").exists()
    receipt = repo / "qa" / "dcl" / "authoring-stats-endpoint.yaml"
    assert receipt.is_file()


@requires_node
def test_clean_but_no_capability_guard(repo) -> None:
    # A header-only file compiles clean but declares no capability -> loud failure.
    seat = _seat("language dcl 1.0\n", "language dcl 1.0\n")
    result = _author(repo, seat, _ok_probe())
    assert result.exit_code == 1
    assert result.authored is False
    assert result.failure_reason and "capability" in result.failure_reason
    assert not (repo / "features" / "stats-endpoint" / "stats-endpoint.dcl").exists()


# ===========================================================================
# 8. Transport retries.
# ===========================================================================


def test_4xx_no_retry_is_exit2(repo, monkeypatch) -> None:
    monkeypatch.setattr(author_mod.time, "sleep", lambda *_: None)
    err = urllib.error.HTTPError("http://x", 400, "bad request", {}, None)  # type: ignore[arg-type]
    seat = _seat(err)
    with pytest.raises(AuthoringInstrumentError):
        _author(repo, seat, _ok_probe())
    assert len(seat.calls) == 1  # a 4xx is NOT retried


@requires_node
def test_5xx_retries_then_succeeds(repo, monkeypatch) -> None:
    monkeypatch.setattr(author_mod.time, "sleep", lambda *_: None)
    e500 = urllib.error.HTTPError("http://x", 503, "unavailable", {}, None)  # type: ignore[arg-type]
    seat = _seat(e500, e500, VALID_DCL)  # 2 retries, then clean
    result = _author(repo, seat, _ok_probe())
    assert result.authored is True
    assert result.attempts == 1  # transport retries are NOT authoring attempts
    assert len(seat.calls) == 3


def test_5xx_exhausted_is_exit2(repo, monkeypatch) -> None:
    monkeypatch.setattr(author_mod.time, "sleep", lambda *_: None)
    e500 = urllib.error.HTTPError("http://x", 500, "err", {}, None)  # type: ignore[arg-type]
    seat = _seat(e500, e500, e500)  # never recovers
    with pytest.raises(AuthoringInstrumentError):
        _author(repo, seat, _ok_probe())
    assert len(seat.calls) == 3  # 1 + 2 retries, then abort


# ===========================================================================
# 9. Config precedence (env > config > default).
# ===========================================================================


def test_resolve_endpoint_model_default(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("GUARDKIT_DCL_AUTHOR_ENDPOINT", raising=False)
    monkeypatch.delenv("GUARDKIT_DCL_AUTHOR_MODEL", raising=False)
    ep, model = resolve_endpoint_model(tmp_path)
    assert ep == "http://127.0.0.1:9000/v1/chat/completions"
    assert model == "qwen36-workhorse"


def test_resolve_endpoint_model_config_over_default(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("GUARDKIT_DCL_AUTHOR_ENDPOINT", raising=False)
    monkeypatch.delenv("GUARDKIT_DCL_AUTHOR_MODEL", raising=False)
    (tmp_path / ".guardkit").mkdir()
    (tmp_path / ".guardkit" / "config.yaml").write_text(
        yaml.safe_dump({"qa": {"dcl_author": {"endpoint": "http://cfg:1/v1/x", "model": "cfg-model"}}}),
        encoding="utf-8",
    )
    ep, model = resolve_endpoint_model(tmp_path)
    assert ep == "http://cfg:1/v1/x"
    assert model == "cfg-model"


def test_resolve_endpoint_model_env_over_config(tmp_path, monkeypatch) -> None:
    (tmp_path / ".guardkit").mkdir()
    (tmp_path / ".guardkit" / "config.yaml").write_text(
        yaml.safe_dump({"qa": {"dcl_author": {"endpoint": "http://cfg:1/v1/x", "model": "cfg-model"}}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("GUARDKIT_DCL_AUTHOR_ENDPOINT", "http://env:2/v1/y")
    monkeypatch.setenv("GUARDKIT_DCL_AUTHOR_MODEL", "env-model")
    ep, model = resolve_endpoint_model(tmp_path)
    assert ep == "http://env:2/v1/y"
    assert model == "env-model"


# ===========================================================================
# 10. Receipt validates via the qa machinery + CLI smoke.
# ===========================================================================


@requires_node
def test_receipt_validates_as_registered_kind(repo) -> None:
    _author(repo, _seat(VALID_DCL), _ok_probe())
    from guardkit.qa.formats import validate_instance

    receipt = repo / "qa" / "dcl" / "authoring-stats-endpoint.yaml"
    model = validate_instance("dcl-authoring", receipt)
    assert model.FORMAT_KIND == "dcl-authoring"
    # The f19 alias resolves too.
    assert validate_instance("f19", receipt).FORMAT_KIND == "dcl-authoring"


@requires_node
def test_cli_author_smoke(repo, monkeypatch) -> None:
    from click.testing import CliRunner

    from guardkit.cli.dcl import dcl

    # The CLI calls author_dcl() with NO injected edges — patch the module-level
    # defaults so the real author_dcl + real checker run end-to-end, no network.
    monkeypatch.setattr(author_mod, "_default_seat_call", _seat(VALID_DCL))
    monkeypatch.setattr(author_mod, "_default_running_probe", _ok_probe())

    result = CliRunner().invoke(
        dcl,
        ["author", "--feature", "stats-endpoint", "--task", "TASK-STAT-001",
         "--repo", str(repo), "--json"],
    )
    assert result.exit_code == 0, result.output
    assert "AUTHORED" in result.output
    assert (repo / "features" / "stats-endpoint" / "stats-endpoint.dcl").is_file()


@requires_node
def test_cli_author_poison_exit1(repo, monkeypatch) -> None:
    from click.testing import CliRunner

    from guardkit.cli.dcl import dcl

    monkeypatch.setattr(author_mod, "_default_seat_call", _seat(BROKEN_DCL, BROKEN_DCL))
    monkeypatch.setattr(author_mod, "_default_running_probe", _ok_probe())

    result = CliRunner().invoke(
        dcl,
        ["author", "--feature", "stats-endpoint", "--task", "TASK-STAT-001", "--repo", str(repo)],
    )
    assert result.exit_code == 1
    assert "AUTHORING FAILED" in result.output
    assert not (repo / "features" / "stats-endpoint" / "stats-endpoint.dcl").exists()


def test_cli_author_missing_inputs_exit2(tmp_path) -> None:
    from click.testing import CliRunner

    from guardkit.cli.dcl import dcl

    result = CliRunner().invoke(
        dcl,
        ["author", "--feature", "nope", "--task", "T-1", "--repo", str(tmp_path)],
    )
    assert result.exit_code == 2
    assert "instrument error" in result.output
