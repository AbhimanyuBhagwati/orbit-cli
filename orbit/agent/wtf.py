from __future__ import annotations

import os

from orbit.config import get_config
from orbit.llm.base import LLMValidationError
from orbit.llm.ollama_provider import OllamaProvider
from orbit.modules.registry import get_all_modules, load_builtin_modules
from orbit.schemas.analysis import WtfAnalysis
from orbit.ui.console import console

WTF_SYSTEM_PROMPT = """You are a DevOps error diagnostician. Given a failed command and its output,
explain the error, identify the root cause, and suggest a fix command.

Be specific and actionable. If you're not confident, say so.
Respond ONLY as JSON matching the provided schema."""


async def diagnose() -> None:
    """Diagnose the last failed command."""
    load_builtin_modules()

    # Try to get last command from environment
    last_cmd = os.environ.get("ORBIT_LAST_COMMAND")
    last_stderr = os.environ.get("ORBIT_LAST_STDERR", "")
    last_stdout = os.environ.get("ORBIT_LAST_STDOUT", "")
    last_exit = os.environ.get("ORBIT_LAST_EXIT_CODE", "")

    if not last_cmd:
        # Try history
        try:
            from orbit.memory.history import get_last_failed

            failed = get_last_failed()
            if failed:
                last_cmd = failed["command"]
                last_stderr = failed.get("stderr", "")
                last_stdout = failed.get("stdout", "")
                last_exit = str(failed.get("exit_code", ""))
        except Exception:
            pass

    if not last_cmd:
        console.print("[orbit.warning]No failed command found. Run a command first, then try orbit wtf.[/]")
        return

    console.print(f"[orbit.blue]Diagnosing:[/] {last_cmd}")

    # Fast path: check module failure patterns
    for module in get_all_modules():
        for pattern, explanation in module.get_common_failures().items():
            if pattern in last_stderr or pattern in last_stdout:
                console.print()
                from rich.panel import Panel

                console.print(
                    Panel(
                        f"[orbit.error]Error:[/] {pattern}\n\n[orbit.warning]Explanation:[/] {explanation}",
                        title=f"[orbit.blue]{module.name} module[/]",
                        border_style="orbit.blue",
                    )
                )
                return

    # Slow path: LLM diagnosis
    config = get_config()
    provider = OllamaProvider(host=config.ollama_host, port=config.ollama_port)

    error_context = (
        f"Command: {last_cmd}\nExit code: {last_exit}\nStderr: {last_stderr[:1000]}\nStdout: {last_stdout[:1000]}"
    )

    messages = [
        {"role": "system", "content": WTF_SYSTEM_PROMPT},
        {"role": "user", "content": error_context},
    ]

    try:
        result = await provider.achat(
            model=config.default_model, messages=messages, schema=WtfAnalysis, temperature=0.0
        )
        if isinstance(result, WtfAnalysis):
            _display_analysis(result)
    except (LLMValidationError, Exception) as e:
        console.print(f"[orbit.error]Could not diagnose: {e}[/]")


def _display_analysis(analysis: WtfAnalysis) -> None:
    from rich.panel import Panel

    parts = [
        f"[orbit.error]Error:[/] {analysis.error_explanation}",
        f"[orbit.warning]Root cause:[/] {analysis.root_cause}",
        f"[dim]Confidence: {analysis.confidence:.0%}[/]",
    ]
    if analysis.fix_command:
        parts.append(f"\n[orbit.success]Fix:[/] [orbit.command]{analysis.fix_command}[/]")
        parts.append(f"[dim]{analysis.fix_explanation}[/]")

    console.print()
    console.print(Panel("\n".join(parts), title="[orbit.blue]Diagnosis[/]", border_style="orbit.blue"))
