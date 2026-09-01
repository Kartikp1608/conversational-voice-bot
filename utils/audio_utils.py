import audioop
import math
from typing import List

import numpy as np


class AudioUtils:
    """High-performance audio processing utilities for 16-bit 16kHz PCM audio."""

    SAMPLE_RATE = 16000
    BYTES_PER_SAMPLE = 2

    @staticmethod
    def pcm_to_mulaw(pcm_data: bytes) -> bytes:
        """Convert 16-bit linear PCM audio bytes to G.711 mu-law bytes."""
        if not pcm_data:
            return b""
        return audioop.lin2ulaw(pcm_data, AudioUtils.BYTES_PER_SAMPLE)

    @staticmethod
    def mulaw_to_pcm(mulaw_data: bytes) -> bytes:
        """Convert G.711 mu-law audio bytes to 16-bit linear PCM bytes."""
        if not mulaw_data:
            return b""
        return audioop.ulaw2lin(mulaw_data, AudioUtils.BYTES_PER_SAMPLE)

    @staticmethod
    def calculate_rms(pcm_data: bytes) -> float:
        """Calculate Root Mean Square (RMS) energy normalized between 0.0 and 1.0."""
        if not pcm_data or len(pcm_data) < 2:
            return 0.0

        # Fast numpy conversion for high throughput
        samples = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32)
        if len(samples) == 0:
            return 0.0

        mean_square = np.mean(samples**2)
        rms = math.sqrt(float(mean_square))
        # Normalize to 0.0 - 1.0 range (32768 maximum value for int16)
        return min(1.0, rms / 32768.0)

    @staticmethod
    def bytes_to_ms(bytes_len: int, sample_rate: int = 16000, bytes_per_sample: int = 2) -> float:
        """Convert audio byte length to milliseconds duration."""
        bytes_per_sec = sample_rate * bytes_per_sample
        if bytes_per_sec == 0:
            return 0.0
        return (bytes_len / bytes_per_sec) * 1000.0

    @staticmethod
    def ms_to_bytes(ms: float, sample_rate: int = 16000, bytes_per_sample: int = 2) -> int:
        """Convert millisecond duration to PCM audio byte length."""
        bytes_per_sec = sample_rate * bytes_per_sample
        return int((ms / 1000.0) * bytes_per_sec)

    @staticmethod
    def chunk_audio(
        pcm_data: bytes, chunk_duration_ms: int = 20, sample_rate: int = 16000
    ) -> List[bytes]:
        """Split a continuous PCM audio buffer into fixed millisecond frame chunks."""
        chunk_size = AudioUtils.ms_to_bytes(chunk_duration_ms, sample_rate)
        if chunk_size <= 0:
            return [pcm_data]

        chunks = []
        for i in range(0, len(pcm_data), chunk_size):
            chunk = pcm_data[i : i + chunk_size]
            if len(chunk) == chunk_size:
                chunks.append(chunk)
            else:
                # Zero pad final frame if incomplete
                padded = chunk + b"\x00" * (chunk_size - len(chunk))
                chunks.append(padded)
        return chunks

    @staticmethod
    def create_silence(duration_ms: int, sample_rate: int = 16000) -> bytes:
        """Generate silent PCM audio bytes for specified duration."""
        num_bytes = AudioUtils.ms_to_bytes(duration_ms, sample_rate)
        return b"\x00" * num_bytes
