"""Small local API client used by the TUI and integration checks."""

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class Client:
    def __init__(self, origin):
        self.origin = origin
        self.info = self.get("/api/info")

    def request(self, path, payload=None, *, refreshed=False):
        headers = {}
        if payload is not None:
            headers = {"Content-Type": "application/json", "X-Hallmark-Token": self.info["token"]}
        request = Request(
            self.origin + path,
            headers=headers,
            data=json.dumps(payload).encode() if payload is not None else None,
        )
        try:
            with urlopen(request, timeout=15) as response:
                return json.load(response)
        except HTTPError as error:
            message = json.load(error).get("error", f"HTTP {error.code}")
            if error.code == 403 and payload is not None and not refreshed:
                updated = self.get("/api/info")
                if updated.get("root") != self.info.get("root"):
                    raise ValueError(
                        "Controller checkout changed; reconnect to the correct workbench"
                    ) from None
                if updated["token"] != self.info["token"]:
                    self.info = updated
                    return self.request(path, payload, refreshed=True)
            raise ValueError(message) from None

    def get(self, path):
        return self.request(path)

    def start(self, workflow, parameters):
        return self.request("/api/runs", dict(workflow=workflow, parameters=parameters))

    def cancel(self, key):
        return self.request(f"/api/runs/{key}/cancel", {})
