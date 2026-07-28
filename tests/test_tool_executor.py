import pytest
from tool_executor.registry import ToolRegistry
from tool_executor.builtins.crm_tool import CRMTool
from tool_executor.builtins.calendar_tool import CalendarTool


@pytest.mark.asyncio
async def test_tool_registry_execution():
    registry = ToolRegistry()
    registry.register(CRMTool())
    registry.register(CalendarTool())

    schemas = registry.get_schemas()
    assert len(schemas) == 2

    # Execute CRM lookup
    res = await registry.execute_tool("crm_lookup", {"customer_id": "CUST-100"})
    assert res["status"] == "success"
    assert res["result"]["customer_id"] == "CUST-100"

    # Execute Calendar booking
    cal_res = await registry.execute_tool(
        "book_appointment",
        {"date": "2026-07-30", "time": "14:00 PM", "service": "General Checkup"},
    )
    assert cal_res["status"] == "success"
    assert cal_res["result"]["status"] == "CONFIRMED"
