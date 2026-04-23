from __future__ import annotations

import pytest

starlette = pytest.importorskip("starlette")
from starlette.testclient import TestClient  # noqa: E402

from orbit.a2a import build_agent_card, create_app  # noqa: E402


def test_agent_card_shape() -> None:
    card = build_agent_card("http://localhost:8000")
    assert card["name"] == "orbit-data-agent"
    assert card["url"] == "http://localhost:8000/"
    assert card["protocolVersion"] == "0.2.0"
    skill_ids = {s["id"] for s in card["skills"]}
    assert {"profile-file", "scan-catalog", "list-connections"} <= skill_ids


def test_well_known_endpoint() -> None:
    client = TestClient(create_app("http://localhost:8000"))
    response = client.get("/.well-known/agent.json")
    assert response.status_code == 200
    assert response.json()["name"] == "orbit-data-agent"


def test_message_send_list_connections() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "message/send",
            "params": {
                "message": {
                    "parts": [{"kind": "data", "data": {"skill": "list-connections"}}]
                }
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    task = body["result"]
    assert task["status"]["state"] == "completed"
    assert task["artifacts"][0]["parts"][0]["data"] == {"connections": []}


def test_tasks_get_round_trip() -> None:
    client = TestClient(create_app())
    send = client.post(
        "/",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "message/send",
            "params": {
                "message": {"parts": [{"kind": "data", "data": {"skill": "list-connections"}}]}
            },
        },
    ).json()
    task_id = send["result"]["id"]

    got = client.post(
        "/",
        json={"jsonrpc": "2.0", "id": 2, "method": "tasks/get", "params": {"id": task_id}},
    ).json()
    assert got["result"]["id"] == task_id
    assert got["result"]["status"]["state"] == "completed"


def test_unknown_method_returns_jsonrpc_error() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/", json={"jsonrpc": "2.0", "id": 1, "method": "does/not/exist", "params": {}}
    )
    body = response.json()
    assert body["error"]["code"] == -32601


def test_unknown_skill_returns_failed_task() -> None:
    client = TestClient(create_app())
    body = client.post(
        "/",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "message/send",
            "params": {
                "message": {"parts": [{"kind": "data", "data": {"skill": "not-a-skill"}}]}
            },
        },
    ).json()
    task = body["result"]
    assert task["status"]["state"] == "completed"
    part = task["artifacts"][0]["parts"][0]
    assert "unknown skill" in part["text"]
