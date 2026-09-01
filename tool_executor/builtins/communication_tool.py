from typing import Any, Dict

from pydantic import BaseModel, Field

from tool_executor.base_tool import BaseTool


class SendNotificationArgs(BaseModel):
    channel: str = Field(..., description="Channel type: 'sms', 'email', 'whatsapp'")
    recipient: str = Field(..., description="Recipient phone number or email address")
    message: str = Field(..., description="Notification message body")


class CommunicationTool(BaseTool):
    name = "send_notification"
    description = "Send confirmation SMS, Email, or WhatsApp message to customer."
    args_schema = SendNotificationArgs

    async def execute(self, channel: str, recipient: str, message: str) -> Dict[str, Any]:
        return {
            "status": "SENT",
            "channel": channel,
            "recipient": recipient,
            "message_id": f"MSG-{channel.upper()}-9901",
        }
