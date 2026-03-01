"""Tests for context budget allocation."""

from __future__ import annotations

from orbit.router.context_budget import allocate, create_budget
from orbit.schemas.context import ContextBudget, ContextSlot


def _slot(source: str, tokens: int, relevance: float) -> ContextSlot:
    return ContextSlot(
        source=source,
        relevance=relevance,
        estimated_tokens=tokens,
        content="x" * (tokens * 4),
        available=True,
    )


def test_allocate_selects_by_relevance():
    budget = ContextBudget(total_tokens=1000, available=200)
    slots = [
        _slot("git", 100, 0.9),
        _slot("docker", 100, 0.3),
        _slot("system", 100, 0.7),
    ]
    selected = allocate(slots, budget)
    sources = [s.source for s in selected]
    assert sources == ["git", "system"]  # top 2 by relevance that fit


def test_allocate_truncates_last_slot():
    budget = ContextBudget(total_tokens=1000, available=350)
    slots = [
        _slot("git", 100, 0.9),
        _slot("system", 400, 0.5),  # won't fully fit, will be truncated (250 remaining > 100 threshold)
    ]
    selected = allocate(slots, budget)
    assert len(selected) == 2
    assert selected[1].estimated_tokens == 250  # truncated to fit


def test_allocate_skips_tiny_remaining():
    budget = ContextBudget(total_tokens=500, available=120)
    slots = [
        _slot("git", 110, 0.9),
        _slot("system", 50, 0.5),  # only 10 tokens left, below 100 threshold
    ]
    selected = allocate(slots, budget)
    assert len(selected) == 1


def test_create_budget():
    budget = create_budget(4096)
    assert budget.total_tokens == 4096
    assert budget.available == 4096 - 500 - 2000  # minus reserves


def test_create_budget_small_window():
    budget = create_budget(100)
    assert budget.available == 0  # reserves exceed window
