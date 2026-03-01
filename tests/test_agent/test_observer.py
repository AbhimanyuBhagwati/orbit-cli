"""Tests for the observer (deterministic result analysis)."""

from __future__ import annotations

from orbit.agent.budget import Budget
from orbit.agent.observer import analyze
from orbit.schemas.execution import CommandResult
from orbit.schemas.plan import PlanStep


def _step(cmd: str = "ls", expected_exit: int = 0, pattern: str | None = None) -> PlanStep:
    return PlanStep(
        command=cmd,
        description="test step",
        risk_level="safe",
        expected_exit_code=expected_exit,
        expected_output_pattern=pattern,
    )


def _result(exit_code: int = 0, stdout: str = "", stderr: str = "", timed_out: bool = False) -> CommandResult:
    return CommandResult(
        command="ls",
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=0.1,
        timed_out=timed_out,
    )


def test_success_on_exit_code_match():
    decision = analyze(_step(), _result(exit_code=0), Budget())
    assert decision.status == "success"


def test_success_with_output_pattern():
    decision = analyze(
        _step(pattern=r"hello"),
        _result(stdout="hello world"),
        Budget(),
    )
    assert decision.status == "success"
    assert "expected output" in decision.analysis


def test_success_without_pattern_match():
    decision = analyze(
        _step(pattern=r"xyz"),
        _result(stdout="hello world"),
        Budget(),
    )
    assert decision.status == "success"  # still success, just notes mismatch
    assert "did not match" in decision.analysis


def test_timeout_is_fatal():
    decision = analyze(_step(), _result(timed_out=True), Budget())
    assert decision.status == "fatal"
    assert "timed out" in decision.analysis.lower()


def test_failure_with_replan_available():
    b = Budget(max_replans_per_step=3)
    b.use_step()
    decision = analyze(_step(), _result(exit_code=1, stderr="error"), b)
    assert decision.status == "replan"


def test_failure_without_replan_is_fatal():
    b = Budget(max_replans_per_step=1, max_llm_calls=2)
    b.use_step()
    b.use_replan()  # exhaust replans
    decision = analyze(_step(), _result(exit_code=1, stderr="error"), b)
    assert decision.status == "fatal"
    assert "budget exhausted" in decision.analysis.lower()
