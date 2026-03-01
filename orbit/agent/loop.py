from __future__ import annotations

import time

from orbit.agent import budget as budget_mod
from orbit.agent import executor, observer, planner
from orbit.config import OrbitConfig, get_config
from orbit.context.scanner import scan
from orbit.llm.ollama_provider import OllamaProvider
from orbit.router import context_budget, decomposer, model_selector
from orbit.router.model_registry import ModelRegistry
from orbit.safety.classifier import classify
from orbit.schemas.execution import ExecutionRecord
from orbit.ui.confirmations import confirm_step
from orbit.ui.console import console
from orbit.ui.panels import show_fatal, show_plan, show_replan, show_step_success, show_summary


async def run(goal: str, config: OrbitConfig | None = None) -> list[ExecutionRecord]:
    """Execute the full agent loop: scan → decompose → plan → confirm → execute → observe."""
    if config is None:
        config = get_config()

    budget = budget_mod.Budget(
        max_steps=config.max_steps,
        max_replans_per_step=config.max_replans,
        max_llm_calls=config.max_llm_calls,
    )
    provider = OllamaProvider(host=config.ollama_host, port=config.ollama_port)

    # 1. Scan environment
    console.print("[orbit.blue]Scanning environment...[/]")
    env = await scan()

    # 2. Scan models and build registry
    registry = ModelRegistry()
    try:
        registry.scan(provider)
    except Exception as e:
        show_fatal(f"Cannot connect to Ollama: {e}")
        return []

    # 3. Decompose goal
    console.print("[orbit.blue]Decomposing goal...[/]")
    budget.use_llm_call()
    decomposition = await decomposer.decompose(goal, env, provider, config.default_model)

    # 4. Select models
    model_map = model_selector.select(decomposition, registry, config.default_model)

    # 5. Allocate context budget
    ctx_window = registry.get_context_window(config.default_model)
    ctx_budget = context_budget.create_budget(ctx_window)
    env.slots = context_budget.allocate(env.slots, ctx_budget)

    # 6. Generate plan
    console.print("[orbit.blue]Generating plan...[/]")
    execution_plan = await planner.plan(goal, decomposition, env, model_map, budget, provider)

    if not execution_plan.steps:
        show_fatal("Could not generate an execution plan.")
        return []

    # 7. Show plan
    show_plan(execution_plan)

    # 8. Execute steps
    records: list[ExecutionRecord] = []
    start_time = time.monotonic()
    i = 0

    try:
        while i < len(execution_plan.steps):
            step = execution_plan.steps[i]
            budget.use_step()

            # Safety gate
            risk = classify(step.command, env)
            if not confirm_step(step, risk):
                console.print(f"  [orbit.warning]Skipped: {step.description}[/]")
                i += 1
                continue

            # Execute
            result = await executor.run(step)
            record = ExecutionRecord(
                step=step,
                result=result,
                rollback_available=step.rollback_command is not None,
            )
            records.append(record)

            # Record to history
            try:
                from orbit.memory.history import record as record_history

                record_history(result, goal=goal)
            except Exception:
                pass  # history recording is best-effort

            # Observe
            decision = observer.analyze(step, result, budget)

            if decision.status == "success":
                show_step_success(step, result)
                i += 1
            elif decision.status == "replan":
                show_replan(decision.analysis)
                budget.use_replan()
                new_plan = await planner.replan(
                    goal, records, decision.analysis, env, budget, provider, config.default_model
                )
                if new_plan.steps:
                    # Replace remaining steps with replan output
                    execution_plan.steps[i:] = new_plan.steps
                else:
                    i += 1
            elif decision.status == "fatal":
                show_fatal(decision.analysis)
                break

    except budget_mod.BudgetExhaustedError as e:
        show_fatal(f"Budget exhausted: {e}")

    duration = time.monotonic() - start_time
    completed = sum(1 for r in records if r.result.exit_code == 0)
    show_summary(completed, len(execution_plan.steps), duration)

    return records
