"""One pair of tests per shape of check: a tree that passes, and a tree that does not.

Every fixture is written inside the test. The one that matters most is
``test_a_query_written_inside_a_docstring_is_not_a_query``: it is the instrument's own
validation, and if it ever fails then the checker is reading text rather than code and
every number it has produced is suspect.
"""

from __future__ import annotations

from tests.conformance.conftest import every_site, findings_at, line_of, outcome

# --------------------------------------------------------------------------
# call-site-home-file
# --------------------------------------------------------------------------

QUERY_RULES = """
format_version: "1.0"
layout:
  source_root: src
  infrastructure_modules: [src/core, src/db]
  composition_root: [src/main.py]
rules:
  - id: R-QUERY
    rule: Database queries live in the feature's crud.py, not in its router.py.
    source_document: docs/architecture/00-system-overview.md
    source_sentence: "CRUD Layer (crud.py): implements database operations."
    signals:
      kind: call-site-home-file
      home_file: crud.py
      scope: all
      functions:
        names: [select, insert, update, delete]
        imported_from: [sqlalchemy]
      methods:
        names: [execute, scalars, add, commit]
        receiver_names: [db, session]
        receiver_types: [AsyncSession]
"""

ROUTER_WITH_QUERY = """
from sqlalchemy import select

from src.users.models import User


async def search(db) -> list[str]:
    stmt = select(User)
    result = await db.execute(stmt)
    return [u.name for u in result.scalars().all()]
"""


def test_a_query_in_a_router_is_reported_at_the_line_that_builds_it(check):
    report = check({"src/search/router.py": ROUTER_WITH_QUERY,
                    "src/users/models.py": "class User:\n    pass\n"}, QUERY_RULES)
    build = line_of(ROUTER_WITH_QUERY, "stmt = select(User)")
    assert findings_at(report, "R-QUERY") == {f"src/search/router.py:{build}"}


def test_the_line_that_only_runs_the_query_is_folded_into_the_line_that_built_it(check):
    """Two lines, one query, one finding — the rules file settles this granularity."""
    report = check({"src/search/router.py": ROUTER_WITH_QUERY,
                    "src/users/models.py": "class User:\n    pass\n"}, QUERY_RULES)
    run_line = line_of(ROUTER_WITH_QUERY, "result = await db.execute(stmt)")
    site = outcome(report, "R-QUERY").findings[0]
    assert site.line != run_line
    assert any(f"line {run_line}" in extra for extra in site.also_at)


def test_the_same_query_in_the_file_the_rule_names_is_not_a_finding(check):
    report = check({"src/users/crud.py": ROUTER_WITH_QUERY,
                    "src/users/models.py": "class User:\n    pass\n"}, QUERY_RULES)
    assert findings_at(report, "R-QUERY") == set()
    assert every_site(report, "R-QUERY")          # it matched; it was simply at home
    assert outcome(report, "R-QUERY").status == "clean"


def test_a_query_written_inside_a_docstring_is_not_a_query(check):
    """The instrument's own validation. A text search fails this; a syntax tree cannot."""
    docstring_file = '''
    async def get_db():
        """Yield a session.

        Example:
            users = await db.execute(select(User))
        """
        yield None
    '''
    report = check({"src/db/dependencies.py": docstring_file}, QUERY_RULES)
    assert every_site(report, "R-QUERY") == set()


def test_a_function_of_the_same_name_from_somewhere_else_is_not_a_query(check):
    """``update()`` counts only when this file imported it from the module the rule names."""
    report = check({"src/users/router.py": "from src.core.tools import update\n\n"
                                           "def go() -> None:\n    update(1)\n"}, QUERY_RULES)
    assert every_site(report, "R-QUERY") == set()


def test_a_session_recognised_by_its_annotation_rather_than_its_name(check):
    """``conn.execute()`` counts when ``conn`` is annotated with a type the rule lists."""
    text = """
    from sqlalchemy.ext.asyncio import AsyncSession


    async def go(handle: AsyncSession) -> None:
        await handle.execute("select 1")
    """
    report = check({"src/users/router.py": text}, QUERY_RULES)
    assert findings_at(report, "R-QUERY") == {
        f"src/users/router.py:{line_of(text, 'await handle.execute')}"}


def test_a_line_the_rules_file_names_as_an_exception_is_not_a_finding(check):
    text = """
    async def live(db) -> bool:
        await db.execute("SELECT 1")
        return True
    """
    rules = QUERY_RULES + """
    exceptions:
      - path: src/health/router.py
        lines: [2]
        why: A liveness probe. It reads no domain data.
"""
    report = check({"src/health/router.py": text}, rules.replace("\n    exceptions:", "\n    exceptions:"))
    assert findings_at(report, "R-QUERY") == set()
    assert [s.placement for s in outcome(report, "R-QUERY").sites] == ["excepted"]


# --------------------------------------------------------------------------
# module-import-boundary
# --------------------------------------------------------------------------

IMPORT_RULES = """
format_version: "1.0"
layout:
  source_root: src
  infrastructure_modules: [src/core, src/db]
  composition_root: [src/main.py]
rules:
  - id: R-IMPORT
    rule: A feature module does not import another feature module.
    source_document: docs/architecture/adr-001.md
    source_sentence: "Cross-feature coupling is forbidden."
    signals:
      kind: module-import-boundary
      scope: feature_modules
      allowed_target_modules: [src.core, src.db]
      skip_files: [src/main.py]
"""


def test_one_feature_importing_another_feature_is_reported(check):
    text = """
    from src.db.dependencies import get_db
    from src.users.models import User
    """
    report = check({"src/search/router.py": text,
                    "src/users/models.py": "class User:\n    pass\n"}, IMPORT_RULES)
    assert findings_at(report, "R-IMPORT") == {
        f"src/search/router.py:{line_of(text, 'src.users.models')}"}


def test_imports_towards_infrastructure_and_within_a_feature_are_not_reported(check):
    files = {
        "src/search/router.py": "from src.db.dependencies import get_db\n"
                                "from src.core.config import settings\n"
                                "from src.search.schemas import SearchResponse\n",
        "src/search/schemas.py": "class SearchResponse:\n    pass\n",
    }
    report = check(files, IMPORT_RULES)
    assert findings_at(report, "R-IMPORT") == set()


def test_the_composition_root_may_import_every_feature(check):
    files = {
        "src/main.py": "from src.users.router import router\n"
                       "from src.search.router import router as s\n",
        "src/users/router.py": "router = 1\n",
        "src/search/router.py": "router = 1\n",
    }
    report = check(files, IMPORT_RULES)
    assert findings_at(report, "R-IMPORT") == set()


# --------------------------------------------------------------------------
# module-import-boundary, with a public read interface named
#
# ADR-001 in the pilot repository was amended on 2026-08-31 to say which of a
# feature's files another feature may import: crud.py and schemas.py, and nothing
# else. A rule says so by listing `public_modules`. A rule that does not list them
# must behave exactly as it did before the signal existed, and the last test here
# is the one that pins that.
# --------------------------------------------------------------------------

PUBLIC_IMPORT_RULES = IMPORT_RULES.replace(
    "      allowed_target_modules: [src.core, src.db]\n",
    "      allowed_target_modules: [src.core, src.db]\n"
    "      public_modules: [crud, schemas]\n")

USERS_FEATURE = {
    "src/users/crud.py": "def get_user(db, user_id):\n    return None\n\n"
                         "def _row_to_schema(row):\n    return row\n",
    "src/users/schemas.py": "class UserRead:\n    pass\n",
    "src/users/models.py": "class User:\n    pass\n",
    "src/users/router.py": "router = 1\n",
}


def test_importing_another_features_public_read_interface_is_allowed(check):
    text = """
    from src.db.dependencies import get_db
    from src.users.crud import get_user
    from src.users.schemas import UserRead
    """
    report = check({"src/analytics/crud.py": text, **USERS_FEATURE},
                   PUBLIC_IMPORT_RULES)
    assert findings_at(report, "R-IMPORT") == set()


def test_importing_another_features_private_file_is_still_a_finding(check):
    text = """
    from src.users.models import User
    """
    report = check({"src/analytics/crud.py": text, **USERS_FEATURE},
                   PUBLIC_IMPORT_RULES)
    assert findings_at(report, "R-IMPORT") == {
        f"src/analytics/crud.py:{line_of(text, 'src.users.models')}"}
    site = outcome(report, "R-IMPORT").findings[0]
    assert "private file of feature module src/users" in site.observed
    assert "crud.py, schemas.py" in site.observed


def test_an_underscore_name_from_a_public_file_is_still_a_finding(check):
    """A public file's address does not make a private helper public."""
    text = """
    from src.users.crud import get_user, _row_to_schema
    """
    report = check({"src/analytics/crud.py": text, **USERS_FEATURE},
                   PUBLIC_IMPORT_RULES)
    assert findings_at(report, "R-IMPORT") == {
        f"src/analytics/crud.py:{line_of(text, '_row_to_schema')}"}
    assert "_row_to_schema" in outcome(report, "R-IMPORT").findings[0].observed


def test_importing_the_whole_feature_package_is_still_a_finding(check):
    """`import src.users` names no file, so it reaches every file in the feature."""
    text = """
    import src.users
    """
    report = check({"src/analytics/crud.py": text, **USERS_FEATURE},
                   PUBLIC_IMPORT_RULES)
    assert findings_at(report, "R-IMPORT") == {
        f"src/analytics/crud.py:{line_of(text, 'import src.users')}"}


def test_same_feature_and_infrastructure_imports_stay_silent_with_a_public_interface(check):
    files = {
        "src/analytics/crud.py": "from src.db.dependencies import get_db\n"
                                 "from src.core.config import settings\n"
                                 "from src.analytics.models import Event\n"
                                 "from src.analytics._helpers import fold\n",
        "src/analytics/models.py": "class Event:\n    pass\n",
        "src/analytics/_helpers.py": "def fold(x):\n    return x\n",
        **USERS_FEATURE,
    }
    report = check(files, PUBLIC_IMPORT_RULES)
    assert findings_at(report, "R-IMPORT") == set()


def test_a_rule_naming_no_public_modules_behaves_exactly_as_it_did_before(check):
    """The backwards-compatibility guarantee, pinned line by line and word for word.

    Every import into another feature is reported, including the two the amended
    record would allow, and the wording of the finding is unchanged.
    """
    text = """
    from src.users.crud import get_user
    from src.users.schemas import UserRead
    from src.users.models import User
    """
    files = {"src/analytics/crud.py": text, **USERS_FEATURE}
    report = check(files, IMPORT_RULES)
    assert findings_at(report, "R-IMPORT") == {
        f"src/analytics/crud.py:{line_of(text, 'src.users.crud')}",
        f"src/analytics/crud.py:{line_of(text, 'src.users.schemas')}",
        f"src/analytics/crud.py:{line_of(text, 'src.users.models')}",
    }
    assert [s.observed for s in outcome(report, "R-IMPORT").findings] == [
        f"an import of src.users.{name}, which is in feature module src/users, "
        f"written in feature module src/analytics"
        for name in ("crud", "schemas", "models")]


# --------------------------------------------------------------------------
# file-layout
# --------------------------------------------------------------------------

LAYOUT_RULES = """
format_version: "1.0"
layout:
  source_root: src
  infrastructure_modules: [src/core, src/db]
  composition_root: [src/main.py]
rules:
  - id: R-NO-GLOBAL
    rule: There is no global models/ or schemas/ directory.
    source_document: docs/architecture/adr-001.md
    source_sentence: "Creating a global models/ directory is forbidden."
    signals:
      kind: file-layout
      forbidden_directories: [src/models, src/schemas]
      allowed_files: [src/schemas.py]
  - id: R-ROUTER-REQUIRED
    rule: Every feature module contains a router.py.
    source_document: docs/architecture/adr-001.md
    source_sentence: "router.py — required in every feature"
    signals:
      kind: file-layout
      scope: feature_modules
      required_files: [router.py]
"""


def test_a_forbidden_directory_and_a_missing_required_file_are_both_reported(check):
    """Note the second line of the second assertion, which is not a mistake.

    The rules file defines a feature module as any directory under the source root
    that is not named as infrastructure. A global ``src/models/`` therefore breaks two
    rules at once: it is a directory that should not exist, and — being a directory
    under the source root — it also has no router.py. Both are reported, because
    hiding the second would mean the checker holding an opinion about which of two
    true statements matters, and that is a judgement it does not have.
    """
    files = {
        "src/models/user.py": "class User:\n    pass\n",
        "src/users/router.py": "router = 1\n",
        "src/stats/__init__.py": "",
    }
    report = check(files, LAYOUT_RULES)
    assert findings_at(report, "R-NO-GLOBAL") == {"src/models"}
    assert findings_at(report, "R-ROUTER-REQUIRED") == {"src/models", "src/stats"}


def test_the_shared_base_schema_file_is_a_file_not_the_forbidden_directory(check):
    files = {
        "src/schemas.py": "class BaseSchema:\n    pass\n",
        "src/users/router.py": "router = 1\n",
    }
    report = check(files, LAYOUT_RULES)
    assert findings_at(report, "R-NO-GLOBAL") == set()
    assert findings_at(report, "R-ROUTER-REQUIRED") == set()
    placements = [s.placement for s in outcome(report, "R-NO-GLOBAL").sites]
    assert placements == ["excepted"], "the sanctioned file is seen and said, not passed over"


# --------------------------------------------------------------------------
# handler-shape
# --------------------------------------------------------------------------

HANDLER_RULES = """
format_version: "1.0"
layout:
  source_root: src
  infrastructure_modules: [src/core, src/db]
  composition_root: [src/main.py]
rules:
  - id: R-ASYNC
    rule: Route handlers are declared with async def.
    source_document: docs/architecture/adr-002.md
    source_sentence: "Synchronous blocking calls are forbidden in route handlers."
    signals:
      kind: handler-shape
      handler_decorator_shape: an attribute call on any object, where the attribute is an HTTP method name
      http_method_names: [get, post, put, patch, delete, head, options]
      require: AsyncFunctionDef
  - id: R-RETURNS
    rule: A route handler declares the type it returns, and never returns a bare dictionary.
    source_document: docs/architecture/adr-003.md
    source_sentence: "No raw dictionaries should be returned from routers."
    signals:
      kind: handler-shape
      handler_decorator_shape: same as R-ASYNC — match the shape, not a list of names
      require: return annotation present
      forbidden_annotations: [dict, Dict, Any, object]
"""


def test_a_synchronous_route_handler_is_reported_and_an_async_one_is_not(check):
    text = """
    router = 1


    @router.get("/a")
    def sync_handler() -> str:
        return "a"


    @router.get("/b")
    async def async_handler() -> str:
        return "b"
    """
    report = check({"src/users/router.py": text}, HANDLER_RULES)
    assert findings_at(report, "R-ASYNC") == {
        f"src/users/router.py:{line_of(text, 'def sync_handler')}"}


def test_a_handler_on_a_second_router_object_is_still_seen(check):
    """A checker hardcoding the name ``router`` would scan every handler but one."""
    text = """
    recent_router = 1


    @recent_router.get("/recent")
    def recent() -> str:
        return "x"
    """
    report = check({"src/users/router.py": text}, HANDLER_RULES)
    assert findings_at(report, "R-ASYNC") == {f"src/users/router.py:{line_of(text, 'def recent')}"}


def test_a_handler_with_no_return_type_and_one_returning_a_bare_dict_are_reported(check):
    text = """
    router = 1


    @router.get("/a")
    async def no_annotation():
        return {}


    @router.get("/b")
    async def bare_dict() -> dict:
        return {}


    @router.get("/c")
    async def typed() -> str:
        return "ok"
    """
    report = check({"src/users/router.py": text}, HANDLER_RULES)
    assert findings_at(report, "R-RETURNS") == {
        f"src/users/router.py:{line_of(text, 'async def no_annotation')}",
        f"src/users/router.py:{line_of(text, 'async def bare_dict')}",
    }


def test_the_second_handler_rule_borrows_the_http_method_names_the_first_one_states(check):
    """Its own words say "same as R-ASYNC", so the list is followed, never invented."""
    text = """
    router = 1


    @router.get("/a")
    async def handler():
        return 1
    """
    report = check({"src/users/router.py": text}, HANDLER_RULES)
    assert outcome(report, "R-RETURNS").inherited_signals == ["http_method_names (from R-ASYNC)"]
    assert outcome(report, "R-RETURNS").examined["route handlers found"] == 1


def test_a_plain_function_that_is_not_a_route_handler_is_not_looked_at(check):
    text = """
    def helper(x: int) -> int:
        return x
    """
    report = check({"src/users/router.py": text}, HANDLER_RULES)
    assert findings_at(report, "R-ASYNC") == set()
    assert findings_at(report, "R-RETURNS") == set()


# --------------------------------------------------------------------------
# forbidden-imports
# --------------------------------------------------------------------------

BLOCKING_RULES = """
format_version: "1.0"
layout:
  source_root: src
  infrastructure_modules: [src/core, src/db]
  composition_root: [src/main.py]
rules:
  - id: R-BLOCKING
    rule: Feature code does not use blocking I/O libraries.
    source_document: docs/architecture/adr-002.md
    source_sentence: "Using blocking libraries is forbidden."
    signals:
      kind: forbidden-imports
      scope: all
      modules: [requests, psycopg2, urllib.request, http.client, MySQLdb]
      calls: [time.sleep]
"""


def test_a_blocking_import_and_a_blocking_call_are_both_reported(check):
    text = """
    import requests
    import time
    from urllib.request import urlopen


    def go() -> None:
        time.sleep(1)
        requests.get("http://x")
        urlopen("http://x")
    """
    report = check({"src/users/router.py": text}, BLOCKING_RULES)
    assert findings_at(report, "R-BLOCKING") == {
        f"src/users/router.py:{line_of(text, 'import requests')}",
        f"src/users/router.py:{line_of(text, 'from urllib.request')}",
        f"src/users/router.py:{line_of(text, 'time.sleep(1)')}",
    }


def test_the_sleep_imported_by_name_is_reported_too(check):
    text = """
    from time import sleep


    def go() -> None:
        sleep(1)
    """
    report = check({"src/users/router.py": text}, BLOCKING_RULES)
    assert findings_at(report, "R-BLOCKING") == {f"src/users/router.py:{line_of(text, 'sleep(1)')}"}


def test_a_module_whose_name_merely_starts_the_same_is_not_reported(check):
    text = """
    import requests_mock
    import urllib.parse
    import time


    def go() -> str:
        return str(time.monotonic())
    """
    report = check({"src/users/router.py": text}, BLOCKING_RULES)
    assert findings_at(report, "R-BLOCKING") == set()


# --------------------------------------------------------------------------
# forbidden-method-call
# --------------------------------------------------------------------------

LEGACY_RULES = """
format_version: "1.0"
layout:
  source_root: src
  infrastructure_modules: [src/core, src/db]
  composition_root: [src/main.py]
rules:
  - id: R-LEGACY
    rule: Database access uses select and execute, not the legacy Query API.
    source_document: docs/architecture/adr-004.md
    source_sentence: "Leveraging select() and execute() rather than legacy query objects."
    signals:
      kind: forbidden-method-call
      scope: all
      methods: [query]
      receiver_names: [db, session]
      receiver_types: [AsyncSession, Session]
"""


def test_the_legacy_query_call_is_reported_and_the_modern_one_is_not(check):
    text = """
    async def go(db) -> None:
        db.query(User)
        await db.execute("select 1")
    """
    report = check({"src/users/crud.py": text}, LEGACY_RULES)
    assert findings_at(report, "R-LEGACY") == {f"src/users/crud.py:{line_of(text, 'db.query')}"}


def test_a_query_method_on_something_that_is_not_a_session_is_not_reported(check):
    text = """
    def go(client) -> None:
        client.query("something")
    """
    report = check({"src/users/crud.py": text}, LEGACY_RULES)
    assert findings_at(report, "R-LEGACY") == set()


# --------------------------------------------------------------------------
# class-definition-home-file
# --------------------------------------------------------------------------

MODEL_RULES = """
format_version: "1.0"
layout:
  source_root: src
  infrastructure_modules: [src/core, src/db]
  composition_root: [src/main.py]
rules:
  - id: R-MODELS
    rule: ORM model classes live in the feature's models.py and inherit DeclarativeBase.
    source_document: docs/architecture/adr-004.md
    source_sentence: "Defining models using the DeclarativeBase pattern."
    signals:
      kind: class-definition-home-file
      home_file: models.py
      scope: feature_modules
      class_marks: [__tablename__, mapped_column]
      required_base_names: [DeclarativeBase]
"""

GOOD_MODEL = """
from src.db.base import DeclarativeBase


class User(DeclarativeBase):
    __tablename__ = "users"
"""


def test_a_table_class_in_the_file_the_rule_names_with_the_right_base_is_not_reported(check):
    report = check({"src/users/models.py": GOOD_MODEL}, MODEL_RULES)
    assert findings_at(report, "R-MODELS") == set()
    assert outcome(report, "R-MODELS").examined["database table classes found"] == 1


def test_a_table_class_in_the_wrong_file_is_reported(check):
    report = check({"src/users/router.py": GOOD_MODEL}, MODEL_RULES)
    assert findings_at(report, "R-MODELS") == {
        f"src/users/router.py:{line_of(GOOD_MODEL, 'class User')}"}


def test_a_table_class_in_the_right_file_without_the_required_base_is_still_reported(check):
    """Being in the home file excuses where it is, never what it inherits."""
    text = """
    class User:
        __tablename__ = "users"
    """
    report = check({"src/users/models.py": text}, MODEL_RULES)
    assert findings_at(report, "R-MODELS") == {f"src/users/models.py:{line_of(text, 'class User')}"}


def test_a_base_class_declared_in_the_same_file_is_followed(check):
    text = """
    from src.db.base import DeclarativeBase


    class Common(DeclarativeBase):
        pass


    class User(Common):
        __tablename__ = "users"
    """
    report = check({"src/users/models.py": text}, MODEL_RULES)
    assert findings_at(report, "R-MODELS") == set()


def test_a_class_with_none_of_the_marks_is_not_a_table_class(check):
    text = """
    class SearchResponse:
        query: str
    """
    report = check({"src/users/schemas.py": text}, MODEL_RULES)
    assert every_site(report, "R-MODELS") == set()


# --------------------------------------------------------------------------
# config-file-fact
# --------------------------------------------------------------------------

CONFIG_RULES = """
format_version: "1.0"
layout:
  source_root: src
  infrastructure_modules: [src/core, src/db]
  composition_root: [src/main.py]
rules:
  - id: R-CONFIG
    rule: Strict mypy and ruff stay configured in pyproject.toml.
    source_document: docs/architecture/adr-005.md
    source_sentence: "This is enforced via [tool.mypy] strict = true in pyproject.toml."
    signals:
      kind: config-file-fact
      file: pyproject.toml
      require:
        - "table [tool.mypy] exists"
        - "tool.mypy.strict is true"
        - "table [tool.ruff] exists"
"""

GOOD_PYPROJECT = """
[tool.ruff]
line-length = 100

[tool.mypy]
strict = true
"""


def test_a_configuration_file_that_states_what_the_rule_wants_is_not_reported(check):
    report = check({"pyproject.toml": GOOD_PYPROJECT, "src/users/router.py": "x = 1\n"},
                   CONFIG_RULES)
    assert findings_at(report, "R-CONFIG") == set()
    assert outcome(report, "R-CONFIG").examined["requirements checked"] == 3


def test_a_setting_turned_off_and_a_missing_table_are_both_reported(check):
    bad = """
    [tool.mypy]
    strict = false
    """
    report = check({"pyproject.toml": bad, "src/users/router.py": "x = 1\n"}, CONFIG_RULES)
    found = outcome(report, "R-CONFIG").findings
    assert len(found) == 2
    assert any("strict" in s.observed for s in found)
    assert any("[tool.ruff]" in s.observed for s in found)
    assert [s for s in found if "strict" in s.observed][0].line == line_of(bad, "[tool.mypy]")


def test_a_configuration_file_that_is_not_there_is_reported_not_assumed(check):
    report = check({"src/users/router.py": "x = 1\n"}, CONFIG_RULES)
    assert [s.observed for s in outcome(report, "R-CONFIG").findings] == [
        "there is no pyproject.toml in this repository"]


# --------------------------------------------------------------------------
# annotation-completeness
# --------------------------------------------------------------------------

ANNOTATION_RULES = """
format_version: "1.0"
layout:
  source_root: src
  infrastructure_modules: [src/core, src/db]
  composition_root: [src/main.py]
rules:
  - id: R-ANNOTATED
    rule: Every function in src/ has type annotations on its arguments and its return.
    source_document: docs/architecture/adr-005.md
    source_sentence: "Forbids implicit Any types, untyped arguments and unannotated returns."
    signals:
      kind: annotation-completeness
      scope: all
      require: [return annotation, annotation on every argument]
      ignore_args: [self, cls]
"""


def test_a_missing_argument_annotation_and_a_missing_return_are_one_finding_per_function(check):
    text = """
    def bare(x):
        return x


    def half(x: int):
        return x


    def whole(x: int) -> int:
        return x
    """
    report = check({"src/users/calculations.py": text}, ANNOTATION_RULES)
    assert findings_at(report, "R-ANNOTATED") == {
        f"src/users/calculations.py:{line_of(text, 'def bare')}",
        f"src/users/calculations.py:{line_of(text, 'def half')}",
    }


def test_self_and_cls_do_not_need_annotations_and_an_explicit_any_is_not_a_finding(check):
    text = """
    from typing import Any


    class Thing:
        def method(self, x: Any) -> Any:
            return x

        @classmethod
        def build(cls) -> "Thing":
            return cls()
    """
    report = check({"src/users/calculations.py": text}, ANNOTATION_RULES)
    assert findings_at(report, "R-ANNOTATED") == set()


# --------------------------------------------------------------------------
# forbidden-construction
# --------------------------------------------------------------------------

SESSION_RULES = """
format_version: "1.0"
layout:
  source_root: src
  infrastructure_modules: [src/core, src/db]
  composition_root: [src/main.py]
rules:
  - id: R-DI
    rule: Database sessions arrive through dependency injection.
    source_document: docs/architecture/adr-006.md
    source_sentence: "Direct instantiation of Session objects is forbidden."
    signals:
      kind: forbidden-construction
      scope: all
      skip_directories: [src/db]
      calls: [Session, AsyncSession, sessionmaker, async_sessionmaker, create_async_engine]
"""


def test_a_session_built_in_feature_code_is_reported(check):
    text = """
    from sqlalchemy.orm import sessionmaker


    def go() -> None:
        factory = sessionmaker()
        factory()
    """
    report = check({"src/users/crud.py": text}, SESSION_RULES)
    assert findings_at(report, "R-DI") == {f"src/users/crud.py:{line_of(text, 'sessionmaker()')}"}


def test_the_same_construction_where_the_rule_says_it_belongs_is_not_reported(check):
    text = """
    from sqlalchemy.ext.asyncio import async_sessionmaker


    def build() -> None:
        async_sessionmaker()
    """
    report = check({"src/db/session.py": text}, SESSION_RULES)
    assert findings_at(report, "R-DI") == set()


def test_taking_a_session_as_an_annotated_parameter_is_not_building_one(check):
    text = """
    from fastapi import Depends
    from sqlalchemy.ext.asyncio import AsyncSession


    async def handler(db: AsyncSession = Depends(get_db)) -> None:
        return None
    """
    report = check({"src/users/router.py": text}, SESSION_RULES)
    assert findings_at(report, "R-DI") == set()


# --- the idiomatic from-import form (2026-08-31) -----------------------------
# `from src.users import crud` reaches exactly the same public file as
# `from src.users.crud import x`. Refusing one form while permitting the other
# said "no" to the code generator without telling it the legal rewrite, which is
# the shape of mistake that cost a real build its turns.


def test_from_feature_import_public_module_is_allowed(check):
    text = """
    from src.users import crud
    """
    report = check({"src/analytics/crud.py": text, **USERS_FEATURE},
                   PUBLIC_IMPORT_RULES)
    assert findings_at(report, "R-IMPORT") == set()


def test_from_feature_import_several_public_modules_is_allowed(check):
    text = """
    from src.users import crud, schemas
    """
    report = check({"src/analytics/crud.py": text, **USERS_FEATURE},
                   PUBLIC_IMPORT_RULES)
    assert findings_at(report, "R-IMPORT") == set()


def test_from_feature_import_private_module_is_still_a_finding(check):
    text = """
    from src.users import models
    """
    report = check({"src/analytics/crud.py": text, **USERS_FEATURE},
                   PUBLIC_IMPORT_RULES)
    assert findings_at(report, "R-IMPORT") == {
        f"src/analytics/crud.py:{line_of(text, 'from src.users import models')}"}


def test_mixing_a_private_module_into_the_import_is_still_a_finding(check):
    """crud is public, models is not; naming both must not launder models."""
    text = """
    from src.users import crud, models
    """
    report = check({"src/analytics/crud.py": text, **USERS_FEATURE},
                   PUBLIC_IMPORT_RULES)
    assert findings_at(report, "R-IMPORT") != set()
    assert "models" in outcome(report, "R-IMPORT").findings[0].observed


def test_bare_package_import_is_still_a_finding(check):
    """`import src.users` reaches every file in the feature, public or not."""
    text = """
    import src.users
    """
    report = check({"src/analytics/crud.py": text, **USERS_FEATURE},
                   PUBLIC_IMPORT_RULES)
    assert findings_at(report, "R-IMPORT") != set()


def test_a_dunder_from_a_public_file_is_not_described_as_private(check):
    text = """
    from src.users.crud import __all__
    """
    report = check({"src/analytics/crud.py": text, **USERS_FEATURE},
                   PUBLIC_IMPORT_RULES)
    for site in outcome(report, "R-IMPORT").findings:
        assert "underscore" not in site.observed
