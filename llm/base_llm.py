from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict, Any, Optional
from utils.async_helpers import CancellationToken


class LLMResponseChunk:
    def __init__(
        self,
        text_delta: Optional[str] = None,
        tool_call_name: Optional[str] = None,
        tool_call_args: Optional[Dict[str, Any]] = None,
        is_finished: bool = False,
    ):
        self.text_delta = text_delta
        self.tool_call_name = tool_call_name
        self.tool_call_args = tool_call_args
        self.is_finished = is_finished


class BaseLLM(ABC):
    """Abstract Language Model provider interface supporting streaming tokens & function calling."""

    @abstractmethod
    async def generate_stream(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools_schema: Optional[List[Dict[str, Any]]] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[LLMResponseChunk, None]:
        """Generate response token stream asynchronously."""
        pass
