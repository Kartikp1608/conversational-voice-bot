from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from tool_executor.base_tool import BaseTool


class DatabaseLookupArgs(BaseModel):
    query_type: str = Field(..., description="Type of query e.g. 'account_balance' or 'transaction_history'")
    account_id: str = Field(..., description="Target account identifier")


class DatabaseTool(BaseTool):
    name = "database_lookup"
    description = "Query database for customer account details and recent transaction records."
    args_schema = DatabaseLookupArgs

    async def execute(self, query_type: str, account_id: str) -> Dict[str, Any]:
        return {
            "account_id": account_id,
            "query_type": query_type,
            "balance": "$4,250.00",
            "recent_transactions": [
                {"date": "2026-07-28", "merchant": "TechCorp", "amount": 249.99, "flagged": False},
                {"date": "2026-07-27", "merchant": "Grocery Store", "amount": 84.20, "flagged": False},
            ],
        }
