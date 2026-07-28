import os
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Production configuration settings using Pydantic Settings v2."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # App Settings
    APP_NAME: str = "VoiceAI Platform"
    APP_ENV: str = "production"
    DEBUG: bool = False
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    API_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "production-super-secret-key-change-in-env"

    # Latency Target (ms)
    TARGET_MAX_LATENCY_MS: float = 800.0

    # Audio Engine Settings
    SAMPLE_RATE: int = 16000
    CHANNELS: int = 1
    BYTES_PER_SAMPLE: int = 2  # 16-bit PCM
    CHUNK_SIZE_MS: int = 20    # 20ms audio chunks = 640 bytes at 16kHz
    CODEC: str = "pcm16"       # pcm16, mulaw, webm

    # VAD Settings
    VAD_MODE: int = 3          # 0-3 (3 is most aggressive)
    VAD_FRAME_DURATION_MS: int = 20
    VAD_SPEECH_PAD_MS: int = 150
    VAD_SILENCE_TIMEOUT_MS: int = 400
    VAD_ENERGY_THRESHOLD: float = 0.015

    # Deepgram API Credentials
    DEEPGRAM_API_KEY: Optional[str] = None

    # LLM Settings (Google Vertex AI / Gemini)
    GEMINI_API_KEY: Optional[str] = None
    VERTEX_PROJECT_ID: Optional[str] = "ml-odio"
    VERTEX_LOCATION: str = "asia-south1"
    LLM_MODEL: str = "gemini-2.5-flash"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 512
    LLM_PROVIDER: str = "gemini_live"  # "gemini_live", "mock"
    GOOGLE_APPLICATION_CREDENTIALS: str = "vertex_creds.json"

    # STT Settings (Deepgram / Google / Mock)
    STT_PROVIDER: str = "deepgram"  # "deepgram", "google", "mock"
    STT_LANGUAGE_CODE: str = "en"
    STT_PUNCTUATION: bool = True
    STT_INTERIM_RESULTS: bool = True

    # TTS Settings (Deepgram / Google / Mock)
    TTS_PROVIDER: str = "deepgram"  # "deepgram", "google", "mock"
    TTS_VOICE_NAME: str = "aura-asteria-en"
    TTS_SPEAKING_RATE: float = 1.05
    TTS_PITCH: float = 0.0
    TTS_AUDIO_ENCODING: str = "LINEAR16"

    # Database Settings
    DATABASE_URL: str = "sqlite+aiosqlite:///./voice_ai.db"
    DB_ECHO: bool = False

    # Telephony (Twilio / SIP)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None

    # Monitoring & Observability
    ENABLE_PROMETHEUS: bool = True
    ENABLE_OTEL: bool = False
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"

    # Rate Limiting
    RATE_LIMIT_CALLS_PER_MIN: int = 60


settings = Settings()
