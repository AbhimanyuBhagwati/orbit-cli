"""Benchmark tests for the executor — real subprocess execution."""

from __future__ import annotations

import pytest

from orbit.agent.executor import run
from orbit.schemas.plan import PlanStep


def _step(cmd: str, timeout: int = 30, expected_exit_code: int = 0) -> PlanStep:
    return PlanStep(
        description=f"Run: {cmd}",
        command=cmd,
        risk_level="safe",
        timeout_seconds=timeout,
        expected_exit_code=expected_exit_code,
    )


@pytest.mark.asyncio
async def test_simple_command_success() -> None:
    result = await run(_step("echo hello"), stream=False)
    assert result.exit_code == 0
    assert "hello" in result.stdout


@pytest.mark.asyncio
async def test_command_captures_stderr() -> None:
    result = await run(_step("bash -c 'echo error >&2; exit 1'", expected_exit_code=1), stream=False)
    assert result.exit_code == 1
    assert "error" in result.stderr


@pytest.mark.asyncio
async def test_command_timeout_kills_process() -> None:
    result = await run(_step("sleep 60", timeout=1), stream=True)
    assert result.timed_out is True
    assert result.exit_code == -1


@pytest.mark.asyncio
async def test_streaming_mode_produces_result() -> None:
    result = await run(_step("echo streaming"), stream=True)
    assert result.exit_code == 0
    assert "streaming" in result.stdout


@pytest.mark.asyncio
async def test_duration_is_measured() -> None:
    result = await run(_step("sleep 0.1"), stream=False)
    assert result.duration_seconds >= 0.05


@pytest.mark.asyncio
async def test_multiline_output() -> None:
    result = await run(_step("printf 'line1\\nline2\\nline3'"), stream=False)
    assert result.exit_code == 0
    assert result.stdout.count("\n") >= 2 or "line3" in result.stdout


@pytest.mark.asyncio
async def test_empty_output_command() -> None:
    result = await run(_step("true"), stream=False)
    assert result.exit_code == 0
    assert result.stdout == ""


@pytest.mark.asyncio
async def test_streaming_timeout() -> None:
    result = await run(_step("sleep 60", timeout=1), stream=True)
    assert result.timed_out is True
    assert result.exit_code == -1
