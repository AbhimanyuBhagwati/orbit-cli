from __future__ import annotations


class BudgetExhaustedError(Exception):
    """Raised when an agent budget limit is exceeded."""

    def __init__(self, resource: str, used: int, limit: int) -> None:
        self.resource = resource
        self.used = used
        self.limit = limit
        super().__init__(f"Budget exhausted: {resource} ({used}/{limit})")


class Budget:
    """Tracks agent loop resource usage with hard limits."""

    def __init__(
        self,
        max_steps: int = 15,
        max_replans_per_step: int = 3,
        max_llm_calls: int = 25,
    ) -> None:
        self.max_steps = max_steps
        self.max_replans_per_step = max_replans_per_step
        self.max_llm_calls = max_llm_calls
        self._steps = 0
        self._replans_current_step = 0
        self._total_replans = 0
        self._llm_calls = 0

    def use_step(self) -> None:
        self._steps += 1
        self._replans_current_step = 0
        if self._steps > self.max_steps:
            raise BudgetExhaustedError("steps", self._steps, self.max_steps)

    def use_replan(self) -> None:
        self._replans_current_step += 1
        self._total_replans += 1
        if self._replans_current_step > self.max_replans_per_step:
            raise BudgetExhaustedError("replans_per_step", self._replans_current_step, self.max_replans_per_step)

    def use_llm_call(self) -> None:
        self._llm_calls += 1
        if self._llm_calls > self.max_llm_calls:
            raise BudgetExhaustedError("llm_calls", self._llm_calls, self.max_llm_calls)

    def can_replan(self) -> bool:
        return self._replans_current_step < self.max_replans_per_step and self._llm_calls < self.max_llm_calls

    def usage(self) -> dict[str, int]:
        return {
            "steps": self._steps,
            "total_replans": self._total_replans,
            "llm_calls": self._llm_calls,
            "max_steps": self.max_steps,
            "max_llm_calls": self.max_llm_calls,
        }
