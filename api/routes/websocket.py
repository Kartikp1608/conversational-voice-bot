import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from logging_config import get_logger
from telephony.twilio_adapter import TwilioAdapter
from voice_gateway.audio_pipeline import AudioPipeline
from voice_gateway.session_manager import SessionManager

logger = get_logger("api.websocket")

router = APIRouter(tags=["Voice Gateway WebSockets"])
session_manager = SessionManager()


@router.websocket("/ws/voice/{session_id}")
async def generic_voice_websocket(
    websocket: WebSocket, session_id: str, prompt_id: str = "sales_outbound"
):
    """Generic full-duplex WebSocket endpoint for direct web client voice & text interaction."""
    await websocket.accept()
    logger.info(f"WebSocket client connected: {session_id}", session_id=session_id)

    call_id = f"call-{session_id}"
    session_manager.create_session(session_id, call_id, prompt_id)
    pipeline = AudioPipeline(session_id=session_id, call_id=call_id, prompt_id=prompt_id)

    async def send_audio_to_client(pcm_chunk: bytes) -> None:
        try:
            await websocket.send_bytes(pcm_chunk)
        except Exception as e:
            logger.warning(
                "Failed to send audio chunk to websocket client",
                session_id=session_id,
                error=str(e),
            )

    await pipeline.start(send_audio_to_client)

    try:
        while True:
            data = await websocket.receive()
            if "bytes" in data and data["bytes"]:
                await pipeline.process_inbound_pcm_frame(data["bytes"])
            elif "text" in data and data["text"]:
                try:
                    msg = json.loads(data["text"])
                    if msg.get("type") == "text" and msg.get("text"):
                        user_text = msg.get("text")
                        # Echo back user transcript for UI
                        await websocket.send_text(
                            json.dumps({"type": "user_transcript", "text": user_text})
                        )
                        # Trigger Voice AI turn
                        await pipeline._generate_and_speak_response(user_text)
                except json.JSONDecodeError as e:
                    logger.warning(
                        "Invalid JSON received from websocket client",
                        session_id=session_id,
                        error=str(e),
                    )

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {session_id}", session_id=session_id)
    except Exception as e:
        logger.warning(f"WebSocket session ended: {e}")
    finally:
        await pipeline.stop()
        session_manager.close_session(session_id)


@router.websocket("/ws/twilio/{call_id}")
async def twilio_media_stream_websocket(
    websocket: WebSocket, call_id: str, prompt_id: str = "sales_outbound"
):
    """Twilio Media Streams WebSocket endpoint."""
    await websocket.accept()
    logger.info(f"Twilio Media Stream connected for call {call_id}", call_id=call_id)

    adapter = TwilioAdapter()
    stream_sid: str | None = None
    session_id = f"twilio-{call_id}"

    session_manager.create_session(session_id, call_id, prompt_id)
    pipeline = AudioPipeline(session_id=session_id, call_id=call_id, prompt_id=prompt_id)

    async def send_mulaw_to_twilio(pcm_chunk: bytes) -> None:
        nonlocal stream_sid
        if stream_sid:
            try:
                payload_json = TwilioAdapter.format_outbound_media_payload(stream_sid, pcm_chunk)
                await websocket.send_text(payload_json)
            except Exception as e:
                logger.warning(
                    "Failed to send mu-law audio chunk to Twilio stream",
                    call_id=call_id,
                    error=str(e),
                )

    await pipeline.start(send_mulaw_to_twilio)

    try:
        while True:
            message_text = await websocket.receive_text()
            event = adapter.parse_media_event(message_text)

            if event.get("event") == "start":
                stream_sid = event.get("stream_sid")

            elif event.get("event") == "media":
                pcm_bytes = event.get("pcm_bytes")
                if pcm_bytes:
                    await pipeline.process_inbound_pcm_frame(pcm_bytes)

            elif event.get("event") == "stop":
                break

    except WebSocketDisconnect:
        logger.info(f"Twilio WebSocket disconnected for call {call_id}")
    finally:
        await pipeline.stop()
        session_manager.close_session(session_id)
