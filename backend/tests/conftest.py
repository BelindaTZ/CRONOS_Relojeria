"""Fixtures compartidas de la suite del backend.

Los tests de la feature 001 necesitan PostgreSQL (guard RBAC, auditoría, etc.).
Se ejecutan dentro de `docker compose exec backend pytest`, donde DATABASE_URL
apunta al servicio `db`. Si no hay base, esos tests se omiten.
"""

from __future__ import annotations

import os

# Base de datos DEDICADA a los tests: aislada del esquema de desarrollo y de
# cualquier dato sembrado (seed_gerencia). Se deriva de DATABASE_URL cambiando el
# nombre de la base a `<db>_test` y se crea si no existe.
_base_url = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://cronos:changeme@localhost:5432/cronos"
)


def _derivar_test_db(url: str) -> str:
    if url.rsplit("/", 1)[-1].endswith("_test"):
        return url
    return url.rsplit("/", 1)[0] + "/" + url.rsplit("/", 1)[-1].split("?")[0] + "_test"


def _crear_db_si_falta(base_url: str, test_url: str) -> None:
    import sqlalchemy as sa

    nombre = test_url.rsplit("/", 1)[-1]
    admin = sa.create_engine(base_url.rsplit("/", 1)[0] + "/postgres", isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as c:
            existe = c.execute(
                sa.text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": nombre}
            ).scalar()
            if not existe:
                c.execute(sa.text(f'CREATE DATABASE "{nombre}"'))
    finally:
        admin.dispose()


_test_url = _derivar_test_db(_base_url)
try:
    _crear_db_si_falta(_base_url, _test_url)
    os.environ["DATABASE_URL"] = _test_url
except Exception:
    # sin DB disponible: los tests que la requieren se omiten igualmente
    os.environ.setdefault("DATABASE_URL", _base_url)

os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MINIO_ROOT_USER", "cronos")
os.environ.setdefault("MINIO_ROOT_PASSWORD", "changeme")
os.environ.setdefault("JWT_SECRET", "test-secret-key-con-al-menos-32-bytes-de-longitud")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
# Los tests NUNCA envían correo real: se fuerza el backend `console` aunque el
# entorno tenga configurado SendGrid/SMTP para la operación normal del sistema.
os.environ["EMAIL_BACKEND"] = "console"

import uuid  # noqa: E402

import pytest  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def _db_available() -> bool:
    try:
        eng = sa.create_engine(os.environ["DATABASE_URL"])
        with eng.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
        return True
    except Exception:
        return False


DB_OK = _db_available()
requires_db = pytest.mark.skipif(not DB_OK, reason="PostgreSQL no disponible")


@pytest.fixture(scope="session", autouse=True)
def _migrar():
    """Asegura el esquema al día antes de la suite (solo si hay DB)."""
    if not DB_OK:
        yield
        return
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    backend = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend / "alembic"))
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _limpiar_estado_proceso():
    if DB_OK:
        from shared.guard import invalidar_cache
        from shared import ratelimit

        invalidar_cache()
        ratelimit._intentos.clear()
        ratelimit._bloqueos.clear()
    yield


@pytest.fixture
def db():
    """Sesión aislada: cada test corre en una transacción que se revierte al final."""
    if not DB_OK:
        pytest.skip("PostgreSQL no disponible")
    from shared.database import engine

    conn = engine.connect()
    trans = conn.begin()
    from sqlalchemy.orm import Session

    session = Session(bind=conn, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        conn.close()


@pytest.fixture
def client(db):
    """TestClient con `get_db` apuntando a la sesión transaccional del test."""
    from fastapi.testclient import TestClient

    from main import create_app
    from shared.database import get_db

    def _override_db():
        yield db

    app = create_app()
    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_header():
    """Devuelve una función usuario -> {'Authorization': 'Bearer ...'}."""
    from shared.security import emitir_access_token

    def _h(usuario, scope: str = "full") -> dict:
        return {"Authorization": f"Bearer {emitir_access_token(usuario.id, scope=scope)}"}

    return _h


# --------------------------------------------------------------- helpers de datos
@pytest.fixture
def factory(db):
    from rbac import repository as rbac_repo
    from shared.models import (
        Modulo,
        Operacion,
        PermisoModulo,
        PermisoOperacion,
        Rol,
        Sucursal,
        Usuario,
        UsuarioRol,
        UsuarioSucursal,
    )
    from shared.security import hash_password

    class F:
        def rol(self, nombre: str | None = None) -> Rol:
            """Get-or-create: los roles de negocio reales (Vendedor, Técnico...) ya
            vienen sembrados por `0024_roles_negocio` — reutilizarlos en vez de
            chocar con el UNIQUE(nombre)."""
            nombre = nombre or f"rol-{uuid.uuid4().hex[:8]}"
            existente = db.scalars(sa.select(Rol).where(Rol.nombre == nombre)).first()
            if existente is not None:
                return existente
            r = Rol(nombre=nombre)
            db.add(r)
            db.flush()
            return r

        def permitir(self, rol: Rol, modulo_clave: str, operaciones: list[str] = ()):
            """Idempotente por la misma razón: un rol sembrado puede ya tener el
            módulo/operación concedidos."""
            m = db.scalars(sa.select(Modulo).where(Modulo.clave == modulo_clave)).one()
            if not db.scalars(
                sa.select(PermisoModulo).where(PermisoModulo.rol_id == rol.id, PermisoModulo.modulo_id == m.id)
            ).first():
                db.add(PermisoModulo(rol_id=rol.id, modulo_id=m.id))
                db.flush()
            for opc in operaciones:
                o = db.scalars(sa.select(Operacion).where(Operacion.clave == opc)).one()
                if not db.scalars(
                    sa.select(PermisoOperacion).where(
                        PermisoOperacion.rol_id == rol.id,
                        PermisoOperacion.modulo_id == m.id,
                        PermisoOperacion.operacion_id == o.id,
                    )
                ).first():
                    db.add(PermisoOperacion(rol_id=rol.id, modulo_id=m.id, operacion_id=o.id))
            db.flush()

        def usuario(
            self,
            *,
            roles: list[Rol] = (),
            sucursales: list[Sucursal] = (),
            password: str = "secreto-123",
            estado: str = "activo",
            must_change: bool = False,
        ) -> Usuario:
            u = Usuario(
                identificacion=f"ID{uuid.uuid4().hex[:12]}",
                nombre="Usuario Test",
                email=f"{uuid.uuid4().hex[:10]}@test.local",
                password_hash=hash_password(password),
                estado=estado,
                must_change_password=must_change,
            )
            db.add(u)
            db.flush()
            for r in roles:
                db.add(UsuarioRol(usuario_id=u.id, rol_id=r.id))
            for s in sucursales:
                db.add(UsuarioSucursal(usuario_id=u.id, sucursal_id=s.id))
            db.flush()
            return u

        def gerencia(self) -> Rol:
            existente = rbac_repo.rol_por_nombre(db, "Gerencia General")
            if existente:
                return existente
            r = Rol(nombre="Gerencia General")
            db.add(r)
            db.flush()
            for m in db.scalars(sa.select(Modulo)):
                db.add(PermisoModulo(rol_id=r.id, modulo_id=m.id))
                for o in db.scalars(sa.select(Operacion)):
                    db.add(PermisoOperacion(rol_id=r.id, modulo_id=m.id, operacion_id=o.id))
            db.flush()
            return r

        def sucursal(self, nombre: str | None = None) -> Sucursal:
            s = Sucursal(nombre=nombre or f"Suc {uuid.uuid4().hex[:6]}", estado="activa")
            db.add(s)
            db.flush()
            return s

        def current_user(self, usuario=None, *, elevado: bool = False, gerencia: bool = False):
            from shared.guard import CurrentUser

            roles: list[str] = []
            if gerencia:
                roles = ["Gerencia General"]
            elif elevado:
                roles = ["Gerente de Sucursal"]
            u = usuario or self.usuario()
            return CurrentUser(
                id=u.id, identificacion=u.identificacion, nombre=u.nombre, email=u.email,
                estado="activo", token_scope="full", roles=roles, rol_ids=[], sucursal_ids=[],
            )

    return F()


@pytest.fixture
def ot_fixture():
    """Feature 005: carga `fixtures/ordenes_trabajo.json` e instala un proveedor de
    OT en `tecnicos.service` (limpiándolo al terminar). `instalar({"t1": tecnico_id})`
    mapea los `tecnico_ref` del fixture a ids reales."""
    import json
    from datetime import date as _date
    from decimal import Decimal as _Dec
    from pathlib import Path

    data = json.loads((Path(__file__).parent / "fixtures" / "ordenes_trabajo.json").read_text("utf-8"))

    from tecnicos import service as _tec

    class Fix:
        periodo = data["periodo"]
        ordenes = data["ordenes"]

        def instalar(self, ref_a_id: dict[str, int]):
            _tec._PROVEEDOR_OT.clear()

            def _prov(db, inicio, fin, tecnico_id):
                out = []
                for o in data["ordenes"]:
                    tid = ref_a_id.get(o["tecnico_ref"])
                    if tid is None:
                        continue
                    fc = _date.fromisoformat(o["fecha_cierre"])
                    if fc < inicio or fc > fin:
                        continue
                    if tecnico_id is not None and tid != tecnico_id:
                        continue
                    out.append(_tec.OrdenTrabajoInfo(
                        orden_trabajo_id=o["orden_trabajo_id"], tecnico_id=tid, fecha_cierre=fc,
                        margen_real=_Dec(str(o["margen_real"])),
                        horas_registradas=o.get("horas_registradas"),
                        tipo_reparacion=o.get("tipo_reparacion"),
                        dentro_de_tiempo=o.get("dentro_de_tiempo", True),
                        es_reproceso=o.get("es_reproceso", False),
                    ))
                return out

            _tec.registrar_proveedor_ot(_prov)

    f = Fix()
    yield f
    _tec._PROVEEDOR_OT.clear()


@pytest.fixture
def tx_fixture():
    """Feature 006: carga `fixtures/transacciones_cliente.json` e instala un proveedor
    de transacciones en `clientes.service`. `instalar({"c_vip": cliente_id})` mapea
    los `cliente_ref` del fixture a ids reales."""
    import json
    from datetime import date as _date
    from decimal import Decimal as _Dec
    from pathlib import Path

    data = json.loads((Path(__file__).parent / "fixtures" / "transacciones_cliente.json").read_text("utf-8"))

    from clientes import service as _cli

    class Fix:
        transacciones = data["transacciones"]

        def instalar(self, ref_a_id: dict[str, int]):
            _cli._PROVEEDORES_TX.clear()

            def _prov(db, cliente_id):
                out = []
                for t in data["transacciones"]:
                    cid = ref_a_id.get(t["cliente_ref"])
                    if cid is None or cid != cliente_id:
                        continue
                    out.append(_cli.TransaccionCliente(
                        cliente_id=cid, fecha=_date.fromisoformat(t["fecha"]),
                        monto=_Dec(str(t["monto"])), tipo=t["tipo"],
                        documento_id=t.get("documento_id"), detalle=t.get("detalle"),
                        sucursal_id=t.get("sucursal_id"),
                    ))
                return out

            _cli.registrar_proveedor_transacciones(_prov)

    f = Fix()
    yield f
    _cli._PROVEEDORES_TX.clear()
