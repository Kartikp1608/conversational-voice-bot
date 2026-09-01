from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm.gemini_live import GeminiLiveLLM
from llm.mock_llm import MockLLM
from utils.async_helpers import CancellationToken


@pytest.mark.asyncio
async def test_mock_llm_streaming_text():
    llm = MockLLM(model="mock-gpt")
    messages = [{"role": "user", "content": "Hello there"}]
    chunks = []

    async for chunk in llm.generate_stream(system_prompt="You are an assistant", messages=messages):
        chunks.append(chunk)

    text = "".join([c.text_delta for c in chunks if c.text_delta])
    assert len(text) > 0
    assert chunks[-1].is_finished is True


@pytest.mark.asyncio
async def test_mock_llm_tool_call_generation():
    llm = MockLLM()
    messages = [
        {"role": "user", "content": "I want to schedule an appointment for tomorrow at 10 AM"}
    ]
    chunks = []

    async for chunk in llm.generate_stream(system_prompt="You are an assistant", messages=messages):
        chunks.append(chunk)

    tool_chunks = [c for c in chunks if c.tool_call_name]
    assert len(tool_chunks) > 0
    assert tool_chunks[0].tool_call_name == "book_appointment"
    assert tool_chunks[0].tool_call_args is not None
    assert "date" in tool_chunks[0].tool_call_args


@pytest.mark.asyncio
async def test_mock_llm_cancellation():
    llm = MockLLM()
    token = CancellationToken()
    token.cancel()

    messages = [{"role": "user", "content": "Tell me a very long story"}]
    chunks = []

    async for chunk in llm.generate_stream(
        system_prompt="Test", messages=messages, cancellation_token=token
    ):
        chunks.append(chunk)

    assert len(chunks) == 0


def test_gemini_format_contents_history():
    llm = GeminiLiveLLM(api_key="test-key")

    # Single turn
    msgs = [{"role": "user", "content": "Hello"}]
    formatted = llm._format_contents_history(msgs)
    assert len(formatted) == 1
    assert formatted[0]["role"] == "user"
    assert formatted[0]["parts"][0]["text"] == "Hello"

    # Consecutive turns merged
    msgs = [
        {"role": "user", "content": "Hello"},
        {"role": "user", "content": "My name is Alice"},
    ]
    formatted = llm._format_contents_history(msgs)
    assert len(formatted) == 1
    assert "Alice" in formatted[0]["parts"][0]["text"]

    # Alternating turns
    msgs = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help?"},
        {"role": "user", "content": "Book a flight"},
    ]
    formatted = llm._format_contents_history(msgs)
    assert len(formatted) == 3
    assert formatted[1]["role"] == "model"


@pytest.mark.asyncio
async def test_gemini_intelligent_conversational_response():
    llm = GeminiLiveLLM(api_key="test-key")

    # Name recall
    messages = [
        {"role": "user", "content": "My name is John"},
        {"role": "assistant", "content": "Nice to meet you John."},
        {"role": "user", "content": "What is my name?"},
    ]
    chunks = []
    async for chunk in llm._intelligent_conversational_response(messages, "prompt", None):
        chunks.append(chunk)

    text = "".join([c.text_delta for c in chunks if c.text_delta])
    assert "John" in text


@pytest.mark.asyncio
async def test_gemini_intelligent_conversational_tool_call():
    llm = GeminiLiveLLM(api_key="test-key")
    messages = [{"role": "user", "content": "Book for tomorrow 10am"}]
    chunks = []
    async for chunk in llm._intelligent_conversational_response(messages, "prompt", None):
        chunks.append(chunk)

    tool_calls = [c for c in chunks if c.tool_call_name]
    assert len(tool_calls) == 1
    assert tool_calls[0].tool_call_name == "book_appointment"


@pytest.mark.asyncio
async def test_gemini_generate_stream_fallback():
    llm = GeminiLiveLLM(api_key="test-key")
    messages = [{"role": "user", "content": "hello"}]
    chunks = []

    async for chunk in llm.generate_stream(system_prompt="Test", messages=messages):
        chunks.append(chunk)

    text = "".join([c.text_delta for c in chunks if c.text_delta])
    assert "Hello" in text
    assert chunks[-1].is_finished is True


@pytest.mark.asyncio
async def test_gemini_generate_stream_vertex_mock():
    llm = GeminiLiveLLM(api_key="test-key")
    llm.project_id = "test-project"

    with patch.object(llm, "_get_access_token", return_value="fake-token"):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Vertex AI Live Response"},
                            {
                                "functionCall": {
                                    "name": "crm_lookup",
                                    "args": {"customer_id": "123"},
                                }
                            },
                        ]
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp

            messages = [{"role": "user", "content": "Find my account"}]
            chunks = []
            async for chunk in llm.generate_stream(system_prompt="Test", messages=messages):
                chunks.append(chunk)

            text_chunks = [c.text_delta for c in chunks if c.text_delta]
            tool_chunks = [c for c in chunks if c.tool_call_name]

            assert "Vertex AI Live Response" in text_chunks
            assert len(tool_chunks) == 1
            assert tool_chunks[0].tool_call_name == "crm_lookup"
