import asyncio
import pytest
from conversation.turn_aggregator import TurnAggregator


@pytest.mark.asyncio
async def test_turn_aggregator_combines_paused_transcripts():
    results = []

    async def callback(final_text: str):
        results.append(final_text)

    aggregator = TurnAggregator(debounce_ms=100.0)

    # User speaks fragment 1
    aggregator.add_transcript("i was hoping that i could get a appointment today at", callback)
    await asyncio.sleep(0.05)

    # User speaks fragment 2 (within 50ms pause window)
    aggregator.add_transcript("three pm", callback)

    # Wait for debouncer to expire
    await asyncio.sleep(0.7)

    assert len(results) == 1
    assert results[0] == "i was hoping that i could get a appointment today at three pm"


@pytest.mark.asyncio
async def test_turn_aggregator_reset_on_barge_in():
    results = []

    async def callback(final_text: str):
        results.append(final_text)

    aggregator = TurnAggregator(debounce_ms=200.0)
    aggregator.add_transcript("partial sentence before barge in", callback)

    # Barge-in resets aggregator
    aggregator.reset()

    await asyncio.sleep(0.3)
    assert len(results) == 0
