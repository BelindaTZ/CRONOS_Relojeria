"""Módulo `servicio_tecnico` (feature 008): órdenes de trabajo con trazabilidad
por número de serie, presupuesto con elección de piezas, costeo y margen del
servicio, ciclo de estados, cobro al retiro (pagos multimedios de `shared/pagos`),
documento de OT + certificado de garantía (`shared/pdf`) e informe de servicios.

Introduce las capacidades compartidas `shared/pagos` y `shared/pdf` (las reutiliza 009).

Registro en el arranque (`main.py`):
- `registrar_consumidores()` — recálculo de costeo por `margen_objetivo_servicio`.
- `registrar_proveedores()` — alimenta a 005 (bono/productividad) y 006 (nivel/reportes).

No expone API de dominio a otros módulos: 011 (mermas) consumirá el payload de
`reportar-dano` y 014 (notificaciones) leerá el historial de estados por HTTP.
"""

from servicio_tecnico.service import (
    registrar_consumidores,
    registrar_proveedores,
    resumen_periodo,
    tiene_ot_activa_para_reloj,
)

__all__ = [
    "registrar_consumidores", "registrar_proveedores", "tiene_ot_activa_para_reloj", "resumen_periodo",
]
