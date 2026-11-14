from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProductoMoebiusIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=20)
    uso_recomendado: str | None = Field(default=None, max_length=255)
    pieza_id: int | None = None


class ProductoMoebiusOut(BaseModel):
    id: int
    codigo: str
    uso_recomendado: str | None = None
    pieza_id: int | None = None
    activo: bool


class PuntoIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    producto_moebius_codigo: str | None = None
    notas: str | None = Field(default=None, max_length=4000)


class FichaIn(BaseModel):
    notas_generales: str | None = Field(default=None, max_length=8000)
    puntos: list[PuntoIn] = Field(default_factory=list)


class PuntoOut(BaseModel):
    id: int
    nombre: str
    producto_moebius_id: int | None = None
    producto_recomendado: str | None = None
    notas: str | None = None
    orden: int


class FichaOut(BaseModel):
    calibre_id: int
    calibre_codigo: str | None = None
    notas_generales: str | None = None
    puntos: list[PuntoOut] = Field(default_factory=list)
    actualizado_en: datetime | None = None


class DesviacionOut(BaseModel):
    orden_trabajo_id: int
    punto_nombre: str
    producto_recomendado: str | None = None
    producto_usado: str
    tecnico_id: int | None = None
    fecha: datetime
