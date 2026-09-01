import time
from typing import Any, Dict, List

from logging_config import get_logger
from monitoring.metrics import (
    LATENCY_END_TO_END,
    LATENCY_LLM_TTFT,
    LATENCY_STT,
    LATENCY_TTS_FIRST_BYTE,
)

logger = get_logger("analytics")


class CallAnalyticsTracker:
    """Production Real-Time Call Latency & Turn Analytics Tracker."""

    def __init__(self, call_id: str):
        self.call_id = call_id
        self.start_time = time.monotonic()
        self.turn_latencies: List[float] = []
        self.stt_latencies: List[float] = []
        self.llm_ttft_latencies: List[float] = []
        self.tts_first_byte_latencies: List[float] = []
        self.interruption_count = 0
        self.turn_count = 0

    def record_stt_latency(self, latency_ms: float) -> None:
        self.stt_latencies.append(latency_ms)
        LATENCY_STT.observe(latency_ms / 1000.0)

    def record_llm_ttft(self, ttft_ms: float) -> None:
        self.llm_ttft_latencies.append(ttft_ms)
        LATENCY_LLM_TTFT.observe(ttft_ms / 1000.0)

    def record_tts_first_byte(self, latency_ms: float) -> None:
        self.tts_first_byte_latencies.append(latency_ms)
        LATENCY_TTS_FIRST_BYTE.observe(latency_ms / 1000.0)

    def record_turn_end_to_end(self, total_latency_ms: float) -> None:
        self.turn_count += 1
        self.turn_latencies.append(total_latency_ms)
        LATENCY_END_TO_END.observe(total_latency_ms / 1000.0)
        logger.info(
            f"Turn {self.turn_count} End-to-End Latency: {total_latency_ms:.2f}ms",
            call_id=self.call_id,
            latency_ms=total_latency_ms,
        )

    def record_interruption(self) -> None:
        self.interruption_count += 1

    def get_summary(self) -> Dict[str, Any]:
        duration_sec = time.monotonic() - self.start_time
        avg_latency = (
            (sum(self.turn_latencies) / len(self.turn_latencies)) if self.turn_latencies else 0.0
        )

        sorted_latencies = sorted(self.turn_latencies)
        p95_index = int(len(sorted_latencies) * 0.95) if sorted_latencies else 0
        p95_latency = sorted_latencies[p95_index] if sorted_latencies else 0.0

        return {
            "call_id": self.call_id,
            "total_duration_sec": round(duration_sec, 2),
            "turn_count": self.turn_count,
            "interruption_count": self.interruption_count,
            "avg_latency_ms": round(avg_latency, 2),
            "p95_latency_ms": round(p95_latency, 2),
        }
