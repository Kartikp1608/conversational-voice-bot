from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    CallAnalytics,
    CallSession,
    PromptTemplate,
    ToolExecutionLog,
    TranscriptSegment,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CallRepository:
    """Async repository for CallSession operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(
        self,
        call_id: str,
        direction: str,
        phone_number: str,
        prompt_id: str,
        metadata: Dict[str, Any] | None = None,
    ) -> CallSession:
        call_session = CallSession(
            call_id=call_id,
            direction=direction,
            phone_number=phone_number,
            prompt_id=prompt_id,
            metadata_json=metadata or {},
            status="connected",
            start_time=utc_now(),
        )
        self.session.add(call_session)
        await self.session.commit()
        await self.session.refresh(call_session)
        return call_session

    async def update_status(
        self, call_id: str, status: str, current_stage: str | None = None
    ) -> CallSession | None:
        stmt = select(CallSession).where(CallSession.call_id == call_id)
        res = await self.session.execute(stmt)
        call_session = res.scalar_one_or_none()
        if call_session:
            call_session.status = status
            if current_stage:
                call_session.current_stage = current_stage
            if status in ["ended", "failed"]:
                call_session.end_time = utc_now()
            await self.session.commit()
            await self.session.refresh(call_session)
        return call_session

    async def get_session(self, call_id: str) -> CallSession | None:
        stmt = select(CallSession).where(CallSession.call_id == call_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def add_transcript(
        self,
        call_id: str,
        speaker: str,
        text: str,
        latency_ms: float | None = None,
        stage: str | None = None,
    ) -> TranscriptSegment:
        segment = TranscriptSegment(
            call_id=call_id,
            speaker=speaker,
            text=text,
            latency_ms=latency_ms,
            stage=stage,
            timestamp=utc_now(),
        )
        self.session.add(segment)
        await self.session.commit()
        return segment

    async def log_tool_execution(
        self,
        call_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Dict[str, Any] | None = None,
        error: str | None = None,
        execution_time_ms: float = 0.0,
    ) -> ToolExecutionLog:
        log = ToolExecutionLog(
            call_id=call_id,
            tool_name=tool_name,
            arguments_json=arguments,
            result_json=result,
            error=error,
            execution_time_ms=execution_time_ms,
            timestamp=utc_now(),
        )
        self.session.add(log)
        await self.session.commit()
        return log

    async def save_analytics(
        self,
        call_id: str,
        total_duration_sec: float,
        avg_latency_ms: float,
        turn_count: int,
        interruption_count: int,
        summary: str | None = None,
    ) -> CallAnalytics:
        analytics = CallAnalytics(
            call_id=call_id,
            total_duration_sec=total_duration_sec,
            avg_latency_ms=avg_latency_ms,
            turn_count=turn_count,
            interruption_count=interruption_count,
            summary=summary,
        )
        self.session.add(analytics)
        await self.session.commit()
        return analytics


class PromptRepository:
    """Async repository for PromptTemplate operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_prompt(
        self, prompt_id: str, name: str, content_yaml: str, description: str | None = None
    ) -> PromptTemplate:
        stmt = select(PromptTemplate).where(PromptTemplate.id == prompt_id)
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            existing.name = name
            existing.content_yaml = content_yaml
            existing.description = description
            existing.version += 1
            existing.updated_at = utc_now()
            await self.session.commit()
            return existing
        else:
            tmpl = PromptTemplate(
                id=prompt_id,
                name=name,
                content_yaml=content_yaml,
                description=description,
            )
            self.session.add(tmpl)
            await self.session.commit()
            return tmpl

    async def get_prompt(self, prompt_id: str) -> PromptTemplate | None:
        stmt = select(PromptTemplate).where(PromptTemplate.id == prompt_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
