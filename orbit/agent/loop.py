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
from orbit.ui.animation import print_pipeline_stage, show_agent_banner, show_step_header, stage_spinner
from orbit.ui.confirmations import confirm_step
from orbit.ui.console import console
from orbit.ui.panels import show_fatal, show_plan, show_replan, show_step_success, show_summary


async def run(goal: str, config: OrbitConfig | None = None) -> list[ExecutionRecord]:
    """Execute the full agent loop: scan → decompose → plan → confirm → execute → observe."""
    if config is None:
        config = get_config()

    # ── Agent banner ────────────────────────────────────────────────────────
    show_agent_banner(goal)

    budget = budget_mod.Budget(
        max_steps=config.max_steps,
        max_replans_per_step=config.max_replans,
        max_llm_calls=config.max_llm_calls,
    )
    provider = OllamaProvider(host=config.ollama_host, port=config.ollama_port)

    # ── Stage 1: SCAN ───────────────────────────────────────────────────────
    print_pipeline_stage("SCAN")
    async with stage_spinner("Scanning environment..."):
        env = await scan()

    async with stage_spinner("Discovering models..."):
        registry = ModelRegistry()
        try:
            registry.scan(provider)
        except Exception as e:
            show_fatal(f"Cannot connect to Ollama: {e}")
            return []

    # ── Stage 2: DECOMPOSE ──────────────────────────────────────────────────
    print_pipeline_stage("DECOMPOSE")
    async with stage_spinner("Decomposing goal into subtasks..."):
        budget.use_llm_call()
        decomposition = await decomposer.decompose(goal, env, provider, config.default_model)

    # ── Stage 3: ROUTE ──────────────────────────────────────────────────────
    print_pipeline_stage("ROUTE")
    async with stage_spinner("Selecting models & allocating context..."):
        model_map = model_selector.select(decomposition, registry, config.default_model)
        ctx_window = registry.get_context_window(config.default_model)
        ctx_budget = context_budget.create_budget(ctx_window)
        env.slots = context_budget.allocate(env.slots, ctx_budget)

    # ── Stage 4: PLAN ───────────────────────────────────────────────────────
    print_pipeline_stage("PLAN")
    async with stage_spinner("Generating execution plan..."):
        execution_plan = await planner.plan(goal, decomposition, env, model_map, budget, provider)

    if not execution_plan.steps:
        show_fatal("Could not generate an execution plan.")
        return []

    show_plan(execution_plan)

    # ── Stage 5: EXECUTE ────────────────────────────────────────────────────
    print_pipeline_stage("EXECUTE")

    records: list[ExecutionRecord] = []
    start_time = time.monotonic()
    i = 0

    try:
        while i < len(execution_plan.steps):
            step = execution_plan.steps[i]
            budget.use_step()
            total_steps = len(execution_plan.steps)

            # Safety gate (interactive — no spinner)
            risk = classify(step.command, env)
            if not confirm_step(step, risk):
                console.print(f"  [orbit.warning]Skipped: {step.description}[/]")
                i += 1
                continue

            # Step header
            show_step_header(i + 1, total_steps, step)

            # Execute
            result = await executor.run(step)
            record = ExecutionRecord(
                step=step,
                result=result,
                rollback_available=step.rollback_command is not None,
            )
            records.append(record)

            # Record to history (best-effort)
            try:
                from orbit.memory.history import record as record_history

                record_history(result, goal=goal)
            except Exception:
                pass

            # Observe
            decision = observer.analyze(step, result, budget)

            if decision.status == "success":
                show_step_success(step, result)
                i += 1
            elif decision.status == "replan":
                show_replan(decision.analysis)
                budget.use_replan()
                async with stage_spinner("Replanning..."):
                    new_plan = await planner.replan(
                        goal, records, decision.analysis, env, budget, provider, config.default_model
                    )
                if new_plan.steps:
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
