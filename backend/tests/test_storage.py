"""Buckets MinIO (US5 / FR-019, FR-020).

- `shared.storage` sube y recupera un objeto en cada bucket de cara a la app.
- El acceso anónimo a un bucket privado falla.
- `landing-zone` NO lo provisiona `shared.storage`/000 — lo crea el job aparte
  `landing-zone-init` de la feature 012 (puede o no existir ya en el MinIO vivo
  del entorno, según si 012 corrió; lo que este test fija es que el backend
  nunca lo incluye en su propia lista de buckets).

Requiere MinIO accesible; si no, se omite (CI lo corre dentro de docker compose).
"""

from __future__ import annotations

import urllib.error
import urllib.request

import pytest

from shared.config import get_settings
from shared.storage import ensure_bucket, get_client, get_object_bytes, put_object


def _minio_available() -> bool:
    try:
        list(get_client().list_buckets())
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _minio_available(), reason="MinIO no disponible")

PUBLIC = ("reloj-imagenes", "perfil-usuarios")
PRIVATE = ("comprobantes-venta", "documentos")


@pytest.mark.parametrize("bucket", PUBLIC + PRIVATE)
def test_roundtrip_de_objeto_en_cada_bucket(bucket):
    ensure_bucket(bucket)
    key = "pruebas/roundtrip.txt"
    payload = b"cronos-000"

    put_object(bucket, key, payload, content_type="text/plain")
    assert get_object_bytes(bucket, key) == payload

    get_client().remove_object(bucket, key)


@pytest.mark.parametrize("bucket", PRIVATE)
def test_acceso_anonimo_denegado_en_buckets_privados(bucket):
    s = get_settings()
    scheme = "https" if s.minio_secure else "http"
    url = f"{scheme}://{s.minio_endpoint}/{bucket}/no-existe"

    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(url, timeout=5)  # noqa: S310
    assert exc.value.code in (401, 403)


def test_landing_zone_no_la_provisiona_shared_storage():
    """`landing-zone` (012) es responsabilidad del job `landing-zone-init`, no de
    `shared.storage`/000 — el backend nunca la incluye en su propia lista de
    buckets (puede existir igual en el MinIO vivo si 012 ya corrió; eso no es
    lo que este test verifica)."""
    assert "landing-zone" not in get_settings().minio_buckets
