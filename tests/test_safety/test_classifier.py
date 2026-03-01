"""Tests for the safety classifier."""

from __future__ import annotations

import pytest

from orbit.safety.classifier import classify, is_production_context
from orbit.schemas.context import EnvironmentState


@pytest.fixture
def prod_env() -> EnvironmentState:
    return EnvironmentState(git_branch="main")


@pytest.fixture
def dev_env() -> EnvironmentState:
    return EnvironmentState(git_branch="feature/add-login")


# ── Safe commands ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "cmd",
    [
        "ls -la",
        "cat /etc/hosts",
        "grep pattern file.txt",
        "git log --oneline",
        "docker ps",
        "kubectl get pods",
        "pwd",
        "echo hello",
        "head -n 10 file.txt",
        "find . -name '*.py'",
        "wc -l file.txt",
        "diff a b",
        "tree",
        "git status",
        "git diff HEAD",
        "docker images",
        "docker logs container",
        "kubectl describe pod mypod",
        "kubectl version",
    ],
)
def test_safe_commands(cmd: str) -> None:
    assessment = classify(cmd)
    assert assessment.tier == "safe", f"{cmd} should be safe, got {assessment.tier}"


# ── Caution commands ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "cmd",
    [
        "git add .",
        "git commit -m 'msg'",
        "git push origin main",
        "docker build -t myapp .",
        "docker run myimage",
        "kubectl apply -f deploy.yaml",
        "mkdir newdir",
        "cp file1 file2",
        "mv file1 file2",
        "chmod 755 file",
        "pip install requests",
        "npm install express",
        "make build",
        "git pull origin main",
        "docker compose up",
        "kubectl exec pod -- bash",
    ],
)
def test_caution_commands(cmd: str) -> None:
    assessment = classify(cmd)
    assert assessment.tier == "caution", f"{cmd} should be caution, got {assessment.tier}"


# ── Destructive commands ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "cmd",
    [
        "rm file.txt",
        "git reset --hard HEAD~1",
        "git push --force origin main",
        "docker rm container123",
        "kubectl delete pod mypod",
        "kill 1234",
        "sudo apt-get install",
        "git clean -fd",
        "git branch -D feature",
    ],
)
def test_destructive_commands(cmd: str) -> None:
    assessment = classify(cmd)
    assert assessment.tier == "destructive", f"{cmd} should be destructive, got {assessment.tier}"


# ── Nuclear commands ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "cmd",
    [
        "rm -rf /",
        "rm -rf ~",
        "rm -rf *",
        "terraform destroy",
        "docker system prune",
        "kubectl delete namespace production",
        "kubectl delete pods --all",
        "DROP TABLE users;",
        "TRUNCATE orders;",
        "reboot",
        "shutdown -h now",
    ],
)
def test_nuclear_commands(cmd: str) -> None:
    assessment = classify(cmd)
    assert assessment.tier == "nuclear", f"{cmd} should be nuclear, got {assessment.tier}"


# ── Unknown defaults to caution ──────────────────────────────────────────────


def test_unknown_command_defaults_to_caution() -> None:
    assessment = classify("some_obscure_tool --do-stuff")
    assert assessment.tier == "caution"
    assert assessment.description == "unrecognized command"


# ── Production detection ─────────────────────────────────────────────────────


def test_production_branch_detection(prod_env: EnvironmentState) -> None:
    assert is_production_context(prod_env)


def test_dev_branch_not_production(dev_env: EnvironmentState) -> None:
    assert not is_production_context(dev_env)


def test_production_k8s_namespace() -> None:
    env = EnvironmentState(k8s_namespace="production")
    assert is_production_context(env)


def test_production_k8s_context() -> None:
    env = EnvironmentState(k8s_context="prod-cluster")
    assert is_production_context(env)


# ── Production escalation ────────────────────────────────────────────────────


def test_destructive_plus_production_escalates_to_nuclear(prod_env: EnvironmentState) -> None:
    assessment = classify("rm important_file.txt", prod_env)
    assert assessment.tier == "nuclear"
    assert assessment.is_production


def test_caution_with_production_escalate_flag(prod_env: EnvironmentState) -> None:
    assessment = classify("git push origin main", prod_env)
    assert assessment.tier == "nuclear"


def test_safe_not_escalated_in_production(prod_env: EnvironmentState) -> None:
    assessment = classify("ls -la", prod_env)
    assert assessment.tier == "safe"


def test_no_escalation_in_dev(dev_env: EnvironmentState) -> None:
    assessment = classify("rm file.txt", dev_env)
    assert assessment.tier == "destructive"  # not escalated


# ── Pattern count ────────────────────────────────────────────────────────────


def test_at_least_100_patterns() -> None:
    from orbit.safety.patterns import PATTERNS

    assert len(PATTERNS) >= 100
