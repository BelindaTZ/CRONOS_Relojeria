from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.guard import CurrentUser, get_current_user_full_scope, require_perm
from shared.pagination import PageParams, page_params
from shared.schemas import Page
from tecnicos import service
from tecnicos.costeo import costo_mo_ot as _costo_mo_ot
from tecnicos.schemas import (
    BonoOut,
    CalcularBonoIn,
    CostoIn,
    CostoMoOtIn,
    CostoMoOtOut,
    CostoOut,
    EspecialidadOut,
    EstadoIn,
    PeriodoIn,
    PeriodoOut,
    ProductividadOut,
    ReglaBonoIn,
    ReglaBonoOut,
    TecnicoIn,
    TecnicoOut,
    TecnicoPatch,
)

router = APIRouter(tags=["tecnicos"])

_leer = require_perm("tecnicos", "consultar")
_crear = require_perm("tecnicos", "crear")
_editar = require_perm("tecnicos", "editar")


# --------------------------------------------------------------------- técnicos
@router.get("/tecnicos", response_model=Page[TecnicoOut])
def listar(
    q: str | None = None,
    especialidad: str | None = None,
    sucursal_id: int | None = None,
    pp: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(_leer),
):
    items, total = service.listar(
        db, user=user, q=q, especialidad=especialidad, sucursal_id=sucursal_id,
        offset=pp.offset, limit=pp.limit,
    )
    return Page(items=items, total=total, page=pp.page, size=pp.size)


@router.get("/tecnicos/especialidades", response_model=list[EspecialidadOut])
def especialidades(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.listar_especialidades(db)


@router.post("/tecnicos/especialidades", response_model=EspecialidadOut, status_code=status.HTTP_201_CREATED)
def crear_especialidad(nombre: str, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear_especialidad(db, nombre, actor=user.id)


@router.post("/tecnicos", response_model=TecnicoOut, status_code=status.HTTP_201_CREATED)
def crear(datos: TecnicoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear(db, datos, actor=user.id)


@router.get("/tecnicos/{tid}", response_model=TecnicoOut)
def detalle(tid: int, db: Session = Depends(get_db), user: CurrentUser = Depends(_leer)):
    return service.obtener_detalle(db, tid, user=user)


@router.patch("/tecnicos/{tid}", response_model=TecnicoOut)
def actualizar(tid: int, datos: TecnicoPatch, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.actualizar(db, tid, datos, user=user)


@router.put("/tecnicos/{tid}/estado", response_model=TecnicoOut)
def set_estado(tid: int, datos: EstadoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.set_estado(db, tid, datos.estado, user=user)


@router.post("/tecnicos/{tid}/costo", response_model=CostoOut, status_code=status.HTTP_201_CREATED)
def set_costo(tid: int, datos: CostoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.set_costo(db, tid, datos, user=user)


# ---------------------------------------------------------------- reglas de bono
@router.get("/reglas-bono", response_model=list[ReglaBonoOut])
def listar_reglas(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.listar_reglas(db)


@router.post("/reglas-bono", response_model=ReglaBonoOut, status_code=status.HTTP_201_CREATED)
def crear_regla(datos: ReglaBonoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear_regla(db, datos, actor=user.id)


# --------------------------------------------------------- periodos + bonos
@router.get("/periodos-liquidacion", response_model=list[PeriodoOut])
def listar_periodos(db: Session = Depends(get_db), _: CurrentUser = Depends(_leer)):
    return service.listar_periodos(db)


@router.post("/periodos-liquidacion", response_model=PeriodoOut, status_code=status.HTTP_201_CREATED)
def crear_periodo(datos: PeriodoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_crear)):
    return service.crear_periodo(db, datos, actor=user.id)


@router.post("/periodos-liquidacion/{pid}/cerrar", response_model=PeriodoOut)
def cerrar_periodo(pid: int, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.cerrar_periodo(db, pid, actor=user.id)


@router.post("/bonos/calcular", response_model=list[BonoOut])
def calcular_bono(datos: CalcularBonoIn, db: Session = Depends(get_db), user: CurrentUser = Depends(_editar)):
    return service.calcular_bono(db, periodo_id=datos.periodo_id, tecnico_id=datos.tecnico_id)


@router.get("/bonos", response_model=list[BonoOut])
def listar_bonos(
    periodo_id: int | None = None,
    tecnico_id: int | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_leer),
):
    return service.listar_bonos(db, periodo_id=periodo_id, tecnico_id=tecnico_id)


@router.get("/productividad", response_model=list[ProductividadOut])
def productividad(
    periodo_id: int,
    tecnico_id: int | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_leer),
):
    return service.productividad(db, periodo_id=periodo_id, tecnico_id=tecnico_id)


# --------------------------------------------------------------- interno (008)
internal_router = APIRouter(prefix="/_internal", tags=["_internal"])


@internal_router.post("/costeo/costo-mo-ot", response_model=CostoMoOtOut)
def costo_mo_ot(
    datos: CostoMoOtIn,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user_full_scope),
):
    """Contrato interno consumido por 008 para el costo de mano de obra de una OT."""
    r = _costo_mo_ot(db, tecnico_id=datos.tecnico_id, horas=datos.horas, tipo_reparacion=datos.tipo_reparacion)
    return CostoMoOtOut(costo_mo=r.costo_mo, tarifa_hora=r.tarifa_hora, horas=r.horas, base=r.base)
