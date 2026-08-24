from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    RECEIVED = "received"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class OperationClass(str, Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    FINANCIAL = "financial"


class NodeKind(str, Enum):
    INGRESS = "ingress"
    PLAN = "plan"
    POLICY = "policy"
    APPROVAL = "approval"
    TOOL = "tool"
    CHECKPOINT = "checkpoint"
    EGRESS = "egress"


class ExecutionRequest(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    principal: str = Field(min_length=1)
    input_text: str = Field(min_length=1)
    scopes: set[str] = Field(default_factory=set)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolInvocation(BaseModel):
    tool_name: str = Field(min_length=1)
    operation: OperationClass
    required_scopes: set[str] = Field(default_factory=set)
    payload: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    success: bool
    output: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    message: str = ""


class PlanDecision(BaseModel):
    invocation: ToolInvocation | None = None
    response_text: str | None = None
    reason: str = ""


class ApprovalRequest(BaseModel):
    approval_id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str
    tool_name: str
    operation: OperationClass
    reason: str
    requested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Checkpoint(BaseModel):
    task_id: str
    sequence: int
    status: TaskStatus
    node: NodeKind
    session_context: list[str] = Field(default_factory=list)
    decision: PlanDecision | None = None
    tool_result: ToolResult | None = None
    pending_approval: ApprovalRequest | None = None
    transition_reason: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TraceEvent(BaseModel):
    task_id: str
    node: NodeKind
    event: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ExecutionResult(BaseModel):
    task_id: str
    status: TaskStatus
    response_text: str | None = None
    tool_result: ToolResult | None = None
    pending_approval: ApprovalRequest | None = None
    checkpoint_sequence: int
