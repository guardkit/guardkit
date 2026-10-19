"""The fix-task writer does not declare a file twice, once by its bare name.

Build FEAT-D31F's repair (19 October 2026): a review recommendation named a
file by its full path and later by its bare name. The file inference kept
both, so the fix task's ``## Files to Modify`` held a bare name that the plan
audit looked for at the top of the repository and never found. Invented file
names only; no network, no model.
"""

from __future__ import annotations


def _infer(text: str):
    from lib.review_parser import SubtaskExtractor

    # The inference reads only the text it is given; the report path is unused.
    return SubtaskExtractor("does-not-exist.md")._infer_files_from_text(text)


def test_a_bare_name_of_a_full_path_in_the_same_text_is_dropped():
    text = (
        "Fix the lint errors in `apps/shelf/src/Shelf.tsx` and "
        "`apps/shelf/src/Shelf.test.tsx`: `Shelf.tsx` line 12 reads an unused "
        "value and `Shelf.test.tsx` line 66 imports an unused helper."
    )
    assert _infer(text) == [
        "apps/shelf/src/Shelf.tsx",
        "apps/shelf/src/Shelf.test.tsx",
    ]


def test_a_bare_name_with_no_full_path_is_kept():
    text = "Rename the helper in `Shelf.tsx` and update `apps/shelf/src/index.ts`."
    assert _infer(text) == ["apps/shelf/src/index.ts", "Shelf.tsx"]


def test_full_paths_that_share_a_name_are_all_kept():
    text = "Both `apps/shelf/src/index.ts` and `apps/api/src/index.ts` need it."
    assert _infer(text) == ["apps/shelf/src/index.ts", "apps/api/src/index.ts"]
