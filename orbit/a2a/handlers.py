from __future__ import annotations

import json
import uuid
from typing import Any


def _extract_request(parts: list[dict[str, Any]]) -> dict[str, Any]:
    """Pull a skill-call payload out of an A2A message's parts."""
    for part in parts:
        kind = part.get("kind") or part.get("type")
        if kind == "data" and isinstance(part.get("data"), dict):
            return part["data"]
        if kind == "text" and isinstance(part.get("text"), str):
            text = part["text"].strip()
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return {"skill": "scan-catalog", "query": text}
    return {}


def _text_part(text: str) -> dict[str, Any]:
    return {"kind": "text", "text": text}


def _data_part(payload: Any) -> dict[str, Any]:
    return {"kind": "data", "data": payload}


def invoke_skill(request: dict[str, Any]) -> list[dict[str, Any]]:
    """Dispatch an A2A skill request to the data agent."""
    skill = request.get("skill") or "scan-catalog"

    if skill == "profile-file":
        from orbit.agents.data.agent import profile_file

        path = request.get("path")
        if not path:
            return [_text_part("error: 'path' is required for profile-file")]
        sample_limit = int(request.get("sample_limit", 10000))
        result = profile_file(path, sample_limit=sample_limit)
        return [_data_part(result.model_dump(mode="json"))]

    if skill == "scan-catalog":
        from orbit.agents.data.agent import scan_all

        catalog = scan_all()
        return [_data_part(catalog.model_dump(mode="json"))]

    if skill == "list-connections":
        from orbit.agents.data.connections import list_connections

        return [_data_part({"connections": list_connections()})]

    return [_text_part(f"error: unknown skill '{skill}'")]


def handle_message_send(params: dict[str, Any], tasks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Handle A2A `message/send` — run the skill synchronously and return a Task."""
    message = params.get("message", {}) or {}
    parts = message.get("parts", []) or []
    request = _extract_request(parts)

    task_id = str(uuid.uuid4())
    context_id = message.get("contextId") or str(uuid.uuid4())

    try:
        reply_parts = invoke_skill(request)
        status = "completed"
        error = None
    except Exception as exc:  # noqa: BLE001 — surface any skill failure to the caller
        reply_parts = [_text_part(f"error: {exc}")]
        status = "failed"
        error = str(exc)

    task: dict[str, Any] = {
        "id": task_id,
        "contextId": context_id,
        "kind": "task",
        "status": {"state": status},
        "artifacts": [
            {
                "artifactId": str(uuid.uuid4()),
                "name": "result",
                "parts": reply_parts,
            }
        ],
        "history": [message] if message else [],
    }
    if error:
        task["status"]["message"] = {"role": "agent", "parts": [_text_part(error)]}

    tasks[task_id] = task
    return task


def handle_tasks_get(params: dict[str, Any], tasks: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    task_id = params.get("id")
    if not task_id:
        return None
    return tasks.get(task_id)
