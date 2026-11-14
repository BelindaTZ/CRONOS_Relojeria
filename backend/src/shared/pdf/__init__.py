"""Capacidad compartida de generación de PDF (feature 008, reutilizada por 009).

API pública:
- `documento_orden_trabajo(ctx) -> bytes`
- `certificado_garantia(ctx) -> bytes`
- `guardar_comprobante(objeto, contenido) -> str` — sube a `comprobantes-venta`.

Los documentos son de cara al cliente: **nunca** llevan costo interno ni margen.
"""

from shared.pdf.documentos import (
    certificado_garantia,
    certificado_garantia_autenticidad,
    comprobante_venta,
    documento_orden_trabajo,
    factura_venta,
    guardar_comprobante,
)

__all__ = [
    "certificado_garantia",
    "certificado_garantia_autenticidad",
    "comprobante_venta",
    "documento_orden_trabajo",
    "factura_venta",
    "guardar_comprobante",
]
