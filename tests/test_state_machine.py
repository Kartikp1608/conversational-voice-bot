from conversation.state_machine import StateMachine, CallStage


def test_state_machine_valid_transitions():
    sm = StateMachine(initial_stage=CallStage.GREETING)
    assert sm.current_stage == CallStage.GREETING

    assert sm.transition_to(CallStage.BUSINESS_LOGIC)
    assert sm.current_stage == CallStage.BUSINESS_LOGIC

    assert sm.transition_to(CallStage.TOOL_EXECUTION)
    assert sm.current_stage == CallStage.TOOL_EXECUTION

    assert sm.transition_to(CallStage.CONFIRMATION)
    assert sm.current_stage == CallStage.CONFIRMATION

    assert sm.transition_to(CallStage.CLOSING)
    assert sm.current_stage == CallStage.CLOSING


def test_state_machine_invalid_transition():
    sm = StateMachine(initial_stage=CallStage.GREETING)
    # Direct transition from GREETING to ENDED is invalid
    assert not sm.transition_to(CallStage.ENDED)
    assert sm.current_stage == CallStage.GREETING
