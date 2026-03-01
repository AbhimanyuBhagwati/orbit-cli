from __future__ import annotations

from orbit.safety.patterns import PATTERNS, PRODUCTION_PATTERNS
from orbit.schemas.context import EnvironmentState
from orbit.schemas.safety import RiskAssessment


def is_production_context(env_state: EnvironmentState) -> bool:
    """Check git branch, k8s namespace/context for production indicators."""
    checks = [env_state.git_branch or "", env_state.k8s_namespace or "", env_state.k8s_context or ""]
    return any(p.search(c) for p in PRODUCTION_PATTERNS for c in checks if c)


def classify(command: str, env_state: EnvironmentState | None = None) -> RiskAssessment:
    """Classify a command's risk tier. Regex-only, NO LLM calls.

    Unrecognized commands default to 'caution', never 'safe'.
    Production context escalates production_escalate patterns to 'nuclear'.
    """
    if env_state is None:
        env_state = EnvironmentState()

    is_prod = is_production_context(env_state)
    cmd_stripped = command.strip()

    for rp in PATTERNS:
        if rp.pattern.search(cmd_stripped):
            tier = rp.tier
            if is_prod and rp.production_escalate and tier != "nuclear":
                tier = "nuclear"
            return RiskAssessment(
                command=command,
                tier=tier,
                description=rp.description,
                is_production=is_prod,
            )

    # DEFAULT: unrecognized commands → caution, never safe
    return RiskAssessment(
        command=command,
        tier="caution",
        description="unrecognized command",
        is_production=is_prod,
    )
