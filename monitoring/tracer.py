import typing
from logging_config import get_logger

logger = get_logger("tracer")

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

_tracer_initialized = False


def init_tracer(service_name: str = "voice-ai-platform"):
    """Initialize OpenTelemetry tracer provider if installed."""
    global _tracer_initialized
    if OTEL_AVAILABLE and not _tracer_initialized:
        try:
            resource = Resource.create({"service.name": service_name})
            provider = TracerProvider(resource=resource)
            processor = BatchSpanProcessor(ConsoleSpanExporter())
            provider.add_span_processor(processor)
            trace.set_tracer_provider(provider)
            _tracer_initialized = True
        except Exception as e:
            logger.warning("Failed to initialize OpenTelemetry tracer", error=str(e))
    return get_tracer(service_name)


def get_tracer(service_name: str = "voice-ai-platform"):
    if OTEL_AVAILABLE:
        return trace.get_tracer(service_name)
    return None
