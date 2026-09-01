import asyncio
from typing import Awaitable, Callable, List

from logging_config import get_logger

logger = get_logger("conversation.turn_aggregator")


class TurnAggregator:
    """Production Real-Time End-of-Utterance Debouncer & Sentence Aggregator.
    Prevents premature LLM triggers when the user takes natural 0.5s speech pauses mid-sentence.
    """

    TRAILING_CONNECTORS = {
        "at",
        "and",
        "or",
        "to",
        "is",
        "my",
        "for",
        "the",
        "a",
        "an",
        "in",
        "on",
        "with",
        "about",
        "of",
        "that",
        "this",
        "because",
        "so",
        "was",
        "were",
        "are",
        "am",
        "have",
        "had",
        "will",
    }

    def __init__(self, debounce_ms: float = 750.0):
        self.debounce_sec = debounce_ms / 1000.0
        self._buffer: List[str] = []
        self._timer_task: asyncio.Task | None = None
        self._callback: Callable[[str], Awaitable[None]] | None = None

    def add_transcript(self, text: str, callback: Callable[[str], Awaitable[None]]) -> None:
        """Ingest STT transcript fragment, buffer it, and start/reset debouncer timer."""
        text = text.strip()
        if not text:
            return

        self._callback = callback
        self._buffer.append(text)

        # Cancel active debounce timer if user continued speaking
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()

        # Schedule debounced utterance finalization
        self._timer_task = asyncio.create_task(self._wait_and_finalize())

    async def _wait_and_finalize(self) -> None:
        """Wait for pause window to elapse before firing single aggregated LLM turn."""
        full_text = " ".join(self._buffer).strip()
        words = full_text.split()
        last_word = words[-1].lower() if words else ""

        wait_time = self.debounce_sec
        # If phrase ends with an incomplete connector word (e.g. "my date of birth is..."), wait extra time
        if last_word in self.TRAILING_CONNECTORS:
            wait_time += 0.45

        try:
            await asyncio.sleep(wait_time)
        except asyncio.CancelledError:
            return

        final_utterance = " ".join(self._buffer).strip()
        self._buffer.clear()

        if final_utterance and self._callback:
            logger.info(
                f"Finalized Aggregated User Utterance: '{final_utterance}'",
                utterance=final_utterance,
            )
            await self._callback(final_utterance)

    def reset(self) -> None:
        """Clear buffer and cancel active timer on barge-in."""
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
        self._buffer.clear()
