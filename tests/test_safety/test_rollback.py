"""Tests for rollback plan generation."""

from __future__ import annotations

from orbit.safety.rollback import generate_rollback


def test_git_reset_hard_rollback():
    plan = generate_rollback("git reset --hard HEAD~1")
    assert plan is not None
    assert "reflog" in plan.description.lower()
    assert any("reflog" in cmd for cmd in plan.rollback_commands)


def test_git_force_push_rollback():
    plan = generate_rollback("git push --force origin main")
    assert plan is not None
    assert len(plan.rollback_commands) > 0


def test_kubectl_apply_rollback():
    plan = generate_rollback("kubectl apply -f deploy.yaml")
    assert plan is not None
    assert "kubectl delete -f deploy.yaml" in plan.rollback_commands


def test_kubectl_delete_rollback():
    plan = generate_rollback("kubectl delete deployment myapp")
    assert plan is not None
    assert "backup" in plan.description.lower() or "restore" in plan.description.lower()


def test_docker_compose_down_rollback():
    plan = generate_rollback("docker compose down")
    assert plan is not None
    assert "docker compose up -d" in plan.rollback_commands


def test_docker_rm_rollback():
    plan = generate_rollback("docker rm my-container")
    assert plan is not None
    assert "recreated" in plan.description.lower()


def test_rm_rollback():
    plan = generate_rollback("rm -rf /tmp/test")
    assert plan is not None
    assert "irreversible" in plan.description.lower()


def test_no_rollback_for_safe_command():
    plan = generate_rollback("ls -la")
    assert plan is None


def test_no_rollback_for_unknown_command():
    plan = generate_rollback("custom-tool --action")
    assert plan is None
