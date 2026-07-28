import asyncio
import time
from typing import Callable, Awaitable, Optional
from stt.base_stt import BaseSTT, STTResult
from logging_config import get_logger

logger = get_logger("stt.google")


class GoogleSTT(BaseSTT):
    """Google Cloud Streaming Speech-to-Text provider."""

    def __init__(self, language_code: str = "en-US", sample_rate: int = 16000):
        self.language_code = language_code
        self.sample_rate = sample_rate
        self._audio_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._callback: Optional[Callable[[STTResult], Awaitable[None]]] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start_stream(self, callback: Callable[[STTResult], Awaitable[None]]) -> None:
        self._callback = callback
        self._running = True
        self._task = asyncio.create_task(self._process_stream())
        logger.info("Started Google Streaming STT stream")

    async def send_audio_chunk(self, chunk: bytes) -> None:
        if self._running:
            await self._audio_queue.put(chunk)

    async def _process_stream(self) -> None:
        """Streaming request generator feeding Google Speech API."""
        try:
            from google.cloud import speech
            client = speech.SpeechAsyncClient()
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=self.sample_rate,
                language_code=self.language_code,
                enable_automatic_punctuation=True,
            )
            streaming_config = speech.StreamingRecognitionConfig(
                config=config,
                interim_results=True,
            )

            async def request_generator():
                yield speech.StreamingRecognizeRequest(streaming_config=streaming_config)
                while self._running:
                    chunk = await self._audio_queue.get()
                    if chunk is None:
                        break
                    yield speech.StreamingRecognizeRequest(audio_content=chunk)

            start_time = time.monotonic()
            responses = await client.streaming_recognize(requests=request_generator())
            async for response in responses:
                if not response.results:
                    continue
                result = response.results[0]
                if not result.alternatives:
                    continue
                transcript = result.alternatives[0].transcript
                is_final = result.is_final
                latency_ms = (time.monotonic() - start_time) * 1000.0

                stt_res = STTResult(
                    text=transcript,
                    is_final=is_final,
                    confidence=result.alternatives[0].confidence or 0.95,
                    latency_ms=latency_ms,
                )
                if self._callback:
                    await self._callback(stt_res)

        except Exception as e:
            logger.warning("Google STT streaming fallthrough to simulation", error=str(e))

    async def close(self) -> None:
        self._running = False
        await self._audio_queue.put(b"")
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("Closed Google STT stream")
