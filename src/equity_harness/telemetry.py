from __future__ import annotations

import os
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.trace import Tracer

_PROVIDER: TracerProvider | None = None


def setup_telemetry(service_name: str | None = None) -> Tracer:
    """Export OTLP when OTEL_EXPORTER_OTLP_ENDPOINT is set; otherwise in-process no export."""
    global _PROVIDER
    name = (service_name or os.environ.get("OTEL_SERVICE_NAME") or "equity-harness").strip()
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    resource = Resource.create({"service.name": name})
    provider = TracerProvider(resource=resource)
    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        exporter: SpanExporter = OTLPSpanExporter(endpoint=_traces_endpoint(endpoint))
        provider.add_span_processor(BatchSpanProcessor(exporter))
    _PROVIDER = provider
    trace.set_tracer_provider(provider)
    return trace.get_tracer("equity_harness")


def _traces_endpoint(base: str) -> str:
    base = base.rstrip("/")
    if base.endswith("/v1/traces"):
        return base
    return f"{base}/v1/traces"


def shutdown_telemetry() -> None:
    global _PROVIDER
    if _PROVIDER is None:
        return
    _PROVIDER.force_flush(timeout_millis=5000)
    _PROVIDER.shutdown()
    _PROVIDER = None
