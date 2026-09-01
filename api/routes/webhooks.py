import uuid

from fastapi import APIRouter, Request, Response

from logging_config import get_logger

logger = get_logger("api.webhooks")

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/twilio/inbound")
async def twilio_inbound_voice_webhook(request: Request):
    """Twilio Inbound Voice Webhook returning TwiML WebSocket Stream directive."""
    call_id = f"inbound-{uuid.uuid4().hex[:12]}"
    ws_url = f"wss://{request.headers.get('host', 'localhost:8000')}/ws/twilio/{call_id}"

    logger.info(f"Incoming Inbound Call registered: {call_id}", call_id=call_id)

    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Say>Connecting to Voice AI assistant...</Say>
        <Connect>
            <Stream url="{ws_url}" />
        </Connect>
    </Response>"""

    return Response(content=twiml_response, media_type="application/xml")


@router.post("/twilio/status")
async def twilio_status_callback(request: Request):
    """Status callback for call event logging."""
    try:
        form_data = await request.form()
        call_sid = form_data.get("CallSid")
        call_status = form_data.get("CallStatus")
    except Exception as e:
        logger.warning("Failed to parse Twilio status callback form data", error=str(e))
        call_sid, call_status = None, None
    logger.info(
        f"Twilio Call {call_sid} status update: {call_status}",
        call_sid=call_sid,
        status=call_status,
    )
    return {"status": "ok"}
