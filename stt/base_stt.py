from abc import ABC, abstractmethod
from typing import Awaitable, Callable


class STTResult:
    def __init__(self, text: str, is_final: bool, confidence: float = 1.0, latency_ms: float = 0.0):
        self.text = text
        self.is_final = is_final
        self.confidence = confidence
        self.latency_ms = latency_ms

    def __repr__(self) -> str:
        return f"STTResult(text='{self.text}', is_final={self.is_final}, confidence={self.confidence:.2f})"


class BaseSTT(ABC):
    """Abstract Speech-To-Text Provider interface."""

    @abstractmethod
    async def start_stream(self, callback: Callable[[STTResult], Awaitable[None]]) -> None:
        """Initialize and start streaming STT session."""
        pass

    @abstractmethod
    async def send_audio_chunk(self, chunk: bytes) -> None:
        """Send raw audio chunk (PCM 16-bit 16kHz) to STT engine."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close STT stream cleanly."""
        pass
