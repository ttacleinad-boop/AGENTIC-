from __future__ import annotations

from typing import Any

from mcp.server import MCPServer

from .demo import DeterministicPlanner, build_demo_runtime
from .evaluation import evaluation_report
from .models import ExecutionRequest

mcp = MCPServer("AGENTIC Core")


@mcp.tool()
def core_status() -> dict[str, Any]:
    """Return the generic platform’s installed local adapters and install-time extension points."""
    return {
        "status": "ready",
        "local_adapters": {
            "checkpoint_store": "memory",
            "long_term_memory": "disabled",
            "tool_executor": "local",
            "telemetry": "in_memory",
        },
        "install_time_adapters": ["postgres", "redis", "pgvector", "qdrant", "mcp", "grpc", "container", "worker_queue"],
    }


@mcp.tool()
def core_evaluate() -> dict[str, object]:
    """Run the static golden trajectory evaluation suite."""
    return evaluation_report()


@mcp.tool()
def core_demo(input_text: str) -> dict[str, Any]:
    """Run a deterministic, local lifecycle demonstration with approval-resume behavior."""
    runtime = build_demo_runtime()
    request = ExecutionRequest(principal="mcp-client", input_text=input_text, scopes={"notes:read", "notes:write"})
    initial = runtime.start(request, DeterministicPlanner())
    result: dict[str, Any] = {"initial": initial.model_dump(mode="json")}
    if initial.pending_approval:
        result["resumed"] = runtime.resume(request.task_id, initial.pending_approval.approval_id, approved=True).model_dump(mode="json")
    result["history"] = [checkpoint.model_dump(mode="json") for checkpoint in runtime.history(request.task_id)]
    return result
