import json
from typing import Dict, Any
from telephony.base_telephony import BaseTelephonyAdapter


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
            except Exception:
                return {"event": "unknown"}
        return {"event": "unknown"}
