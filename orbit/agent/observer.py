from __future__ import annotations

import re
from dataclasses import dataclass

from orbit.agent.budget import Budget
from orbit.schemas.execution import CommandResult
from orbit.schemas.plan import PlanStep


@dataclass
class ObserverDecision:
    """Decision from the observer about how to proceed."""

    status: str  # "success", "replan", "fatal"
    analysis: str
    suggested_fix: str | None = None


def analyze(step: PlanStep, result: CommandResult, budget: Budget) -> ObserverDecision:
    """Analyze a step result and decide: success / replan / fatal. Deterministic, no LLM."""
    if result.timed_out:
        return ObserverDecision("fatal", f"Command timed out after {step.timeout_seconds}s: {step.command}")

    if result.exit_code == step.expected_exit_code:
        if step.expected_output_pattern:
            if re.search(step.expected_output_pattern, result.stdout):
                return ObserverDecision("success", "Command succeeded with expected output.")
            return ObserverDecision(
                "success",
                f"Command succeeded (exit 0) but output did not match pattern '{step.expected_output_pattern}'.",
            )
        return ObserverDecision("success", "Command succeeded.")

    error_summary = (result.stderr[:500] if result.stderr else result.stdout[:500]) or "(no output)"
    if budget.can_replan():
        return ObserverDecision("replan", f"Command failed (exit {result.exit_code}): {error_summary}")

    msg = f"Command failed (exit {result.exit_code}), replan budget exhausted: {error_summary}"
    return ObserverDecision("fatal", msg)
