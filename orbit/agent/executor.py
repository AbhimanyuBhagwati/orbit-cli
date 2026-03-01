from __future__ import annotations

import asyncio
import subprocess
import time

from orbit.schemas.execution import CommandResult
from orbit.schemas.plan import PlanStep
from orbit.ui.console import console


async def run(step: PlanStep, stream: bool = True) -> CommandResult:
    """Execute a command with streaming output and timeout."""
    start = time.monotonic()

    try:
        if stream:
            return await _run_streaming(step, start)
        else:
            return await _run_simple(step, start)
    except TimeoutError:
        duration = time.monotonic() - start
        return CommandResult(
            command=step.command,
            exit_code=-1,
            stdout="",
            stderr=f"Command timed out after {step.timeout_seconds}s",
            duration_seconds=duration,
            timed_out=True,
        )


async def _run_streaming(step: PlanStep, start: float) -> CommandResult:
    """Run with streaming stdout to terminal."""
    proc = await asyncio.create_subprocess_shell(
        step.command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    async def read_stream(stream: asyncio.StreamReader | None, lines: list[str], display: bool) -> None:
        if stream is None:
            return
        while True:
            line = await stream.readline()
            if not line:
                break
            decoded = line.decode("utf-8", errors="replace")
            lines.append(decoded)
            if display:
                console.print(f"  [dim]{decoded.rstrip()}[/]")

    try:
        await asyncio.wait_for(
            asyncio.gather(
                read_stream(proc.stdout, stdout_lines, True),
                read_stream(proc.stderr, stderr_lines, False),
                proc.wait(),
            ),
            timeout=step.timeout_seconds,
        )
    except TimeoutError:
        proc.kill()
        raise

    duration = time.monotonic() - start
    return CommandResult(
        command=step.command,
        exit_code=proc.returncode if proc.returncode is not None else -1,
        stdout="".join(stdout_lines),
        stderr="".join(stderr_lines),
        duration_seconds=duration,
    )


async def _run_simple(step: PlanStep, start: float) -> CommandResult:
    """Run without streaming, capture all output."""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: subprocess.run(
            step.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=step.timeout_seconds,
        ),
    )
    duration = time.monotonic() - start
    return CommandResult(
        command=step.command,
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        duration_seconds=duration,
    )
