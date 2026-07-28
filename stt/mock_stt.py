import asyncio
import time
from typing import Callable, Awaitable, Optional
from stt.base_stt import BaseSTT, STTResult
from logging_config import get_logger

logger = get_logger("stt.mock")


class MockSTT(BaseSTT):
    """Simulated STT engine for fast testing without flooding Gemini requests."""

    def __init__(self, simulated_text: str = "Hello, I want to book an appointment for tomorrow."):
        self.simulated_text = simulated_text
        self._callback: Optional[Callable[[STTResult], Awaitable[None]]] = None
        self._running = False
        self.audio_bytes_received = 0
        self.last_emitted_time = 0.0

    async def start_stream(self, callback: Callable[[STTResult], Awaitable[None]]) -> None:
        self._callback = callback
        self._running = True
        self.audio_bytes_received = 0
        self.last_emitted_time = 0.0
        logger.info("Started Mock STT stream")

    async def send_audio_chunk(self, chunk: bytes) -> None:
        if not self._running or not chunk:
            return

        self.audio_bytes_received += len(chunk)
        now = time.time()

        # Emit single initial transcript per session after ~500ms of audio, with 10s cooldown
        if self.audio_bytes_received >= 16000 and (now - self.last_emitted_time) > 10.0:
            self.last_emitted_time = now
            if self._callback:
                await self._callback(STTResult(text=self.simulated_text, is_final=True, confidence=0.99, latency_ms=20.0))

    async def inject_transcript(self, text: str, is_final: bool = True) -> None:
        """Manual injection helper for integration tests."""
        if self._callback:
            await self._callback(STTResult(text=text, is_final=is_final, confidence=0.99, latency_ms=10.0))

    async def close(self) -> None:
        self._running = False
        logger.info("Closed Mock STT stream")
