import asyncio

from logging_config import get_logger
from monitoring.metrics import INTERRUPTIONS_COUNT
from utils.async_helpers import BoundedAudioQueue, CancellationToken

logger = get_logger("interruptions.manager")


class InterruptManager:
    """Production Interruption & Barge-in Handling Engine.
    Instantly stops TTS playback stream, cancels in-flight LLM token generation, flushes audio buffers, and notifies metrics.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.current_token: CancellationToken | None = None
        self.current_llm_task: asyncio.Task | None = None
        self.current_tts_task: asyncio.Task | None = None

    def create_token(self) -> CancellationToken:
        """Create new active turn cancellation token."""
        self.current_token = CancellationToken()
        return self.current_token

    def trigger_interruption(self, audio_queue: BoundedAudioQueue | None = None) -> int:
        """Execute barge-in cut-off sequence immediately on user speech detection.
        Returns count of dropped audio frames flushed from buffer.
        """
        logger.info("⚡ BARGE-IN TRIGGERED: Aborting ongoing response generation & audio playback")

        # 1. Cancel token
        if self.current_token:
            self.current_token.cancel()

        # 2. Cancel LLM task if active
        if self.current_llm_task and not self.current_llm_task.done():
            self.current_llm_task.cancel()

        # 3. Cancel TTS task if active
        if self.current_tts_task and not self.current_tts_task.done():
            self.current_tts_task.cancel()

        # 4. Flush outbound audio buffer queue
        flushed_frames = 0
        if audio_queue:
            flushed_frames = audio_queue.clear()

        # 5. Record interruption metric
        INTERRUPTIONS_COUNT.labels(session_id=self.session_id).inc()

        return flushed_frames
