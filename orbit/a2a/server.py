from __future__ import annotations

from typing import Any

from orbit.a2a.card import build_agent_card
from orbit.a2a.handlers import handle_message_send, handle_tasks_get


def _jsonrpc_error(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _jsonrpc_result(req_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def create_app(base_url: str = "http://localhost:8000") -> Any:
    """Build the Starlette ASGI app that serves the A2A protocol.

    Routes:
      GET  /.well-known/agent.json — agent card
      POST /                        — JSON-RPC 2.0 (message/send, tasks/get)
    """
    try:
        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.responses import JSONResponse
        from starlette.routing import Route
    except ImportError as exc:
        msg = (
            "A2A server requires starlette and uvicorn. Install with: "
            'pip install "orbit-cli[a2a]"'
        )
        raise ImportError(msg) from exc

    tasks: dict[str, dict[str, Any]] = {}
    agent_card = build_agent_card(base_url)

    async def agent_card_route(_request: Request) -> JSONResponse:
        return JSONResponse(agent_card)

    async def jsonrpc_route(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(_jsonrpc_error(None, -32700, "Parse error"), status_code=400)

        req_id = body.get("id")
        method = body.get("method")
        params = body.get("params") or {}

        if method == "message/send":
            task = handle_message_send(params, tasks)
            return JSONResponse(_jsonrpc_result(req_id, task))

        if method == "tasks/get":
            task = handle_tasks_get(params, tasks)
            if task is None:
                return JSONResponse(_jsonrpc_error(req_id, -32001, "Task not found"))
            return JSONResponse(_jsonrpc_result(req_id, task))

        return JSONResponse(_jsonrpc_error(req_id, -32601, f"Method not found: {method}"))

    return Starlette(
        routes=[
            Route("/.well-known/agent.json", agent_card_route, methods=["GET"]),
            Route("/", jsonrpc_route, methods=["POST"]),
        ]
    )
