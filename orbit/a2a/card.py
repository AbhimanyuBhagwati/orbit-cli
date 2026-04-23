from __future__ import annotations

from typing import Any

from orbit import __version__


def build_agent_card(base_url: str) -> dict[str, Any]:
    """Return the A2A agent card served at /.well-known/agent.json.

    See https://a2aproject.github.io/A2A/specification/#agent-card
    """
    return {
        "name": "orbit-data-agent",
        "description": (
            "Orbit's local-first data intelligence agent. Profiles files and "
            "database tables, detects PII, scores data quality, and builds "
            "catalogs across saved connections."
        ),
        "version": __version__,
        "protocolVersion": "0.2.0",
        "url": base_url.rstrip("/") + "/",
        "provider": {
            "organization": "orbit-cli",
            "url": "https://github.com/AbhimanyuBhagwati/orbit-cli",
        },
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": False,
        },
        "defaultInputModes": ["text/plain", "application/json"],
        "defaultOutputModes": ["application/json", "text/plain"],
        "skills": [
            {
                "id": "profile-file",
                "name": "Profile a data file",
                "description": (
                    "Profile a CSV, Parquet, or JSON file — column stats, "
                    "PII detection, quality score."
                ),
                "tags": ["data", "profiling", "pii", "quality"],
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
                "examples": [
                    '{"skill": "profile-file", "path": "/data/users.csv"}',
                ],
            },
            {
                "id": "scan-catalog",
                "name": "Scan all connections",
                "description": (
                    "Scan every saved connection and return a catalog of "
                    "tables plus similar-column suggestions."
                ),
                "tags": ["data", "catalog", "discovery"],
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
                "examples": ['{"skill": "scan-catalog"}'],
            },
            {
                "id": "list-connections",
                "name": "List saved connections",
                "description": "List names of saved data connections.",
                "tags": ["data", "connections"],
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
                "examples": ['{"skill": "list-connections"}'],
            },
        ],
    }
