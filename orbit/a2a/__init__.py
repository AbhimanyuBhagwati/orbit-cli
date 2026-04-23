"""A2A (Agent2Agent) protocol integration for Orbit.

Exposes Orbit's data intelligence agent as an A2A-compliant server so other
agents can discover and call it over HTTP + JSON-RPC 2.0.

Spec: https://a2aproject.github.io/A2A/
"""

from orbit.a2a.card import build_agent_card
from orbit.a2a.server import create_app

__all__ = ["build_agent_card", "create_app"]
