import time
from typing import Any, Dict, List

from logging_config import get_logger
from monitoring.metrics import TOOL_EXECUTIONS
from tool_executor.base_tool import BaseTool

logger = get_logger("tool_executor.registry")


class ToolRegistry:
    """Async central Tool Registry managing pluggable tool registration and execution."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool
        logger.info(f"Registered tool plugin: {tool.name}")

    def get_tool(self, tool_name: str) -> BaseTool | None:
        return self._tools.get(tool_name)

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Return schema declarations for all registered tools."""
        return [tool.get_openai_schema() for tool in self._tools.values()]

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute registered tool by name with arguments and log execution metrics."""
        tool = self.get_tool(tool_name)
        if not tool:
            logger.error(f"Tool {tool_name} not found in registry")
            TOOL_EXECUTIONS.labels(tool_name=tool_name, status="not_found").inc()
            return {"status": "error", "message": f"Tool '{tool_name}' is not registered."}

        start_time = time.monotonic()
        try:
            # Validate parameters using tool's pydantic schema
            validated_args = tool.args_schema(**arguments)
            result = await tool.execute(**validated_args.model_dump())
            elapsed_ms = (time.monotonic() - start_time) * 1000.0

            logger.info(
                f"Successfully executed tool {tool_name}",
                tool_name=tool_name,
                execution_time_ms=elapsed_ms,
            )
            TOOL_EXECUTIONS.labels(tool_name=tool_name, status="success").inc()
            return {
                "status": "success",
                "result": result,
                "execution_time_ms": elapsed_ms,
            }

        except Exception as e:
            elapsed_ms = (time.monotonic() - start_time) * 1000.0
            logger.error(
                f"Error executing tool {tool_name}", error=str(e), execution_time_ms=elapsed_ms
            )
            TOOL_EXECUTIONS.labels(tool_name=tool_name, status="error").inc()
            return {
                "status": "error",
                "message": f"Failed to execute tool '{tool_name}': {str(e)}",
                "execution_time_ms": elapsed_ms,
            }
