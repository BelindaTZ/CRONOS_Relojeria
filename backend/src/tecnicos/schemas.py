from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

Estado = Literal["activo", "inactivo"]
Periodicidad = Literal["mensual", "trimestral"]
TipoComponente = Literal["monto_por_meta", "porcentaje_margen", "combinacion"]
Indicador = Literal["ot_completadas", "cumplimiento_tiempos", "margen_generado", "calidad"]


# ------------------------------------------------------------------ especialidad
class EspecialidadOut(BaseModel):
    id: int
    nombre: str
    activo: bool = True


# ------------------------------------------------------------------------ técnico
class TecnicoIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=160)
    certificaciones: str | None = Field(default=None, max_length=4000)
    usuario_id: int | None = None
    especialidades: list[int] = Field(default_factory=list)   # ids de `especialidad`
    especialidades_nuevas: list[str] = Field(default_factory=list)  # nombres a crear
    sucursales: list[int] = Field(default_factory=list)


class TecnicoPatch(BaseModel):
    nombre: str | None = Field(default=None, max_length=160)
    certificaciones: str | None = Field(default=None, max_length=4000)
    usuario_id: int | None = None
    especialidades: list[int] | None = None
    especialidades_nuevas: list[str] | None = None
    sucursales: list[int] | None = None


class EstadoIn(BaseModel):
    estado: Estado


class CostoIn(BaseModel):
    sueldo_mensual: Decimal = Field(ge=0)
    vigente_desde: date


class CostoOut(BaseModel):
    sueldo_mensual: Decimal
    vigente_desde: date
    tarifa_hora: Decimal
    horas_estandar_mes: Decimal


class TecnicoOut(BaseModel):
    id: int
    nombre: str
    certificaciones: str | None = None
    estado: str
    usuario_id: int | None = None
    especialidades: list[str] = Field(default_factory=list)
    especialidad_ids: list[int] = Field(default_factory=list)
    sucursal_ids: list[int] = Field(default_factory=list)
    costos_visibles: bool = False           # el rol puede ver el costo interno de MO
    costo_vigente: CostoOut | None = None    # solo si costos_visibles
    creado_en: datetime


# --------------------------------------------------------------------- regla bono
class ComponenteBonoIn(BaseModel):
    tipo: TipoComponente
    indicador: Indicador
    umbral: Decimal = Field(default=Decimal("0"))
    valor: Decimal


class ReglaBonoIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    periodicidad: Periodicidad = "mensual"
    vigente_desde: date | None = None
    componentes: list[ComponenteBonoIn] = Field(min_length=1)


class ComponenteBonoOut(ComponenteBonoIn):
    id: int


class ReglaBonoOut(BaseModel):
    id: int
    nombre: str
    periodicidad: str
    vigente_desde: date
    activa: bool
    componentes: list[ComponenteBonoOut] = Field(default_factory=list)
    creado_en: datetime


# ---------------------------------------------------------------- periodo / bono
class PeriodoIn(BaseModel):
    fecha_inicio: date
    fecha_fin: date


class PeriodoOut(BaseModel):
    id: int
    fecha_inicio: date
    fecha_fin: date
    estado: str
    cerrado_en: datetime | None = None
    creado_en: datetime


class CalcularBonoIn(BaseModel):
    periodo_id: int
    tecnico_id: int | None = None


class BonoOtOut(BaseModel):
    orden_trabajo_id: int
    monto: Decimal


class BonoOut(BaseModel):
    tecnico_id: int
    tecnico_nombre: str | None = None
    periodo_id: int
    regla_bono_id: int | None = None
    valor_total: Decimal
    desglose: dict | None = None
    estado: str
    bono_ot: list[BonoOtOut] = Field(default_factory=list)
    calculado_en: datetime | None = None


# ------------------------------------------------------------------ productividad
class ProductividadOut(BaseModel):
    tecnico_id: int
    tecnico_nombre: str
    ot_completadas: int
    tiempo_promedio_horas: float
    margen_generado: Decimal
    bono_alcanzado: Decimal


# ---------------------------------------------------- contrato interno para 008
class CostoMoOtIn(BaseModel):
    tecnico_id: int
    horas: float | None = None
    tipo_reparacion: str | None = None


class CostoMoOtOut(BaseModel):
    costo_mo: Decimal
    tarifa_hora: Decimal
    horas: float
    base: str  # "horas_registradas" | "tiempo_estimado"
