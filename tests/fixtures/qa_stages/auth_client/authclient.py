"""Tiny auth client — the ST-05 mutation-gate fixture (WS2 B6).

Four verbs each set an ``Authorization`` header. The companion test pins the
header on three of them and DELIBERATELY leaves ``delete`` unpinned — so the
strip-auth-header mutation of the delete verb survives its own suite, exactly
reproducing the study-tutor retro's "auth-header pins missing on four verbs".
"""


class AuthClient:
    def __init__(self, token: str) -> None:
        self.token = token

    def get(self, path: str) -> dict:
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        return {"method": "GET", "path": path, "auth": headers.get("Authorization")}

    def post(self, path: str, body: dict) -> dict:
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        return {"method": "POST", "path": path, "body": body, "auth": headers.get("Authorization")}

    def put(self, path: str, body: dict) -> dict:
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        return {"method": "PUT", "path": path, "body": body, "auth": headers.get("Authorization")}

    def delete(self, path: str) -> dict:
        headers = {"Authorization": f"Bearer {self.token}"}
        return {"method": "DELETE", "path": path, "auth": headers.get("Authorization")}
