# AGENTIC Core

AGENTIC Core is a **source-independent agentic AI foundation**. It supplies deterministic execution state, validation contracts, tool governance, human approval gates, telemetry, and evaluation boundaries now. Real tools, databases, vector stores, identity providers, model endpoints, and production secrets are installed later through configuration and adapters.

## Implemented Foundation

| Layer | Delivered boundary |
|---|---|
| State and orchestration | Deterministic graph transitions, durable checkpoint-store interface, recovery/retry state, and time-ordered history. |
| Memory | Session sliding window plus long-term memory-provider interface. No vector database or data is embedded. |
| Tool execution | Pydantic-validated tool contracts, MCP-compatible adapter boundary, and isolated-executor interface. |
| Security and control | Per-step scopes, policy checks, human-approval pause state, input screening, and output secret/PII redaction interface. |
| Telemetry and evaluation | OpenTelemetry-compatible trace boundary, step metrics, and static golden-trajectory assertions. |
| Infrastructure | Local deterministic execution by default; install-time configuration declares PostgreSQL, Redis, container, or worker adapters without hard-coding any one provider. |

## Single Execution Lifecycle

1. **Ingress and safety:** validate the request, start a trace, screen input, and load the last checkpoint.
2. **Reasoning and tool selection:** invoke an injected planner using session context and registered tool schemas.
3. **Policy and approval:** verify the exact per-step scope; pause on high-impact actions pending explicit approval.
4. **Isolated execution:** submit the validated payload to the configured tool executor and validate its output before context insertion.
5. **Checkpoint and egress:** persist the transition, update session memory, emit metrics, and return the standard result envelope.

The initial repository contains only in-memory/local adapters so the execution contract can be verified without external systems. Production adapters are an install-time change, not a different architecture.

## MCP Surface

The included MCP server exposes only generic platform controls:

| Tool | Purpose |
|---|---|
| `core_status` | Reports local adapters and declared install-time extension points. |
| `core_evaluate` | Runs static golden trajectory evaluations. |
| `core_demo` | Demonstrates a deterministic tool call, approval pause, checkpoint recovery, and egress. |

Run it locally with:

```bash
mcp run server.py
```

## Install

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -p "test_*.py"
```

On Windows PowerShell:

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e .
python -m unittest discover -s tests -p "test_*.py"
```

## Configuration

Copy `config.example.json` to `config.json` and set only adapter names and public endpoints. Do not commit secrets. Production deployments must provide secrets through their deployment environment.

## Current Non-Goals

This foundation does **not** include a live model provider, external tool credentials, a production database, a vector database, container host, Kubernetes cluster, worker queue, or identity provider. Those require verified source-system and deployment information. The interfaces needed to install them are included.

## Validation

```bash
agentic-core demo
agentic-core evaluate
agentic-core status
```

The demo proves the lifecycle, including a human-approval pause and resumable checkpoint flow, using only local deterministic adapters.
