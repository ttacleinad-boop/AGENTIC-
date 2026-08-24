from __future__ import annotations

from pydantic import BaseModel, Field

from .config import AgenticConfig
from .models import ExecutionRequest, OperationClass, PlanDecision, ToolInvocation
from .runtime import AgentRuntime, Planner
from .state import InMemoryCheckpointStore, SessionMemory
from .telemetry import InMemoryTelemetry
from .tools import LocalToolExecutor, ToolRegistry


class EchoInput(BaseModel):
    message: str = Field(min_length=1)


class EchoOutput(BaseModel):
    message: str


class DeterministicPlanner(Planner):
    """A test-only planner showing contract shape; install a real model adapter later."""

    def decide(self, request: ExecutionRequest, context: list[str], tool_schemas: dict[str, dict[str, object]]) -> PlanDecision:
        if request.input_text.startswith("respond:"):
            return PlanDecision(response_text=request.input_text.removeprefix("respond:").strip(), reason="direct response route")
        operation = OperationClass.WRITE if request.input_text.startswith("write:") else OperationClass.READ
        required_scopes = {"notes:write"} if operation == OperationClass.WRITE else {"notes:read"}
        payload = {"message": request.input_text.split(":", 1)[-1].strip()}
        return PlanDecision(
            invocation=ToolInvocation(
                tool_name="echo",
                operation=operation,
                required_scopes=required_scopes,
                payload=payload,
            ),
            reason="deterministic example tool selection",
        )


def build_demo_runtime(config: AgenticConfig | None = None) -> AgentRuntime:
    config = config or AgenticConfig()
    registry = ToolRegistry()
    registry.register("echo", EchoInput, EchoOutput, lambda payload: EchoOutput(message=payload.message))
    return AgentRuntime(
        config=config,
        checkpoint_store=InMemoryCheckpointStore(),
        session_memory=SessionMemory(config.memory.session_window_messages),
        tool_registry=registry,
        tool_executor=LocalToolExecutor(registry),
        telemetry=InMemoryTelemetry(),
    )
