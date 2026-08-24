from __future__ import annotations

from .models import NodeKind


class ExecutionGraph:
    """Static DAG-like execution topology with the single approval-resume loop declared explicitly."""

    _edges: dict[NodeKind, set[NodeKind]] = {
        NodeKind.INGRESS: {NodeKind.PLAN},
        NodeKind.PLAN: {NodeKind.POLICY, NodeKind.APPROVAL, NodeKind.TOOL, NodeKind.EGRESS},
        NodeKind.POLICY: {NodeKind.APPROVAL, NodeKind.TOOL, NodeKind.EGRESS},
        NodeKind.APPROVAL: {NodeKind.APPROVAL, NodeKind.TOOL, NodeKind.EGRESS},
        NodeKind.TOOL: {NodeKind.EGRESS},
        NodeKind.CHECKPOINT: set(),
        NodeKind.EGRESS: set(),
    }

    def validate_transition(self, previous: NodeKind | None, current: NodeKind) -> None:
        if previous is None:
            if current != NodeKind.INGRESS:
                raise ValueError("execution must begin at ingress")
            return
        if current not in self._edges[previous]:
            raise ValueError(f"invalid execution transition: {previous.value} -> {current.value}")
