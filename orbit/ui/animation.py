from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from rich.panel import Panel
from rich.text import Text

from orbit.ui.console import console

if TYPE_CHECKING:
    from orbit.schemas.plan import PlanStep


# ── Pipeline stages ─────────────────────────────────────────────────────────

STAGES = ["SCAN", "DECOMPOSE", "ROUTE", "PLAN", "EXECUTE"]


def show_agent_banner(goal: str) -> None:
    """Print the agent invocation banner at loop start."""
    title = Text()
    title.append("ORBIT", style="bold #4A9EFF")
    title.append(" Agent", style="dim")

    body = Text()
    body.append("Goal: ", style="bold")
    body.append(goal)

    pipeline = Text(justify="center")
    for i, stage in enumerate(STAGES):
        if i > 0:
            pipeline.append("  >  ", style="dim")
        pipeline.append(stage.lower(), style="dim")

    console.print()
    console.print(
        Panel(
            body,
            title=title,
            subtitle=pipeline,
            border_style="#4A9EFF",
            padding=(1, 2),
        )
    )
    console.print()


def print_pipeline_stage(current: str) -> None:
    """Print the pipeline progress bar with current stage highlighted."""
    line = Text()
    found_current = False

    for i, stage in enumerate(STAGES):
        if i > 0:
            sep_style = "orbit.success" if not found_current else "dim"
            line.append(" > ", style=sep_style)

        if stage == current:
            line.append(stage, style="bold orbit.blue")
            found_current = True
        elif not found_current:
            line.append(stage, style="orbit.success")
        else:
            line.append(stage, style="dim")

    console.print(line)


# ── Spinners ────────────────────────────────────────────────────────────────


@asynccontextmanager
async def stage_spinner(message: str) -> AsyncIterator[Any]:
    """Show an animated spinner while an async operation runs."""
    with console.status(f"[orbit.blue]{message}[/]", spinner="dots") as status:
        yield status


# ── Step display ────────────────────────────────────────────────────────────


def show_step_header(index: int, total: int, step: PlanStep) -> None:
    """Print step header before execution begins."""
    console.print()
    console.print(
        f"  [orbit.step]Step {index}/{total}[/]  [bold]{step.description}[/]"
    )
    console.print(f"  [orbit.command]$ {step.command}[/]")
    console.rule(style="dim")
