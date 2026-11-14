"""Generación de PDF con la identidad visual de CRONOS (feature 008).

Capacidad compartida introducida por 008 (documento de orden de trabajo y
certificado de garantía del servicio) y reutilizada por 009 (comprobante de venta).
Motor: **reportlab** (Python puro, sin dependencias del sistema).

Regla transversal (Const. Ppio V / spec §FR-009): estos documentos son de cara al
cliente — **nunca** incluyen el costo interno, el costo de mano de obra ni el
margen. El `ctx` que reciben ya viene saneado por el módulo que llama.
"""

from __future__ import annotations

import io
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from shared.storage import ensure_bucket, put_object

# Paleta de marca (Constitución v1.7.0): marfil de fondo, dorado como filete.
_GOLD = colors.HexColor("#B08A3E")
_INK = colors.HexColor("#2A2723")
_HAIRLINE = colors.HexColor("#CBB98F")
_HEAD_BG = colors.HexColor("#E8DFC9")

_BUCKET = "comprobantes-venta"


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo", parent=base["Title"], fontName="Times-Roman", fontSize=20,
            textColor=_INK, spaceAfter=2,
        ),
        "eyebrow": ParagraphStyle(
            "eyebrow", parent=base["Normal"], fontName="Helvetica", fontSize=8,
            textColor=_GOLD, spaceAfter=8, leading=10,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName="Times-Roman", fontSize=12,
            textColor=_INK, spaceBefore=10, spaceAfter=4,
        ),
        "cuerpo": ParagraphStyle(
            "cuerpo", parent=base["Normal"], fontName="Helvetica", fontSize=9.5,
            textColor=_INK, leading=13,
        ),
        "pie": ParagraphStyle(
            "pie", parent=base["Normal"], fontName="Helvetica", fontSize=7.5,
            textColor=colors.HexColor("#8A8272"), leading=10,
        ),
    }


def _fmt(v: Any) -> str:
    if isinstance(v, Decimal | float | int) and not isinstance(v, bool):
        return f"{Decimal(str(v)):,.2f}"
    if isinstance(v, datetime):
        return v.strftime("%d/%m/%Y %H:%M")
    if isinstance(v, date):
        return v.strftime("%d/%m/%Y")
    return "—" if v is None else str(v)


def _kv_table(filas: list[tuple[str, Any]]) -> Table:
    data = [[Paragraph(f"<b>{k}</b>", _styles()["cuerpo"]), Paragraph(_fmt(v), _styles()["cuerpo"])]
            for k, v in filas]
    t = Table(data, colWidths=[45 * mm, 120 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, _HAIRLINE),
    ]))
    return t


def _encabezado(story: list, st: dict, titulo: str, numero: str) -> None:
    story.append(Paragraph("CRONOS · RELOJERÍA DE ALTA GAMA", st["eyebrow"]))
    story.append(Paragraph(titulo, st["titulo"]))
    story.append(Paragraph(f"N.º {numero}", st["cuerpo"]))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.2, color=_GOLD, spaceAfter=10))


def _render(bloques) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
        leftMargin=20 * mm, rightMargin=20 * mm, title="CRONOS",
    )
    doc.build(bloques)
    return buf.getvalue()


def documento_orden_trabajo(ctx: dict) -> bytes:
    """OT de cara al cliente: unidad, diagnóstico, trabajo realizado, repuestos,
    precio del servicio y condiciones de garantía. Sin costos internos."""
    st = _styles()
    story: list = []
    _encabezado(story, st, "Orden de Trabajo", ctx.get("numero", "—"))

    story.append(_kv_table([
        ("Cliente", ctx.get("cliente_nombre")),
        ("N.º de afiliado", ctx.get("cliente_afiliado")),
        ("Sucursal", ctx.get("sucursal_nombre")),
        ("Fecha de ingreso", ctx.get("fecha_ingreso")),
        ("Fecha de entrega", ctx.get("fecha_real_entrega")),
    ]))

    story.append(Paragraph("Unidad", st["h2"]))
    story.append(_kv_table([
        ("Marca", ctx.get("reloj_marca")),
        ("Referencia", ctx.get("reloj_referencia")),
        ("N.º de serie", ctx.get("reloj_serie")),
        ("Técnico responsable", ctx.get("tecnico_nombre")),
    ]))

    story.append(Paragraph("Diagnóstico", st["h2"]))
    story.append(Paragraph(_fmt(ctx.get("diagnostico")), st["cuerpo"]))
    story.append(Paragraph("Trabajo realizado", st["h2"]))
    story.append(Paragraph(_fmt(ctx.get("trabajo_realizado")), st["cuerpo"]))

    repuestos = ctx.get("repuestos") or []
    if repuestos:
        story.append(Paragraph("Repuestos utilizados", st["h2"]))
        data = [["Descripción", "Tipo", "Cant."]]
        data += [[r.get("descripcion", "—"), r.get("tipo", "—"), str(r.get("cantidad", 1))]
                 for r in repuestos]
        t = Table(data, colWidths=[110 * mm, 35 * mm, 20 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _HEAD_BG),
            ("LINEBELOW", (0, 0), (-1, 0), 0.75, _HAIRLINE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)

    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=0.75, color=_HAIRLINE, spaceAfter=8))
    story.append(_kv_table([
        ("Precio del servicio", ctx.get("precio_cobrado")),
        ("Saldo pendiente", ctx.get("saldo")),
    ]))

    story.append(Paragraph("Garantía del servicio", st["h2"]))
    story.append(Paragraph(
        f"{_fmt(ctx.get('garantia_cobertura'))} · Vigencia: "
        f"{_fmt(ctx.get('garantia_periodo_dias'))} días desde la entrega.",
        st["cuerpo"],
    ))
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "Documento generado por CRONOS. Conserve este comprobante para cualquier "
        "reclamo de garantía.", st["pie"],
    ))
    return _render(story)


def certificado_garantia(ctx: dict) -> bytes:
    """Certificado de garantía del servicio prestado."""
    st = _styles()
    story: list = []
    _encabezado(story, st, "Certificado de Garantía", ctx.get("numero", "—"))
    story.append(_kv_table([
        ("Cliente", ctx.get("cliente_nombre")),
        ("Unidad", f"{_fmt(ctx.get('reloj_marca'))} {_fmt(ctx.get('reloj_referencia'))}"),
        ("N.º de serie", ctx.get("reloj_serie")),
        ("Servicio realizado", ctx.get("trabajo_realizado")),
        ("Fecha de entrega", ctx.get("fecha_real_entrega")),
        ("Cobertura", ctx.get("garantia_cobertura")),
        ("Vigencia (días)", ctx.get("garantia_periodo_dias")),
        ("Válida hasta", ctx.get("garantia_hasta")),
    ]))
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "CRONOS garantiza la mano de obra y los repuestos instalados en este "
        "servicio durante el período indicado, en las condiciones de uso normales "
        "del instrumento. La garantía no cubre golpes, humedad por manipulación de "
        "terceros ni el desgaste natural de componentes.", st["cuerpo"],
    ))
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="60%", thickness=0.75, color=_INK, spaceAfter=4))
    story.append(Paragraph("Firma y sello · Servicio Técnico CRONOS", st["pie"]))
    return _render(story)


def factura_venta(ctx: dict) -> bytes:
    """Factura de venta de cara al cliente (§7), con el desglose reglamentario
    ecuatoriano: emisor (RUC, dirección, obligado a contabilidad), No. tipo SRI
    `EEE-PPP-NNNNNNNNN`, cliente e identificación, detalle con precio unitario sin
    impuesto y descuento por línea, y el bloque de totales (subtotales por tarifa,
    total descuento, IVA, valor total) + formas de pago. Sin autorización del SRI en
    esta fase. **Nunca** incluye costo ni margen (§FR-009)."""
    st = _styles()
    story: list = []
    em = ctx.get("emisor", {})
    tot = ctx.get("totales", {})
    cli = ctx.get("cliente", {})

    story.append(Paragraph("CRONOS · RELOJERÍA DE ALTA GAMA", st["eyebrow"]))
    story.append(Paragraph(em.get("nombre_comercial") or em.get("razon_social") or "Factura", st["titulo"]))
    story.append(Paragraph("FACTURA", st["cuerpo"]))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.2, color=_GOLD, spaceAfter=8))

    story.append(_kv_table([
        ("Razón social", em.get("razon_social")),
        ("RUC", em.get("ruc")),
        ("Dirección matriz", em.get("direccion_matriz")),
        ("Dirección establecimiento", em.get("direccion_establecimiento")),
        ("Obligado a llevar contabilidad", em.get("obligado_contabilidad")),
        ("Contribuyente especial", em.get("contribuyente_especial")),
        ("Régimen", em.get("regimen")),
    ]))
    story.append(Spacer(1, 6))
    story.append(_kv_table([
        ("Factura N.º", ctx.get("numero_factura")),
        ("Fecha de emisión", ctx.get("fecha")),
        ("Establecimiento", ctx.get("sucursal")),
        ("Atendió", ctx.get("vendedor")),
    ]))

    story.append(Paragraph("Cliente", st["h2"]))
    story.append(_kv_table([
        ("Razón social / Nombres", cli.get("nombre")),
        (f"Identificación ({cli.get('tipo_identificacion', '—')})", cli.get("identificacion")),
        ("Dirección", cli.get("direccion")),
        ("Teléfono", cli.get("telefono")),
        ("Correo", cli.get("email")),
    ]))

    story.append(Paragraph("Detalle", st["h2"]))
    data = [["Cód.", "Cant.", "Descripción", "P. unit.", "Desc.", "Subtotal"]]
    for d in ctx.get("detalle") or []:
        data.append([
            str(d.get("codigo", ""))[:14], str(d.get("cantidad", 1)),
            Paragraph(str(d.get("descripcion", "—")), st["cuerpo"]),
            _fmt(d.get("precio_unitario")), _fmt(d.get("descuento")), _fmt(d.get("precio_total")),
        ])
    t = Table(data, colWidths=[20 * mm, 12 * mm, 73 * mm, 22 * mm, 18 * mm, 22 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _HEAD_BG),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, _HAIRLINE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, _HAIRLINE),
    ]))
    story.append(t)

    story.append(Spacer(1, 8))
    iva_pct = _fmt(tot.get("iva_porcentaje"))
    tot_rows = [
        ("Subtotal 15%", tot.get("subtotal_15")),
        ("Subtotal 0%", tot.get("subtotal_0")),
        ("Subtotal no objeto de IVA", tot.get("subtotal_no_objeto")),
        ("Subtotal sin impuestos", tot.get("subtotal_sin_impuestos")),
        ("Total descuento", tot.get("total_descuento")),
        (f"IVA {iva_pct}%", tot.get("iva_monto")),
        ("Propina", tot.get("propina")),
        ("VALOR TOTAL", tot.get("valor_total")),
    ]
    tt = Table([[k, _fmt(v)] for k, v in tot_rows], colWidths=[55 * mm, 32 * mm], hAlign="RIGHT")
    tt.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.75, _INK),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(tt)

    fp = ctx.get("formas_pago") or []
    if fp:
        story.append(Paragraph("Formas de pago", st["h2"]))
        fpt = Table(
            [["Forma de pago", "Valor"]] + [[f.get("forma", "—"), _fmt(f.get("valor"))] for f in fp],
            colWidths=[110 * mm, 30 * mm],
        )
        fpt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _HEAD_BG),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(fpt)
        if _to_dec(ctx.get("saldo")) > 0:
            story.append(Paragraph(f"Saldo pendiente: {_fmt(ctx.get('saldo'))} (cuenta por cobrar).", st["cuerpo"]))

    gar = ctx.get("garantias") or []
    if gar:
        story.append(Paragraph("Garantías", st["h2"]))
        story.append(Paragraph(
            " · ".join(
                f"{'Fábrica' if g.get('tipo') == 'fabrica' else 'Tienda'}: {g.get('periodo_dias', 0)} días "
                f"(hasta {_fmt(g.get('fecha_fin'))})"
                for g in gar
            ),
            st["cuerpo"],
        ))

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        (em.get("leyenda_pie") or "")
        + "  Documento interno de CRONOS — sin autorización del SRI en esta fase. "
        + ("El consumidor final no tiene derecho a crédito tributario."
           if ctx.get("es_consumidor_final") else ""),
        st["pie"],
    ))
    return _render(story)


def _to_dec(v):
    try:
        return Decimal(str(v or 0))
    except Exception:  # noqa: BLE001
        return Decimal("0")


# Alias retrocompatible (009 lo importaba como `comprobante_venta`).
comprobante_venta = factura_venta


def certificado_garantia_autenticidad(ctx: dict) -> bytes:
    """Certificado de autenticidad y garantía de una unidad vendida, vinculado a su
    número de serie (Const. Ppio III, §2.3, §7)."""
    st = _styles()
    story: list = []
    _encabezado(story, st, "Certificado de Autenticidad y Garantía", ctx.get("numero", "—"))
    story.append(_kv_table([
        ("Cliente", ctx.get("cliente_nombre")),
        ("Unidad", f"{_fmt(ctx.get('reloj_marca'))} {_fmt(ctx.get('reloj_referencia'))}"),
        ("N.º de serie", ctx.get("reloj_serie")),
        ("Fecha de venta", ctx.get("fecha")),
    ]))
    story.append(Paragraph("Garantías", st["h2"]))
    data = [["Tipo", "Cobertura", "Vigencia", "Hasta"]]
    for g in ctx.get("garantias") or []:
        data.append([
            "Fábrica" if g.get("tipo") == "fabrica" else "Tienda",
            g.get("cobertura", "—"),
            f"{g.get('periodo_dias', 0)} días",
            _fmt(g.get("fecha_fin")),
        ])
    t = Table(data, colWidths=[22 * mm, 90 * mm, 25 * mm, 28 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _HEAD_BG),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, _HAIRLINE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "CRONOS certifica la autenticidad de la unidad identificada por su número de "
        "serie y respalda las garantías indicadas conforme a la Ley Orgánica de Defensa "
        "del Consumidor. La garantía de fábrica la atiende la marca; la garantía de "
        "tienda cubre la mano de obra del servicio propio.", st["cuerpo"],
    ))
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="60%", thickness=0.75, color=_INK, spaceAfter=4))
    story.append(Paragraph("Firma y sello · CRONOS Relojería", st["pie"]))
    return _render(story)


def guardar_comprobante(objeto: str, contenido: bytes) -> str:
    """Sube un PDF al bucket privado `comprobantes-venta` y devuelve su clave."""
    ensure_bucket(_BUCKET)
    put_object(_BUCKET, objeto, contenido, content_type="application/pdf")
    return objeto
