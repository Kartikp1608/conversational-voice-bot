import json
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from stt.mock_stt import MockSTT
from stt.deepgram_stt import DeepgramSTT
from stt.google_stt import GoogleSTT
from stt.base_stt import STTResult
from utils.audio_utils import AudioUtils


@pytest.mark.asyncio
async def test_mock_stt_lifecycle():
    results = []

    async def callback(res: STTResult):
        results.append(res)

    stt = MockSTT(simulated_text="Hello world")
    await stt.start_stream(callback)

    # 1. Send enough audio bytes to trigger automatic threshold
    pcm_chunk = AudioUtils.create_silence(duration_ms=500)
    await stt.send_audio_chunk(pcm_chunk)

    # 2. Test manual transcript injection
    await stt.inject_transcript("Manual injected text", is_final=True)

    await asyncio.sleep(0.01)
    await stt.close()

    assert len(results) >= 2
    assert results[0].text == "Hello world"
    assert results[1].text == "Manual injected text"


@pytest.mark.asyncio
async def test_deepgram_stt_no_api_key_fallback():
    stt = DeepgramSTT(api_key=None)
    called = False

    async def callback(res: STTResult):
        nonlocal called
        called = True

    await stt.start_stream(callback)
    await stt.send_audio_chunk(b"\x00" * 320)
    await stt.close()
    assert called is False


@pytest.mark.asyncio
async def test_deepgram_stt_websocket_mock():
    stt = DeepgramSTT(api_key="valid-mock-key")
    results = []

    async def callback(res: STTResult):
        results.append(res)

    mock_msg = json.dumps({
        "channel": {
            "alternatives": [
                {"transcript": "Test Deepgram Streaming", "confidence": 0.98}
            ]
        },
        "is_final": True,
    })

    class AsyncWsMock:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not hasattr(self, "_sent"):
                self._sent = True
                return mock_msg
            await asyncio.sleep(0.1)
            raise StopAsyncIteration

        async def send(self, data):
            pass

        async def close(self):
            pass

    with patch("websockets.connect", return_value=AsyncWsMock()):
        await stt.start_stream(callback)
        await stt.send_audio_chunk(b"\x00" * 320)
        await asyncio.sleep(0.05)
        await stt.close()

    assert len(results) > 0
    assert results[0].text == "Test Deepgram Streaming"
    assert results[0].is_final is True


@pytest.mark.asyncio
async def test_google_stt_lifecycle():
    stt = GoogleSTT(language_code="en-US")
    results = []

    async def callback(res: STTResult):
        results.append(res)

    mock_client = MagicMock()
    mock_client.streaming_recognize = AsyncMock(return_value=iter([]))

    with patch("google.cloud.speech.SpeechAsyncClient", return_value=mock_client):
        await stt.start_stream(callback)
        pcm = AudioUtils.create_silence(duration_ms=20)
        await stt.send_audio_chunk(pcm)
        await asyncio.sleep(0.01)
        await stt.close()

    assert stt._running is False
