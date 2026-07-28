from api.routes.health import router as health_router
from api.routes.calls import router as calls_router
from api.routes.webhooks import router as webhooks_router
from api.routes.prompts import router as prompts_router
from api.routes.websocket import router as websocket_router

__all__ = ["health_router", "calls_router", "webhooks_router", "prompts_router", "websocket_router"]
