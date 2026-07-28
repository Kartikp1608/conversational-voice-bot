import pytest
import asyncio
from voice_gateway.audio_pipeline import AudioPipeline
from utils.audio_utils import AudioUtils


@pytest.mark.asyncio
async def test_audio_pipeline_execution():
    pipeline = AudioPipeline(session_id="sess-gw-1", call_id="call-gw-1", prompt_id="sales_outbound")
    
    received_audio_chunks = []

    async def output_callback(chunk: bytes):
        received_audio_chunks.append(chunk)

    await pipeline.start(output_callback)

    # Stream 100ms of PCM speech frames
    pcm_audio = AudioUtils.create_silence(duration_ms=100)
    for frame in AudioUtils.chunk_audio(pcm_audio, chunk_duration_ms=20):
        await pipeline.process_inbound_pcm_frame(frame)

    await asyncio.sleep(0.1)
    await pipeline.stop()

    assert pipeline.session_id == "sess-gw-1"
