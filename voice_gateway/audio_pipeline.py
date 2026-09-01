import asyncio
import time
from typing import AsyncGenerator, Awaitable, Callable

from analytics.call_analytics import CallAnalyticsTracker
from config.settings import settings
from conversation.conversation_manager import ConversationManager
from conversation.turn_aggregator import TurnAggregator
from interruptions.interrupt_manager import InterruptManager
from llm.base_llm import BaseLLM
from llm.gemini_live import GeminiLiveLLM
from llm.mock_llm import MockLLM
from logging_config import get_logger
from noise_filter.audio_filter import AudioFilter
from stt.base_stt import BaseSTT, STTResult
from stt.deepgram_stt import DeepgramSTT
from stt.google_stt import GoogleSTT
from stt.mock_stt import MockSTT
from tool_executor.builtins.calendar_tool import CalendarTool
from tool_executor.builtins.communication_tool import CommunicationTool
from tool_executor.builtins.crm_tool import CRMTool
from tool_executor.builtins.database_tool import DatabaseTool
from tool_executor.builtins.webhook_tool import WebhookTool
from tool_executor.registry import ToolRegistry
from tts.base_tts import BaseTTS
from tts.deepgram_tts import DeepgramTTS
from tts.google_tts import GoogleTTS
from tts.mock_tts import MockTTS
from utils.async_helpers import BoundedAudioQueue
from vad.vad_engine import VADEngine, VADState

logger = get_logger("voice_gateway.pipeline")


class AudioPipeline:
    """Production Real-Time Low Latency Conversational Voice AI Pipeline.
    Integrates VAD -> Noise Filter -> Deepgram/Google STT -> Turn Aggregator -> Interruption Manager -> Gemini LLM -> Deepgram/Google TTS.
    Target End-to-End Latency: < 800ms.
    """

    def __init__(self, session_id: str, call_id: str, prompt_id: str = "sales_outbound"):
        self.session_id = session_id
        self.call_id = call_id
        self.prompt_id = prompt_id

        self.vad = VADEngine(
            sample_rate=settings.SAMPLE_RATE,
            frame_duration_ms=settings.CHUNK_SIZE_MS,
            energy_threshold=settings.VAD_ENERGY_THRESHOLD,
            speech_pad_ms=settings.VAD_SPEECH_PAD_MS,
            silence_timeout_ms=settings.VAD_SILENCE_TIMEOUT_MS,
        )
        self.audio_filter = AudioFilter()
        self.conversation = ConversationManager(prompt_id=prompt_id, call_id=call_id)
        self.turn_aggregator = TurnAggregator(debounce_ms=750.0)
        self.interrupt_manager = InterruptManager(session_id=session_id)
        self.analytics = CallAnalyticsTracker(call_id=call_id)

        # Initialize Tool Registry
        self.tool_registry = ToolRegistry()
        self.tool_registry.register(CRMTool())
        self.tool_registry.register(CalendarTool())
        self.tool_registry.register(DatabaseTool())
        self.tool_registry.register(CommunicationTool())
        self.tool_registry.register(WebhookTool())

        # Select STT Provider
        if settings.STT_PROVIDER == "deepgram":
            self.stt: BaseSTT = DeepgramSTT(api_key=settings.DEEPGRAM_API_KEY)
        elif settings.STT_PROVIDER == "google":
            self.stt = GoogleSTT(language_code=settings.STT_LANGUAGE_CODE)
        else:
            self.stt = MockSTT()

        # Select LLM Provider
        if settings.LLM_PROVIDER == "gemini_live":
            self.llm: BaseLLM = GeminiLiveLLM(
                api_key=settings.GEMINI_API_KEY,
                model=settings.LLM_MODEL,
                creds_file=getattr(settings, "GOOGLE_APPLICATION_CREDENTIALS", "vertex_creds.json"),
            )
        else:
            self.llm = MockLLM()

        # Select TTS Provider
        if settings.TTS_PROVIDER == "deepgram":
            self.tts: BaseTTS = DeepgramTTS(
                api_key=settings.DEEPGRAM_API_KEY, model=settings.TTS_VOICE_NAME
            )
        elif settings.TTS_PROVIDER == "google":
            self.tts = GoogleTTS(voice_name=settings.TTS_VOICE_NAME)
        else:
            self.tts = MockTTS()

        self.outbound_audio_queue = BoundedAudioQueue(maxsize=200)
        self.turn_start_time: float | None = None
        self._is_running = False

    async def start(self, audio_output_callback: Callable[[bytes], Awaitable[None]]) -> None:
        """Start streaming STT and output audio consumer loops."""
        self._is_running = True
        await self.stt.start_stream(self._on_stt_result)
        self._consumer_task = asyncio.create_task(
            self._consume_outbound_audio(audio_output_callback)
        )
        logger.info(f"AudioPipeline started for call {self.call_id}", session_id=self.session_id)

        # Trigger Initial Bot Greeting on Call Connect
        self._greeting_task = asyncio.create_task(self._trigger_initial_greeting())

    async def _trigger_initial_greeting(self) -> None:
        """Send instant bot greeting when call connects."""
        await asyncio.sleep(0.1)
        greeting_text = "Hello! Welcome to our service. How can I assist you today?"
        if self.prompt_id == "healthcare_appointment":
            greeting_text = (
                "Hello! Welcome to Apex Health Clinic. How can I assist you with scheduling today?"
            )
        elif self.prompt_id == "sales_outbound":
            greeting_text = (
                "Hello! This is CloudScale AI calling. Do you have two minutes to speak today?"
            )
        elif self.prompt_id == "customer_support_inbound":
            greeting_text = "Welcome to Nexus Telecom Support. How can I help you today?"
        elif self.prompt_id == "banking_verification":
            greeting_text = "Hello, this is Vantage Bank Fraud Prevention unit calling regarding recent activity."

        logger.info(f"Triggering Initial Bot Greeting: '{greeting_text}'")
        token = self.interrupt_manager.create_token()
        self.conversation.record_assistant_turn(greeting_text)

        async def text_gen():
            yield greeting_text

        async for audio_chunk in self.tts.synthesize_stream(text_gen(), cancellation_token=token):
            if token.is_cancelled:
                break
            await self.outbound_audio_queue.put(audio_chunk)

    async def process_inbound_pcm_frame(self, pcm_frame: bytes) -> None:
        """Process 20ms inbound audio frame from WebSocket."""
        if not self._is_running:
            return

        # 1. Apply Noise Suppression & DC offset filter
        filtered_frame = self.audio_filter.process(pcm_frame)

        # 2. Evaluate Voice Activity Detection (VAD)
        state, rms, is_speech = self.vad.process_frame(filtered_frame)

        # 3. Handle Barge-in Interruption: User started speaking while AI was talking
        if state == VADState.SPEECH_START:
            self.turn_start_time = time.monotonic()
            self.turn_aggregator.reset()
            flushed_count = self.interrupt_manager.trigger_interruption(self.outbound_audio_queue)
            if flushed_count > 0:
                self.analytics.record_interruption()
                logger.info(f"Barge-in: Flushed {flushed_count} queued audio frames")

        # 4. Stream audio frame to Speech-to-Text engine
        await self.stt.send_audio_chunk(filtered_frame)

    async def _on_stt_result(self, result: STTResult) -> None:
        """Callback triggered when Speech-to-Text emits transcript."""
        if not result.is_final:
            return

        user_text = result.text.strip()
        if not user_text:
            return

        self.analytics.record_stt_latency(result.latency_ms)

        # Pass transcript through TurnAggregator debouncer to handle 0.5s pauses smartly
        self.turn_aggregator.add_transcript(user_text, self._generate_and_speak_response)

    async def _generate_and_speak_response(self, aggregated_user_text: str) -> None:
        """Full Low Latency Pipeline: Aggregated Utterance -> Conversation Manager -> LLM -> Tool -> TTS -> Audio Queue."""
        token = self.interrupt_manager.create_token()

        logger.info(
            f"User Aggregated Utterance: '{aggregated_user_text}'", user_text=aggregated_user_text
        )

        # 1. Update Conversation Manager & System Prompt
        system_prompt = self.conversation.process_user_turn(aggregated_user_text)
        messages = self.conversation.get_messages()
        tools_schema = self.tool_registry.get_schemas()

        # 2. Stream LLM Response & Handle Tool Calls
        llm_start_time = time.monotonic()
        first_token_received = False
        accumulated_text = ""

        async def text_stream_generator() -> AsyncGenerator[str, None]:
            nonlocal first_token_received, accumulated_text
            async for chunk in self.llm.generate_stream(
                system_prompt=system_prompt,
                messages=messages,
                tools_schema=tools_schema,
                cancellation_token=token,
            ):
                if token.is_cancelled:
                    logger.info("LLM stream generation cancelled by barge-in")
                    return

                if chunk.tool_call_name:
                    logger.info(
                        f"LLM requested tool call: {chunk.tool_call_name}",
                        tool=chunk.tool_call_name,
                    )
                    tool_res = await self.tool_registry.execute_tool(
                        chunk.tool_call_name, chunk.tool_call_args or {}
                    )
                    tool_msg = f"Tool result for {chunk.tool_call_name}: {tool_res.get('result')}"
                    self.conversation.record_assistant_turn(tool_msg)
                    res_text = f"I've executed {chunk.tool_call_name}. Everything is confirmed."
                    accumulated_text += res_text
                    yield res_text
                    return

                if chunk.text_delta:
                    if not first_token_received:
                        first_token_received = True
                        ttft_ms = (time.monotonic() - llm_start_time) * 1000.0
                        self.analytics.record_llm_ttft(ttft_ms)

                    accumulated_text += chunk.text_delta
                    yield chunk.text_delta

        # 3. Stream Text to TTS Synthesis
        tts_start_time = time.monotonic()
        first_audio_byte_sent = False

        async for audio_chunk in self.tts.synthesize_stream(
            text_stream_generator(), cancellation_token=token
        ):
            if token.is_cancelled:
                break

            if not first_audio_byte_sent:
                first_audio_byte_sent = True
                first_byte_ms = (time.monotonic() - tts_start_time) * 1000.0
                self.analytics.record_tts_first_byte(first_byte_ms)

                if self.turn_start_time:
                    end_to_end_ms = (time.monotonic() - self.turn_start_time) * 1000.0
                    self.analytics.record_turn_end_to_end(end_to_end_ms)

            await self.outbound_audio_queue.put(audio_chunk)

        if accumulated_text.strip():
            self.conversation.record_assistant_turn(accumulated_text.strip())

    async def _consume_outbound_audio(self, callback: Callable[[bytes], Awaitable[None]]) -> None:
        """Consumer task sending queued PCM audio chunks to WebSocket client."""
        while self._is_running:
            try:
                chunk = await self.outbound_audio_queue.get()
                if chunk is not None:
                    await callback(chunk)
                    await asyncio.sleep(0.005)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Error consuming outbound audio frame", error=str(e))

    async def stop(self) -> None:
        """Clean pipeline shutdown."""
        self._is_running = False
        if (
            hasattr(self, "_consumer_task")
            and self._consumer_task
            and not self._consumer_task.done()
        ):
            self._consumer_task.cancel()
        if (
            hasattr(self, "_greeting_task")
            and self._greeting_task
            and not self._greeting_task.done()
        ):
            self._greeting_task.cancel()
        await self.stt.close()
        logger.info(f"AudioPipeline stopped for session {self.session_id}")
