from typing import List, Dict, Any, Optional
from conversation.state_machine import StateMachine, CallStage
from memory.short_term_memory import ShortTermMemory
from memory.knowledge_base import KnowledgeBase
from prompt_engine.prompt_builder import PromptBuilder
from logging_config import get_logger

logger = get_logger("conversation_manager")


class ConversationManager:
    """Central Orchestrator for conversation history, goal state, stage transitions, and prompt generation."""

    def __init__(self, prompt_id: str = "sales_outbound", call_id: str = "call-100"):
        self.prompt_id = prompt_id
        self.call_id = call_id
        self.state_machine = StateMachine(initial_stage=CallStage.GREETING)
        self.memory = ShortTermMemory(max_turns=12)
        self.knowledge_base = KnowledgeBase()
        self.prompt_builder = PromptBuilder()
        self.context_vars: Dict[str, Any] = {"call_id": call_id}

    def process_user_turn(self, user_transcript: str) -> str:
        """Record user input, update stage progression heuristic, and return updated system prompt."""
        self.memory.add_user_message(user_transcript)

        # Stage progression heuristics based on transcript content
        lower = user_transcript.lower()
        if "yes" in lower or "confirm" in lower or "book" in lower:
            if self.state_machine.current_stage == CallStage.GREETING:
                self.state_machine.transition_to(CallStage.BUSINESS_LOGIC)
            elif self.state_machine.current_stage == CallStage.BUSINESS_LOGIC:
                self.state_machine.transition_to(CallStage.TOOL_EXECUTION)

        elif "human" in lower or "operator" in lower or "transfer" in lower:
            self.state_machine.transition_to(CallStage.ESCALATION)

        elif "bye" in lower or "thank you" in lower or "stop" in lower:
            self.state_machine.transition_to(CallStage.CLOSING)

        # Retrieve RAG context facts
        rag_facts = self.knowledge_base.search(user_transcript, top_k=2)

        # Build dynamic system prompt
        system_prompt = self.prompt_builder.build_system_prompt(
            prompt_id=self.prompt_id,
            current_stage=self.state_machine.current_stage.value,
            context_vars=self.context_vars,
            rag_facts=rag_facts,
        )

        return system_prompt

    def record_assistant_turn(self, assistant_text: str) -> None:
        """Record generated assistant turn in short term memory."""
        self.memory.add_assistant_message(assistant_text)

    def get_messages(self) -> List[Dict[str, Any]]:
        return self.memory.get_messages()
