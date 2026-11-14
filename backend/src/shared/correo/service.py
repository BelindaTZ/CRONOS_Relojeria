"""Render de plantillas Jinja2 con la identidad visual del Principio XI + envío."""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from shared.config import get_settings
from shared.correo.backends import enviar_raw

logger = logging.getLogger("cronos.correo")

_TEMPLATES = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES)),
    autoescape=select_autoescape(["html", "xml"]),
)

# Asunto por plantilla (fijo — el override editable de 014 en `plantilla_email`
# lo reemplaza en tiempo de render si existe una fila `activa` para ese tipo).
_ASUNTOS = {
    "password_temporal": "CRONOS · Contraseña temporal de acceso",
    "inactivacion_sucursal": "CRONOS · Aviso de inactivación de sucursal",
    "cancelacion_orden": "CRONOS · Cancelación de orden de compra",
    "usuario_bienvenida": "CRONOS · Acceso al sistema",
    "tecnico_asignado": "CRONOS · Su reloj está en manos de nuestro técnico",
    "factura_venta": "CRONOS · Su factura de compra",
    "tecnico_nueva_ot": "CRONOS · Nueva orden de trabajo asignada",
    "diagnostico_cliente": "CRONOS · Diagnóstico de su reloj",
    "servicio_listo_retiro": "CRONOS · Su reloj está listo para retiro",
    "compra_urgente_solicitada": "CRONOS · Compra urgente solicitada por taller",
    # feature 014 — disparadores automáticos nuevos
    "ot_entregado": "CRONOS · Gracias por su visita",
    "ot_cancelada": "CRONOS · Orden de servicio cancelada",
    "cupon": "CRONOS · Tiene un cupón esperando",
    "nivel": "CRONOS · Subió de nivel de fidelización",
    "recordatorio_cita": "CRONOS · Recordatorio de su cita",
}


def _contexto_base() -> dict:
    return {"app_base_url": get_settings().app_base_url}


def _override_activo(plantilla: str) -> tuple[str, str] | None:
    """Fila `plantilla_email` activa para `plantilla`, si Gerencia la editó
    (feature 014). Sesión de BD propia y desechable — ningún llamante de
    `render()`/`enviar()` tiene por qué pasar una (Ppio VII: cero cambios en
    ~15 sitios de llamada ya existentes). Un fallo aquí NUNCA rompe el envío:
    se sigue usando el archivo Jinja2 de siempre."""
    try:
        from sqlalchemy import select

        from shared.database import SessionLocal
        from shared.models import PlantillaEmail

        with SessionLocal() as db:
            fila = db.scalars(
                select(PlantillaEmail).where(PlantillaEmail.tipo == plantilla, PlantillaEmail.activa.is_(True))
            ).first()
            if fila:
                return fila.asunto, fila.cuerpo
    except Exception as exc:  # noqa: BLE001 — nunca bloquea el render
        logger.warning("No se pudo consultar el override de plantilla '%s': %s", plantilla, exc)
    return None


def render(plantilla: str, contexto: dict) -> tuple[str, str]:
    """Devuelve (html, texto_plano) de la plantilla — con el override de BD de
    014 si Gerencia lo guardó, si no el archivo Jinja2 de siempre."""
    ctx = {**_contexto_base(), **contexto}
    override = _override_activo(plantilla)
    if override:
        _, cuerpo = override
        html = _env.from_string(cuerpo).render(**ctx)
    else:
        html = _env.get_template(f"{plantilla}.html").render(**ctx)
    try:
        texto = _env.get_template(f"{plantilla}.txt").render(**ctx)
    except Exception:
        texto = "(Ver este correo en un cliente compatible con HTML.)"
    return html, texto


def asunto_de(plantilla: str, contexto: dict) -> str:
    override = _override_activo(plantilla)
    if override:
        asunto_tpl, _ = override
        return _env.from_string(asunto_tpl).render(**{**_contexto_base(), **contexto})
    return _ASUNTOS.get(plantilla, "CRONOS")


def enviar(plantilla: str, a: str, contexto: dict, *, asunto: str | None = None, envio_id: int | None = None) -> str | None:
    """Renderiza `plantilla` y la envía a `a` por el backend configurado.
    Devuelve el `message_id` del proveedor si lo hay (014 lo usa para conciliar
    webhooks de entrega) — `None` para quien no lo necesite (~15 llamadas
    existentes que ignoran el valor de retorno, sin cambios)."""
    html, texto = render(plantilla, contexto)
    asunto_final = asunto or asunto_de(plantilla, contexto)
    return enviar_raw(asunto_final, a, html, texto, envio_id=envio_id)
