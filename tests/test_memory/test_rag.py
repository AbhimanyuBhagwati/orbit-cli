"""Tests for RAG availability check."""

from __future__ import annotations


def test_is_available_returns_bool():
    from orbit.memory.rag import is_available

    result = is_available()
    assert isinstance(result, bool)
