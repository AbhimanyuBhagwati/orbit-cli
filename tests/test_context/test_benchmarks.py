"""Benchmark tests for context budget, scanner parsing, and rollback edge cases."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from orbit.context.scanner import clear_cache, scan
from orbit.router.context_budget import _truncate, allocate, create_budget
from orbit.safety.rollback import generate_rollback
from orbit.schemas.context import ContextBudget, ContextSlot, EnvironmentState


# ── Context Budget Tests ─────────────────────────────────────────────────────


class TestContextBudget:
    def test_create_budget_normal(self) -> None:
        budget = create_budget(4096)
        assert budget.total_tokens == 4096
        assert budget.system_prompt_reserve == 500
        assert budget.response_reserve == 2000
        assert budget.available == 1596

    def test_create_budget_small_window_clamps_to_zero(self) -> None:
        budget = create_budget(100)
        assert budget.available == 0

    def test_create_budget_exact_reserves(self) -> None:
        budget = create_budget(2500)
        assert budget.available == 0

    def test_allocate_empty_slots(self) -> None:
        budget = ContextBudget(total_tokens=4096, available=1596)
        result = allocate([], budget)
        assert result == []

    def test_allocate_single_slot_fits(self) -> None:
        budget = ContextBudget(total_tokens=4096, available=1596)
        slot = ContextSlot(source="git", relevance=0.8, estimated_tokens=500, content="x" * 2000)
        result = allocate([slot], budget)
        assert len(result) == 1
        assert result[0].estimated_tokens == 500

    def test_allocate_single_slot_truncated(self) -> None:
        budget = ContextBudget(total_tokens=4096, available=200)
        slot = ContextSlot(source="git", relevance=0.8, estimated_tokens=500, content="x" * 2000)
        result = allocate([slot], budget)
        assert len(result) == 1
        assert result[0].estimated_tokens == 200

    def test_allocate_skips_when_remaining_too_small(self) -> None:
        budget = ContextBudget(total_tokens=4096, available=50)
        slot = ContextSlot(source="git", relevance=0.8, estimated_tokens=500, content="x" * 2000)
        result = allocate([slot], budget)
        assert len(result) == 0  # 50 <= 100 threshold

    def test_allocate_sorts_by_relevance(self) -> None:
        budget = ContextBudget(total_tokens=4096, available=500)
        low = ContextSlot(source="system", relevance=0.3, estimated_tokens=200, content="sys")
        high = ContextSlot(source="git", relevance=0.9, estimated_tokens=200, content="git")
        result = allocate([low, high], budget)
        assert result[0].source == "git"

    def test_truncate_head_strategy(self) -> None:
        content = "a" * 1000
        truncated = _truncate(content, 100, "head")
        assert len(truncated) == 400  # 100 tokens * 4 chars
        assert truncated == "a" * 400

    def test_truncate_tail_strategy(self) -> None:
        content = "a" * 1000
        truncated = _truncate(content, 100, "tail")
        assert len(truncated) == 400
        assert truncated == "a" * 400

    def test_truncate_summary_strategy(self) -> None:
        content = "A" * 500 + "B" * 500
        truncated = _truncate(content, 100, "summary")
        assert "...[truncated]..." in truncated
        assert truncated.startswith("A")
        assert truncated.endswith("B")


# ── Scanner Parsing Tests ────────────────────────────────────────────────────


class TestScannerParsing:
    @pytest.fixture(autouse=True)
    def _clear_cache(self) -> None:
        clear_cache()

    @pytest.mark.asyncio
    async def test_git_branch_extracted(self) -> None:
        git_slot = ContextSlot(
            source="git", relevance=0.8, estimated_tokens=100, content="Branch: feature/login\nStatus: clean"
        )

        async def mock_git_collect() -> ContextSlot:
            return git_slot

        async def mock_unavailable() -> ContextSlot:
            return ContextSlot(source="docker", relevance=0.0, estimated_tokens=0, content="", available=False)

        with (
            patch("orbit.context.scanner.git_ctx.collect", mock_git_collect),
            patch("orbit.context.scanner.docker_ctx.collect", mock_unavailable),
            patch("orbit.context.scanner.k8s_ctx.collect", mock_unavailable),
            patch("orbit.context.scanner.system_ctx.collect", mock_unavailable),
            patch("orbit.context.scanner.filesystem_ctx.collect", mock_unavailable),
        ):
            env = await scan()

        assert env.git_branch == "feature/login"

    @pytest.mark.asyncio
    async def test_k8s_fields_extracted(self) -> None:
        k8s_slot = ContextSlot(
            source="k8s",
            relevance=0.7,
            estimated_tokens=100,
            content="Context: prod-cluster\nNamespace: kube-system\nPods: 5 running",
        )

        async def mock_k8s_collect() -> ContextSlot:
            return k8s_slot

        async def mock_unavailable() -> ContextSlot:
            return ContextSlot(source="x", relevance=0.0, estimated_tokens=0, content="", available=False)

        with (
            patch("orbit.context.scanner.git_ctx.collect", mock_unavailable),
            patch("orbit.context.scanner.docker_ctx.collect", mock_unavailable),
            patch("orbit.context.scanner.k8s_ctx.collect", mock_k8s_collect),
            patch("orbit.context.scanner.system_ctx.collect", mock_unavailable),
            patch("orbit.context.scanner.filesystem_ctx.collect", mock_unavailable),
        ):
            env = await scan()

        assert env.k8s_context == "prod-cluster"
        assert env.k8s_namespace == "kube-system"

    @pytest.mark.asyncio
    async def test_all_collectors_unavailable(self) -> None:
        async def mock_unavailable() -> ContextSlot:
            return ContextSlot(source="x", relevance=0.0, estimated_tokens=0, content="", available=False)

        with (
            patch("orbit.context.scanner.git_ctx.collect", mock_unavailable),
            patch("orbit.context.scanner.docker_ctx.collect", mock_unavailable),
            patch("orbit.context.scanner.k8s_ctx.collect", mock_unavailable),
            patch("orbit.context.scanner.system_ctx.collect", mock_unavailable),
            patch("orbit.context.scanner.filesystem_ctx.collect", mock_unavailable),
        ):
            env = await scan()

        assert env.slots == []
        assert env.git_branch is None
        assert env.k8s_namespace is None
        assert env.k8s_context is None

    @pytest.mark.asyncio
    async def test_collector_exception_tolerated(self) -> None:
        async def mock_explode() -> ContextSlot:
            raise RuntimeError("boom")

        async def mock_unavailable() -> ContextSlot:
            return ContextSlot(source="x", relevance=0.0, estimated_tokens=0, content="", available=False)

        with (
            patch("orbit.context.scanner.git_ctx.collect", mock_explode),
            patch("orbit.context.scanner.docker_ctx.collect", mock_unavailable),
            patch("orbit.context.scanner.k8s_ctx.collect", mock_unavailable),
            patch("orbit.context.scanner.system_ctx.collect", mock_unavailable),
            patch("orbit.context.scanner.filesystem_ctx.collect", mock_unavailable),
        ):
            env = await scan()  # should not raise

        assert isinstance(env, EnvironmentState)


# ── Rollback Edge Cases ──────────────────────────────────────────────────────


class TestRollbackEdgeCases:
    def test_kubectl_apply_extracts_manifest(self) -> None:
        plan = generate_rollback("kubectl apply -f ./k8s/deployment.yaml")
        assert plan is not None
        assert "kubectl delete -f ./k8s/deployment.yaml" in plan.rollback_commands

    def test_rm_returns_irreversible(self) -> None:
        plan = generate_rollback("rm important.db")
        assert plan is not None
        assert "irreversible" in plan.description.lower() or "backup" in plan.description.lower()

    def test_docker_compose_down_rollback(self) -> None:
        plan = generate_rollback("docker compose down")
        assert plan is not None
        assert "docker compose up -d" in plan.rollback_commands

    def test_git_reset_hard_rollback(self) -> None:
        plan = generate_rollback("git reset --hard HEAD~3")
        assert plan is not None
        assert any("reflog" in cmd for cmd in plan.rollback_commands)

    def test_git_force_push_rollback(self) -> None:
        plan = generate_rollback("git push --force origin main")
        assert plan is not None

    def test_no_rollback_for_terraform(self) -> None:
        plan = generate_rollback("terraform apply")
        assert plan is None

    def test_no_rollback_for_systemctl(self) -> None:
        plan = generate_rollback("systemctl restart nginx")
        assert plan is None

    def test_no_rollback_for_safe_command(self) -> None:
        plan = generate_rollback("ls -la")
        assert plan is None

    def test_no_rollback_for_unknown(self) -> None:
        plan = generate_rollback("some_tool --do-stuff")
        assert plan is None
