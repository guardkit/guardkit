"""S1 gate — diff ingestion for the R-b code-review seat (2026-07-13).

Spec of record: ``ai-transition/docs/factory-code-quality-seat-options-2026-07.md``
R-b build-lane stage S-1. Two layers are exercised:

1. :func:`parse_unified_diff` — the PURE parser, driven by fixed diff text
   (adds / deletes / modifies / renames / copies / binary / mode-only /
   multi-hunk / no-newline-at-EOF / truncated tail / quoted paths). No git.

2. The ``ingest_*`` constructors — driven against a REAL throwaway git repo
   built in ``tmp_path`` (the B2 test's fixture-repo pattern), covering every
   F14 ``SubjectKind`` (tree / commit / merge) plus an arbitrary range, and the
   loud-failure + empty-payload honesty rules.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from guardkit.qa.diff_ingest import (
    DiffIngestError,
    ReviewPayload,
    ingest_commit,
    ingest_merge,
    ingest_range,
    ingest_working_tree,
    parse_unified_diff,
)


# ===========================================================================
# Layer 1 — the pure parser (no git)
# ===========================================================================


class TestParseUnifiedDiff:
    def test_empty_input_is_empty_tuple(self):
        assert parse_unified_diff("") == ()
        assert parse_unified_diff("   \n  \n") == ()

    def test_simple_modify_single_hunk(self):
        text = (
            "diff --git a/foo.py b/foo.py\n"
            "index 1111111..2222222 100644\n"
            "--- a/foo.py\n"
            "+++ b/foo.py\n"
            "@@ -1,3 +1,3 @@ def f():\n"
            " a\n"
            "-b\n"
            "+B\n"
            " c\n"
        )
        (f,) = parse_unified_diff(text)
        assert f.path == "foo.py"
        assert f.old_path == "foo.py"
        assert f.change_kind == "modified"
        assert f.is_binary is False
        assert f.additions == 1
        assert f.deletions == 1
        assert len(f.hunks) == 1
        h = f.hunks[0]
        assert (h.old_start, h.old_count, h.new_start, h.new_count) == (1, 3, 1, 3)
        assert h.section_heading == "def f():"
        # Line kinds + numbering.
        kinds = [(l.kind, l.old_lineno, l.new_lineno, l.content) for l in h.lines]
        assert kinds == [
            ("context", 1, 1, "a"),
            ("removed", 2, None, "b"),
            ("added", None, 2, "B"),
            ("context", 3, 3, "c"),
        ]

    def test_added_file(self):
        text = (
            "diff --git a/new.txt b/new.txt\n"
            "new file mode 100644\n"
            "index 0000000..89abcde\n"
            "--- /dev/null\n"
            "+++ b/new.txt\n"
            "@@ -0,0 +1,2 @@\n"
            "+one\n"
            "+two\n"
        )
        (f,) = parse_unified_diff(text)
        assert f.change_kind == "added"
        assert f.path == "new.txt"
        assert f.old_path is None
        assert f.new_mode == "100644"
        assert f.additions == 2 and f.deletions == 0

    def test_deleted_file(self):
        text = (
            "diff --git a/gone.txt b/gone.txt\n"
            "deleted file mode 100644\n"
            "index 89abcde..0000000\n"
            "--- a/gone.txt\n"
            "+++ /dev/null\n"
            "@@ -1,2 +0,0 @@\n"
            "-one\n"
            "-two\n"
        )
        (f,) = parse_unified_diff(text)
        assert f.change_kind == "deleted"
        assert f.path == "gone.txt"
        assert f.old_path == "gone.txt"
        assert f.old_mode == "100644"
        assert f.deletions == 2 and f.additions == 0

    def test_pure_rename_no_hunks(self):
        text = (
            "diff --git a/old_name.py b/new_name.py\n"
            "similarity index 100%\n"
            "rename from old_name.py\n"
            "rename to new_name.py\n"
        )
        (f,) = parse_unified_diff(text)
        assert f.change_kind == "renamed"
        assert f.is_rename is True
        assert f.old_path == "old_name.py"
        assert f.path == "new_name.py"
        assert f.similarity == 100
        assert f.hunks == ()

    def test_rename_with_edits(self):
        text = (
            "diff --git a/old.py b/new.py\n"
            "similarity index 80%\n"
            "rename from old.py\n"
            "rename to new.py\n"
            "index 1111111..2222222 100644\n"
            "--- a/old.py\n"
            "+++ b/new.py\n"
            "@@ -1 +1 @@\n"
            "-x = 1\n"
            "+x = 2\n"
        )
        (f,) = parse_unified_diff(text)
        assert f.change_kind == "renamed"
        assert f.old_path == "old.py"
        assert f.path == "new.py"
        assert f.similarity == 80
        assert f.additions == 1 and f.deletions == 1
        # Omitted counts default to 1.
        h = f.hunks[0]
        assert (h.old_count, h.new_count) == (1, 1)

    def test_copy(self):
        text = (
            "diff --git a/src.py b/copy.py\n"
            "similarity index 100%\n"
            "copy from src.py\n"
            "copy to copy.py\n"
        )
        (f,) = parse_unified_diff(text)
        assert f.change_kind == "copied"
        assert f.old_path == "src.py"
        assert f.path == "copy.py"

    def test_binary_file(self):
        text = (
            "diff --git a/img.png b/img.png\n"
            "index 1111111..2222222 100644\n"
            "Binary files a/img.png and b/img.png differ\n"
        )
        (f,) = parse_unified_diff(text)
        assert f.is_binary is True
        assert f.path == "img.png"
        assert f.old_path == "img.png"
        assert f.hunks == ()
        assert f.additions == 0 and f.deletions == 0

    def test_mode_only_change(self):
        text = (
            "diff --git a/script.sh b/script.sh\n"
            "old mode 100644\n"
            "new mode 100755\n"
        )
        (f,) = parse_unified_diff(text)
        assert f.change_kind == "type_changed"
        assert f.old_mode == "100644"
        assert f.new_mode == "100755"
        assert f.hunks == ()

    def test_multi_hunk_and_multi_file(self):
        text = (
            "diff --git a/a.py b/a.py\n"
            "--- a/a.py\n"
            "+++ b/a.py\n"
            "@@ -1,2 +1,2 @@\n"
            " keep\n"
            "-old1\n"
            "+new1\n"
            "@@ -10,2 +10,3 @@ class C:\n"
            " keepx\n"
            "+extra\n"
            " keepy\n"
            "diff --git a/b.py b/b.py\n"
            "--- a/b.py\n"
            "+++ b/b.py\n"
            "@@ -5 +5 @@\n"
            "-z\n"
            "+Z\n"
        )
        a, b = parse_unified_diff(text)
        assert a.path == "a.py" and b.path == "b.py"
        assert len(a.hunks) == 2
        # Second hunk of a.py starts numbering at line 10.
        h2 = a.hunks[1]
        assert h2.section_heading == "class C:"
        added = h2.added_lines
        assert len(added) == 1 and added[0].new_lineno == 11
        assert a.additions == 2 and a.deletions == 1
        assert b.additions == 1 and b.deletions == 1

    def test_no_newline_at_eof_annotation_is_not_a_line(self):
        text = (
            "diff --git a/f.txt b/f.txt\n"
            "--- a/f.txt\n"
            "+++ b/f.txt\n"
            "@@ -1 +1 @@\n"
            "-a\n"
            "\\ No newline at end of file\n"
            "+b\n"
            "\\ No newline at end of file\n"
        )
        (f,) = parse_unified_diff(text)
        assert f.additions == 1 and f.deletions == 1
        # The "\ No newline" annotations are dropped, not counted as content.
        assert all("No newline" not in l.content for l in f.hunks[0].lines)

    def test_blank_context_line_counted(self):
        # git emits a bare "" for a blank context line inside a hunk.
        text = (
            "diff --git a/f.txt b/f.txt\n"
            "--- a/f.txt\n"
            "+++ b/f.txt\n"
            "@@ -1,3 +1,3 @@\n"
            " x\n"
            "\n"
            "-y\n"
            "+Y\n"
        )
        (f,) = parse_unified_diff(text)
        lines = f.hunks[0].lines
        assert lines[0].kind == "context" and lines[0].content == "x"
        assert lines[1].kind == "context" and lines[1].content == ""
        # Blank context advances both line counters.
        assert lines[1].old_lineno == 2 and lines[1].new_lineno == 2

    def test_truncated_final_hunk_is_tolerated(self):
        # A diff cut off mid-hunk still yields what was parsed.
        text = (
            "diff --git a/f.txt b/f.txt\n"
            "--- a/f.txt\n"
            "+++ b/f.txt\n"
            "@@ -1,5 +1,5 @@\n"
            " a\n"
            "-b\n"
            "+B\n"
        )
        (f,) = parse_unified_diff(text)
        assert f.additions == 1 and f.deletions == 1
        assert len(f.hunks) == 1

    def test_quoted_path_with_space_is_unquoted(self):
        text = (
            'diff --git a/dir/with space.txt b/dir/with space.txt\n'
            "--- a/dir/with space.txt\n"
            "+++ b/dir/with space.txt\n"
            "@@ -1 +1 @@\n"
            "-a\n"
            "+b\n"
        )
        (f,) = parse_unified_diff(text)
        assert f.path == "dir/with space.txt"


# ===========================================================================
# Layer 2 — the ingest_* constructors against a real git repo
# ===========================================================================


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    (r / "seed.py").write_text("a\nb\nc\n")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "seed")
    return r


def _head(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


class TestIngestWorkingTree:
    def test_clean_tree_is_empty_payload(self, repo: Path):
        payload = ingest_working_tree(repo)
        assert isinstance(payload, ReviewPayload)
        assert payload.subject_kind == "tree"
        assert payload.is_empty is True
        assert payload.changed_paths == ()

    def test_all_scope_sees_staged_and_unstaged(self, repo: Path):
        # One staged new file + one unstaged edit to a tracked file.
        (repo / "staged.py").write_text("x\n")
        _git(repo, "add", "staged.py")
        (repo / "seed.py").write_text("a\nB\nc\n")  # unstaged edit
        payload = ingest_working_tree(repo, scope="all")
        assert set(payload.changed_paths) == {"staged.py", "seed.py"}
        assert payload.subject_kind == "tree"

    def test_staged_scope_only(self, repo: Path):
        (repo / "staged.py").write_text("x\n")
        _git(repo, "add", "staged.py")
        (repo / "seed.py").write_text("a\nB\nc\n")  # unstaged, excluded
        payload = ingest_working_tree(repo, scope="staged")
        assert payload.changed_paths == ("staged.py",)

    def test_unstaged_scope_only(self, repo: Path):
        (repo / "staged.py").write_text("x\n")
        _git(repo, "add", "staged.py")
        (repo / "seed.py").write_text("a\nB\nc\n")  # unstaged, included
        payload = ingest_working_tree(repo, scope="unstaged")
        assert payload.changed_paths == ("seed.py",)

    def test_context_lines_widen_the_hunk(self, repo: Path):
        (repo / "seed.py").write_text("a\nB\nc\n")
        narrow = ingest_working_tree(repo, scope="all", context_lines=0)
        wide = ingest_working_tree(repo, scope="all", context_lines=3)
        n_ctx = sum(
            1 for h in narrow.files[0].hunks for l in h.lines if l.kind == "context"
        )
        w_ctx = sum(
            1 for h in wide.files[0].hunks for l in h.lines if l.kind == "context"
        )
        assert n_ctx == 0
        assert w_ctx > n_ctx
        # The change itself is identical regardless of context width.
        assert narrow.total_additions == wide.total_additions == 1


class TestIngestCommit:
    def test_single_commit_diff(self, repo: Path):
        (repo / "seed.py").write_text("a\nB\nc\nd\n")
        _git(repo, "commit", "-aqm", "edit")
        sha = _head(repo)
        payload = ingest_commit(repo, sha)
        assert payload.subject_kind == "commit"
        assert payload.ref == sha
        assert payload.changed_paths == ("seed.py",)
        assert payload.total_additions == 2  # B replaces b, plus new d
        assert payload.total_deletions == 1

    def test_root_commit_handled(self, repo: Path):
        # git show --format= on the root commit must not fail (no parent).
        root = _git(repo, "rev-list", "--max-parents=0", "HEAD").stdout.strip()
        payload = ingest_commit(repo, root)
        assert payload.changed_paths == ("seed.py",)
        assert payload.files[0].change_kind == "added"

    def test_empty_commit_ref_raises(self, repo: Path):
        with pytest.raises(DiffIngestError):
            ingest_commit(repo, "  ")

    def test_bad_ref_raises_loudly(self, repo: Path):
        with pytest.raises(DiffIngestError):
            ingest_commit(repo, "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")


class TestIngestMerge:
    def test_merge_shows_branch_contribution(self, repo: Path):
        # main advances; a feature branch adds a file; merge --no-ff.
        _git(repo, "checkout", "-q", "-b", "feature")
        (repo / "feature.py").write_text("f\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "feat")
        _git(repo, "checkout", "-q", "main")
        (repo / "seed.py").write_text("a\nb\nc\nmain-change\n")
        _git(repo, "commit", "-aqm", "main advance")
        _git(repo, "merge", "-q", "--no-ff", "-m", "merge feature", "feature")
        merge_sha = _head(repo)
        payload = ingest_merge(repo, merge_sha)
        assert payload.subject_kind == "merge"
        # Diff vs first parent (main) = what the feature branch brought in.
        assert "feature.py" in payload.changed_paths
        assert "seed.py" not in payload.changed_paths

    def test_empty_merge_ref_raises(self, repo: Path):
        with pytest.raises(DiffIngestError):
            ingest_merge(repo, "")


class TestIngestRange:
    def test_two_arg_range(self, repo: Path):
        base = _head(repo)
        (repo / "seed.py").write_text("a\nb\nc\nd\n")
        _git(repo, "commit", "-aqm", "c2")
        head = _head(repo)
        payload = ingest_range(repo, base, head)
        assert payload.subject_kind == "commit"
        assert payload.ref == f"{base}..{head}"
        assert payload.changed_paths == ("seed.py",)
        assert payload.total_additions == 1

    def test_single_expression_range(self, repo: Path):
        base = _head(repo)
        (repo / "new.py").write_text("n\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "c2")
        head = _head(repo)
        payload = ingest_range(repo, f"{base}..{head}")
        assert payload.ref == f"{base}..{head}"
        assert payload.changed_paths == ("new.py",)

    def test_empty_base_raises(self, repo: Path):
        with pytest.raises(DiffIngestError):
            ingest_range(repo, "")


class TestHonestyRules:
    def test_negative_context_lines_raises(self, repo: Path):
        with pytest.raises(DiffIngestError):
            ingest_working_tree(repo, context_lines=-1)

    def test_not_a_repo_raises(self, tmp_path: Path):
        with pytest.raises(DiffIngestError):
            ingest_working_tree(tmp_path / "not-a-repo")

    def test_git_run_is_injectable(self, repo: Path):
        # A stub runner proves the seam: parser is exercised on canned text.
        canned = (
            "diff --git a/x.py b/x.py\n"
            "--- a/x.py\n"
            "+++ b/x.py\n"
            "@@ -1 +1 @@\n"
            "-a\n"
            "+b\n"
        )

        def fake_git(args):
            return subprocess.CompletedProcess(args, 0, stdout=canned, stderr="")

        payload = ingest_working_tree(repo, git_run=fake_git)
        assert payload.changed_paths == ("x.py",)

    def test_git_failure_raises_with_stderr(self, repo: Path):
        def fake_git(args):
            return subprocess.CompletedProcess(
                args, 128, stdout="", stderr="fatal: bad object"
            )

        with pytest.raises(DiffIngestError, match="bad object"):
            ingest_commit(repo, "whatever", git_run=fake_git)
