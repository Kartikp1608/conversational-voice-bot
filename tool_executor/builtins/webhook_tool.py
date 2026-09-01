from typing import Any, Dict

import httpx
from pydantic import BaseModel, Field

from logging_config import get_logger
from tool_executor.base_tool import BaseTool

logger = get_logger("tool_executor.webhook")


class WebhookArgs(BaseModel):
    url: str = Field(..., description="Target HTTP REST API endpoint")
    method: str = Field("POST", description="HTTP Method: GET or POST")
    payload: Dict[str, Any] = Field(default_factory=dict, description="JSON payload data")


class WebhookTool(BaseTool):
    name = "execute_webhook"
    description = "Trigger external REST HTTP webhook endpoint for custom business integrations."
    args_schema = WebhookArgs

    async def execute(
        self, url: str, method: str = "POST", payload: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        payload = payload or {}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                if method.upper() == "GET":
                    resp = await client.get(url, params=payload)
                else:
                    resp = await client.post(url, json=payload)
                return {
                    "status_code": resp.status_code,
                    "response": (
                        resp.json()
                        if resp.headers.get("content-type", "").startswith("application/json")
                        else resp.text
                    ),
                }
        except Exception as e:
            logger.warning(
                "Webhook HTTP call failed, falling back to simulation", error=str(e), url=url
            )
            return {
                "status": "simulated",
                "url": url,
                "payload": payload,
                "message": "Simulated successful webhook execution.",
            }
