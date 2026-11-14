"""Inactivación de sucursal (US5): sin motivo -> 422; con motivo -> estado + N correos + auditoría."""

from __future__ import annotations

import sqlalchemy as sa

from shared.models import RegistroAuditoria
from sucursales import service
from sucursales.schemas import SucursalIn


def test_sin_motivo_falla_validacion(db, factory):
    import pytest

    from shared.exceptions import ValidationError

    s = factory.sucursal()
    with pytest.raises(ValidationError):
        service.inactivar(db, s.id, motivo="   ", actor=1)


def test_con_motivo_inactiva_notifica_y_audita(db, factory, monkeypatch):
    enviados: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "sucursales.service.enviar",
        lambda plantilla, a, ctx: enviados.append((plantilla, a)),
    )
    g = factory.gerencia()
    s = factory.sucursal("Cumbayá")
    u1 = factory.usuario(roles=[g], sucursales=[s])
    u2 = factory.usuario(sucursales=[s])

    out = service.inactivar(db, s.id, motivo="cierre temporal por remodelación", actor=u1.id)
    assert out.estado == "inactiva"
    assert out.motivo_inactivacion.startswith("cierre temporal")

    destinatarios = {a for _, a in enviados}
    assert {u1.email, u2.email} <= destinatarios
    assert all(p == "inactivacion_sucursal" for p, _ in enviados)

    aud = db.scalars(
        sa.select(RegistroAuditoria).where(
            RegistroAuditoria.entidad == "sucursal", RegistroAuditoria.accion == "inactivar"
        )
    ).all()
    assert aud and aud[-1].despues["avisos_enviados"] == 2
