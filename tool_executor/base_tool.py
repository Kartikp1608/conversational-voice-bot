from abc import ABC, abstractmethod
from typing import Dict, Any, Type
from pydantic import BaseModel


class BaseTool(ABC):
    """Abstract pluggable tool interface with strict typing and schema generation."""

    name: str
    description: str
    args_schema: Type[BaseModel]

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Async execution handler for tool plugin."""
        pass

    def get_openai_schema(self) -> Dict[str, Any]:
        """Export tool signature as OpenAI / Gemini compliant tool declaration schema."""
        schema = self.args_schema.model_json_schema()
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "OBJECT",
                "properties": schema.get("properties", {}),
                "required": schema.get("required", []),
            }
        }
