# Orbit

**Local-first, multi-model DevOps CLI agent.**

[![PyPI version](https://img.shields.io/pypi/v/orbit-cli.svg)](https://pypi.org/project/orbit-cli/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

Orbit turns natural language into safe, observable DevOps actions. It decomposes goals into plans, picks the best local model for each step, and executes with a 4-tier safety system — all running against your own Ollama instance.

## Features

- **Multi-model routing** — automatically selects the best locally-available model for each subtask (coding, ops, analysis)
- **4-tier safety system** — every command is classified as safe, caution, destructive, or nuclear before execution
- **Auto-replan** — observes command output and adjusts the plan when things go wrong
- **Context-aware** — scans your git state, Docker containers, Kubernetes clusters, and system environment
- **Command history** — searchable SQLite-backed history of every action taken
- **Runbook capture** — record successful workflows as replayable YAML runbooks
- **Streaming output** — real-time LLM and subprocess output in a Rich terminal UI

## Installation

```bash
pip install orbit-cli
```

### Requirements

- Python 3.11+
- [Ollama](https://ollama.ai) running locally with at least one model pulled (e.g. `ollama pull qwen2.5:7b`)

## Quick Start

### Execute a goal

```bash
orbit do "find large files in this repo and show disk usage by directory"
```

Orbit will decompose the goal, build a plan, ask for confirmation on risky steps, execute, and replan if needed.

### Scan your environment

```bash
orbit sense
```

Collects context from git, Docker, Kubernetes, and system — shows what Orbit sees before planning.

### Debug the last failure

```bash
orbit wtf
```

Analyzes the most recent failed command with full context and suggests fixes.

### Ask a question

```bash
orbit ask "what Kubernetes pods are in CrashLoopBackOff and why?"
```

One-shot question answering with environment context.

### Check configuration

```bash
orbit config doctor
```

Verifies Ollama connectivity, available models, and configuration health.

## Safety Tiers

| Tier | Behavior | Examples |
|------|----------|---------|
| **safe** | Execute silently | `ls`, `cat`, `kubectl get`, `docker ps` |
| **caution** | Single confirmation | `git push`, `docker build`, `kubectl apply` |
| **destructive** | Impact analysis + double confirm | `rm`, `kubectl delete`, `git reset --hard` |
| **nuclear** | Type confirmation + cooldown | Destructive in production context |

Production detection automatically escalates destructive commands to nuclear when it detects a production environment (main/master branch, prod namespace, etc.).

## Configuration

Orbit stores its configuration at `~/.orbit/config.toml`. Run `orbit config doctor` to check your setup.

Key settings:

```toml
[llm]
provider = "ollama"          # ollama, openai, or anthropic
base_url = "http://localhost:11434"

[safety]
default_tier = "caution"     # for unrecognized commands

[agent]
max_steps = 15               # hard budget per goal
max_replans = 3              # retries per step
max_llm_calls = 25           # total LLM calls per goal
```

## Optional Extras

```bash
pip install orbit-cli[rag]        # ChromaDB for semantic memory
pip install orbit-cli[openai]     # OpenAI provider
pip install orbit-cli[anthropic]  # Anthropic provider
pip install orbit-cli[all]        # everything
```

## Development

```bash
git clone https://github.com/abhimanyubhagwati/orbit-cli.git
cd orbit-cli
pip install -e ".[dev]"
pytest
ruff check orbit/ tests/
mypy orbit/
```

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
