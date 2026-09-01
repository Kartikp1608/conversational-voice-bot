from enum import Enum
from typing import Dict, List

from logging_config import get_logger

logger = get_logger("conversation.state_machine")


class CallStage(str, Enum):
    GREETING = "GREETING"
    VERIFICATION = "VERIFICATION"
    BUSINESS_LOGIC = "BUSINESS_LOGIC"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    CONFIRMATION = "CONFIRMATION"
    ESCALATION = "ESCALATION"
    CLOSING = "CLOSING"
    ENDED = "ENDED"


class StateMachine:
    """Production State Machine governing call stage transitions and business flow requirements."""

    VALID_TRANSITIONS: Dict[CallStage, List[CallStage]] = {
        CallStage.GREETING: [
            CallStage.VERIFICATION,
            CallStage.BUSINESS_LOGIC,
            CallStage.CLOSING,
            CallStage.ESCALATION,
        ],
        CallStage.VERIFICATION: [CallStage.BUSINESS_LOGIC, CallStage.ESCALATION, CallStage.CLOSING],
        CallStage.BUSINESS_LOGIC: [
            CallStage.TOOL_EXECUTION,
            CallStage.CONFIRMATION,
            CallStage.ESCALATION,
            CallStage.CLOSING,
        ],
        CallStage.TOOL_EXECUTION: [
            CallStage.CONFIRMATION,
            CallStage.BUSINESS_LOGIC,
            CallStage.ESCALATION,
        ],
        CallStage.CONFIRMATION: [CallStage.CLOSING, CallStage.BUSINESS_LOGIC, CallStage.ESCALATION],
        CallStage.ESCALATION: [CallStage.CLOSING, CallStage.ENDED],
        CallStage.CLOSING: [CallStage.ENDED],
        CallStage.ENDED: [],
    }

    def __init__(self, initial_stage: CallStage = CallStage.GREETING):
        self.current_stage = initial_stage
        self.previous_stage: CallStage | None = None

    def transition_to(self, target_stage: CallStage) -> bool:
        """Attempt stage transition. Returns True if valid transition, False otherwise."""
        if target_stage == self.current_stage:
            return True

        allowed = self.VALID_TRANSITIONS.get(self.current_stage, [])
        if target_stage in allowed:
            logger.info(
                f"State transition: {self.current_stage.value} -> {target_stage.value}",
                from_stage=self.current_stage.value,
                to_stage=target_stage.value,
            )
            self.previous_stage = self.current_stage
            self.current_stage = target_stage
            return True
        else:
            logger.warning(
                f"Invalid transition attempted: {self.current_stage.value} -> {target_stage.value}",
                from_stage=self.current_stage.value,
                to_stage=target_stage.value,
            )
            return False
