from typing import Any, Dict

from pydantic import BaseModel, Field

from tool_executor.base_tool import BaseTool


class CRMLookupArgs(BaseModel):
    customer_id: str | None = Field(None, description="Unique customer ID")
    phone_number: str | None = Field(None, description="Customer phone number")


class CRMTool(BaseTool):
    name = "crm_lookup"
    description = "Lookup customer profile, balance, and subscription metadata in CRM."
    args_schema = CRMLookupArgs

    async def execute(
        self, customer_id: str | None = None, phone_number: str | None = None
    ) -> Dict[str, Any]:
        # Simulated production CRM response
        return {
            "customer_id": customer_id or "CUST-9842",
            "full_name": "Jane Doe",
            "phone_number": phone_number or "+15550199",
            "tier": "VIP Gold",
            "active_plan": "Enterprise Fiber 1Gbps",
            "account_status": "Active",
            "balance_due": 0.00,
        }
