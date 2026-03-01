from __future__ import annotations

import pytest
from pydantic import ValidationError

from orbit.schemas.context import ContextBudget, ContextSlot, EnvironmentState
from orbit.schemas.execution import CommandResult, ExecutionRecord
from orbit.schemas.plan import Plan, PlanStep, SubTask, TaskDecomposition
from orbit.schemas.runbook import Runbook, RunbookStep
from orbit.schemas.safety import RiskAssessment, RollbackPlan


class TestPlanSchemas:
    def test_plan_step_defaults(self) -> None:
        step = PlanStep(description="test", command="echo hi", risk_level="safe")
        assert step.expected_exit_code == 0
        assert step.timeout_seconds == 30
        assert step.requires_context == []
        assert step.rollback_command is None

    def test_plan_step_all_fields(self) -> None:
        step = PlanStep(
            description="deploy",
            command="kubectl apply -f deploy.yaml",
            risk_level="caution",
            rollback_command="kubectl delete -f deploy.yaml",
            expected_exit_code=0,
            expected_output_pattern="configured",
            timeout_seconds=60,
            requires_context=["k8s"],
        )
        assert step.risk_level == "caution"
        assert step.rollback_command == "kubectl delete -f deploy.yaml"

    def test_plan_step_invalid_risk_level(self) -> None:
        with pytest.raises(ValidationError):
            PlanStep(description="test", command="echo", risk_level="unknown")  # type: ignore[arg-type]

    def test_plan_json_schema(self) -> None:
        schema = Plan.model_json_schema()
        assert "properties" in schema
        assert "goal" in schema["properties"]

    def test_plan_round_trip(self, sample_plan: Plan) -> None:
        json_str = sample_plan.model_dump_json()
        restored = Plan.model_validate_json(json_str)
        assert restored.goal == sample_plan.goal
        assert len(restored.steps) == len(sample_plan.steps)

    def test_subtask(self) -> None:
        st = SubTask(description="analyze code", capability="code", estimated_tokens=500)
        assert st.context_needed == []

    def test_task_decomposition(self) -> None:
        td = TaskDecomposition(
            subtasks=[SubTask(description="step1", capability="general", estimated_tokens=100)],
            execution_order=[0],
        )
        assert len(td.subtasks) == 1


class TestContextSchemas:
    def test_context_slot_defaults(self) -> None:
        slot = ContextSlot(source="git", relevance=0.8, estimated_tokens=50, content="data")
        assert slot.available is True
        assert slot.truncation_strategy == "tail"

    def test_context_budget(self, sample_context_budget: ContextBudget) -> None:
        assert sample_context_budget.system_prompt_reserve == 500
        assert sample_context_budget.response_reserve == 2000

    def test_environment_state(self, sample_env_state: EnvironmentState) -> None:
        assert sample_env_state.git_branch == "main"
        assert len(sample_env_state.slots) == 1

    def test_context_slot_truncation_literal(self) -> None:
        with pytest.raises(ValidationError):
            ContextSlot(
                source="git",
                relevance=0.5,
                estimated_tokens=10,
                content="x",
                truncation_strategy="random",  # type: ignore[arg-type]
            )


class TestExecutionSchemas:
    def test_command_result(self, sample_command_result: CommandResult) -> None:
        assert sample_command_result.exit_code == 0
        assert sample_command_result.timed_out is False

    def test_execution_record(self, sample_plan_step: PlanStep, sample_command_result: CommandResult) -> None:
        record = ExecutionRecord(step=sample_plan_step, result=sample_command_result)
        assert record.rollback_available is False
        assert record.rolled_back is False

    def test_command_result_json_schema(self) -> None:
        schema = CommandResult.model_json_schema()
        assert "command" in schema["properties"]


class TestSafetySchemas:
    def test_risk_assessment(self) -> None:
        ra = RiskAssessment(command="rm -rf /", tier="nuclear", description="Deletes everything", is_production=True)
        assert ra.is_production is True

    def test_risk_assessment_default_production(self) -> None:
        ra = RiskAssessment(command="ls", tier="safe", description="List files")
        assert ra.is_production is False

    def test_rollback_plan(self) -> None:
        rp = RollbackPlan(
            original_command="kubectl apply -f x.yaml",
            rollback_commands=["kubectl delete -f x.yaml"],
            description="Undo apply",
        )
        assert len(rp.rollback_commands) == 1


class TestRunbookSchemas:
    def test_runbook_step(self) -> None:
        step = RunbookStep(description="check pods", command="kubectl get pods", risk_level="safe")
        assert step.expected_exit_code == 0

    def test_runbook(self) -> None:
        rb = Runbook(
            name="deploy",
            description="Deploy the app",
            steps=[RunbookStep(description="apply", command="kubectl apply -f .", risk_level="caution")],
        )
        assert rb.name == "deploy"
        assert rb.created_at is not None

    def test_runbook_round_trip(self) -> None:
        rb = Runbook(name="test", description="test runbook")
        json_str = rb.model_dump_json()
        restored = Runbook.model_validate_json(json_str)
        assert restored.name == rb.name
