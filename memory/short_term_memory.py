from typing import List, Dict, Any, Optional


class ShortTermMemory:
    """Manages sliding window turn context, conversation state, intent, and extracted entities."""

    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self.messages: List[Dict[str, Any]] = []
        self.entities: Dict[str, Any] = {}
        self.intent: Optional[str] = None
        self.pending_questions: List[str] = []

    def add_user_message(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})
        self._trim()

    def add_assistant_message(self, text: str) -> None:
        self.messages.append({"role": "assistant", "content": text})
        self._trim()

    def set_entity(self, key: str, value: Any) -> None:
        self.entities[key] = value

    def get_entity(self, key: str) -> Optional[Any]:
        return self.entities.get(key)

    def _trim(self) -> None:
        if len(self.messages) > self.max_turns * 2:
            self.messages = self.messages[-(self.max_turns * 2):]

    def get_messages(self) -> List[Dict[str, Any]]:
        return list(self.messages)

    def clear(self) -> None:
        self.messages.clear()
        self.entities.clear()
        self.intent = None
        self.pending_questions.clear()
