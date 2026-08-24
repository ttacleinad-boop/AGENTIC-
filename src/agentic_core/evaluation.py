from __future__ import annotations

from dataclasses import dataclass

from .demo import DeterministicPlanner, build_demo_runtime
from .models import ExecutionRequest, TaskStatus


@dataclass(frozen=True)
class EvaluationCase:
    name: str
    passed: bool
    detail: str


def run_golden_evaluations() -> list[EvaluationCase]:
    planner = DeterministicPlanner()
    cases: list[EvaluationCase] = []

    runtime = build_demo_runtime()
    read = runtime.start(ExecutionRequest(principal="eval", input_text="read:hello", scopes={"notes:read"}), planner)
    cases.append(EvaluationCase("read_tool_selection", read.status == TaskStatus.SUCCEEDED and read.tool_result is not None, "read tool completes with required scope"))

    runtime = build_demo_runtime()
    missing_scope = runtime.start(ExecutionRequest(principal="eval", input_text="read:hello", scopes=set()), planner)
    cases.append(EvaluationCase("scope_enforcement", missing_scope.status == TaskStatus.FAILED, "missing required scope fails before tool execution"))

    runtime = build_demo_runtime()
    paused = runtime.start(ExecutionRequest(principal="eval", input_text="write:hello", scopes={"notes:write"}), planner)
    resumed = runtime.resume(paused.task_id, paused.pending_approval.approval_id, approved=True) if paused.pending_approval else None
    cases.append(EvaluationCase("approval_pause_and_resume", paused.status == TaskStatus.PAUSED and resumed is not None and resumed.status == TaskStatus.SUCCEEDED, "write pauses until approval then resumes from checkpoint"))

    runtime = build_demo_runtime()
    denied = runtime.start(ExecutionRequest(principal="eval", input_text="write:hello", scopes={"notes:write"}), planner)
    denied_result = runtime.resume(denied.task_id, denied.pending_approval.approval_id, approved=False) if denied.pending_approval else None
    cases.append(EvaluationCase("approval_denial", denied_result is not None and denied_result.status == TaskStatus.FAILED, "denied approval prevents tool execution"))

    return cases


def evaluation_report() -> dict[str, object]:
    cases = run_golden_evaluations()
    return {
        "overall": "PASS" if all(case.passed for case in cases) else "FAIL",
        "cases": [case.__dict__ for case in cases],
    }
