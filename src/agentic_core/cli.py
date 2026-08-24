from __future__ import annotations

import argparse
import json

from .demo import DeterministicPlanner, build_demo_runtime
from .evaluation import evaluation_report
from .models import ExecutionRequest


def main() -> None:
    parser = argparse.ArgumentParser(description="AGENTIC Core generic platform")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="Show installed generic platform capabilities")
    subparsers.add_parser("evaluate", help="Run static golden trajectory evaluations")
    demo = subparsers.add_parser("demo", help="Run the deterministic local lifecycle demo")
    demo.add_argument("--input", default="write:example approval-gated operation")

    args = parser.parse_args()
    if args.command == "status":
        result = {
            "status": "ready",
            "adapters": {
                "checkpoint_store": "memory",
                "long_term_memory": "disabled",
                "tool_executor": "local",
                "telemetry": "in_memory",
            },
            "install_time_adapters": ["postgres", "redis", "pgvector", "qdrant", "mcp", "grpc", "container", "worker_queue"],
        }
    elif args.command == "evaluate":
        result = evaluation_report()
    else:
        runtime = build_demo_runtime()
        request = ExecutionRequest(principal="demo", input_text=args.input, scopes={"notes:read", "notes:write"})
        initial = runtime.start(request, DeterministicPlanner())
        result = {"initial": initial.model_dump(mode="json"), "history": [item.model_dump(mode="json") for item in runtime.history(request.task_id)]}
        if initial.pending_approval:
            resumed = runtime.resume(request.task_id, initial.pending_approval.approval_id, approved=True)
            result["resumed"] = resumed.model_dump(mode="json")
            result["history"] = [item.model_dump(mode="json") for item in runtime.history(request.task_id)]
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
