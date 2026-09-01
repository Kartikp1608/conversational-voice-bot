import os

from pydantic import model_validator
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
    CHUNK_SIZE_MS: int = 20  # 20ms audio chunks = 640 bytes at 16kHz
    CODEC: str = "pcm16"  # pcm16, mulaw, webm

    # VAD Settings
    VAD_MODE: int = 3  # 0-3 (3 is most aggressive)
    VAD_FRAME_DURATION_MS: int = 20
    VAD_SPEECH_PAD_MS: int = 150
    VAD_SILENCE_TIMEOUT_MS: int = 400
    VAD_ENERGY_THRESHOLD: float = 0.015

    # Deepgram API Credentials
    DEEPGRAM_API_KEY: str | None = None

    # LLM Settings (Google Vertex AI / Gemini)
    GEMINI_API_KEY: str | None = None
    VERTEX_PROJECT_ID: str | None = "ml-odio"
    VERTEX_LOCATION: str = "asia-south1"
    LLM_MODEL: str = "gemini-2.5-flash"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 512
    LLM_PROVIDER: str = "mock"  # "gemini_live", "mock"
    GOOGLE_APPLICATION_CREDENTIALS: str = "vertex_creds.json"

    # STT Settings (Deepgram / Google / Mock)
    STT_PROVIDER: str = "mock"  # "deepgram", "google", "mock"
    STT_LANGUAGE_CODE: str = "en"
    STT_PUNCTUATION: bool = True
    STT_INTERIM_RESULTS: bool = True

    # TTS Settings (Deepgram / Google / Mock)
    TTS_PROVIDER: str = "mock"  # "deepgram", "google", "mock"
    TTS_VOICE_NAME: str = "aura-asteria-en"
    TTS_SPEAKING_RATE: float = 1.05
    TTS_PITCH: float = 0.0
    TTS_AUDIO_ENCODING: str = "LINEAR16"

    # Database Settings
    DATABASE_URL: str = "sqlite+aiosqlite:///./voice_ai.db"
    DB_ECHO: bool = False

    # Telephony (Twilio / SIP)
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    TWILIO_PHONE_NUMBER: str | None = None

    # Monitoring & Observability
    ENABLE_PROMETHEUS: bool = True
    ENABLE_OTEL: bool = False
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"

    # Rate Limiting
    RATE_LIMIT_CALLS_PER_MIN: int = 60

    @model_validator(mode="after")
    def validate_provider_credentials(self) -> "Settings":
        """Validate that non-mock providers have required API credentials configured."""
        llm = (self.LLM_PROVIDER or "").lower()
        if llm in ["gemini", "gemini_live"]:
            has_gemini_key = bool(
                self.GEMINI_API_KEY and not self.GEMINI_API_KEY.startswith("your_")
            )
            has_google_creds = bool(
                self.GOOGLE_APPLICATION_CREDENTIALS
                and os.path.exists(self.GOOGLE_APPLICATION_CREDENTIALS)
            )
            if not has_gemini_key and not has_google_creds:
                raise ValueError(
                    f"LLM_PROVIDER is set to '{self.LLM_PROVIDER}', but neither GEMINI_API_KEY nor "
                    f"valid GOOGLE_APPLICATION_CREDENTIALS ({self.GOOGLE_APPLICATION_CREDENTIALS}) was found."
                )

        stt = (self.STT_PROVIDER or "").lower()
        if stt == "deepgram":
            if not self.DEEPGRAM_API_KEY or self.DEEPGRAM_API_KEY.startswith("your_"):
                raise ValueError(
                    "DEEPGRAM_API_KEY is required when STT_PROVIDER is set to 'deepgram'"
                )
        elif stt == "google":
            has_creds = bool(
                self.GOOGLE_APPLICATION_CREDENTIALS
                and os.path.exists(self.GOOGLE_APPLICATION_CREDENTIALS)
            )
            if not has_creds and not self.VERTEX_PROJECT_ID:
                raise ValueError(
                    "GOOGLE_APPLICATION_CREDENTIALS or VERTEX_PROJECT_ID is required when STT_PROVIDER is 'google'"
                )

        tts = (self.TTS_PROVIDER or "").lower()
        if tts == "deepgram":
            if not self.DEEPGRAM_API_KEY or self.DEEPGRAM_API_KEY.startswith("your_"):
                raise ValueError(
                    "DEEPGRAM_API_KEY is required when TTS_PROVIDER is set to 'deepgram'"
                )
        elif tts == "google":
            has_creds = bool(
                self.GOOGLE_APPLICATION_CREDENTIALS
                and os.path.exists(self.GOOGLE_APPLICATION_CREDENTIALS)
            )
            if not has_creds and not self.VERTEX_PROJECT_ID:
                raise ValueError(
                    "GOOGLE_APPLICATION_CREDENTIALS or VERTEX_PROJECT_ID is required when TTS_PROVIDER is 'google'"
                )

        return self


settings = Settings()
