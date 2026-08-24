from __future__ import annotations

import re
from dataclasses import dataclass

from .models import OperationClass, ToolInvocation, ToolResult


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    approval_required: bool
    reason: str


class BaselineInputGuard:
    """Deterministic baseline filter; replace with a managed guardrail adapter at installation time."""

    _injection_patterns = (
        re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
        re.compile(r"reveal\s+(the\s+)?(system|developer)\s+prompt", re.IGNORECASE),
        re.compile(r"bypass\s+(security|guardrails|policy)", re.IGNORECASE),
    )

    def screen(self, text: str) -> tuple[bool, str]:
        for pattern in self._injection_patterns:
            if pattern.search(text):
                return False, "input matched a blocked prompt-injection pattern"
        return True, "input accepted"


class BaselineOutputRedactor:
    """Redacts common token-like strings before a tool result re-enters context or egress."""

    _patterns = (
        re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
        re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_.-]+\.[A-Za-z0-9_.-]+\b"),
    )

    def redact(self, result: ToolResult) -> ToolResult:
        rendered = result.model_dump_json()
        for pattern in self._patterns:
            rendered = pattern.sub("[REDACTED]", rendered)
        return ToolResult.model_validate_json(rendered)


class ScopePolicy:
    def __init__(self, approval_required_operations: set[str]) -> None:
        self._approval_required = {OperationClass(value) for value in approval_required_operations}

    def evaluate(self, invocation: ToolInvocation, granted_scopes: set[str]) -> PolicyDecision:
        missing = invocation.required_scopes - granted_scopes
        if missing:
            return PolicyDecision(False, False, f"missing scopes: {', '.join(sorted(missing))}")
        if invocation.operation in self._approval_required:
            return PolicyDecision(True, True, f"{invocation.operation.value} requires human approval")
        return PolicyDecision(True, False, "scope and operation policy accepted")
