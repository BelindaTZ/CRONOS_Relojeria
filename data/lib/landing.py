"""Fase Load raw del flujo ELT (feature 012): escritura/lectura del raw en
`landing-zone` (MinIO). Objetos `<dominio>/<run_id>/<dominio>.ndjson` — raw sin
transformar, versionado por `run_id`, NUNCA fuente de negocio (Ppio III).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from minio.error import S3Error

from lib.db import landing_bucket, minio_client

logger = logging.getLogger("cronos.elt.landing")


def _object_key(dominio: str, run_id: str) -> str:
    return f"{dominio}/{run_id}/{dominio}.ndjson"


def subir(dominio: str, run_id: str, ruta_local: Path) -> str:
    """Sube el raw extraído a `landing-zone`. Devuelve la clave del objeto."""
    cliente = minio_client()
    bucket = landing_bucket()
    if not cliente.bucket_exists(bucket):
        raise RuntimeError(f"landing-zone (bucket '{bucket}') no existe — ¿corrió landing-zone-init?")
    key = _object_key(dominio, run_id)
    cliente.fput_object(bucket, key, str(ruta_local))
    logger.info("load_raw[%s] run_id=%s -> s3://%s/%s", dominio, run_id, bucket, key)
    return key


def descargar(dominio: str, run_id: str, ruta_local: Path) -> Path:
    """Descarga el raw de `landing-zone` para la fase Load warehouse (nunca se
    reutiliza el archivo local de `extract` directamente: el contrato ELT dice
    que `load_wh` lee de `landing-zone`, no del disco temporal del extract)."""
    cliente = minio_client()
    bucket = landing_bucket()
    key = _object_key(dominio, run_id)
    ruta_local.parent.mkdir(parents=True, exist_ok=True)
    cliente.fget_object(bucket, key, str(ruta_local))
    return ruta_local


def purgar_antiguos(dias_retencion: int) -> int:
    """Política de retención de `landing-zone` (Spec §FR-012): borra objetos con
    más de `dias_retencion` días. Devuelve cuántos objetos borró."""
    cliente = minio_client()
    bucket = landing_bucket()
    if not cliente.bucket_exists(bucket):
        return 0
    limite = datetime.now(timezone.utc) - timedelta(days=dias_retencion)
    borrados = 0
    for obj in cliente.list_objects(bucket, recursive=True):
        if obj.last_modified and obj.last_modified < limite:
            try:
                cliente.remove_object(bucket, obj.object_name)
                borrados += 1
            except S3Error as exc:  # no bloquea el resto de la limpieza
                logger.warning("No se pudo borrar %s: %s", obj.object_name, exc)
    logger.info("Retención landing-zone: %d objeto(s) borrados (> %d días)", borrados, dias_retencion)
    return borrados
