"""Feature 008 — capacidad compartida `shared/pagos` (reutilizada por 009).

Un pago es append-only; el saldo de un documento es `total − Σ pagos`.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
import sqlalchemy as sa

from shared.exceptions import ValidationError
from shared.pagos import pagado, pagos_de, registrar_pago, saldo


def _medio(db, clave="efectivo"):
    from shared.models import MedioPago

    return db.scalars(sa.select(MedioPago).where(MedioPago.clave == clave)).one()


def test_saldo_baja_con_cada_pago(db):
    m_ef = _medio(db, "efectivo")
    m_tj = _medio(db, "tarjeta")

    assert saldo(db, documento_tipo="orden_trabajo", documento_id=77, total=Decimal("500")) == Decimal("500.00")

    registrar_pago(db, documento_tipo="orden_trabajo", documento_id=77, medio_pago_id=m_ef.id,
                   monto=Decimal("300"), referencia="caja")
    registrar_pago(db, documento_tipo="orden_trabajo", documento_id=77, medio_pago_id=m_tj.id,
                   monto=Decimal("200"), referencia="POS 123")

    assert pagado(db, documento_tipo="orden_trabajo", documento_id=77) == Decimal("500.00")
    assert saldo(db, documento_tipo="orden_trabajo", documento_id=77, total=Decimal("500")) == Decimal("0.00")
    assert len(pagos_de(db, documento_tipo="orden_trabajo", documento_id=77)) == 2


def test_monto_no_positivo_y_tipo_invalido(db):
    m = _medio(db)
    with pytest.raises(ValidationError):
        registrar_pago(db, documento_tipo="orden_trabajo", documento_id=1, medio_pago_id=m.id, monto=Decimal("0"))
    with pytest.raises(ValidationError):
        registrar_pago(db, documento_tipo="factura_x", documento_id=1, medio_pago_id=m.id, monto=Decimal("10"))


def test_pago_es_append_only(db):
    m = _medio(db)
    p = registrar_pago(db, documento_tipo="orden_trabajo", documento_id=9, medio_pago_id=m.id, monto=Decimal("50"))
    with pytest.raises(Exception):
        db.execute(sa.text("UPDATE pago SET monto = 1 WHERE id = :i"), {"i": p.id})
        db.flush()
