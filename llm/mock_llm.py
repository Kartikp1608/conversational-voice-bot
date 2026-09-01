import asyncio
from typing import Any, AsyncGenerator, Dict, List

from llm.base_llm import BaseLLM, LLMResponseChunk
from logging_config import get_logger
from utils.async_helpers import CancellationToken

logger = get_logger("llm.mock")


class MockLLM(BaseLLM):
    """Deterministic Mock LLM streaming provider for unit tests and local execution."""

    def __init__(
        self,
        response_text: str | None = None,
        trigger_tool: str | None = None,
        tool_args: Dict[str, Any] | None = None,
        model: str | None = None,
    ):
        self.response_text = response_text
        self.trigger_tool = trigger_tool
        self.tool_args = tool_args or {}
        self.model = model or "mock-model"

    async def generate_stream(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools_schema: List[Dict[str, Any]] | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncGenerator[LLMResponseChunk, None]:

        # Check if last user message asks for a tool execution trigger
        last_msg = (messages[-1].get("content", "") if messages else "").lower()

        if (
            self.trigger_tool
            or "book" in last_msg
            or "calendar" in last_msg
            or "schedule" in last_msg
        ):
            tool_name = self.trigger_tool or "book_appointment"
            tool_params = self.tool_args or {
                "date": "2026-07-29",
                "time": "10:00 AM",
                "service": "General Consultation",
            }
            yield LLMResponseChunk(tool_call_name=tool_name, tool_call_args=tool_params)
            yield LLMResponseChunk(is_finished=True)
            return

        text = self.response_text
        if not text:
            if "hello" in last_msg or "hi" in last_msg:
                text = "Hello! Welcome to Apex Health Services. How can I assist you with your booking today?"
            elif "verify" in last_msg or "name" in last_msg:
                text = "Thank you. Could you please confirm your date of birth for verification?"
            else:
                text = "Thank you for that information. Let me check our database to process your request."

        tokens = text.split(" ")
        for token in tokens:
            if cancellation_token and cancellation_token.is_cancelled:
                logger.info("Mock LLM generation cancelled by barge-in")
                return
            yield LLMResponseChunk(text_delta=token + " ")
            await asyncio.sleep(0.01)

        yield LLMResponseChunk(is_finished=True)
