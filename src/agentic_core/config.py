from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class ServiceConfig(BaseModel):
    name: str = "agentic-core"
    environment: str = "development"


class PersistenceConfig(BaseModel):
    adapter: Literal["memory", "postgres", "redis"] = "memory"
    checkpoint_url: str = ""


class MemoryConfig(BaseModel):
    session_window_messages: int = Field(default=12, ge=1, le=1000)
    long_term_adapter: Literal["disabled", "pgvector", "qdrant"] = "disabled"
    vector_endpoint: str = ""


class ExecutionConfig(BaseModel):
    tool_executor: Literal["local", "mcp", "grpc"] = "local"
    isolation_adapter: Literal["local-contract", "container", "remote-sandbox"] = "local-contract"
    worker_queue: Literal["disabled", "celery", "bullmq", "nats"] = "disabled"


class TelemetryConfig(BaseModel):
    enabled: bool = True
    otlp_endpoint: str = ""


class SecurityConfig(BaseModel):
    input_guardrail: str = "baseline"
    output_redactor: str = "baseline"
    approval_required_operations: set[str] = {"write", "execute", "network", "financial"}


class AgenticConfig(BaseModel):
    service: ServiceConfig = ServiceConfig()
    persistence: PersistenceConfig = PersistenceConfig()
    memory: MemoryConfig = MemoryConfig()
    execution: ExecutionConfig = ExecutionConfig()
    telemetry: TelemetryConfig = TelemetryConfig()
    security: SecurityConfig = SecurityConfig()


def load_config(path: str | Path | None = None) -> AgenticConfig:
    if path is None:
        return AgenticConfig()
    source = Path(path)
    return AgenticConfig.model_validate(json.loads(source.read_text(encoding="utf-8")))
