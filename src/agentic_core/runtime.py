from __future__ import annotations

from typing import Protocol

from .config import AgenticConfig
from .graph import ExecutionGraph
from .models import (
    ApprovalRequest,
    Checkpoint,
    ExecutionRequest,
    ExecutionResult,
    NodeKind,
    PlanDecision,
    TaskStatus,
    TraceEvent,
)
from .security import BaselineInputGuard, BaselineOutputRedactor, ScopePolicy
from .state import CheckpointStore, DisabledLongTermMemory, LongTermMemory, SessionMemory
from .telemetry import TelemetrySink
from .tools import ToolExecutor, ToolRegistry


class Planner(Protocol):
    def decide(self, request: ExecutionRequest, context: list[str], tool_schemas: dict[str, dict[str, object]]) -> PlanDecision: ...


class AgentRuntime:
    """The generic graph runtime. Providers are injected; no external system is hard-coded."""

    def __init__(
        self,
        config: AgenticConfig,
        checkpoint_store: CheckpointStore,
        session_memory: SessionMemory,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
        telemetry: TelemetrySink,
        long_term_memory: LongTermMemory | None = None,
        input_guard: BaselineInputGuard | None = None,
        output_redactor: BaselineOutputRedactor | None = None,
    ) -> None:
        self.config = config
        self.checkpoints = checkpoint_store
        self.session_memory = session_memory
        self.tool_registry = tool_registry
        self.tool_executor = tool_executor
        self.telemetry = telemetry
        self.long_term_memory = long_term_memory or DisabledLongTermMemory()
        self.input_guard = input_guard or BaselineInputGuard()
        self.output_redactor = output_redactor or BaselineOutputRedactor()
        self.policy = ScopePolicy(config.security.approval_required_operations)
        self.graph = ExecutionGraph()

    def _emit(self, task_id: str, node: NodeKind, event: str, **attributes: object) -> None:
        self.telemetry.emit(TraceEvent(task_id=task_id, node=node, event=event, attributes=attributes))

    def _context(self, task_id: str) -> list[str]:
        latest = self.checkpoints.latest(task_id)
        if latest is not None:
            self.session_memory.restore(task_id, latest.session_context)
        return self.session_memory.snapshot(task_id)

    def _checkpoint(
        self,
        task_id: str,
        status: TaskStatus,
        node: NodeKind,
        *,
        decision: PlanDecision | None = None,
        pending_approval: ApprovalRequest | None = None,
        tool_result=None,
        reason: str,
    ) -> Checkpoint:
        history = self.checkpoints.history(task_id)
        self.graph.validate_transition(history[-1].node if history else None, node)
        checkpoint = Checkpoint(
            task_id=task_id,
            sequence=len(history) + 1,
            status=status,
            node=node,
            session_context=self.session_memory.snapshot(task_id),
            decision=decision,
            pending_approval=pending_approval,
            tool_result=tool_result,
            transition_reason=reason,
        )
        self.checkpoints.append(checkpoint)
        self._emit(task_id, node, "checkpoint", status=status.value, sequence=checkpoint.sequence)
        return checkpoint

    def start(self, request: ExecutionRequest, planner: Planner) -> ExecutionResult:
        accepted, reason = self.input_guard.screen(request.input_text)
        self.session_memory.add(request.task_id, request.input_text)
        if not accepted:
            checkpoint = self._checkpoint(request.task_id, TaskStatus.FAILED, NodeKind.INGRESS, reason=reason)
            return ExecutionResult(task_id=request.task_id, status=TaskStatus.FAILED, response_text=reason, checkpoint_sequence=checkpoint.sequence)

        self._checkpoint(request.task_id, TaskStatus.READY, NodeKind.INGRESS, reason="input accepted")
        context = self._context(request.task_id)
        context.extend(self.long_term_memory.retrieve(request.input_text))
        decision = planner.decide(request, context, self.tool_registry.schemas())
        self._emit(request.task_id, NodeKind.PLAN, "plan_selected", reason=decision.reason)
        self._checkpoint(request.task_id, TaskStatus.RUNNING, NodeKind.PLAN, decision=decision, reason=decision.reason)

        if decision.invocation is None:
            response = decision.response_text or "planner returned no tool call"
            self.session_memory.add(request.task_id, response)
            checkpoint = self._checkpoint(request.task_id, TaskStatus.SUCCEEDED, NodeKind.EGRESS, decision=decision, reason="response completed")
            return ExecutionResult(task_id=request.task_id, status=TaskStatus.SUCCEEDED, response_text=response, checkpoint_sequence=checkpoint.sequence)

        policy = self.policy.evaluate(decision.invocation, request.scopes)
        self._emit(request.task_id, NodeKind.POLICY, "policy_evaluated", allowed=policy.allowed, approval_required=policy.approval_required)
        if not policy.allowed:
            checkpoint = self._checkpoint(request.task_id, TaskStatus.FAILED, NodeKind.POLICY, decision=decision, reason=policy.reason)
            return ExecutionResult(task_id=request.task_id, status=TaskStatus.FAILED, response_text=policy.reason, checkpoint_sequence=checkpoint.sequence)
        if policy.approval_required:
            approval = ApprovalRequest(
                task_id=request.task_id,
                tool_name=decision.invocation.tool_name,
                operation=decision.invocation.operation,
                reason=policy.reason,
            )
            checkpoint = self._checkpoint(
                request.task_id,
                TaskStatus.PAUSED,
                NodeKind.APPROVAL,
                decision=decision,
                pending_approval=approval,
                reason=policy.reason,
            )
            return ExecutionResult(
                task_id=request.task_id,
                status=TaskStatus.PAUSED,
                pending_approval=approval,
                checkpoint_sequence=checkpoint.sequence,
            )
        self._checkpoint(request.task_id, TaskStatus.RUNNING, NodeKind.POLICY, decision=decision, reason=policy.reason)
        return self._execute(request.task_id, decision)

    def resume(self, task_id: str, approval_id: str, approved: bool) -> ExecutionResult:
        latest = self.checkpoints.latest(task_id)
        if latest is None or latest.status != TaskStatus.PAUSED or latest.pending_approval is None or latest.decision is None:
            raise ValueError("task has no pending approval")
        if latest.pending_approval.approval_id != approval_id:
            raise ValueError("approval identifier does not match pending task")
        self._context(task_id)
        if not approved:
            checkpoint = self._checkpoint(task_id, TaskStatus.FAILED, NodeKind.APPROVAL, decision=latest.decision, reason="human approval denied")
            return ExecutionResult(task_id=task_id, status=TaskStatus.FAILED, response_text="human approval denied", checkpoint_sequence=checkpoint.sequence)
        self._checkpoint(task_id, TaskStatus.RUNNING, NodeKind.APPROVAL, decision=latest.decision, reason="human approval granted")
        return self._execute(task_id, latest.decision)

    def _execute(self, task_id: str, decision: PlanDecision) -> ExecutionResult:
        assert decision.invocation is not None
        self._emit(task_id, NodeKind.TOOL, "tool_execution_started", tool=decision.invocation.tool_name)
        result = self.output_redactor.redact(self.tool_executor.execute(decision.invocation))
        self.session_memory.add(task_id, result.model_dump_json())
        status = TaskStatus.RUNNING if result.success else TaskStatus.FAILED
        self._checkpoint(task_id, status, NodeKind.TOOL, decision=decision, tool_result=result, reason=result.message)
        final_status = TaskStatus.SUCCEEDED if result.success else TaskStatus.FAILED
        checkpoint = self._checkpoint(task_id, final_status, NodeKind.EGRESS, decision=decision, tool_result=result, reason="tool execution completed")
        return ExecutionResult(task_id=task_id, status=final_status, tool_result=result, checkpoint_sequence=checkpoint.sequence)

    def history(self, task_id: str) -> list[Checkpoint]:
        return self.checkpoints.history(task_id)
