import pytest
from conversation.conversation_manager import ConversationManager
from conversation.state_machine import CallStage


def test_conversation_manager_stage_progression():
    cm = ConversationManager(prompt_id="sales_outbound", call_id="call-conv-1")
    assert cm.state_machine.current_stage == CallStage.GREETING

    # Step 1: User says yes -> moves to business logic
    p1 = cm.process_user_turn("Yes, I would like to hear more.")
    assert cm.state_machine.current_stage == CallStage.BUSINESS_LOGIC
    assert len(p1) > 0

    # Step 2: User confirms booking -> moves to tool execution
    p2 = cm.process_user_turn("Please confirm and book.")
    assert cm.state_machine.current_stage == CallStage.TOOL_EXECUTION

    # Step 3: Record assistant turn
    cm.record_assistant_turn("Appointment is booked.")
    messages = cm.get_messages()
    assert len(messages) == 3
    assert messages[-1]["role"] == "assistant"


def test_conversation_manager_escalation_and_closing():
    cm = ConversationManager(prompt_id="healthcare_appointment", call_id="call-conv-2")

    # Escalation trigger
    cm.process_user_turn("I want to speak with a human operator.")
    assert cm.state_machine.current_stage == CallStage.ESCALATION

    # Closing trigger
    cm.process_user_turn("Thank you, bye.")
    assert cm.state_machine.current_stage == CallStage.CLOSING
