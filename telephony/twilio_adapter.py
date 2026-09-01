import base64
import json
from typing import Any, Dict

import httpx

from logging_config import get_logger
from telephony.base_telephony import BaseTelephonyAdapter
from utils.audio_utils import AudioUtils

logger = get_logger("telephony.twilio")


class TwilioAdapter(BaseTelephonyAdapter):
    """Twilio Media Streams & Voice REST API integration adapter."""

    def __init__(
        self,
        account_sid: str | None = None,
        auth_token: str | None = None,
        default_from_number: str | None = None,
    ):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.default_from_number = default_from_number

    async def make_outbound_call(
        self,
        to_phone_number: str,
        from_phone_number: str,
        websocket_url: str,
    ) -> Dict[str, Any]:
        """Trigger Twilio REST API to place outbound call using TwiML WebSocket stream connector."""
        if not self.account_sid or not self.auth_token:
            logger.warning("Twilio credentials not configured, executing simulated outbound call")
            return {
                "status": "queued",
                "call_sid": "CA-SIMULATED-99012",
                "to": to_phone_number,
                "from": from_phone_number,
                "websocket_url": websocket_url,
            }

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Calls.json"

        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Connect>
                <Stream url="{websocket_url}" />
            </Connect>
        </Response>"""

        data = {
            "To": to_phone_number,
            "From": from_phone_number or self.default_from_number,
            "Twiml": twiml,
        }

        try:
            async with httpx.AsyncClient(auth=(self.account_sid, self.auth_token)) as client:
                response = await client.post(url, data=data)
                response.raise_for_status()
                res = response.json()
                return {
                    "status": res.get("status"),
                    "call_sid": res.get("sid"),
                    "to": to_phone_number,
                }
        except Exception as e:
            logger.error("Failed to place Twilio outbound call", error=str(e))
            return {"status": "error", "message": str(e)}

    def parse_media_event(self, raw_message: str) -> Dict[str, Any]:
        """Parse incoming JSON frame from Twilio WebSocket Media Stream (connected, start, media, stop)."""
        try:
            data = json.loads(raw_message)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Failed to decode Twilio media JSON event", error=str(e))
            return {"event": "error", "error": str(e)}

        event_type = data.get("event")

        if event_type == "media":
            payload_mulaw = base64.b64decode(data["media"]["payload"])
            # Convert G.711 mu-law to 16-bit 16kHz linear PCM
            pcm_bytes = AudioUtils.mulaw_to_pcm(payload_mulaw)
            return {
                "event": "media",
                "stream_sid": data.get("streamSid"),
                "pcm_bytes": pcm_bytes,
                "track": data["media"].get("track"),
            }
        elif event_type == "start":
            return {
                "event": "start",
                "stream_sid": data.get("streamSid"),
                "call_sid": data.get("start", {}).get("callSid"),
                "media_format": data.get("start", {}).get("mediaFormat"),
            }
        elif event_type == "stop":
            return {"event": "stop", "stream_sid": data.get("streamSid")}
        else:
            return {"event": event_type, "raw": data}

    @staticmethod
    def format_outbound_media_payload(stream_sid: str, pcm_bytes: bytes) -> str:
        """Format 16-bit linear PCM audio chunk into Twilio WebSocket G.711 mu-law JSON payload."""
        mulaw_bytes = AudioUtils.pcm_to_mulaw(pcm_bytes)
        b64_payload = base64.b64encode(mulaw_bytes).decode("utf-8")
        return json.dumps(
            {
                "event": "media",
                "streamSid": stream_sid,
                "media": {"payload": b64_payload},
            }
        )
