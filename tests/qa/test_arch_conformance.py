"""Tests for the architecture-rules checker.

Every fixture here is written inside the test, so these tests prove what the
checker does without depending on any other repository being present on disk.
The one test that matters most is ``test_a_query_inside_a_docstring_is_not_a_query``:
it is the instrument's own validation, and if it ever fails, every number the
checker has ever produced is suspect.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from guardkit.qa import arch_conformance as A

RULES = """
format_version: "1.0"
repo: fixture
source_document: .claude/CLAUDE.md
ruled_by: test
layout:
  source_root: src
  infrastructure_modules: [src/core, src/db]
  composition_root: [src/main.py]
rules:
  - id: queries-live-in-crud
    says: "Database query operations live in the feature's crud.py."
    source: {file: .claude/CLAUDE.md, line: 102, quote: "CRUD Layer (crud.py)"}
    check:
      kind: call-site-home-file
      home_file: crud.py
      scope: all
      functions: {names: [select, delete], imported_from: [sqlalchemy]}
      methods:
        names: [execute, add, commit]
        receiver_names: [db, session]
        receiver_types: [AsyncSession]
    exceptions:
      - path: src/health/router.py
        lines: [3]
        why: "Liveness probe."
  - id: features-do-not-import-features
    says: "A feature module does not import another feature module."
    source: {file: .claude/CLAUDE.md, line: 9, quote: "Feature-Based Organization"}
    check:
      kind: module-import-boundary
      scope: feature_modules
      allowed_target_modules: [src.core, src.db]
    exceptions: []
  - id: schemas-live-in-schemas-py
    says: "Pydantic models are declared in schemas.py."
    source: {file: .claude/CLAUDE.md, line: 98, quote: "Schema Layer (schemas.py)"}
    check:
      kind: class-definition-home-file
      home_file: schemas.py
      scope: feature_modules
      base_names: [BaseModel]
    exceptions: []
"""

FILES = {
    "src/__init__.py": "",
    "src/main.py": "from src.users.router import router\nfrom src.search.router import router as s\n",
    "src/core/__init__.py": "",
    "src/db/__init__.py": "",
    "src/db/dependencies.py": '''
        """Database dependencies."""
        async def get_db():
            """Yield a session.

            Example:
                users = await db.execute(select(User))
            """
            yield None
    ''',
    "src/users/__init__.py": "",
    "src/users/crud.py": '''
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession
        from src.users.models import User

        async def get_user(db: AsyncSession, uid):
            stmt = select(User)
            result = await db.execute(stmt)
            return result.scalars().all()
    ''',
    "src/users/models.py": "class User:\n    pass\n",
    "src/users/schemas.py": '''
        from pydantic import BaseModel

        class UserBase(BaseModel):
            pass

        class UserCreate(UserBase):
            pass
    ''',
    "src/users/router.py": '''
        from src.users import crud
        router = None
    ''',
    "src/search/__init__.py": "",
    "src/search/router.py": '''
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession
        from src.db.dependencies import get_db
        from src.users.models import User

        async def search(db: AsyncSession):
            stmt = select(User)
            return await db.execute(stmt)
    ''',
    "src/health/__init__.py": "",
    "src/health/router.py": '''
        from sqlalchemy.ext.asyncio import AsyncSession
        async def health(db: AsyncSession):
            return await db.execute("SELECT 1")
    ''',
}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "fixture"
    (root / "docs").mkdir(parents=True)
    (root / "docs/architecture-rules.yaml").write_text(RULES)
    for rel, body in FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(body).lstrip("\n"))
    return root


def findings(repo: Path, rule: str | None = None) -> list[dict]:
    out = A.to_json(A.run(repo, None))
    return [f for f in out["findings"] if rule is None or f["rule_id"] == rule]


def at(repo: Path, rule: str | None = None) -> set[str]:
    return {f["observed_at"] for f in findings(repo, rule)}


# --- the instrument's own validation -----------------------------------------

def test_a_query_inside_a_docstring_is_not_a_query(repo: Path):
    """src/db/dependencies.py has `await db.execute(select(User))` inside a docstring.

    A checker that searches source TEXT reports it. A checker that reads the
    syntax tree cannot see it, because a docstring is a string constant. If this
    test fails the checker is reading prose as code and no result it produces
    can be trusted.
    """
    report = A.run(repo, None)
    scanned = {s.path for s in report.sites} | {u["path"] for u in report.files_unparsed}
    assert report.files_scanned == len(FILES), "the checker must read every file"
    assert "src/db/dependencies.py" in {
        p.relative_to(repo).as_posix() for p in (repo / "src").rglob("*.py")}
    assert not any(f.startswith("src/db/dependencies.py") for f in at(repo))
    assert "db.execute(select(User))" in (repo / "src/db/dependencies.py").read_text()


def test_the_text_a_naive_checker_would_match_is_present(repo: Path):
    """Guards the test above from passing because the fixture drifted."""
    assert "db.execute" in (repo / "src/db/dependencies.py").read_text()


# --- catching --------------------------------------------------------------

def test_it_names_every_line_of_a_misplaced_query(repo: Path):
    assert at(repo, "queries-live-in-crud") == {
        "src/search/router.py:7",   # stmt = select(User)
        "src/search/router.py:8"}   # await db.execute(stmt)


def test_it_names_a_cross_feature_import(repo: Path):
    assert at(repo, "features-do-not-import-features") == {"src/search/router.py:4"}


def test_a_class_inheriting_a_local_base_still_counts(repo: Path):
    """UserCreate(UserBase) where UserBase(BaseModel) sits above it in the same file."""
    out = A.to_json(A.run(repo, None))
    rule = next(r for r in out["rules"] if r["id"] == "schemas-live-in-schemas-py")
    assert rule["sites_matched"] == 2, "both UserBase and UserCreate must be seen"
    assert rule["sites_by_placement"]["elsewhere"] == 0


# --- staying silent --------------------------------------------------------

def test_it_is_silent_on_the_file_the_rule_names(repo: Path):
    assert not any(f.startswith("src/users/crud.py") for f in at(repo))


def test_it_is_silent_on_a_named_exception_and_says_why(repo: Path):
    assert "src/health/router.py:3" not in at(repo)
    out = A.to_json(A.run(repo, None))
    rule = next(r for r in out["rules"] if r["id"] == "queries-live-in-crud")
    assert rule["sites_by_placement"]["excepted"] == 1
    assert "Liveness probe." in rule["exceptions"][0]["why"]


def test_it_is_silent_on_the_composition_root(repo: Path):
    assert not any(f.startswith("src/main.py") for f in at(repo))


def test_it_is_silent_on_an_intra_feature_import(repo: Path):
    assert "src/users/router.py:1" not in at(repo)


def test_it_is_silent_on_a_feature_reaching_infrastructure(repo: Path):
    assert "src/search/router.py:3" not in at(repo)  # from src.db.dependencies


def test_a_method_call_on_a_non_session_receiver_is_not_a_query(repo: Path):
    """`@router.delete(...)` is a FastAPI decorator, not a database delete."""
    (repo / "src/time").mkdir()
    (repo / "src/time/__init__.py").write_text("")
    (repo / "src/time/router.py").write_text(
        "router = None\n\n@router.delete('/x')\nasync def d():\n    pass\n")
    assert not any(f.startswith("src/time/router.py") for f in at(repo))


def test_a_bare_call_not_imported_from_sqlalchemy_is_not_a_query(repo: Path):
    (repo / "src/time").mkdir()
    (repo / "src/time/__init__.py").write_text("")
    (repo / "src/time/router.py").write_text(
        "from src.core.helpers import select\n\ndef go():\n    return select(1)\n")
    assert not any(f.startswith("src/time/router.py") for f in at(repo))


# --- the corrected version --------------------------------------------------

def test_moving_the_query_into_crud_silences_the_rule(repo: Path):
    (repo / "src/search/crud.py").write_text(textwrap.dedent('''
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession

        async def all_rows(db: AsyncSession):
            return await db.execute(select(1))
    ''').lstrip("\n"))
    (repo / "src/search/router.py").write_text(textwrap.dedent('''
        from src.db.dependencies import get_db
        from src.search import crud

        async def search(db):
            return await crud.all_rows(db)
    ''').lstrip("\n"))
    assert at(repo) == set(), "a corrected feature must produce nothing at all"


# --- refusing to speak where it cannot ---------------------------------------

def test_no_rules_file_reports_no_rules_file_and_not_clean(tmp_path: Path):
    (tmp_path / "src").mkdir()
    rep = A.run(tmp_path, None)
    assert rep.rules_path is None
    assert A.to_json(rep)["findings"] == []
    assert "not the same as clean" in " ".join(rep.notes)


def test_rules_from_another_repository_are_withheld(repo: Path, tmp_path: Path):
    other = tmp_path / "somewhere-else"
    (other / "src/users").mkdir(parents=True)
    (other / "src/users/router.py").write_text(
        "from sqlalchemy import select\n\ndef f():\n    return select(1)\n")
    rep = A.run(other, repo / "docs/architecture-rules.yaml")
    assert rep.rules_withheld is not None
    assert A.to_json(rep)["findings"] == []
    rep2 = A.run(other, repo / "docs/architecture-rules.yaml",
                 rules_are_for_another_repo=True)
    assert rep2.rules_withheld is None
    assert A.to_json(rep2)["findings"], "the escape hatch must actually print them"


def test_a_file_that_does_not_parse_is_reported_not_dropped(repo: Path):
    (repo / "src/users/broken.py").write_text("def (: this is not python\n")
    rep = A.run(repo, None)
    assert [u["path"] for u in rep.files_unparsed] == ["src/users/broken.py"]


# --- what it must never do ---------------------------------------------------

def test_no_finding_uses_a_word_that_draws_a_conclusion(repo: Path):
    """The machine-facing output states observations and nothing else.

    Filesystem paths are excluded: pytest names its temporary directory after the
    test, so a test named "...no_score..." would otherwise fail on its own path.
    """
    out = A.to_json(A.run(repo, None))
    speech = (str(out["findings"]) + str(out["rules"]) + str(out["notes"])
              ).replace(str(repo), "<repo>").lower()
    for word in ("severity", "confidence", "score", "verdict", "violation",
                 "critical", "aligned", "misaligned"):
        assert word not in speech, (
            f"the checker must not use the word {word!r}: it draws a conclusion")


def test_no_finding_carries_a_conclusion_shaped_field(repo: Path):
    out = A.to_json(A.run(repo, None))
    assert out["findings"], "this fixture is meant to produce findings"
    for f in out["findings"]:
        assert set(f) == {
            "rule_id", "rule_says", "rule_source", "observed_at", "observed",
            "enclosing_function", "how_observed", "same_repo_comparison"}


def test_the_text_output_says_out_loud_that_it_is_not_a_verdict(repo: Path):
    text = A.to_text(A.run(repo, None))
    assert "It is not a verdict, a score, or a count of defects" in text


def test_the_exit_code_is_always_zero(repo: Path, capsys):
    assert A.main(["--repo", str(repo)]) == 0
    assert A.main(["--repo", str(repo), "--json"]) == 0


def test_every_finding_carries_the_document_line_it_came_from(repo: Path):
    for f in findings(repo):
        assert f["rule_source"]["file"] and f["rule_source"]["line"]
        assert f["how_observed"].startswith("python ast:")
