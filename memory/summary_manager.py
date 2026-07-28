from typing import List, Dict, Any
from logging_config import get_logger

logger = get_logger("memory.summary")


class SummaryManager:
    """Async background conversation summarizer and context compression engine."""

    def __init__(self):
        self.summary: str = ""

    async def summarize(self, messages: List[Dict[str, Any]]) -> str:
        """Compress long conversation transcript into concise factual summary."""
        if not messages:
            return self.summary

        user_texts = [m["content"] for m in messages if m.get("role") == "user"]
        assistant_texts = [m["content"] for m in messages if m.get("role") == "assistant"]

        brief = f"User inquired about {', '.join(user_texts[:3])}. Assistant provided response."
        self.summary = brief
        logger.info("Generated compressed conversation summary", summary=self.summary)
        return self.summary
