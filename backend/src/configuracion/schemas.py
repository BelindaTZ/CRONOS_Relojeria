from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CatalogoItem(BaseModel):
    id: int
    clave: str | None = None
    nombre: str
    tipo: str | None = None
    dias_credito: int | None = None
    activo: bool = True
    pais: str | None = None
    sitio_web: str | None = None
    nota: str | None = None
    hex: str | None = None


class MarcaRelojIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    pais: str | None = Field(default=None, max_length=80)
    sitio_web: str | None = Field(default=None, max_length=200)
    nota: str | None = Field(default=None, max_length=500)


class MaterialIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)


class ColorIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    hex: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class CategoriaGastoIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    tipo: Literal["local_operativos", "personal", "otros", "mermas_perdidas"]


class CategoriaMermaIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    causa: Literal[
        "dano_tienda", "dano_transito", "robo_perdida", "defecto_fabrica", "dano_servicio", "insumo_caducado",
    ]


class MedioPagoIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)


class CondicionPagoIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    dias_credito: int = Field(default=0, ge=0, le=365)


class ActivoIn(BaseModel):
    activo: bool


class CanalCitaIn(BaseModel):
    clave: str = Field(min_length=2, max_length=40)
    nombre: str = Field(min_length=2, max_length=80)
    activo: bool = True


class ParametroHistorialItem(BaseModel):
    valor: Any
    vigente_desde: datetime
    creado_por: str | None = None


class ParametroOut(BaseModel):
    clave: str
    tipo: str
    valor_vigente: Any
    historial: list[ParametroHistorialItem]


class ParametroIn(BaseModel):
    valor: Any
    tipo: Literal["numero", "porcentaje", "monto", "json", "texto"] = "numero"
    ambito_tipo: Literal["global", "sucursal", "marca", "producto", "tipo_servicio"] = "global"
    ambito_ref: str | None = None
    vigente_desde: datetime | None = None


class RecalculoOut(BaseModel):
    consumidores: list[str]
    entidades_abiertas_afectadas: int
    documentos_emitidos_intactos: int


class SetParametroOut(BaseModel):
    clave: str
    valor_vigente: Any
    recalculo: RecalculoOut


class AuditoriaItem(BaseModel):
    id: int
    actor_usuario_id: int | None
    actor_nombre: str | None = None
    actor_identificacion: str | None = None
    accion: str
    entidad: str
    entidad_id: str | None
    antes: Any | None
    despues: Any | None
    ip_origen: str | None = None
    creado_en: datetime
