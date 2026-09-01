import asyncio
from typing import AsyncGenerator

from logging_config import get_logger
from tts.base_tts import BaseTTS
from utils.async_helpers import CancellationToken
from utils.audio_utils import AudioUtils

logger = get_logger("tts.mock")


class MockTTS(BaseTTS):
    """Silent/Clean Mock TTS provider for testing without audio noise."""

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate

    async def synthesize_stream(
        self,
        text_stream: AsyncGenerator[str, None],
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncGenerator[bytes, None]:
        char_count = 0
        async for token in text_stream:
            if cancellation_token and cancellation_token.is_cancelled:
                return
            char_count += len(token)

        # Output silent audio frames without tone noise
        silence_chunk = AudioUtils.create_silence(duration_ms=20, sample_rate=self.sample_rate)
        total_frames = max(5, min(char_count * 2, 50))

        for _ in range(total_frames):
            if cancellation_token and cancellation_token.is_cancelled:
                return
            yield silence_chunk
            await asyncio.sleep(0.01)
