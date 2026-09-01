from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from config.settings import settings

router = APIRouter(tags=["Health & Metrics"])


@router.get("/health")
async def health_check():
    """Service health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "target_max_latency_ms": settings.TARGET_MAX_LATENCY_MS,
        "providers": {
            "llm": settings.LLM_PROVIDER,
            "stt": settings.STT_PROVIDER,
            "tts": settings.TTS_PROVIDER,
        },
    }


@router.get("/metrics")
async def get_prometheus_metrics():
    """Expose Prometheus telemetry metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
