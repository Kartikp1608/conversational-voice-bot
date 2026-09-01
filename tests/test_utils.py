import asyncio

import numpy as np
import pytest

from noise_filter.audio_filter import AudioFilter
from utils.async_helpers import BoundedAudioQueue, CancellationToken
from utils.audio_utils import AudioUtils


def test_audio_filter_processing():
    filt = AudioFilter(noise_gate_threshold=0.01)

    # Empty bytes
    assert filt.process(b"") == b""

    # Noise gate: low amplitude signal should be zeroed
    low_noise = (np.ones(320, dtype=np.int16) * 50).tobytes()
    filtered = filt.process(low_noise)
    assert filtered == b"\x00" * len(low_noise)

    # Higher amplitude signal
    high_signal = (np.sin(np.linspace(0, 10, 320)) * 10000).astype(np.int16).tobytes()
    filtered_high = filt.process(high_signal)
    assert len(filtered_high) == len(high_signal)
    assert filtered_high != b"\x00" * len(high_signal)


def test_audio_utils_conversion_and_rms():
    # Empty
    assert AudioUtils.pcm_to_mulaw(b"") == b""
    assert AudioUtils.mulaw_to_pcm(b"") == b""
    assert AudioUtils.calculate_rms(b"") == 0.0
    assert AudioUtils.calculate_rms(b"\x00") == 0.0

    # Silence
    silence = AudioUtils.create_silence(duration_ms=40)
    assert len(silence) == AudioUtils.ms_to_bytes(40)
    assert AudioUtils.calculate_rms(silence) == 0.0

    # mu-law roundtrip
    pcm_audio = (np.sin(np.linspace(0, 10, 320)) * 10000).astype(np.int16).tobytes()
    mulaw = AudioUtils.pcm_to_mulaw(pcm_audio)
    assert len(mulaw) == len(pcm_audio) // 2
    pcm_reconstructed = AudioUtils.mulaw_to_pcm(mulaw)
    assert len(pcm_reconstructed) == len(pcm_audio)

    # RMS calculation on loud signal
    rms = AudioUtils.calculate_rms(pcm_audio)
    assert 0.0 < rms <= 1.0

    # Conversions
    ms = AudioUtils.bytes_to_ms(len(silence))
    assert ms == 40.0


def test_audio_utils_chunking():
    # 50ms audio chunked into 20ms frames -> 3 frames (with padding on last frame)
    audio = AudioUtils.create_silence(duration_ms=50)
    chunks = AudioUtils.chunk_audio(audio, chunk_duration_ms=20)
    assert len(chunks) == 3
    # Each chunk should be exactly 20ms = 640 bytes
    for c in chunks:
        assert len(c) == 640

    # Zero chunk size returns whole buffer
    assert len(AudioUtils.chunk_audio(audio, chunk_duration_ms=0)) == 1


@pytest.mark.asyncio
async def test_cancellation_token():
    token = CancellationToken()
    assert token.is_cancelled is False

    # Wait until cancelled in async task
    async def cancel_later():
        await asyncio.sleep(0.02)
        token.cancel()

    asyncio.create_task(cancel_later())
    await token.wait_until_cancelled()
    assert token.is_cancelled is True

    # Reset token
    token.reset()
    assert token.is_cancelled is False


@pytest.mark.asyncio
async def test_bounded_audio_queue():
    queue = BoundedAudioQueue(maxsize=10)
    assert queue.empty() is True

    await queue.put(b"chunk1")
    await queue.put(b"chunk2")
    await queue.put(b"chunk3")
    assert queue.empty() is False

    c1 = await queue.get()
    assert c1 == b"chunk1"

    # Flush queue on interruption
    cleared = queue.clear()
    assert cleared == 2
    assert queue.empty() is True
