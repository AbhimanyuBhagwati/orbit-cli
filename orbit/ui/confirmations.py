from __future__ import annotations

import time
from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from orbit.ui.console import console

if TYPE_CHECKING:
    from orbit.schemas.plan import PlanStep
    from orbit.schemas.safety import RiskAssessment


def confirm_step(step: PlanStep, risk: RiskAssessment) -> bool:
    """Dispatch confirmation based on risk tier.

    Returns True if the user approves execution, False otherwise.
    """
    if risk.tier == "safe":
        return _confirm_safe(step, risk)
    elif risk.tier == "caution":
        return _confirm_caution(step, risk)
    elif risk.tier == "destructive":
        return _confirm_destructive(step, risk)
    elif risk.tier == "nuclear":
        return _confirm_nuclear(step, risk)
    # Unknown tier — treat as destructive
    return _confirm_destructive(step, risk)


def _confirm_safe(step: PlanStep, risk: RiskAssessment) -> bool:
    """Safe commands execute silently."""
    return True


def _confirm_caution(step: PlanStep, risk: RiskAssessment) -> bool:
    """Single confirmation for caution-level commands."""
    console.print(f"  [orbit.command]{step.command}[/]")
    console.print(f"  [orbit.warning]{risk.description}[/]")
    return Confirm.ask("  Proceed?", default=True)


def _confirm_destructive(step: PlanStep, risk: RiskAssessment) -> bool:
    """Impact analysis + double confirmation for destructive commands."""
    console.print(
        Panel(
            f"[orbit.command]{step.command}[/]\n\n{risk.description}",
            title="[orbit.error]Destructive Command[/]",
            border_style="orbit.error",
        )
    )
    if step.rollback_command:
        console.print(f"  [dim]Rollback: {step.rollback_command}[/]")

    first = Confirm.ask("  Do you understand the impact?", default=False)
    if not first:
        return False
    return Confirm.ask("  Confirm execution?", default=False)


def _confirm_nuclear(step: PlanStep, risk: RiskAssessment) -> bool:
    """Type 'i am sure' + 3s cooldown for nuclear commands."""
    prod_label = " [bold red](PRODUCTION)[/]" if risk.is_production else ""
    console.print(
        Panel(
            f"[orbit.command]{step.command}[/]{prod_label}\n\n{risk.description}",
            title="[bold red on white] NUCLEAR COMMAND [/]",
            border_style="red",
        )
    )
    if step.rollback_command:
        console.print(f"  [dim]Rollback: {step.rollback_command}[/]")

    response = Prompt.ask('  Type [bold]"i am sure"[/] to proceed')
    if response.strip().lower() != "i am sure":
        console.print("  [orbit.error]Aborted.[/]")
        return False

    console.print("  [dim]3 second cooldown...[/]")
    time.sleep(3)
    return True
