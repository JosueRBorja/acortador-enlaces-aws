from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator


class ShortenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    original_url: HttpUrl

    @field_validator("original_url")
    @classmethod
    def reject_credentials(cls, value: HttpUrl) -> HttpUrl:
        if value.username is not None or value.password is not None:
            raise ValueError("No se permiten credenciales dentro de la URL.")
        return value


class LinkInfo(BaseModel):
    short_code: UUID
    original_url: HttpUrl
    created_at: datetime


class ShortenResponse(LinkInfo):
    short_url: HttpUrl
