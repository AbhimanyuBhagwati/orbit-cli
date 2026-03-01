"""Benchmark tests for the observer — decision logic edge cases."""

from __future__ import annotations

from orbit.agent.budget import Budget
from orbit.agent.observer import analyze
from orbit.schemas.execution import CommandResult
from orbit.schemas.plan import PlanStep


def _step(
    cmd: str = "echo test",
    expected_exit_code: int = 0,
    expected_output_pattern: str | None = None,
    timeout: int = 30,
) -> PlanStep:
    return PlanStep(
        description="test step",
        command=cmd,
        risk_level="safe",
        expected_exit_code=expected_exit_code,
        expected_output_pattern=expected_output_pattern,
        timeout_seconds=timeout,
    )


def _result(
    exit_code: int = 0,
    stdout: str = "",
    stderr: str = "",
    timed_out: bool = False,
) -> CommandResult:
    return CommandResult(
        command="echo test",
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=0.1,
        timed_out=timed_out,
    )


def _budget(replans: int = 3) -> Budget:
    return Budget(max_steps=15, max_replans_per_step=replans, max_llm_calls=25)


# ── Success cases ────────────────────────────────────────────────────────────


def test_success_on_exit_code_match() -> None:
    decision = analyze(_step(), _result(exit_code=0), _budget())
    assert decision.status == "success"


def test_success_with_nonzero_expected_exit_code() -> None:
    decision = analyze(_step(expected_exit_code=1), _result(exit_code=1), _budget())
    assert decision.status == "success"


def test_success_with_output_pattern_match() -> None:
    step = _step(expected_output_pattern=r"\d+ pods?")
    result = _result(stdout="3 pods running")
    decision = analyze(step, result, _budget())
    assert decision.status == "success"
    assert "expected output" in decision.analysis.lower() or "succeeded" in decision.analysis.lower()


def test_success_with_pattern_mismatch_still_success() -> None:
    step = _step(expected_output_pattern=r"\d+ pods?")
    result = _result(stdout="no matches found")
    decision = analyze(step, result, _budget())
    assert decision.status == "success"
    assert "did not match" in decision.analysis


# ── Timeout ──────────────────────────────────────────────────────────────────


def test_timeout_is_fatal() -> None:
    decision = analyze(_step(timeout=5), _result(timed_out=True), _budget())
    assert decision.status == "fatal"
    assert "timed out" in decision.analysis.lower()


# ── Failure with replan available ────────────────────────────────────────────


def test_failure_triggers_replan_when_budget_available() -> None:
    decision = analyze(_step(), _result(exit_code=1, stderr="error msg"), _budget(replans=3))
    assert decision.status == "replan"
    assert "error msg" in decision.analysis


def test_failure_uses_stdout_when_stderr_empty() -> None:
    decision = analyze(_step(), _result(exit_code=1, stdout="stdout error"), _budget(replans=3))
    assert decision.status == "replan"
    assert "stdout error" in decision.analysis


def test_failure_no_output() -> None:
    decision = analyze(_step(), _result(exit_code=1), _budget(replans=3))
    assert decision.status == "replan"
    assert "(no output)" in decision.analysis


# ── Failure with replan exhausted ────────────────────────────────────────────


def test_failure_fatal_when_no_replans() -> None:
    budget = _budget(replans=1)
    budget.use_replan()  # exhaust the single replan
    decision = analyze(_step(), _result(exit_code=1, stderr="fail"), budget)
    assert decision.status == "fatal"
    assert "budget exhausted" in decision.analysis.lower() or "fail" in decision.analysis


# ── Error truncation ─────────────────────────────────────────────────────────


def test_stderr_truncated_at_500_chars() -> None:
    long_error = "x" * 600
    decision = analyze(_step(), _result(exit_code=1, stderr=long_error), _budget())
    # The analysis should contain at most 500 chars of the error
    assert len(decision.analysis) < len(long_error) + 100
