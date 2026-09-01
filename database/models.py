from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_yaml: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class CallSession(Base):
    __tablename__ = "call_sessions"

    call_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)  # inbound / outbound
    phone_number: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="initiated"
    )  # initiated, connected, ended, failed
    current_stage: Mapped[str] = mapped_column(String(64), default="GREETING")
    start_time: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    metadata_json: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    transcripts: Mapped[list["TranscriptSegment"]] = relationship(
        "TranscriptSegment", back_populates="session", cascade="all, delete-orphan"
    )
    analytics: Mapped[Optional["CallAnalytics"]] = relationship(
        "CallAnalytics", back_populates="session", uselist=False, cascade="all, delete-orphan"
    )
    tool_logs: Mapped[list["ToolExecutionLog"]] = relationship(
        "ToolExecutionLog", back_populates="session", cascade="all, delete-orphan"
    )


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    call_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("call_sessions.call_id"), nullable=False
    )
    speaker: Mapped[str] = mapped_column(String(16), nullable=False)  # "user" or "assistant"
    text: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True)

    session: Mapped["CallSession"] = relationship("CallSession", back_populates="transcripts")


class CallAnalytics(Base):
    __tablename__ = "call_analytics"

    call_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("call_sessions.call_id"), primary_key=True
    )
    total_duration_sec: Mapped[float] = mapped_column(Float, default=0.0)
    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    p95_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    turn_count: Mapped[int] = mapped_column(Integer, default=0)
    interruption_count: Mapped[int] = mapped_column(Integer, default=0)
    user_talk_time_sec: Mapped[float] = mapped_column(Float, default=0.0)
    bot_talk_time_sec: Mapped[float] = mapped_column(Float, default=0.0)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(32), nullable=True)

    session: Mapped["CallSession"] = relationship("CallSession", back_populates="analytics")


class ToolExecutionLog(Base):
    __tablename__ = "tool_execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    call_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("call_sessions.call_id"), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(String(64), nullable=False)
    arguments_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    result_json: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    session: Mapped["CallSession"] = relationship("CallSession", back_populates="tool_logs")
