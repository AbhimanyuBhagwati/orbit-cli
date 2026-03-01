"""Tests for agent budget enforcement."""

from __future__ import annotations

import pytest

from orbit.agent.budget import Budget, BudgetExhaustedError


def test_step_budget():
    b = Budget(max_steps=2)
    b.use_step()
    b.use_step()
    with pytest.raises(BudgetExhaustedError, match="steps"):
        b.use_step()


def test_replan_budget():
    b = Budget(max_replans_per_step=2)
    b.use_step()
    b.use_replan()
    b.use_replan()
    with pytest.raises(BudgetExhaustedError, match="replans_per_step"):
        b.use_replan()


def test_replan_resets_per_step():
    b = Budget(max_replans_per_step=1)
    b.use_step()
    b.use_replan()  # uses 1
    b.use_step()  # new step resets replan counter
    b.use_replan()  # should be fine now


def test_llm_call_budget():
    b = Budget(max_llm_calls=3)
    b.use_llm_call()
    b.use_llm_call()
    b.use_llm_call()
    with pytest.raises(BudgetExhaustedError, match="llm_calls"):
        b.use_llm_call()


def test_can_replan():
    b = Budget(max_replans_per_step=2, max_llm_calls=10)
    b.use_step()
    assert b.can_replan()
    b.use_replan()
    b.use_replan()
    assert not b.can_replan()


def test_usage():
    b = Budget(max_steps=10, max_llm_calls=25)
    b.use_step()
    b.use_llm_call()
    b.use_llm_call()
    usage = b.usage()
    assert usage["steps"] == 1
    assert usage["llm_calls"] == 2
    assert usage["max_steps"] == 10
    assert usage["max_llm_calls"] == 25


def test_budget_exhausted_exception_info():
    with pytest.raises(BudgetExhaustedError) as exc_info:
        b = Budget(max_steps=1)
        b.use_step()
        b.use_step()
    assert exc_info.value.resource == "steps"
    assert exc_info.value.used == 2
    assert exc_info.value.limit == 1
