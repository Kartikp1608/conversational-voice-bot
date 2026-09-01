from unittest.mock import patch

import pytest

from tts.deepgram_tts import DeepgramTTS
from tts.google_tts import GoogleTTS
from tts.mock_tts import MockTTS
from utils.async_helpers import CancellationToken
from utils.audio_utils import AudioUtils


async def sample_text_generator(text="Hello world"):
    for word in text.split(" "):
        yield word + " "


@pytest.mark.asyncio
async def test_mock_tts_synthesis():
    tts = MockTTS()
    chunks = []
    async for chunk in tts.synthesize_stream(
        sample_text_generator("Welcome to our voice assistant")
    ):
        chunks.append(chunk)

    assert len(chunks) > 0
    assert isinstance(chunks[0], bytes)


@pytest.mark.asyncio
async def test_mock_tts_cancellation():
    tts = MockTTS()
    token = CancellationToken()
    token.cancel()

    chunks = []
    async for chunk in tts.synthesize_stream(sample_text_generator(), cancellation_token=token):
        chunks.append(chunk)

    assert len(chunks) == 0


@pytest.mark.asyncio
async def test_deepgram_tts_no_api_key():
    tts = DeepgramTTS(api_key=None)
    chunks = []
    async for chunk in tts.synthesize_stream(sample_text_generator()):
        chunks.append(chunk)

    assert len(chunks) == 0


@pytest.mark.asyncio
async def test_deepgram_tts_streaming_mock():
    tts = DeepgramTTS(api_key="valid-mock-key")

    mock_audio = AudioUtils.create_silence(duration_ms=100)

    class MockStreamResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def aiter_bytes(self, chunk_size=640):
            for i in range(0, len(mock_audio), chunk_size):
                yield mock_audio[i : i + chunk_size]

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        def stream(self, *args, **kwargs):
            return MockStreamResponse()

    with patch("httpx.AsyncClient", return_value=MockClient()):
        chunks = []
        async for chunk in tts.synthesize_stream(sample_text_generator("Synthesizing audio")):
            chunks.append(chunk)

        assert len(chunks) > 0


@pytest.mark.asyncio
async def test_google_tts_streaming_fallback():
    tts = GoogleTTS(voice_name="en-US-Neural2-F")
    # Patch to trigger fallback immediately without network timeout
    with patch(
        "google.cloud.texttospeech.TextToSpeechAsyncClient", side_effect=Exception("API offline")
    ):
        chunks = []
        async for chunk in tts.synthesize_stream(sample_text_generator("Testing Google TTS")):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert isinstance(chunks[0], bytes)


@pytest.mark.asyncio
async def test_google_tts_cancellation():
    tts = GoogleTTS()
    token = CancellationToken()
    token.cancel()

    chunks = []
    async for chunk in tts.synthesize_stream(sample_text_generator(), cancellation_token=token):
        chunks.append(chunk)

    assert len(chunks) == 0
