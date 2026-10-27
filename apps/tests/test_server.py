import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from hallmark_demo.client import Client
from hallmark_demo.server import DemoServer


@pytest.fixture
def server(root):
    instance = DemoServer(root, 0)
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    yield instance
    instance.shutdown()
    instance.server_close()
    thread.join(2)


def request(server, path, headers=None, body=None):
    return urlopen(Request(server.origin + path, headers=headers or {}, data=body), timeout=5)


def test_host_origin_and_mutation_token(server):
    client = Client(server.origin)
    assert len(client.info["token"]) > 20
    for headers in ({"Host": "evil.example"}, {"Origin": "https://evil.example"}):
        with pytest.raises(HTTPError) as error:
            request(server, "/api/info", headers)
        assert error.value.code == 403
    with pytest.raises(HTTPError) as error:
        request(server, "/api/runs", {"Content-Type": "application/json"}, b"{}")
    assert error.value.code == 403
    with pytest.raises(HTTPError) as error:
        request(
            server,
            "/api/runs",
            {"Content-Type": "application/json", "X-Hallmark-Token": client.info["token"]},
            b'{"command":"sh"}',
        )
    assert error.value.code == 400


def test_static_paths_and_artifact_ids_do_not_expose_files(server):
    for path in ("/.env", "/../../.env", "/api/runs/../artifacts/0", "/static/../pyproject.toml"):
        with pytest.raises(HTTPError) as error:
            request(server, path)
        assert error.value.code == 404
    with request(server, "/") as response:
        assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
        assert b"Proof workbench" in response.read()
    with request(server, "/app.js") as response:
        assert response.headers["Content-Type"].startswith("text/javascript")


def test_client_refreshes_only_explicitly_rejected_session_tokens(server):
    client = Client(server.origin)
    server.token = "rotated-local-token-for-test"
    with pytest.raises(ValueError, match="Not found"):
        client.cancel("unknown")
    assert client.info["token"] == server.token
    assert server.manager.list() == []


def test_duplicate_json_fields_are_rejected(server):
    client = Client(server.origin)
    headers = {"Content-Type": "application/json", "X-Hallmark-Token": client.info["token"]}
    with pytest.raises(HTTPError) as error:
        request(server, "/api/runs", headers, b'{"workflow":"a","workflow":"b","parameters":{}}')
    assert error.value.code == 400
