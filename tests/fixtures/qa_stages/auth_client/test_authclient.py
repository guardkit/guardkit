"""Auth-client suite with a DELIBERATE coverage hole on the delete verb.

get/post/put assert the Authorization header; delete asserts only the method —
so a strip-auth-header mutation of delete survives, and the mutation gate must
catch it. Do not "fix" the delete gap: it is the fixture's whole point.
"""

from authclient import AuthClient


def test_get_is_authorized():
    r = AuthClient("t").get("/a")
    assert r["auth"] == "Bearer t"


def test_post_is_authorized():
    r = AuthClient("t").post("/a", {})
    assert r["auth"] == "Bearer t"


def test_put_is_authorized():
    r = AuthClient("t").put("/a", {})
    assert r["auth"] == "Bearer t"


def test_delete_returns_method():
    # NOTE: deliberately does NOT assert the auth header — the coverage hole.
    r = AuthClient("t").delete("/a")
    assert r["method"] == "DELETE"
