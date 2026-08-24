from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

from .models import ToolInvocation, ToolResult

InputModel = TypeVar("InputModel", bound=BaseModel)
OutputModel = TypeVar("OutputModel", bound=BaseModel)


class ToolExecutor(Protocol):
    def execute(self, invocation: ToolInvocation) -> ToolResult: ...


@dataclass(frozen=True)
class RegisteredTool:
    name: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    handler: Callable[[BaseModel], BaseModel]


class ToolRegistry:
    """Validated local adapter. Replace the executor, not the policy or orchestration contracts."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(
        self,
        name: str,
        input_model: type[InputModel],
        output_model: type[OutputModel],
        handler: Callable[[InputModel], OutputModel],
    ) -> None:
        if name in self._tools:
            raise ValueError(f"tool already registered: {name}")
        self._tools[name] = RegisteredTool(name, input_model, output_model, handler)

    def schemas(self) -> dict[str, dict[str, object]]:
        return {
            name: {
                "input": tool.input_model.model_json_schema(),
                "output": tool.output_model.model_json_schema(),
            }
            for name, tool in self._tools.items()
        }

    def execute(self, invocation: ToolInvocation) -> ToolResult:
        tool = self._tools.get(invocation.tool_name)
        if tool is None:
            return ToolResult(success=False, error_code="tool_not_found", message="tool is not registered")
        try:
            validated_input = tool.input_model.model_validate(invocation.payload)
            validated_output = tool.handler(validated_input)
            output = tool.output_model.model_validate(validated_output)
            return ToolResult(success=True, output=output.model_dump(), message="tool completed")
        except Exception as exc:
            return ToolResult(success=False, error_code="tool_execution_failed", message=str(exc))


class LocalToolExecutor:
    """Local development executor. Production isolation is installed as an adapter, not bypassed."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def execute(self, invocation: ToolInvocation) -> ToolResult:
        return self._registry.execute(invocation)
