import asyncio
from typing import AsyncGenerator

from logging_config import get_logger
from tts.base_tts import BaseTTS
from utils.async_helpers import CancellationToken
from utils.audio_utils import AudioUtils

logger = get_logger("tts.google")


class GoogleTTS(BaseTTS):
    """Google Cloud Text-to-Speech Streaming Synthesis provider."""

    def __init__(self, voice_name: str = "en-US-Neural2-F", speaking_rate: float = 1.05):
        self.voice_name = voice_name
        self.speaking_rate = speaking_rate

    async def synthesize_stream(
        self,
        text_stream: AsyncGenerator[str, None],
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncGenerator[bytes, None]:
        full_text = ""
        async for token in text_stream:
            if cancellation_token and cancellation_token.is_cancelled:
                logger.info("TTS synthesis aborted early by cancellation token")
                return
            full_text += token

        if not full_text.strip():
            return

        try:
            from google.cloud import texttospeech

            client = texttospeech.TextToSpeechAsyncClient()
            synthesis_input = texttospeech.SynthesisInput(text=full_text)

            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name=self.voice_name,
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                speaking_rate=self.speaking_rate,
            )

            response = await client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )

            # Chunk raw audio into 20ms frames for streaming output
            chunks = AudioUtils.chunk_audio(response.audio_content, chunk_duration_ms=20)
            for chunk in chunks:
                if cancellation_token and cancellation_token.is_cancelled:
                    logger.info("TTS frame streaming aborted on barge-in")
                    break
                yield chunk
                await asyncio.sleep(0.015)  # Real-time cadence streaming

        except Exception as e:
            logger.warning("Google TTS API fallback to synthetic generator", error=str(e))
            # Fallback to silent/tone PCM frames
            pcm = AudioUtils.create_silence(duration_ms=500)
            for chunk in AudioUtils.chunk_audio(pcm, chunk_duration_ms=20):
                yield chunk
