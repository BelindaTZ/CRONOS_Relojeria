from __future__ import annotations

from pydantic import BaseModel, Field


class SucursalIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    direccion: str | None = Field(default=None, max_length=255)
    responsable_usuario_id: int | None = None


class SucursalOut(BaseModel):
    id: int
    nombre: str
    direccion: str | None = None
    responsable_usuario_id: int | None = None
    estado: str
    motivo_inactivacion: str | None = None


class InactivarIn(BaseModel):
    motivo: str = Field(min_length=5, max_length=500)


class HorarioSucursalIn(BaseModel):
    dia_semana: int = Field(ge=0, le=6, description="0 = lunes … 6 = domingo")
    cerrado: bool = False
    hora_apertura: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    hora_cierre: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")


class HorarioSucursalOut(BaseModel):
    dia_semana: int
    cerrado: bool
    hora_apertura: str | None
    hora_cierre: str | None
