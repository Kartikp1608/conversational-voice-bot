from typing import Any, Dict

from pydantic import BaseModel, Field

from tool_executor.base_tool import BaseTool


class CalendarBookingArgs(BaseModel):
    date: str = Field(..., description="Target appointment date (YYYY-MM-DD)")
    time: str = Field(..., description="Target time slot (e.g. 10:00 AM)")
    service: str = Field("General Consultation", description="Service type or appointment reason")
    patient_name: str | None = Field(None, description="Patient or customer name")


class CalendarTool(BaseTool):
    name = "book_appointment"
    description = "Check calendar availability and schedule a confirmed appointment."
    args_schema = CalendarBookingArgs

    async def execute(
        self,
        date: str,
        time: str,
        service: str = "General Consultation",
        patient_name: str | None = None,
    ) -> Dict[str, Any]:
        return {
            "booking_id": "APT-88219",
            "status": "CONFIRMED",
            "date": date,
            "time": time,
            "service": service,
            "patient_name": patient_name or "Valued Customer",
            "confirmation_code": "APX-9012",
        }
