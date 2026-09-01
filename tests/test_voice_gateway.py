import asyncio
import pytest
from unittest.mock import AsyncMock
from voice_gateway.audio_pipeline import AudioPipeline
from voice_gateway.session_manager import SessionManager, VoiceSession
from voice_gateway.stream_manager import AudioStreamManager
from stt.base_stt import STTResult
from utils.audio_utils import AudioUtils


def test_session_manager_lifecycle():
    sm = SessionManager()
    session = sm.create_session("sess-1", "call-1", "sales_outbound", "outbound")
    assert session.session_id == "sess-1"
    assert session.direction == "outbound"
    assert session.is_active is True

    session.touch()
    assert sm.get_session("sess-1") is not None
    assert sm.get_session("sess-nonexistent") is None

    sm.close_session("sess-1")
    assert sm.get_session("sess-1") is None


def test_audio_stream_manager_framing():
    asm = AudioStreamManager(sample_rate=16000, chunk_duration_ms=20)
    # 20ms at 16kHz = 640 bytes. Send 1500 bytes -> should yield 2 frames of 640 bytes (1280 bytes) and keep 220 bytes
    frames = asm.write_inbound_pcm(b"\x00" * 1500)
    assert len(frames) == 2
    assert len(frames[0]) == 640
    assert len(frames[1]) == 640
    assert len(asm.inbound_buffer) == 220

    # Send remaining 420 bytes -> total 640 -> yields 1 frame
    more_frames = asm.write_inbound_pcm(b"\x00" * 420)
    assert len(more_frames) == 1
    assert len(asm.inbound_buffer) == 0


@pytest.mark.asyncio
async def test_audio_stream_manager_queue():
    asm = AudioStreamManager()
    await asm.enqueue_outbound_chunk(b"outbound-chunk-1")
    await asm.enqueue_outbound_chunk(b"outbound-chunk-2")
    cleared = asm.clear_outbound_queue()
    assert cleared == 2


@pytest.mark.asyncio
async def test_audio_pipeline_execution():
    pipeline = AudioPipeline(session_id="sess-gw-1", call_id="call-gw-1", prompt_id="healthcare_appointment")
    received_audio_chunks = []

    async def output_callback(chunk: bytes):
        received_audio_chunks.append(chunk)

    await pipeline.start(output_callback)

    # Stream 100ms of PCM speech frames
    pcm_audio = AudioUtils.create_silence(duration_ms=100)
    for frame in AudioUtils.chunk_audio(pcm_audio, chunk_duration_ms=20):
        await pipeline.process_inbound_pcm_frame(frame)

    # Trigger STT result
    stt_res = STTResult(text="Yes please schedule appointment", is_final=True, confidence=0.99, latency_ms=25.0)
    await pipeline._on_stt_result(stt_res)

    await asyncio.sleep(0.15)
    await pipeline.stop()

    assert pipeline.session_id == "sess-gw-1"


@pytest.mark.asyncio
async def test_audio_pipeline_different_prompt_greetings():
    for prompt in ["sales_outbound", "customer_support_inbound", "banking_verification"]:
        p = AudioPipeline(session_id=f"sess-{prompt}", call_id=f"call-{prompt}", prompt_id=prompt)
        await p.start(AsyncMock())
        await asyncio.sleep(0.05)
        await p.stop()
