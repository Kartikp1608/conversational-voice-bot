from prometheus_client import Counter, Gauge, Histogram

# Voice AI System Performance Metrics

ACTIVE_CALLS = Gauge("voice_ai_active_calls", "Number of currently active voice call sessions")

TOTAL_CALLS = Counter(
    "voice_ai_calls_total", "Total number of initiated calls", ["direction", "status"]
)

INTERRUPTIONS_COUNT = Counter(
    "voice_ai_interruptions_total", "Total user barge-in interruptions triggered", ["session_id"]
)

LATENCY_END_TO_END = Histogram(
    "voice_ai_end_to_end_latency_seconds",
    "End to end latency from user silence to first TTS audio playback byte",
    buckets=[0.1, 0.25, 0.4, 0.6, 0.8, 1.0, 1.5, 2.0, 3.0],
)

LATENCY_STT = Histogram(
    "voice_ai_stt_latency_seconds",
    "Latency of Speech-to-Text streaming recognition",
    buckets=[0.05, 0.1, 0.2, 0.3, 0.5, 1.0],
)

LATENCY_LLM_TTFT = Histogram(
    "voice_ai_llm_ttft_seconds",
    "Time to first token (TTFT) from LLM generation",
    buckets=[0.05, 0.1, 0.2, 0.3, 0.5, 0.8, 1.2],
)

LATENCY_TTS_FIRST_BYTE = Histogram(
    "voice_ai_tts_first_byte_seconds",
    "Time to first audio byte from TTS synthesis",
    buckets=[0.05, 0.1, 0.2, 0.3, 0.5, 0.8],
)

TOOL_EXECUTIONS = Counter(
    "voice_ai_tool_executions_total", "Total tool executions", ["tool_name", "status"]
)
