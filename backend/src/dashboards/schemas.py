"""Schemas del módulo `dashboards` (feature 013). Sin entidades OLTP — todo es
forma de respuesta sobre lecturas del warehouse (012)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

TipoGrafico = Literal["barras", "pastel", "lineas", "kpi", "tabla"]


class FrescuraDominioOut(BaseModel):
    dominio: str
    ultima_carga_ts: str | None = None


class DrillDownOut(BaseModel):
    tipo: Literal["navegar", "abrir_flujo"]
    ruta: str
    filtros: dict[str, Any] = {}


class TendenciaOut(BaseModel):
    valor: float | None = None
    direccion: Literal["sube", "baja", "estable"] = "estable"


class KpiOut(BaseModel):
    clave: str
    titulo: str
    valor: float | None = None
    unidad: str = ""
    tendencia: TendenciaOut | None = None
    drill_down: DrillDownOut | None = None


class PanelOut(BaseModel):
    disponible: bool
    motivo: str | None = None
    frescura: FrescuraDominioOut | None = None
    kpis: list[KpiOut] = []


class SerieOut(BaseModel):
    nombre: str
    datos: list[float | None]


class ReporteOut(BaseModel):
    disponible: bool
    motivo: str | None = None
    slug: str | None = None
    titulo: str | None = None
    tipo_grafico: TipoGrafico | None = None
    filtros_soportados: list[str] = []
    filtros_aplicados: dict[str, Any] = {}
    categorias: list[str] = []
    series: list[SerieOut] = []
    filas: list[dict[str, Any]] = []
    total_filas: int = 0
    frescura: FrescuraDominioOut | None = None


class ReporteSimpleOut(BaseModel):
    titulo: str
    modulo: str
    ruta: str
    icono: str = "file-text"


class IndiceReportesOut(BaseModel):
    simples: list[ReporteSimpleOut] = []
    complejos: list[dict[str, Any]] = []
