import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from logging_config import configure_logging, get_logger
from database.db import init_db
from api.routes import health_router, calls_router, webhooks_router, prompts_router, websocket_router

configure_logging("INFO")
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("Initializing Voice AI Platform database & services...")
    await init_db()
    logger.info("Voice AI Platform initialized and ready for calls.")
    yield
    logger.info("Shutting down Voice AI Platform...")


app = FastAPI(
    title=settings.APP_NAME,
    description="Production Real-Time Low Latency AI Voice Gateway Engine (Gemini 2.5 Flash Live / Google Cloud STT & TTS)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Root endpoint serving Web Audio Tester
@app.get("/", response_class=HTMLResponse)
async def get_web_tester():
    file_path = os.path.join("static", "index.html")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Voice AI Platform Server Running</h1>"

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(health_router)
app.include_router(calls_router, prefix=settings.API_PREFIX)
app.include_router(webhooks_router, prefix=settings.API_PREFIX)
app.include_router(prompts_router, prefix=settings.API_PREFIX)
app.include_router(websocket_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
