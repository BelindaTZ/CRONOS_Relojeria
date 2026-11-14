"""Cliente MinIO compartido y helpers de bucket.

La capacidad de almacenamiento de objetos vive aquí (Constitución, Principio III y X):
los módulos de negocio suben/recuperan archivos a través de estos helpers, sin crear
su propio cliente.

URLs de cara al navegador: el cliente interno habla con `minio:9000` (hostname de
Docker), que el navegador NO resuelve. Para servir un objeto a la app se usa
`minio_browser_endpoint` (`localhost:9100` en dev):
- bucket público  → URL directa `http(s)://<endpoint>/<bucket>/<key>` (descarga anónima).
- bucket privado   → URL firmada generada contra ese mismo endpoint público.
"""

from __future__ import annotations

import io
from datetime import timedelta
from functools import lru_cache
from urllib.parse import quote

from minio import Minio

from shared.config import get_settings


@lru_cache
def get_client() -> Minio:
    """Cliente MinIO interno (contenedor ↔ contenedor)."""
    s = get_settings()
    return Minio(
        s.minio_endpoint,
        access_key=s.minio_root_user,
        secret_key=s.minio_root_password,
        secure=s.minio_secure,
        region="us-east-1",
    )


@lru_cache
def _get_public_client() -> Minio:
    """Cliente ligado al endpoint que resuelve el navegador — solo para FIRMAR URLs.

    `region` fijo es obligatorio aquí: sin él, el SDK de minio intenta
    autodetectar la región llamando en vivo a `minio_browser_endpoint`
    (`localhost:9100` en dev) para pedir la ubicación del bucket — y ese
    endpoint solo es alcanzable desde el navegador del usuario, NUNCA desde
    dentro de este contenedor (su `localhost` es el propio contenedor, no el
    host). Sin `region`, cualquier URL firmada (bucket privado, p. ej.
    `comprobantes-venta`) revienta con 500 (bug encontrado 2026-09-11: el
    botón "Factura (PDF)" no abría nada)."""
    s = get_settings()
    return Minio(
        s.minio_browser_endpoint,
        access_key=s.minio_root_user,
        secret_key=s.minio_root_password,
        secure=s.minio_public_scheme == "https",
        region="us-east-1",
    )


def ensure_bucket(name: str) -> None:
    """Crea el bucket si no existe (operación idempotente)."""
    client = get_client()
    if not client.bucket_exists(name):
        client.make_bucket(name)


def put_object(bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    """Sube un objeto a `bucket/key`."""
    client = get_client()
    client.put_object(bucket, key, io.BytesIO(data), length=len(data), content_type=content_type)


def get_object_bytes(bucket: str, key: str) -> bytes:
    """Recupera el contenido de un objeto (uso interno del backend)."""
    client = get_client()
    response = client.get_object(bucket, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def get_object_url(bucket: str, key: str, expires: timedelta = timedelta(hours=12)) -> str:
    """URL que el navegador puede abrir para recuperar un objeto.

    Bucket público → URL directa (sin firma). Bucket privado → URL firmada
    generada contra el endpoint público."""
    s = get_settings()
    if bucket in s.minio_public_buckets:
        return f"{s.minio_public_scheme}://{s.minio_browser_endpoint}/{bucket}/{quote(key)}"
    return _get_public_client().presigned_get_object(bucket, key, expires=expires)
