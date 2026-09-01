import asyncio
from typing import AsyncGenerator

import httpx

from config.settings import settings
from logging_config import get_logger
from tts.base_tts import BaseTTS
from utils.async_helpers import CancellationToken

logger = get_logger("tts.deepgram")


class DeepgramTTS(BaseTTS):
    """Deepgram Aura Streaming Text-To-Speech provider."""

    def __init__(self, api_key: str | None = None, model: str = "aura-asteria-en"):
        self.api_key = api_key or getattr(settings, "DEEPGRAM_API_KEY", None)
        self.model = model

    async def synthesize_stream(
        self,
        text_stream: AsyncGenerator[str, None],
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncGenerator[bytes, None]:
        full_text = ""
        async for token in text_stream:
            if cancellation_token and cancellation_token.is_cancelled:
                logger.info("Deepgram TTS synthesis aborted early")
                return
            full_text += token

        full_text = full_text.strip()
        if not full_text:
            return

        if not self.api_key or self.api_key == "your_deepgram_api_key_here":
            logger.warning("No Deepgram API Key configured, TTS streaming empty audio")
            return

        url = f"https://api.deepgram.com/v1/speak?model={self.model}&encoding=linear16&sample_rate=16000&container=none"
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"text": full_text}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        err_body = await response.aread()
                        logger.error(
                            f"Deepgram TTS API error {response.status_code}: {err_body.decode('utf-8', errors='ignore')}"
                        )
                        return

                    async for chunk in response.aiter_bytes(chunk_size=640):
                        if cancellation_token and cancellation_token.is_cancelled:
                            logger.info("Deepgram TTS streaming cut off by barge-in")
                            break
                        yield chunk
                        await asyncio.sleep(0.015)

        except Exception as e:
            logger.error("Deepgram TTS streaming connection error", error=str(e))
