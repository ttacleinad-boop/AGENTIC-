from __future__ import annotations

from typing import Protocol

from opentelemetry import trace

from .models import TraceEvent


class TelemetrySink(Protocol):
    def emit(self, event: TraceEvent) -> None: ...


class InMemoryTelemetry:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def emit(self, event: TraceEvent) -> None:
        self.events.append(event)


class OpenTelemetryEmitter:
    """Emits standard spans while retaining no production exporter configuration in source."""

    def __init__(self, tracer_name: str = "agentic-core") -> None:
        self._tracer = trace.get_tracer(tracer_name)

    def emit(self, event: TraceEvent) -> None:
        with self._tracer.start_as_current_span(event.event) as span:
            span.set_attribute("agentic.task_id", event.task_id)
            span.set_attribute("agentic.node", event.node.value)
            for key, value in event.attributes.items():
                span.set_attribute(f"agentic.{key}", str(value))
