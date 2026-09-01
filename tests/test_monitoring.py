from monitoring.tracer import init_tracer, get_tracer
from monitoring.metrics import (
    ACTIVE_CALLS,
    TOTAL_CALLS,
    INTERRUPTIONS_COUNT,
    TOOL_EXECUTIONS,
    LATENCY_END_TO_END,
)


def test_tracer_initialization():
    tracer = init_tracer("test-service")
    # Returns trace object if OTEL is installed or None
    same_tracer = get_tracer("test-service")
    assert tracer == same_tracer


def test_prometheus_metrics_manipulation():
    ACTIVE_CALLS.set(5)
    assert ACTIVE_CALLS._value.get() == 5
    ACTIVE_CALLS.dec(2)
    assert ACTIVE_CALLS._value.get() == 3

    TOTAL_CALLS.labels(direction="outbound", status="success").inc(3)
    INTERRUPTIONS_COUNT.labels(session_id="sess-mon-1").inc()
    TOOL_EXECUTIONS.labels(tool_name="book_appointment", status="success").inc()
    LATENCY_END_TO_END.observe(0.450)
