import asyncio
from typing import Optional, List
from utils.audio_utils import AudioUtils
from utils.async_helpers import BoundedAudioQueue
from logging_config import get_logger

logger = get_logger("voice_gateway.stream_manager")


class AudioStreamManager:
    """Manages raw audio stream ingestion, framing, jitter buffering, and output packetization."""

    def __init__(self, sample_rate: int = 16000, chunk_duration_ms: int = 20):
        self.sample_rate = sample_rate
        self.chunk_duration_ms = chunk_duration_ms
        self.chunk_bytes = AudioUtils.ms_to_bytes(chunk_duration_ms, sample_rate)
        self.inbound_buffer = bytearray()
        self.outbound_queue = BoundedAudioQueue(maxsize=200)

    def write_inbound_pcm(self, raw_pcm: bytes) -> List[bytes]:
        """Ingest arbitrary byte length PCM and yield exact 20ms audio frames."""
        self.inbound_buffer.extend(raw_pcm)
        frames = []
        while len(self.inbound_buffer) >= self.chunk_bytes:
            frame = bytes(self.inbound_buffer[:self.chunk_bytes])
            del self.inbound_buffer[:self.chunk_bytes]
            frames.append(frame)
        return frames

    async def enqueue_outbound_chunk(self, chunk: bytes) -> None:
        """Enqueue synthesized audio chunk for WebSocket output."""
        await self.outbound_queue.put(chunk)

    def clear_outbound_queue(self) -> int:
        """Flush pending audio playback frames on user interruption."""
        return self.outbound_queue.clear()
