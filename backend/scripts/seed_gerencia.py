"""Crea el rol 'Gerencia General' (con acceso total a la matriz) y un usuario
inicial de Gerencia General a partir de `.env`. Idempotente.

Uso:  docker compose exec backend python -m scripts.seed_gerencia

Variables `.env`:
  SEED_GERENCIA_IDENTIFICACION, SEED_GERENCIA_NOMBRE,
  SEED_GERENCIA_EMAIL, SEED_GERENCIA_PASSWORD
"""

from __future__ import annotations

import sys

from sqlalchemy import select

from shared.config import get_settings
from shared.database import SessionLocal
from shared.models import (
    Modulo,
    Operacion,
    PermisoModulo,
    PermisoOperacion,
    Rol,
    Usuario,
    UsuarioRol,
)
from shared.security import hash_password

ROL = "Gerencia General"


def main() -> int:
    s = get_settings()
    if not (s.seed_gerencia_identificacion and s.seed_gerencia_email and s.seed_gerencia_password):
        print("Faltan SEED_GERENCIA_* en .env — nada que sembrar.", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        rol = db.scalars(select(Rol).where(Rol.nombre == ROL)).first()
        if rol is None:
            rol = Rol(nombre=ROL, descripcion="Acceso total. No se puede dejar sin titulares activos.")
            db.add(rol)
            db.flush()
            print(f"Rol '{ROL}' creado (id={rol.id}).")

        # matriz completa: todos los módulos + todas las operaciones
        modulos = list(db.scalars(select(Modulo)))
        operaciones = list(db.scalars(select(Operacion)))
        pm_existentes = {
            r for r in db.scalars(select(PermisoModulo.modulo_id).where(PermisoModulo.rol_id == rol.id))
        }
        po_existentes = {
            (r.modulo_id, r.operacion_id)
            for r in db.execute(
                select(PermisoOperacion.modulo_id, PermisoOperacion.operacion_id).where(
                    PermisoOperacion.rol_id == rol.id
                )
            )
        }
        for m in modulos:
            if m.id not in pm_existentes:
                db.add(PermisoModulo(rol_id=rol.id, modulo_id=m.id))
            for o in operaciones:
                if (m.id, o.id) not in po_existentes:
                    db.add(PermisoOperacion(rol_id=rol.id, modulo_id=m.id, operacion_id=o.id))
        db.flush()

        usuario = db.scalars(
            select(Usuario).where(Usuario.identificacion == s.seed_gerencia_identificacion)
        ).first()
        if usuario is None:
            usuario = Usuario(
                identificacion=s.seed_gerencia_identificacion,
                nombre=s.seed_gerencia_nombre,
                email=s.seed_gerencia_email,
                password_hash=hash_password(s.seed_gerencia_password),
                estado="activo",
                must_change_password=False,
            )
            db.add(usuario)
            db.flush()
            print(f"Usuario Gerencia General creado (id={usuario.id}, {usuario.identificacion}).")
        else:
            print(f"Usuario {usuario.identificacion} ya existe (id={usuario.id}).")

        if not db.scalars(
            select(UsuarioRol).where(
                UsuarioRol.usuario_id == usuario.id, UsuarioRol.rol_id == rol.id
            )
        ).first():
            db.add(UsuarioRol(usuario_id=usuario.id, rol_id=rol.id))

        db.commit()
        print("Semilla de Gerencia General aplicada.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
