import time
from typing import Dict

from logging_config import get_logger
from monitoring.metrics import ACTIVE_CALLS

logger = get_logger("voice_gateway.session_manager")


class VoiceSession:
    """Encapsulates active voice session lifecycle and stream metadata."""

    def __init__(self, session_id: str, call_id: str, prompt_id: str, direction: str = "inbound"):
        self.session_id = session_id
        self.call_id = call_id
        self.prompt_id = prompt_id
        self.direction = direction
        self.created_at = time.time()
        self.last_heartbeat = time.time()
        self.is_active = True

    def touch(self) -> None:
        self.last_heartbeat = time.time()


class SessionManager:
    """Central Manager tracking active Voice Sessions across WebSocket connections."""

    def __init__(self):
        self._sessions: Dict[str, VoiceSession] = {}

    def create_session(
        self, session_id: str, call_id: str, prompt_id: str, direction: str = "inbound"
    ) -> VoiceSession:
        session = VoiceSession(session_id, call_id, prompt_id, direction)
        self._sessions[session_id] = session
        ACTIVE_CALLS.set(len(self._sessions))
        logger.info(
            f"Created active voice session {session_id}", session_id=session_id, call_id=call_id
        )
        return session

    def get_session(self, session_id: str) -> VoiceSession | None:
        return self._sessions.get(session_id)

    def close_session(self, session_id: str) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]
            ACTIVE_CALLS.set(len(self._sessions))
            logger.info(f"Closed voice session {session_id}", session_id=session_id)
