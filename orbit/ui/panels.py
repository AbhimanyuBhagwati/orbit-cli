from __future__ import annotations

from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.table import Table

from orbit.ui.console import console

if TYPE_CHECKING:
    from orbit.config import OrbitConfig
    from orbit.schemas.context import EnvironmentState
    from orbit.schemas.execution import CommandResult
    from orbit.schemas.plan import Plan, PlanStep


def show_plan(plan: Plan) -> None:
    """Display a plan with all steps in a Rich panel."""
    table = Table(show_header=True, header_style="orbit.blue", expand=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Step", style="bold")
    table.add_column("Command", style="orbit.command")
    table.add_column("Risk", width=12)

    for i, step in enumerate(plan.steps, 1):
        risk_style = f"orbit.risk.{step.risk_level}"
        table.add_row(str(i), step.description, step.command, f"[{risk_style}]{step.risk_level}[/]")

    console.print(Panel(table, title=f"[orbit.blue]Plan: {plan.goal}[/]", border_style="orbit.blue"))


def show_step_success(step: PlanStep, result: CommandResult) -> None:
    """Show a successful step result."""
    console.print(f"  [orbit.success]✓[/] {step.description} [dim]({result.duration_seconds:.1f}s)[/]")


def show_replan(reason: str) -> None:
    """Show a replan notification."""
    console.print(Panel(reason, title="[orbit.warning]Replanning[/]", border_style="orbit.warning"))


def show_fatal(message: str) -> None:
    """Show a fatal error."""
    console.print(Panel(message, title="[orbit.error]Fatal Error[/]", border_style="orbit.error"))


def show_summary(completed: int, total: int, duration: float) -> None:
    """Show execution summary."""
    console.print()
    console.print(
        Panel(
            f"Completed [bold]{completed}[/]/{total} steps in [bold]{duration:.1f}s[/]",
            title="[orbit.blue]Summary[/]",
            border_style="orbit.blue",
        )
    )


def show_config_table(config: OrbitConfig) -> None:
    """Display config as a Rich table."""
    table = Table(title="Orbit Configuration", show_header=True, header_style="orbit.blue")
    table.add_column("Key", style="bold")
    table.add_column("Value")

    for key in type(config).model_fields:
        value = getattr(config, key)
        table.add_row(key, str(value))

    console.print(table)


def show_doctor_result(results: list[tuple[str, bool, str]]) -> None:
    """Display doctor check results."""
    table = Table(title="Orbit Doctor", show_header=True, header_style="orbit.blue")
    table.add_column("Check", style="bold")
    table.add_column("Status", width=8)
    table.add_column("Details")

    for name, passed, detail in results:
        status = "[orbit.success]✓ OK[/]" if passed else "[orbit.error]✗ FAIL[/]"
        table.add_row(name, status, detail)

    console.print(table)


def show_environment(env: EnvironmentState) -> None:
    """Display environment state as a Rich tree."""
    from rich.tree import Tree

    tree = Tree("[orbit.blue]Environment[/]")

    for slot in env.slots:
        if not slot.available:
            continue
        branch = tree.add(
            f"[bold]{slot.source}[/] [dim](~{slot.estimated_tokens} tokens, relevance: {slot.relevance:.1f})[/]"
        )
        lines = slot.content.splitlines()
        for line in lines[:15]:
            branch.add(f"[dim]{line}[/]")
        if len(lines) > 15:
            branch.add("[dim]...(truncated)[/]")

    if env.git_branch:
        tree.add(f"[orbit.info]Git branch:[/] {env.git_branch}")
    if env.k8s_context:
        tree.add(f"[orbit.info]K8s context:[/] {env.k8s_context}")
    if env.k8s_namespace:
        tree.add(f"[orbit.info]K8s namespace:[/] {env.k8s_namespace}")
