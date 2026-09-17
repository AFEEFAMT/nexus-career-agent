from pathlib import Path

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


BASE_DIR = Path(
    __file__
).resolve().parents[2]


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int = 5432
    DB_NAME: str = "postgres"
    DB_USER: str
    DB_PASSWORD: str

    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-3.8-flash"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    TAVUS_API_KEY: str | None = None
    TAVUS_REPLICA_ID: str | None = None

    HEYGEN_API_KEY: str | None = None
    HEYGEN_AVATAR_ID: str | None = None
    HEYGEN_VOICE_ID: str | None = None

    EDGE_TTS_VOICE: str = (
        "en-US-AriaNeural"
    )

    FRONTEND_ORIGIN: str = (
        "http://localhost:5173"
    )

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()