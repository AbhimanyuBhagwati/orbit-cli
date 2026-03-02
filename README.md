<p align="center">
  <h1 align="center">Orbit</h1>
  <p align="center">
    <strong>Local-first, multi-model DevOps CLI agent.</strong>
    <br />
    Turn natural language into safe, observable DevOps actions — everything runs on your machine.
  </p>
  <p align="center">
    <a href="https://pypi.org/project/orbit-cli/"><img src="https://img.shields.io/pypi/v/orbit-cli.svg" alt="PyPI version" /></a>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python 3.11+" /></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License" /></a>
    <a href="#testing"><img src="https://img.shields.io/badge/tests-300%20passing-brightgreen.svg" alt="Tests" /></a>
  </p>
</p>

---

```bash
pip install orbit-cli
orbit do "find why my pods are crashing and fix it"
```

Orbit decomposes goals into plans, picks the best local model for each step, classifies every command through a **regex-only safety system** (no LLM in the safety path), executes with tiered confirmations, and **auto-replans when things fail** — all running against your own [Ollama](https://ollama.ai) instance. Nothing leaves your machine.

## Why Orbit?

Most AI CLI tools send your infrastructure details to the cloud, use one model for everything, and let the LLM decide what's safe. Orbit takes a different approach:

| Problem | How Orbit Solves It |
|---------|-------------------|
| Your kubectl configs, env vars, and error logs flow through third-party APIs | **100% local** — runs on Ollama, nothing leaves your machine |
| The LLM that generates a command also judges if it's safe (circular dependency) | **173 regex patterns** classify risk — deterministic, immune to prompt injection |
| One model handles everything from `ls` to debugging cascade failures | **Multi-model routing** — picks the best local model per subtask |
| When a command fails, you're on your own | **Auto-replan** — observes failures and generates corrective steps |
| No awareness of what branch/namespace/cluster you're in | **Context-aware** — auto-scans git, Docker, K8s, system, and filesystem |

## Quick Start

### Requirements

- Python 3.11+
- [Ollama](https://ollama.ai) running locally with at least one model:

```bash
ollama pull qwen2.5:7b
```

### Install

```bash
pip install orbit-cli
```

### Your first goal

```bash
orbit do "find large files in this repo and show disk usage by directory"
```

Orbit will scan your environment, decompose the goal, build a plan, ask for confirmation on risky steps, execute, and replan if needed.

## Commands

```bash
orbit do "goal"          # Execute a goal with the full agent loop
orbit sense              # Scan environment — see what Orbit sees before planning
orbit wtf                # Diagnose the last failed command with full context
orbit ask "question"     # One-shot Q&A with environment context
orbit config doctor      # Verify Ollama connectivity and configuration health
orbit config show        # Show current configuration
orbit runbook list       # List saved runbooks
orbit runbook run name   # Replay a saved workflow
orbit history list       # Browse command history
```

## How It Works

```
                         orbit do "debug my crashing pods"
                                      │
                    ┌─────────────────────────────────────┐
                    │         1. ENVIRONMENT SCAN          │
                    │   5 parallel collectors (async):     │
                    │   git · docker · k8s · system · fs   │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │        2. TASK DECOMPOSITION         │
                    │   Goal → SubTasks with capability    │
                    │   tags: fast_shell, code_gen,        │
                    │   reasoning, general    (LLM call)   │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │        3. MODEL SELECTION            │
                    │   Capability → best local model      │
                    │   (deterministic, no LLM call)       │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │        4. PLAN GENERATION            │
                    │   Structured output via Pydantic     │
                    │   JSON schema → Ollama    (LLM call) │
                    └──────────────┬──────────────────────┘
                                   │
              ┌────────────────────▼─────────────────────────┐
              │              5. EXECUTION LOOP               │
              │                                              │
              │   For each step:                             │
              │   ┌─────────┐  ┌─────────┐  ┌────────────┐  │
              │   │CLASSIFY │→ │CONFIRM  │→ │  EXECUTE   │  │
              │   │(regex)  │  │(tiered) │  │(subprocess)│  │
              │   └─────────┘  └─────────┘  └─────┬──────┘  │
              │                                    │         │
              │                             ┌──────▼──────┐  │
              │                             │  OBSERVE    │  │
              │                             │(deterministic)│ │
              │                             └──────┬──────┘  │
              │                      ┌─────────────┼────┐    │
              │                  success       replan  fatal │
              │                  (next)     (LLM call) (stop)│
              └──────────────────────────────────────────────┘
```

**The LLM is used for exactly 2 things:** decomposing goals and generating plans. Safety classification, observation, model routing, and budget enforcement are all deterministic code.

## The Safety System

This is the core design decision: **the LLM never decides what's safe.**

173 hand-crafted regex patterns classify every command into four tiers. Patterns are checked in order (nuclear first), first match wins. Unrecognized commands default to **caution, never safe**.

| Tier | What Happens | Examples |
|------|-------------|----------|
| **safe** | Runs silently | `ls`, `cat`, `kubectl get`, `docker ps`, `git log` |
| **caution** | Single confirmation | `git push`, `docker build`, `kubectl apply`, `pip install` |
| **destructive** | Impact analysis + double confirm | `rm`, `kubectl delete pod`, `git reset --hard` |
| **nuclear** | Type "i am sure" + 3s cooldown | `rm -rf /`, `kubectl delete namespace`, `DROP TABLE` |

### Production detection

Orbit checks your git branch, K8s namespace, and K8s context for production indicators (`main`, `master`, `release/*`, `prod`, `live`). When production is detected, 28 patterns auto-escalate:

```
git push origin main  (on feature branch)  →  caution  (single confirm)
git push origin main  (ON main branch)     →  nuclear  (type "i am sure" + 3s cooldown)
```

Safe commands (`ls`, `kubectl get`, `git log`) are **never** escalated, even in production.

### Why not use the LLM for safety?

Using the same system that generates commands to evaluate their safety is a circular dependency. Three failure modes:

1. **Prompt injection** — attacker crafts a goal that tricks the LLM into classifying dangerous commands as safe
2. **Hallucination** — the LLM might just be wrong
3. **Latency** — regex takes microseconds, LLM takes seconds

Regex patterns are deterministic, immune to prompt injection, and fast.

## Multi-Model Routing

Not every task needs a 32B model. Orbit routes subtasks to the best locally-available model:

| Capability | Use Case | Preferred Models |
|-----------|----------|-----------------|
| `fast_shell` | Status checks, listing | Small models (qwen2.5:7b, phi3) |
| `code_gen` | Scripts, configs, Dockerfiles | Code models (codellama, qwen2.5) |
| `reasoning` | Complex debugging, root cause | Large models (deepseek-r1:32b) |
| `general` | Fallback | Default model |

The selector walks a priority list of known-good models, checks what's installed locally, and returns the first match. **No LLM call in the routing path** — it's a deterministic lookup.

## Context-Aware Scanning

Five collectors run in parallel via `asyncio.gather`:

| Source | Data Collected | Truncation |
|--------|---------------|-----------|
| **Git** | Branch, changed files, recent commits, diff stats, remotes | tail |
| **Docker** | Running containers, compose services, images (top 20) | head |
| **Kubernetes** | Context, namespace, pod list, recent events | tail |
| **System** | OS, shell, Python version, env vars (**values redacted**) | summary |
| **Filesystem** | Directory tree (2 levels), key files (Dockerfile, etc.) | head |

**Fault-tolerant:** If you don't have kubectl installed, the K8s collector returns empty instead of crashing. Each collector has a 5-second timeout. Results are cached with 5-second TTL.

**Token-aware:** Context slots are ranked by relevance and greedily allocated to fit the model's context window (with reserves for system prompt and response).

## Auto-Replan on Failure

Real DevOps isn't linear. When a step fails:

1. **Observer** checks exit code against expected (deterministic, no LLM)
2. If replan budget remains → error summary (first 500 chars) fed to **replanner** (LLM call)
3. Replanner generates **replacement steps** without re-running successful steps
4. If budget exhausted → graceful exit with summary

**Hard budget limits** prevent runaway execution:

| Resource | Default | On Exhaustion |
|----------|:---:|---|
| Total steps | 15 | Graceful exit with summary |
| Replans per step | 3 | Observer returns "fatal" |
| Total LLM calls | 25 | Graceful exit with summary |

## Rollback Plans

Destructive commands get automatic rollback plans:

| Command | Rollback |
|---------|----------|
| `git reset --hard` | `git reflog` → `git reset --hard HEAD@{1}` |
| `git push --force` | Force push previous HEAD via reflog |
| `kubectl apply -f manifest.yaml` | `kubectl delete -f manifest.yaml` |
| `docker compose down` | `docker compose up -d` |
| `rm`, `kubectl delete pod` | Marked irreversible — "check backups" |

## Memory

| Layer | Storage | Use Case |
|-------|---------|----------|
| **Command history** | SQLite (`~/.orbit/history.db`) | Searchable log of every action. Powers `orbit wtf`. |
| **Runbooks** | YAML (`~/.orbit/runbooks/`) | Save successful workflows, replay with `orbit runbook run` |
| **Semantic search** | ChromaDB (optional) | Vector search over past actions (`pip install orbit-cli[rag]`) |

## Configuration

Stored at `~/.orbit/config.toml`. Run `orbit config doctor` to check your setup.

```toml
default_model = "qwen2.5:7b"
safety_mode = "normal"           # normal, strict, or yolo
ollama_host = "localhost"
ollama_port = 11434
max_steps = 15                   # hard budget per goal
max_replans = 3                  # retries per step
max_llm_calls = 25               # total LLM calls per goal
```

## Optional Extras

```bash
pip install orbit-cli[rag]        # ChromaDB for semantic memory
pip install orbit-cli[openai]     # OpenAI provider
pip install orbit-cli[anthropic]  # Anthropic provider
pip install orbit-cli[all]        # everything
```

## Testing

**300 tests. All passing. 3.09 seconds.**

```
Component               Tests   What's Tested
──────────────────────────────────────────────────────────────
Safety Classifier         129   Every regex edge case, disambiguation,
                                production detection, escalation
Agent                      53   Real subprocess execution, observer
                                decisions, planner fallbacks, budget
Context                    43   Parallel scanning, fault tolerance,
                                budget allocation, truncation strategies
Router                     18   Model matching, capability lookup,
                                decomposition with LLM fallback
Schemas                    20   Pydantic validation, JSON roundtrip
Config                     12   Persistence, health checks, singleton
CLI                         9   Command entry points, flag handling
LLM Provider                9   Interface compliance, retry logic
Memory                     12   SQLite history, YAML runbooks, RAG
```

```bash
pytest                    # run all 300 tests
ruff check orbit/ tests/  # lint
mypy orbit/               # type check (strict mode)
```

## Architecture

```
orbit/
├── cli.py                  # Typer CLI (do, sense, wtf, ask, config, runbook, history)
├── config.py               # TOML config with singleton loader + health checks
├── schemas/                # Pydantic v2 data contracts (zero logic)
│   ├── plan.py             # PlanStep, Plan, SubTask, TaskDecomposition
│   ├── context.py          # ContextSlot, ContextBudget, EnvironmentState
│   ├── execution.py        # CommandResult, ExecutionRecord
│   └── safety.py           # RiskAssessment, RollbackPlan
├── llm/                    # LLM provider abstraction
│   ├── base.py             # BaseLLM Protocol + exceptions
│   └── ollama_provider.py  # Ollama: sync + async + structured output + retry
├── context/                # Environment scanning
│   ├── scanner.py          # Parallel orchestrator + caching + relevance scoring
│   ├── git_ctx.py          # Git state collector
│   ├── docker_ctx.py       # Docker/Compose collector
│   ├── k8s_ctx.py          # Kubernetes collector
│   ├── system_ctx.py       # System info (env vars redacted)
│   └── filesystem_ctx.py   # Project structure + key file detection
├── router/                 # Task decomposition + model selection
│   ├── decomposer.py       # Goal → SubTasks (LLM call)
│   ├── model_registry.py   # Scan Ollama, map capabilities
│   ├── model_selector.py   # Deterministic model selection (no LLM)
│   └── context_budget.py   # Token-aware greedy allocation
├── safety/                 # Risk classification
│   ├── patterns.py         # 173 regex patterns across 4 tiers
│   ├── classifier.py       # classify() + production detection
│   └── rollback.py         # 7 rollback generators (decorator registry)
├── agent/                  # Execution engine
│   ├── loop.py             # Main agent loop (scan→plan→execute→observe→replan)
│   ├── executor.py         # Async subprocess with streaming + timeout
│   ├── observer.py         # Deterministic result analysis (no LLM)
│   ├── planner.py          # Plan generation + replanning (LLM calls)
│   └── budget.py           # Hard limits on steps, replans, LLM calls
├── memory/                 # Persistence
│   ├── history.py          # SQLite command history
│   ├── runbooks.py         # YAML runbook save/load
│   └── rag.py              # ChromaDB vector store (optional)
└── ui/                     # Terminal rendering
    ├── console.py          # Rich console
    ├── panels.py           # Plan display, summaries, environment view
    └── confirmations.py    # Tiered confirmation UX (safe → nuclear)
```

**3,152 lines** of production code across **56 modules**. **2,623 lines** of test code across **30 test files**. Test-to-code ratio: **0.83**.

## Development

```bash
git clone https://github.com/abhimanyubhagwati/orbit-cli.git
cd orbit-cli
pip install -e ".[dev]"
pytest
ruff check orbit/ tests/
mypy orbit/
```

## Contributing

Contributions welcome! Some areas that would benefit from help:

- **Safety patterns** — more command families, better disambiguation
- **Rollback generators** — Terraform, SQL, systemctl
- **Pipeline-aware classification** — `echo "rm -rf /" | bash` currently classifies as safe (matches `echo`)
- **Context collectors** — cloud provider CLIs (AWS, GCP, Azure)
- **Model mappings** — new Ollama models and their capabilities

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built by <a href="https://github.com/abhimanyubhagwati">Abhimanyu Bhagwati</a>
</p>
