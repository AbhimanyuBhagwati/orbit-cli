"""Benchmark tests for safety classifier edge cases.

Tests regex disambiguation, production detection variants,
cross-domain command classification, and escalation logic.
"""

from __future__ import annotations

import pytest

from orbit.safety.classifier import classify, is_production_context
from orbit.safety.patterns import PATTERNS
from orbit.schemas.context import EnvironmentState


# ── sed disambiguation ──────────────────────────────────────────────────────


def test_sed_without_i_is_safe() -> None:
    assert classify("sed 's/foo/bar/' file.txt").tier == "safe"


def test_sed_with_i_flag_is_caution() -> None:
    assert classify("sed -i 's/foo/bar/' file.txt").tier == "caution"


def test_sed_i_backup_is_caution() -> None:
    assert classify("sed -i.bak 's/foo/bar/' file.txt").tier == "caution"


# ── rm -rf path variants ────────────────────────────────────────────────────


def test_rm_rf_slash_is_nuclear() -> None:
    assert classify("rm -rf /").tier == "nuclear"


def test_rm_rf_home_is_nuclear() -> None:
    assert classify("rm -rf ~").tier == "nuclear"


def test_rm_rf_slash_tmp_is_nuclear() -> None:
    """rm -rf /tmp matches rm -rf /\w pattern → nuclear."""
    assert classify("rm -rf /tmp").tier == "nuclear"


def test_rm_rf_slash_var_is_nuclear() -> None:
    assert classify("rm -rf /var/log").tier == "nuclear"


def test_rm_rf_relative_is_destructive() -> None:
    """rm -rf ./mydir has no nuclear pattern match → falls to destructive rm."""
    assert classify("rm -rf ./mydir").tier == "destructive"


def test_rm_rf_star_is_nuclear() -> None:
    assert classify("rm -rf *").tier == "nuclear"


def test_rm_single_file_is_destructive() -> None:
    assert classify("rm important.db").tier == "destructive"


# ── git stash disambiguation ────────────────────────────────────────────────


def test_git_stash_list_is_safe() -> None:
    assert classify("git stash list").tier == "safe"


def test_git_stash_pop_is_caution() -> None:
    assert classify("git stash pop").tier == "caution"


def test_git_stash_apply_is_caution() -> None:
    assert classify("git stash apply").tier == "caution"


def test_git_stash_drop_is_caution() -> None:
    assert classify("git stash drop").tier == "caution"


# ── git push variants ───────────────────────────────────────────────────────


def test_git_push_is_caution() -> None:
    assert classify("git push origin main").tier == "caution"


def test_git_push_force_long_is_destructive() -> None:
    assert classify("git push --force origin main").tier == "destructive"


def test_git_push_force_short_is_destructive() -> None:
    assert classify("git push -f origin main").tier == "destructive"


# ── git branch delete variants ──────────────────────────────────────────────


def test_git_branch_D_uppercase_is_destructive() -> None:
    assert classify("git branch -D old-feature").tier == "destructive"


def test_git_branch_d_lowercase_is_destructive() -> None:
    assert classify("git branch -d old-feature").tier == "destructive"


# ── kubectl delete variants ─────────────────────────────────────────────────


def test_kubectl_delete_pod_is_destructive() -> None:
    assert classify("kubectl delete pod mypod").tier == "destructive"


def test_kubectl_delete_namespace_is_nuclear() -> None:
    assert classify("kubectl delete namespace staging").tier == "nuclear"


def test_kubectl_delete_all_is_nuclear() -> None:
    assert classify("kubectl delete pods --all").tier == "nuclear"


def test_kubectl_delete_all_namespaces_is_nuclear() -> None:
    assert classify("kubectl delete pods --all-namespaces --all").tier == "nuclear"


# ── docker compose disambiguation ───────────────────────────────────────────


def test_docker_compose_ps_is_safe() -> None:
    assert classify("docker compose ps").tier == "safe"


def test_docker_compose_up_is_caution() -> None:
    assert classify("docker compose up").tier == "caution"


def test_docker_compose_down_is_destructive() -> None:
    assert classify("docker compose down").tier == "destructive"


def test_docker_system_prune_is_nuclear() -> None:
    assert classify("docker system prune").tier == "nuclear"


# ── SQL commands ─────────────────────────────────────────────────────────────


def test_select_is_safe() -> None:
    assert classify("SELECT * FROM users;").tier == "safe"


def test_drop_table_is_nuclear() -> None:
    assert classify("DROP TABLE users;").tier == "nuclear"


def test_truncate_is_nuclear() -> None:
    assert classify("TRUNCATE orders;").tier == "nuclear"


# ── echo with embedded dangerous content ────────────────────────────────────


def test_echo_with_sql_is_safe() -> None:
    """echo matches first (safe), before SQL patterns."""
    assert classify("echo 'SELECT * FROM users'").tier == "safe"


def test_echo_with_rm_is_safe() -> None:
    assert classify("echo 'rm -rf /'").tier == "safe"


# ── Nuclear misc ─────────────────────────────────────────────────────────────


def test_dd_device_write_is_nuclear() -> None:
    assert classify("dd if=/dev/zero of=/dev/sda").tier == "nuclear"


def test_reboot_is_nuclear() -> None:
    assert classify("reboot").tier == "nuclear"


def test_shutdown_is_nuclear() -> None:
    assert classify("shutdown -h now").tier == "nuclear"


def test_terraform_destroy_is_nuclear() -> None:
    assert classify("terraform destroy").tier == "nuclear"


# ── Scripting languages are safe ─────────────────────────────────────────────


def test_python_is_safe() -> None:
    assert classify("python manage.py migrate").tier == "safe"


def test_node_is_safe() -> None:
    assert classify("node server.js").tier == "safe"


# ── sudo escalation ─────────────────────────────────────────────────────────


def test_sudo_is_destructive() -> None:
    assert classify("sudo apt-get install nginx").tier == "destructive"


def test_sudo_in_production_is_nuclear() -> None:
    env = EnvironmentState(git_branch="main")
    assert classify("sudo systemctl restart nginx", env).tier == "nuclear"


# ── Production detection variants ────────────────────────────────────────────


def test_master_branch_is_production() -> None:
    assert is_production_context(EnvironmentState(git_branch="master"))


def test_main_branch_is_production() -> None:
    assert is_production_context(EnvironmentState(git_branch="main"))


def test_release_branch_is_production() -> None:
    assert is_production_context(EnvironmentState(git_branch="release/v2.1"))


def test_live_namespace_is_production() -> None:
    assert is_production_context(EnvironmentState(k8s_namespace="live"))


def test_prod_context_is_production() -> None:
    assert is_production_context(EnvironmentState(k8s_context="prod-us-east"))


def test_feature_branch_not_production() -> None:
    assert not is_production_context(EnvironmentState(git_branch="feature/login"))


def test_dev_namespace_not_production() -> None:
    assert not is_production_context(EnvironmentState(k8s_namespace="dev"))


def test_staging_branch_not_production() -> None:
    assert not is_production_context(EnvironmentState(git_branch="staging"))


def test_empty_env_not_production() -> None:
    assert not is_production_context(EnvironmentState())


# ── Production escalation edge cases ────────────────────────────────────────


def test_kubectl_apply_in_prod_is_nuclear() -> None:
    env = EnvironmentState(k8s_namespace="production")
    assert classify("kubectl apply -f deploy.yaml", env).tier == "nuclear"


def test_docker_build_in_prod_stays_caution() -> None:
    """docker build does not have production_escalate=True."""
    env = EnvironmentState(git_branch="main")
    result = classify("docker build -t myapp .", env)
    assert result.tier == "caution"


def test_safe_command_never_escalates() -> None:
    env = EnvironmentState(git_branch="main", k8s_namespace="production")
    assert classify("ls -la", env).tier == "safe"
    assert classify("git log", env).tier == "safe"
    assert classify("kubectl get pods", env).tier == "safe"


# ── Pattern coverage stats ───────────────────────────────────────────────────


def test_pattern_count_at_least_100() -> None:
    assert len(PATTERNS) >= 100


def test_pattern_tier_distribution() -> None:
    """Verify we have patterns across all tiers."""
    tiers = {rp.tier for rp in PATTERNS}
    assert tiers == {"safe", "caution", "destructive", "nuclear"}


def test_all_patterns_compile() -> None:
    """Verify all regex patterns compile and can match."""
    for rp in PATTERNS:
        assert rp.pattern is not None
        assert rp.tier in ("safe", "caution", "destructive", "nuclear")
        assert rp.description
