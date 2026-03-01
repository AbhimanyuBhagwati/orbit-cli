from __future__ import annotations

from orbit.schemas.context import ContextBudget, ContextSlot


def allocate(slots: list[ContextSlot], budget: ContextBudget) -> list[ContextSlot]:
    """Fill context window greedily by relevance. Truncates last slot if needed."""
    sorted_slots = sorted(slots, key=lambda s: s.relevance, reverse=True)
    selected: list[ContextSlot] = []
    remaining = budget.available

    for slot in sorted_slots:
        if remaining <= 0:
            break
        if slot.estimated_tokens <= remaining:
            selected.append(slot)
            remaining -= slot.estimated_tokens
        elif remaining > 100:
            slot.content = _truncate(slot.content, remaining, slot.truncation_strategy)
            slot.estimated_tokens = remaining
            selected.append(slot)
            remaining = 0

    return selected


def _truncate(content: str, max_tokens: int, strategy: str) -> str:
    """Truncate content to fit within max_tokens (rough: 4 chars per token)."""
    max_chars = max_tokens * 4
    if strategy == "head":
        return content[:max_chars]
    elif strategy == "tail":
        return content[-max_chars:]
    else:  # summary
        half = max_chars // 2
        return content[:half] + "\n...[truncated]...\n" + content[-half:]


def create_budget(context_window: int) -> ContextBudget:
    """Create a ContextBudget from a model's context window size."""
    system_reserve = 500
    response_reserve = 2000
    available = max(context_window - system_reserve - response_reserve, 0)
    return ContextBudget(
        total_tokens=context_window,
        system_prompt_reserve=system_reserve,
        response_reserve=response_reserve,
        available=available,
    )
