import os
import yaml
from typing import Dict, Any, Optional
from logging_config import get_logger

logger = get_logger("prompt_loader")


class PromptLoader:
    """Loads, validates and caches business prompt YAML files."""

    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = prompts_dir
        self._cache: Dict[str, Dict[str, Any]] = {}

    def load_prompt(self, prompt_id: str) -> Dict[str, Any]:
        """Load prompt specification by ID (filename without extension)."""
        if prompt_id in self._cache:
            return self._cache[prompt_id]

        file_path = os.path.join(self.prompts_dir, f"{prompt_id}.yaml")
        if not os.path.exists(file_path):
            file_path = os.path.join(self.prompts_dir, f"{prompt_id}.yml")

        if not os.path.exists(file_path):
            logger.warning(f"Prompt file {file_path} not found, using default fallback template")
            return self._get_fallback_prompt(prompt_id)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                self._cache[prompt_id] = data
                return data
        except Exception as e:
            logger.error(f"Failed to parse YAML prompt file {file_path}", error=str(e))
            return self._get_fallback_prompt(prompt_id)

    def _get_fallback_prompt(self, prompt_id: str) -> Dict[str, Any]:
        return {
            "name": prompt_id,
            "role": "Conversational AI Voice Assistant",
            "personality": "Helpful, professional, clear, concise, human-like.",
            "tone": "Warm, professional, natural.",
            "rules": [
                "Keep responses under 25 words for conversational voice pacing.",
                "Speak naturally with human conversational pauses.",
                "If the user interrupts, stop speaking immediately.",
                "Confirm key details before taking actions."
            ],
            "workflow": {
                "GREETING": "Greet the user warmly and introduce yourself.",
                "BUSINESS_LOGIC": "Understand user's intent and assist them.",
                "CLOSING": "Thank the user and end the call politely."
            },
            "fallbacks": [
                "I'm sorry, I didn't quite catch that. Could you please repeat?",
                "Could you clarify your request for me?"
            ]
        }
