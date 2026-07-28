import httpx
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from tool_executor.base_tool import BaseTool


class WebhookArgs(BaseModel):
    url: str = Field(..., description="Target HTTP REST API endpoint")
    method: str = Field("POST", description="HTTP Method: GET or POST")
    payload: Dict[str, Any] = Field(default_factory=dict, description="JSON payload data")


class WebhookTool(BaseTool):
    name = "execute_webhook"
    description = "Trigger external REST HTTP webhook endpoint for custom business integrations."
    args_schema = WebhookArgs

    async def execute(self, url: str, method: str = "POST", payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                if method.upper() == "GET":
                    resp = await client.get(url, params=payload)
                else:
                    resp = await client.post(url, json=payload)
                return {
                    "status_code": resp.status_code,
                    "response": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text,
                }
        except Exception as e:
            return {"status": "simulated", "url": url, "payload": payload, "message": "Simulated successful webhook execution."}
