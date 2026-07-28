from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
from utils.async_helpers import CancellationToken


class BaseTTS(ABC):
    """Abstract Text-To-Speech Provider interface."""

    @abstractmethod
    async def synthesize_stream(
        self,
        text_stream: AsyncGenerator[str, None],
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[bytes, None]:
        """Synthesize text token stream into raw PCM 16-bit 16kHz audio frame chunks."""
        pass
