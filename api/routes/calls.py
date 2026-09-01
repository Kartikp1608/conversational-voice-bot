import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.db import get_db_session
from database.repositories import CallRepository
from logging_config import get_logger
from telephony.twilio_adapter import TwilioAdapter

logger = get_logger("api.calls")

router = APIRouter(prefix="/calls", tags=["Calls"])


class OutboundCallRequest(BaseModel):
    to_phone_number: str = Field(..., description="Target phone number in E.164 format (+15550199)")
    from_phone_number: str | None = Field(None, description="Origin phone number")
    prompt_id: str = Field("sales_outbound", description="ID of business prompt configuration file")
    metadata: Dict[str, Any] | None = Field(
        default_factory=dict, description="Custom call metadata"
    )


class OutboundCallResponse(BaseModel):
    call_id: str
    status: str
    to_phone_number: str
    websocket_url: str


@router.post("/outbound", response_model=OutboundCallResponse, status_code=status.HTTP_201_CREATED)
async def trigger_outbound_call(
    req: OutboundCallRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Initiate an outbound AI Voice call."""
    call_id = f"call-{uuid.uuid4().hex[:12]}"
    websocket_url = f"wss://{settings.HOST}:{settings.PORT}/ws/twilio/{call_id}"

    repo = CallRepository(db)
    await repo.create_session(
        call_id=call_id,
        direction="outbound",
        phone_number=req.to_phone_number,
        prompt_id=req.prompt_id,
        metadata=req.metadata,
    )

    adapter = TwilioAdapter(
        account_sid=settings.TWILIO_ACCOUNT_SID,
        auth_token=settings.TWILIO_AUTH_TOKEN,
        default_from_number=settings.TWILIO_PHONE_NUMBER,
    )

    res = await adapter.make_outbound_call(
        to_phone_number=req.to_phone_number,
        from_phone_number=req.from_phone_number or settings.TWILIO_PHONE_NUMBER or "+18005550199",
        websocket_url=websocket_url,
    )

    return OutboundCallResponse(
        call_id=call_id,
        status=res.get("status", "initiated"),
        to_phone_number=req.to_phone_number,
        websocket_url=websocket_url,
    )


@router.get("/{call_id}")
async def get_call_details(call_id: str, db: AsyncSession = Depends(get_db_session)):
    """Fetch call session status and metadata."""
    repo = CallRepository(db)
    session = await repo.get_session(call_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Call session '{call_id}' not found.")
    return {
        "call_id": session.call_id,
        "direction": session.direction,
        "phone_number": session.phone_number,
        "prompt_id": session.prompt_id,
        "status": session.status,
        "current_stage": session.current_stage,
        "start_time": session.start_time,
        "end_time": session.end_time,
    }
