import pytest
import asyncio
from interruptions.interrupt_manager import InterruptManager
from utils.async_helpers import BoundedAudioQueue


@pytest.mark.asyncio
async def test_barge_in_interruption_flush():
    mgr = InterruptManager(session_id="sess-test-1")
    queue = BoundedAudioQueue(maxsize=100)

    # Populate audio buffer
    await queue.put(b"frame1")
    await queue.put(b"frame2")
    await queue.put(b"frame3")

    token = mgr.create_token()
    assert not token.is_cancelled

    # Trigger barge-in
    flushed = mgr.trigger_interruption(queue)
    assert flushed == 3
    assert token.is_cancelled
    assert queue.empty()
