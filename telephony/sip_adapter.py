import json
from typing import Dict, Any
from telephony.base_telephony import BaseTelephonyAdapter


from logging_config import get_logger

logger = get_logger("telephony.sip")


class SIPAdapter(BaseTelephonyAdapter):
    """Generic SIP / WebRTC direct binary PCM stream adapter."""

    async def make_outbound_call(
        self,
        to_phone_number: str,
        from_phone_number: str,
        websocket_url: str,
    ) -> Dict[str, Any]:
        return {
            "status": "initiated",
            "sip_uri": f"sip:{to_phone_number}@gateway.sip.local",
            "websocket_url": websocket_url,
        }

    def parse_media_event(self, raw_message: Any) -> Dict[str, Any]:
        if isinstance(raw_message, bytes):
            return {"event": "media", "pcm_bytes": raw_message}
        elif isinstance(raw_message, str):
            try:
                data = json.loads(raw_message)
                return {"event": data.get("type", "unknown"), "data": data}
            except json.JSONDecodeError as e:
                logger.warning("Invalid JSON received in SIP media stream", error=str(e))
                return {"event": "error", "error": f"Invalid JSON message: {str(e)}"}
        return {"event": "unknown"}
