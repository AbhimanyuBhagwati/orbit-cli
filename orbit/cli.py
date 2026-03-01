from __future__ import annotations

import typer

from orbit import __version__
from orbit.ui.console import console

app = typer.Typer(
    name="orbit",
    help="Orbit — local-first, multi-model DevOps CLI agent.",
    no_args_is_help=True,
)

config_app = typer.Typer(help="Manage Orbit configuration.")
runbook_app = typer.Typer(help="Manage runbooks.")
history_app = typer.Typer(help="Command history.")
module_app = typer.Typer(help="Manage modules.")

app.add_typer(config_app, name="config")
app.add_typer(runbook_app, name="runbook")
app.add_typer(history_app, name="history")
app.add_typer(module_app, name="module")


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"orbit {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", help="Show version.", callback=_version_callback, is_eager=True
    ),
) -> None:
    """Orbit — local-first, multi-model DevOps CLI agent."""


# ── Config commands ──────────────────────────────────────────────────────────


@config_app.command("show")
def config_show() -> None:
    """Show current configuration."""
    from orbit.config import get_config
    from orbit.ui.panels import show_config_table

    show_config_table(get_config())


@config_app.command("set")
def config_set(
    key: str = typer.Argument(help="Config key to set"),
    value: str = typer.Argument(help="Value to set"),
) -> None:
    """Set a configuration value."""
    from orbit.config import OrbitConfig, write_config

    if key not in OrbitConfig.model_fields:
        console.print(f"[orbit.error]Unknown config key: {key}[/]")
        raise typer.Exit(code=1)

    write_config(key, value)
    console.print(f"[orbit.success]Set {key} = {value}[/]")


@config_app.command("doctor")
def config_doctor() -> None:
    """Run health checks."""
    from orbit.config import doctor, get_config
    from orbit.ui.panels import show_doctor_result

    results = doctor(get_config())
    show_doctor_result(results)

    if not all(passed for _, passed, _ in results):
        raise typer.Exit(code=1)


# ── Stub commands ────────────────────────────────────────────────────────────


@app.command("do")
def do_command(
    goal: str = typer.Argument(help="What you want Orbit to do"),
) -> None:
    """Execute a goal using the agent loop."""
    import asyncio

    from orbit.agent.loop import run

    try:
        asyncio.run(run(goal))
    except KeyboardInterrupt:
        console.print("\n[orbit.warning]Aborted.[/]")
        raise typer.Exit(code=130) from None


@app.command("wtf")
def wtf_command() -> None:
    """Diagnose the last failed command."""
    import asyncio

    from orbit.agent.wtf import diagnose

    asyncio.run(diagnose())


@app.command("ask")
def ask_command(
    question: str = typer.Argument(help="Question to ask"),
) -> None:
    """Ask a question about your environment."""
    import asyncio

    from orbit.agent.ask import ask

    asyncio.run(ask(question))


@app.command("sense")
def sense_command(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Sense the current environment."""
    import asyncio

    from orbit.context.scanner import scan
    from orbit.ui.panels import show_environment

    env = asyncio.run(scan())
    if json_output:
        console.print_json(env.model_dump_json())
    else:
        show_environment(env)


@runbook_app.command("list")
def runbook_list() -> None:
    """List saved runbooks."""
    from orbit.memory.runbooks import list_runbooks

    names = list_runbooks()
    if not names:
        console.print("[dim]No saved runbooks.[/]")
        return
    for name in names:
        console.print(f"  [orbit.blue]{name}[/]")


@runbook_app.command("show")
def runbook_show(
    name: str = typer.Argument(help="Runbook name"),
) -> None:
    """Show a runbook's details."""
    from orbit.memory.runbooks import load

    rb = load(name)
    if rb is None:
        console.print(f"[orbit.error]Runbook '{name}' not found.[/]")
        raise typer.Exit(code=1)
    console.print(f"[bold]{rb.name}[/] — {rb.description}")
    for i, step in enumerate(rb.steps, 1):
        console.print(f"  {i}. [cyan]{step.command}[/]  {step.description or ''}")


@runbook_app.command("run")
def runbook_run(
    name: str = typer.Argument(help="Runbook name to run"),
) -> None:
    """Run a saved runbook."""
    import asyncio

    from orbit.agent.executor import run as run_step
    from orbit.memory.runbooks import load
    from orbit.schemas.plan import PlanStep

    rb = load(name)
    if rb is None:
        console.print(f"[orbit.error]Runbook '{name}' not found.[/]")
        raise typer.Exit(code=1)

    console.print(f"[bold]Running runbook:[/] {rb.name}")
    for i, step in enumerate(rb.steps, 1):
        console.print(f"\n[orbit.blue]Step {i}:[/] {step.command}")
        plan_step = PlanStep(
            command=step.command,
            description=step.description or step.command,
            risk_level=step.risk_level,
            expected_exit_code=0,
        )
        result = asyncio.run(run_step(plan_step))
        if result.exit_code != 0:
            console.print(f"[orbit.error]Step {i} failed (exit {result.exit_code})[/]")
            raise typer.Exit(code=1)
    console.print("\n[orbit.success]Runbook completed successfully.[/]")


@runbook_app.command("delete")
def runbook_delete(
    name: str = typer.Argument(help="Runbook name to delete"),
) -> None:
    """Delete a saved runbook."""
    from orbit.memory.runbooks import delete

    if delete(name):
        console.print(f"[orbit.success]Deleted runbook '{name}'.[/]")
    else:
        console.print(f"[orbit.error]Runbook '{name}' not found.[/]")
        raise typer.Exit(code=1)


@history_app.command("list")
def history_list(
    query: str = typer.Option(None, "--search", "-s", help="Search term"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max results"),
) -> None:
    """List command history."""
    from orbit.memory.history import search

    rows = search(query=query, limit=limit)
    if not rows:
        console.print("[dim]No command history.[/]")
        return
    for row in rows:
        status = "[orbit.success]OK[/]" if row["exit_code"] == 0 else f"[orbit.error]exit {row['exit_code']}[/]"
        console.print(f"  {row['timestamp'][:19]}  {status}  [cyan]{row['command']}[/]")


@module_app.command("list")
def module_list() -> None:
    """List available modules."""
    from orbit.modules.registry import get_all_modules, load_builtin_modules

    load_builtin_modules()
    modules = get_all_modules()
    if not modules:
        console.print("[dim]No modules loaded.[/]")
        return
    for mod in modules:
        cmds = ", ".join(mod.commands)
        console.print(f"  [orbit.blue]{mod.name}[/] — {mod.description} ({cmds})")
