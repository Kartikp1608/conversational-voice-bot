import time
from analytics.call_analytics import CallAnalyticsTracker


def test_call_analytics_tracker_full_cycle():
    tracker = CallAnalyticsTracker(call_id="call-analytics-1")

    # Record individual latency components
    tracker.record_stt_latency(35.0)
    tracker.record_llm_ttft(120.0)
    tracker.record_tts_first_byte(65.0)
    tracker.record_turn_end_to_end(220.0)

    tracker.record_stt_latency(40.0)
    tracker.record_llm_ttft(150.0)
    tracker.record_tts_first_byte(70.0)
    tracker.record_turn_end_to_end(260.0)

    tracker.record_interruption()
    tracker.record_interruption()

    summary = tracker.get_summary()

    assert summary["call_id"] == "call-analytics-1"
    assert summary["turn_count"] == 2
    assert summary["interruption_count"] == 2
    assert summary["avg_latency_ms"] == 240.0
    assert summary["p95_latency_ms"] >= 240.0
    assert summary["total_duration_sec"] >= 0.0


def test_call_analytics_empty_summary():
    tracker = CallAnalyticsTracker(call_id="call-empty")
    summary = tracker.get_summary()
    assert summary["turn_count"] == 0
    assert summary["avg_latency_ms"] == 0.0
    assert summary["p95_latency_ms"] == 0.0
