from __future__ import annotations

from abc import ABC, abstractmethod


class BaseModule(ABC):
    """Abstract base class for Orbit domain modules."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def commands(self) -> list[str]: ...

    @abstractmethod
    def get_system_prompt(self) -> str: ...

    @abstractmethod
    def get_common_failures(self) -> dict[str, str]: ...

    @abstractmethod
    def suggest_rollback(self, command: str) -> str | None: ...
