from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tool_executor.builtins.calendar_tool import CalendarTool
from tool_executor.builtins.communication_tool import CommunicationTool
from tool_executor.builtins.crm_tool import CRMTool
from tool_executor.builtins.database_tool import DatabaseTool
from tool_executor.builtins.webhook_tool import WebhookTool
from tool_executor.registry import ToolRegistry


@pytest.mark.asyncio
async def test_crm_tool_execution():
    tool = CRMTool()
    res = await tool.execute(customer_id="CUST-100", phone_number="+15550199")
    assert res["customer_id"] == "CUST-100"
    assert res["phone_number"] == "+15550199"
    assert res["tier"] == "VIP Gold"


@pytest.mark.asyncio
async def test_calendar_tool_execution():
    tool = CalendarTool()
    res = await tool.execute(
        date="2026-08-01", time="14:00", service="Cardiology", patient_name="John Doe"
    )
    assert res["status"] == "CONFIRMED"
    assert res["date"] == "2026-08-01"
    assert res["patient_name"] == "John Doe"


@pytest.mark.asyncio
async def test_database_tool_execution():
    tool = DatabaseTool()
    res = await tool.execute(query_type="account_balance", account_id="ACC-777")
    assert res["account_id"] == "ACC-777"
    assert res["balance"] == "$4,250.00"
    assert len(res["recent_transactions"]) > 0


@pytest.mark.asyncio
async def test_communication_tool_execution():
    tool = CommunicationTool()
    res = await tool.execute(
        channel="sms", recipient="+15550199", message="Your appointment is confirmed."
    )
    assert res["status"] == "SENT"
    assert res["channel"] == "sms"
    assert "MSG-SMS" in res["message_id"]


@pytest.mark.asyncio
async def test_webhook_tool_get_and_post():
    tool = WebhookTool()

    # Mock successful GET
    mock_resp_get = MagicMock()
    mock_resp_get.status_code = 200
    mock_resp_get.headers = {"content-type": "application/json"}
    mock_resp_get.json.return_value = {"success": True}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp_get):
        res = await tool.execute(url="https://api.example.com/status", method="GET")
        assert res["status_code"] == 200
        assert res["response"]["success"] is True

    # Mock successful POST
    mock_resp_post = MagicMock()
    mock_resp_post.status_code = 201
    mock_resp_post.headers = {"content-type": "application/json"}
    mock_resp_post.json.return_value = {"created": True}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp_post):
        res = await tool.execute(
            url="https://api.example.com/leads", method="POST", payload={"lead": "123"}
        )
        assert res["status_code"] == 201

    # Mock error fallback to simulation
    with patch("httpx.AsyncClient.post", side_effect=Exception("Network error")):
        sim_res = await tool.execute(url="https://invalid.url", method="POST")
        assert sim_res["status"] == "simulated"


@pytest.mark.asyncio
async def test_tool_registry_lifecycle():
    registry = ToolRegistry()
    registry.register(CRMTool())
    registry.register(CalendarTool())

    schemas = registry.get_schemas()
    assert len(schemas) == 2
    assert any(s["name"] == "crm_lookup" for s in schemas)

    # Valid execution
    res = await registry.execute_tool("crm_lookup", {"customer_id": "CUST-99"})
    assert res["status"] == "success"
    assert res["result"]["customer_id"] == "CUST-99"

    # Execution with missing required arguments
    reg2 = ToolRegistry()
    reg2.register(CommunicationTool())
    missing_args_res = await reg2.execute_tool("send_notification", {})
    assert missing_args_res["status"] == "error"

    # Unregistered tool
    unknown_res = await registry.execute_tool("nonexistent_tool", {})
    assert unknown_res["status"] == "error"
