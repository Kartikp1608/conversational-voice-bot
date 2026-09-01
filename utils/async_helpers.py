import asyncio


class CancellationToken:
    """Thread-safe async cancellation token used to abort running speech synthesis or tool execution on barge-in."""

    def __init__(self):
        self._is_cancelled = False
        self._event = asyncio.Event()

    def cancel(self) -> None:
        """Mark token as cancelled and notify waiting tasks."""
        self._is_cancelled = True
        self._event.set()

    def reset(self) -> None:
        """Reset cancellation token for the next turn."""
        self._is_cancelled = False
        self._event.clear()

    @property
    def is_cancelled(self) -> bool:
        return self._is_cancelled

    async def wait_until_cancelled(self) -> None:
        """Wait until cancellation token is triggered."""
        await self._event.wait()


class BoundedAudioQueue:
    """Async bounded queue for streaming audio frames with instant flush capability on interruption."""

    def __init__(self, maxsize: int = 100):
        self.queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=maxsize)

    async def put(self, chunk: bytes | None) -> None:
        """Put audio chunk into stream queue."""
        await self.queue.put(chunk)

    async def get(self) -> bytes | None:
        """Get audio chunk from queue."""
        return await self.queue.get()

    def clear(self) -> int:
        """Flush all pending audio frames from buffer (used on user interruption). Returns count of dropped frames."""
        cleared_count = 0
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
                cleared_count += 1
            except (asyncio.QueueEmpty, ValueError):
                break
        return cleared_count

    def empty(self) -> bool:
        return self.queue.empty()
