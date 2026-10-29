from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    aws_region: str = "us-east-1"
    dynamodb_table: str = "url-shortener-links"
    public_base_url: str = "http://127.0.0.1:8000"
    cors_origins: list[str] = ["http://localhost:5500", "http://127.0.0.1:5500"]
    log_level: str = "INFO"

    @field_validator("public_base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError("PUBLIC_BASE_URL debe ser un origen HTTP(S), sin ruta.")
        return value.rstrip("/")

    @field_validator("cors_origins")
    @classmethod
    def validate_origins(cls, values: list[str]) -> list[str]:
        for value in values:
            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
            ):
                raise ValueError("CORS_ORIGINS requiere orígenes exactos, sin ruta ni comodines.")
        return values


@lru_cache
def get_settings() -> Settings:
    return Settings()
