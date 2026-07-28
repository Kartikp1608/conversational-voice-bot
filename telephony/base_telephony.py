from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseTelephonyAdapter(ABC):
    """Abstract Telephony Provider Interface (Twilio, Plivo, WebRTC, SIP)."""

    @abstractmethod
    async def make_outbound_call(
        self,
        to_phone_number: str,
        from_phone_number: str,
        websocket_url: str,
    ) -> Dict[str, Any]:
        """Initiate outbound phone call linking to WebSocket media gateway."""
        pass

    @abstractmethod
    def parse_media_event(self, raw_message: str) -> Dict[str, Any]:
        """Parse raw incoming WebSocket frame into normalized audio payload format."""
        pass
