"""Agrega más unidades de reloj al inventario de venta sobre una base ya sembrada,
sin tocar clientes/proveedores/ventas (para no duplicar nada ni disparar correos).

Uso: python scripts/add_relojes_venta.py [cantidad]
"""
from __future__ import annotations

import json
import random
import sys
import urllib.error
import urllib.request

BASE = "http://localhost:8100"
CANTIDAD = int(sys.argv[1]) if len(sys.argv) > 1 else 140
SUCURSALES = [5, 6]

MARCAS_INFO = {
    "Rolex": (9000, 26000), "Tudor": (2800, 6500), "Omega": (4000, 12500),
    "Patek Philippe": (32000, 130000), "Cartier": (5500, 22000), "IWC Schaffhausen": (6000, 24000),
    "Breitling": (4500, 13000), "Longines": (1800, 4500), "TAG Heuer": (2200, 6000),
    "Jaeger-LeCoultre": (7000, 30000), "Audemars Piguet": (28000, 95000),
    "Vacheron Constantin": (25000, 120000), "Panerai": (7500, 22000), "Zenith": (6500, 18000),
    "Hublot": (9000, 35000), "Breguet": (18000, 70000), "Piaget": (12000, 45000),
    "Chopard": (8000, 30000), "Grand Seiko": (4500, 14000), "Oris": (1800, 4800),
}
REFERENCIAS = {
    "Rolex": ["Datejust 41", "Submariner Date", "Daytona", "GMT-Master II", "Explorer II", "Sky-Dweller"],
    "Tudor": ["Black Bay 58", "Black Bay GMT", "Pelagos", "Royal"],
    "Omega": ["Speedmaster Professional", "Seamaster Diver 300M", "Constellation", "De Ville"],
    "Patek Philippe": ["5711/1A", "Calatrava 5227", "Aquanaut 5167", "Nautilus 5712"],
    "Cartier": ["Santos de Cartier", "Tank Must", "Ballon Bleu", "Panthère"],
    "IWC Schaffhausen": ["Portugieser Chrono", "Pilot's Watch Mark XX", "Aquatimer"],
    "Breitling": ["Navitimer B01", "Superocean Automatic", "Chronomat"],
    "Longines": ["HydroConquest", "Master Collection", "Spirit"],
    "TAG Heuer": ["Carrera Calibre 16", "Aquaracer Professional", "Monaco"],
    "Jaeger-LeCoultre": ["Reverso Classic", "Master Control", "Polaris"],
    "Audemars Piguet": ["Royal Oak", "Royal Oak Offshore", "Code 11.59"],
    "Vacheron Constantin": ["Overseas", "Patrimony", "Traditionnelle"],
    "Panerai": ["Luminor Marina", "Radiomir", "Submersible"],
    "Zenith": ["Chronomaster Sport", "Defy Skyline", "Elite Classic"],
    "Hublot": ["Big Bang", "Classic Fusion", "Spirit of Big Bang"],
    "Breguet": ["Classique", "Marine", "Tradition"],
    "Piaget": ["Polo", "Altiplano", "Limelight Gala"],
    "Chopard": ["Happy Sport", "Alpine Eagle", "L.U.C"],
    "Grand Seiko": ["Snowflake", "Heritage Spring Drive", "Evolution 9"],
    "Oris": ["Aquis Date", "Big Crown Pointer Date", "Artelier"],
}
MATERIALES_CAJA = ["Acero", "Oro rosa 18k", "Oro amarillo 18k", "Titanio", "Platino", "Acero y oro"]
COLORES_ESFERA = ["Negro", "Verde oliva", "Azul sunburst", "Plata opalina", "Champagne", "Blanco perlado"]

random.seed()


def _request(method: str, url: str, data: bytes, headers: dict) -> dict | None:
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read()
        raise RuntimeError(f"{method} {url} -> {exc.code}: {body[:400].decode('utf-8', 'replace')}") from None
    return json.loads(body) if body else None


def login(identificacion: str, password: str) -> str:
    payload = json.dumps({"identificacion": identificacion, "password": password}).encode("utf-8")
    res = _request("POST", f"{BASE}/auth/login", payload, {"Content-Type": "application/json"})
    return res["access_token"]


TOKEN = login("1700000000", "changeme-gerencia")
HDRS = {"Authorization": f"Bearer {TOKEN}"}


def call(method: str, path: str, json_payload: dict | None = None, multipart_data: dict | None = None):
    headers = dict(HDRS)
    if multipart_data is not None:
        boundary = "----cronosBoundary7d8f3a"
        parts = []
        for name, value in multipart_data.items():
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n")
        parts.append(f"--{boundary}--\r\n")
        body = "".join(parts).encode("utf-8")
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    else:
        body = json.dumps(json_payload if json_payload is not None else {}).encode("utf-8")
        headers["Content-Type"] = "application/json"
    return _request(method, f"{BASE}{path}", body, headers)


def main():
    creados = 0
    errores: list[str] = []
    for i in range(CANTIDAD):
        marca = random.choice(list(MARCAS_INFO.keys()))
        lo, hi = MARCAS_INFO[marca]
        precio = round(random.uniform(lo, hi), -1)
        costo = round(precio * random.uniform(0.55, 0.72), 2)
        serie = f"{marca[:3].upper()}-{random.randint(100000, 999999)}"
        payload = {
            "numero_serie": serie, "marca": marca, "referencia": random.choice(REFERENCIAS[marca]),
            "anio_fabricacion": random.randint(2019, 2026),
            "material_caja": random.choice(MATERIALES_CAJA),
            "color_esfera": random.choice(COLORES_ESFERA),
            "tipo_cristal": "zafiro", "estado_producto": "nuevo",
            "costo_adquisicion": costo, "precio_venta": precio,
            "motivo_alta_manual": "Alta de inventario — ampliación de catálogo de vitrina",
            "sucursal_actual_id": random.choice(SUCURSALES),
        }
        try:
            call("POST", "/relojes", multipart_data={"data": json.dumps(payload)})
            creados += 1
        except Exception as exc:  # noqa: BLE001
            errores.append(str(exc))

    print(f"relojes creados: {creados}")
    print(f"errores: {len(errores)}")
    for e in errores[:10]:
        print(f"  ! {e}")


if __name__ == "__main__":
    main()
