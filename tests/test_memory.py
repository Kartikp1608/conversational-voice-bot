import pytest

from memory.knowledge_base import KnowledgeBase
from memory.short_term_memory import ShortTermMemory
from memory.summary_manager import SummaryManager


def test_short_term_memory_sliding_window():
    mem = ShortTermMemory(max_turns=3)
    for i in range(10):
        mem.add_user_message(f"User msg {i}")
        mem.add_assistant_message(f"Bot msg {i}")

    msgs = mem.get_messages()
    assert len(msgs) == 6  # max_turns * 2
    assert msgs[-1]["content"] == "Bot msg 9"
    assert msgs[0]["content"] == "User msg 7"


def test_short_term_memory_entities_and_clear():
    mem = ShortTermMemory()
    mem.set_entity("name", "Alice")
    mem.set_entity("account_id", "ACC-12345")
    mem.intent = "book_appointment"
    mem.pending_questions.append("What time?")

    assert mem.get_entity("name") == "Alice"
    assert mem.get_entity("account_id") == "ACC-12345"
    assert mem.get_entity("nonexistent") is None

    mem.clear()
    assert len(mem.get_messages()) == 0
    assert mem.get_entity("name") is None
    assert mem.intent is None
    assert len(mem.pending_questions) == 0


def test_knowledge_base_search():
    kb = KnowledgeBase()
    assert kb.search("") == []
    assert kb.search("anything") == []

    kb.add_document(
        "doc1",
        "Apex Health Clinic offers cardiology, dermatology, and general consultation services.",
    )
    kb.add_document(
        "doc2", "Vantage Bank offers checking accounts, mortgages, and fraud monitoring."
    )
    kb.add_document("doc3", "Nexus Telecom provides high-speed fiber internet and mobile plans.")

    res = kb.search("cardiology dermatology", top_k=1)
    assert len(res) == 1
    assert "Apex Health Clinic" in res[0]

    res2 = kb.search("fiber internet plans", top_k=2)
    assert len(res2) >= 1
    assert "Nexus Telecom" in res2[0]


@pytest.mark.asyncio
async def test_summary_manager():
    sm = SummaryManager()
    empty_res = await sm.summarize([])
    assert empty_res == ""

    messages = [
        {"role": "user", "content": "I need to book a dental checkup."},
        {"role": "assistant", "content": "Sure, tomorrow at 10 AM is available."},
        {"role": "user", "content": "Please confirm."},
    ]
    summary = await sm.summarize(messages)
    assert "dental checkup" in summary
    assert sm.summary == summary
