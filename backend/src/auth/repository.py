from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.models import RefreshToken, SolicitudRestablecimiento, Usuario


def usuario_por_identificacion(db: Session, ident: str) -> Usuario | None:
    return db.scalars(select(Usuario).where(Usuario.identificacion == ident)).first()


def crear_refresh(db: Session, *, usuario_id: int, token_hash: str, expira_en: datetime) -> None:
    db.add(RefreshToken(usuario_id=usuario_id, token_hash=token_hash, expira_en=expira_en))
    db.flush()


def refresh_vigente(db: Session, token_hash: str) -> RefreshToken | None:
    row = db.scalars(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).first()
    if row is None or row.revocado_en is not None:
        return None
    if row.expira_en <= datetime.now(timezone.utc):
        return None
    return row


def revocar_refresh(db: Session, token_hash: str) -> None:
    row = db.scalars(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).first()
    if row and row.revocado_en is None:
        row.revocado_en = datetime.now(timezone.utc)
        db.flush()


def revocar_todos_refresh(db: Session, usuario_id: int) -> None:
    for row in db.scalars(
        select(RefreshToken).where(
            RefreshToken.usuario_id == usuario_id, RefreshToken.revocado_en.is_(None)
        )
    ):
        row.revocado_en = datetime.now(timezone.utc)
    db.flush()


def crear_solicitud(db: Session, *, usuario_id: int, hash_: str, expira_en: datetime) -> None:
    db.add(
        SolicitudRestablecimiento(
            usuario_id=usuario_id, password_temporal_hash=hash_, expira_en=expira_en
        )
    )
    db.flush()


def solicitud_vigente(db: Session, usuario_id: int) -> SolicitudRestablecimiento | None:
    row = db.scalars(
        select(SolicitudRestablecimiento)
        .where(
            SolicitudRestablecimiento.usuario_id == usuario_id,
            SolicitudRestablecimiento.usada.is_(False),
        )
        .order_by(SolicitudRestablecimiento.creado_en.desc())
    ).first()
    if row is None or row.expira_en <= datetime.now(timezone.utc):
        return None
    return row
