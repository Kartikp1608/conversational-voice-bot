from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List

from utils.async_helpers import CancellationToken


class LLMResponseChunk:
    def __init__(
        self,
        text_delta: str | None = None,
        tool_call_name: str | None = None,
        tool_call_args: Dict[str, Any] | None = None,
        is_finished: bool = False,
    ):
        self.text_delta = text_delta
        self.tool_call_name = tool_call_name
        self.tool_call_args = tool_call_args
        self.is_finished = is_finished


class BaseLLM(ABC):
    """Abstract Language Model provider interface supporting streaming tokens & function calling."""

    @abstractmethod
    def generate_stream(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools_schema: List[Dict[str, Any]] | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncGenerator[LLMResponseChunk, None]:
        """Generate response token stream asynchronously."""
        pass
