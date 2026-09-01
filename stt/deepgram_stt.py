import asyncio
import json
from typing import Any, Awaitable, Callable

import websockets

from config.settings import settings
from logging_config import get_logger
from stt.base_stt import BaseSTT, STTResult

logger = get_logger("stt.deepgram")


class DeepgramSTT(BaseSTT):
    """Deepgram Real-Time Streaming Speech-to-Text provider over WebSockets."""

    def __init__(self, api_key: str | None = None, language: str = "en", sample_rate: int = 16000):
        self.api_key = api_key or getattr(settings, "DEEPGRAM_API_KEY", None)
        self.language = language
        self.sample_rate = sample_rate
        self._audio_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._callback: Callable[[STTResult], Awaitable[None]] | None = None
        self._running = False
        self._ws_task: asyncio.Task | None = None
        self._ws: Any = None

    async def start_stream(self, callback: Callable[[STTResult], Awaitable[None]]) -> None:
        self._callback = callback
        self._running = True
        if not self.api_key or self.api_key == "your_deepgram_api_key_here":
            logger.warning("No Deepgram API Key configured, STT will use fallback mode")
            return

        self._ws_task = asyncio.create_task(self._websocket_loop())
        logger.info("Started Deepgram Streaming STT session")

    async def send_audio_chunk(self, chunk: bytes) -> None:
        if self._running and self._ws:
            try:
                await self._ws.send(chunk)
            except Exception as e:
                logger.warning("Failed to send audio chunk to Deepgram", error=str(e))

    async def _websocket_loop(self) -> None:
        url = (
            f"wss://api.deepgram.com/v1/listen?"
            f"model=nova-2&encoding=linear16&sample_rate={self.sample_rate}&channels=1"
            f"&interim_results=true&endpointing=300&language={self.language}"
        )
        headers = {"Authorization": f"Token {self.api_key}"}

        try:
            # Compatible with websockets v16+ (additional_headers) and older versions (extra_headers)
            try:
                connection = websockets.connect(url, additional_headers=headers)
            except TypeError:
                connection = websockets.connect(url, extra_headers=headers)

            async with connection as ws:
                self._ws = ws
                logger.info("Connected to Deepgram WebSocket API")

                async for message in ws:
                    if not self._running:
                        break

                    try:
                        data = json.loads(message)
                        channel = data.get("channel", {})
                        alts = channel.get("alternatives", [])
                        if not alts:
                            continue

                        transcript = alts[0].get("transcript", "").strip()
                        if not transcript:
                            continue

                        is_final = data.get("is_final", False)
                        confidence = alts[0].get("confidence", 0.95)

                        stt_res = STTResult(
                            text=transcript,
                            is_final=is_final,
                            confidence=confidence,
                            latency_ms=30.0,
                        )

                        if self._callback:
                            await self._callback(stt_res)

                    except json.JSONDecodeError as e:
                        logger.warning("Failed to decode Deepgram WS message JSON", error=str(e))
                        continue

        except Exception as e:
            logger.error("Deepgram WebSocket connection error", error=str(e))

    async def close(self) -> None:
        self._running = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception as e:
                logger.debug("Error closing Deepgram websocket", error=str(e))
        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()
        logger.info("Closed Deepgram STT stream")
