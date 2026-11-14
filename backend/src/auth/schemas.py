from __future__ import annotations

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    identificacion: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str | None = None
    must_change_password: bool = False
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class AccessOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CambiarContrasenaIn(BaseModel):
    actual: str
    nueva: str = Field(min_length=8, max_length=128)


class OlvideContrasenaIn(BaseModel):
    identificacion: str
