import os
from contextlib import contextmanager
from time import time

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

_tracer_initialized = False


def init_tracer(service_name: str = "signet-protocol"):
    global _tracer_initialized
    if _tracer_initialized:
        return
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")  # optional
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    if endpoint:
        try:
            exporter = OTLPSpanExporter(endpoint=endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except Exception:
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    else:
        # No endpoint configured; default to console exporter (no network IO)
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    _tracer_initialized = True


@contextmanager
def start_span(name: str):
    tracer = trace.get_tracer("signet.protocol")
    with tracer.start_as_current_span(name) as span:
        t0 = time()
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_attribute("error", True)
            raise
        finally:
            span.set_attribute("duration_ms", (time() - t0) * 1000.0)


# Convenience wrapper to annotate phase latency
@contextmanager
def phase(name: str):
    with start_span(f"exchange.phase.{name}") as span:
        yield span
