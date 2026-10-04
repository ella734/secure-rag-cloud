"""LLMOps Observability, OpenTelemetry Tracing, and Structured Logging for Azure Monitor."""

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from app.core.config import settings

# Context variable for request correlation tracking
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="system-init")


class JsonFormatter(logging.Formatter):
    """Formats log records into structured JSON compliant with Azure Log Analytics."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_ctx.get(),
            "service": settings.otel_service_name,
            "environment": settings.environment,
        }

        # Include custom extra attributes if supplied
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_obj["data"] = record.extra_data

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, ensure_ascii=False)


def setup_logging() -> logging.Logger:
    """Configure structured JSON logging to stdout."""
    logger = logging.getLogger("secure_rag")
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger


logger = setup_logging()


def setup_telemetry() -> trace.Tracer:
    """Initialize OpenTelemetry tracer and configure Azure Application Insights if available."""
    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)

    # Optional Azure Monitor / Application Insights integration
    if settings.applicationinsights_connection_string:
        try:
            from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
            exporter = AzureMonitorTraceExporter(
                connection_string=settings.applicationinsights_connection_string
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info("Azure Application Insights OpenTelemetry exporter connected.")
        except ImportError:
            logger.warning("azure-monitor-opentelemetry not installed; falling back to Console tracer.")
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    else:
        # Simple span processor without background thread shutdown race conditions
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    return trace.get_tracer(settings.otel_service_name)


tracer = setup_telemetry()


class MetricsTracker:
    """In-memory operational metrics collector for LLMOps dashboards."""

    def __init__(self):
        self.total_queries = 0
        self.blocked_queries = 0
        self.refusals = 0
        self.retrieval_latencies = []
        self.generation_latencies = []

    def record_query(
        self,
        retrieval_ms: float,
        generation_ms: float,
        is_refusal: bool = False,
        is_blocked: bool = False,
    ):
        self.total_queries += 1
        if is_blocked:
            self.blocked_queries += 1
            return

        if is_refusal:
            self.refusals += 1

        self.retrieval_latencies.append(retrieval_ms)
        self.generation_latencies.append(generation_ms)

        # Cap memory buffer
        if len(self.retrieval_latencies) > 1000:
            self.retrieval_latencies = self.retrieval_latencies[-1000:]
            self.generation_latencies = self.generation_latencies[-1000:]

    def get_summary(self) -> Dict[str, Any]:
        """Compute aggregated operational metrics."""
        import numpy as np

        ret_p50 = float(np.median(self.retrieval_latencies)) if self.retrieval_latencies else 0.0
        ret_p95 = float(np.percentile(self.retrieval_latencies, 95)) if self.retrieval_latencies else 0.0
        gen_p50 = float(np.median(self.generation_latencies)) if self.generation_latencies else 0.0
        gen_p95 = float(np.percentile(self.generation_latencies, 95)) if self.generation_latencies else 0.0

        block_rate = (self.blocked_queries / self.total_queries * 100) if self.total_queries > 0 else 0.0
        refusal_rate = (self.refusals / self.total_queries * 100) if self.total_queries > 0 else 0.0

        return {
            "total_queries": self.total_queries,
            "blocked_adversarial_queries": self.blocked_queries,
            "block_rate_pct": round(block_rate, 2),
            "refusal_rate_pct": round(refusal_rate, 2),
            "retrieval_latency_ms": {"p50": round(ret_p50, 2), "p95": round(ret_p95, 2)},
            "generation_latency_ms": {"p50": round(gen_p50, 2), "p95": round(gen_p95, 2)},
        }


metrics_tracker = MetricsTracker()
