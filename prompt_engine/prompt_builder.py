from typing import Dict, Any, List, Optional
from prompt_engine.prompt_loader import PromptLoader


class PromptBuilder:
    """Dynamic System Prompt Construction Engine.
    Compiles system instructions from business configuration prompts, active state, short-term memory, and RAG knowledge.
    """

    def __init__(self, loader: Optional[PromptLoader] = None):
        self.loader = loader or PromptLoader()

    def build_system_prompt(
        self,
        prompt_id: str,
        current_stage: str = "GREETING",
        context_vars: Optional[Dict[str, Any]] = None,
        rag_facts: Optional[List[str]] = None,
    ) -> str:
        data = self.loader.load_prompt(prompt_id)
        context_vars = context_vars or {}

        sections = []

        # Role & Persona
        role = data.get("role", "Voice AI Assistant")
        personality = data.get("personality", "Friendly and efficient.")
        tone = data.get("tone", "Professional")
        sections.append(f"=== YOUR ROLE & PERSONALITY ===\nRole: {role}\nPersonality: {personality}\nTone: {tone}\n")

        # Rules
        rules = data.get("rules", [])
        if rules:
            rule_str = "\n".join([f"- {r}" for r in rules])
            sections.append(f"=== STRICT CONVERSATIONAL RULES ===\n{rule_str}\n")

        # Do's and Don'ts
        dos = data.get("dos", [])
        donts = data.get("donts", [])
        if dos or donts:
            do_str = "\n".join([f"✓ DO: {d}" for d in dos])
            dont_str = "\n".join([f"✗ DON'T: {d}" for d in donts])
            sections.append(f"=== GUIDELINES ===\n{do_str}\n{dont_str}\n")

        # Workflow & Current Stage
        workflow = data.get("workflow", {})
        sections.append(f"=== CURRENT CONVERSATION STAGE: {current_stage} ===")
        if current_stage in workflow:
            sections.append(f"Stage Directive: {workflow[current_stage]}")
        else:
            sections.append("Stage Directive: Guide the customer toward resolving their request efficiently.")
        sections.append("")

        # Knowledge Base / RAG Context
        kb = data.get("knowledge_base", [])
        if rag_facts:
            kb.extend(rag_facts)
        if kb:
            kb_str = "\n".join([f"• {k}" for k in kb])
            sections.append(f"=== KNOWLEDGE BASE ===\n{kb_str}\n")

        # Dynamic Context variables (Customer metadata, CRM info)
        if context_vars:
            ctx_str = "\n".join([f"- {k}: {v}" for k, v in context_vars.items()])
            sections.append(f"=== CUSTOMER CONTEXT ===\n{ctx_str}\n")

        # Fallback & Escalation Directives
        fallbacks = data.get("fallbacks", [])
        escalations = data.get("escalations", [])
        if escalations:
            esc_str = "\n".join([f"- {e}" for e in escalations])
            sections.append(f"=== HUMAN ESCALATION PROTOCOL ===\n{esc_str}\n")

        return "\n".join(sections)
