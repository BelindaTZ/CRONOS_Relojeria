"""Acceso a datos compartido: engine, sesión y `Base` declarativa.

Ningún módulo de negocio crea su propio engine; todos importan desde aquí
(Constitución, Principio X).
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from shared.config import get_settings

_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Base declarativa común a todos los modelos ORM del proyecto."""


def get_db() -> Iterator[Session]:
    """Dependencia FastAPI: entrega una sesión, confirma al terminar bien y
    revierte si el handler lanzó una excepción."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
