"""Repuebla las tablas transaccionales de CRONOS con datos de demostración realistas.

Se ejecuta contra la API real (localhost:8100) autenticado como Gerencia General
(que tiene acceso total por diseño — Constitución §3), para que TODA la lógica de
negocio real se aplique (stock, garantías, asientos automáticos, niveles de
fidelización, costeo, etc.) en vez de INSERTs crudos que podrían romper invariantes.

IMPORTANTE — correo: este script debe correr con EMAIL_BACKEND=console (nunca
sendgrid), porque genera decenas de eventos que disparan correo (ventas, OT,
ascensos de nivel, cupones, citas). Ver README de la sección "Seed de demo" o
simplemente:
    1. Edita .env -> EMAIL_BACKEND=console
    2. docker compose up -d --no-deps backend
    3. python scripts/seed_demo_data.py
    4. Cancela cualquier envio 'encolado' generado (ver script auxiliar)
    5. Edita .env -> EMAIL_BACKEND=sendgrid ; docker compose up -d --no-deps backend

Idempotencia: NO es idempotente. Pensado para correr una vez sobre una base con
poco dato. Cada operación de negocio está envuelta en try/except: un fallo puntual
se registra y el script continúa (mejor-esfuerzo), imprimiendo un resumen final.
"""

from __future__ import annotations

import sys
import json
import random

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import requests

BASE = "http://localhost:8100"
random.seed(20260911)

COUNTS: dict[str, int] = defaultdict(int)
ERRORS: list[tuple[str, str]] = []
CREATED: dict[str, list] = defaultdict(list)


def login(identificacion: str, password: str) -> str:
    r = requests.post(f"{BASE}/auth/login", json={"identificacion": identificacion, "password": password}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


TOKEN = login("1700000000", "changeme-gerencia")
HDRS = {"Authorization": f"Bearer {TOKEN}"}


def call(method: str, path: str, **kw):
    headers = kw.pop("headers", {})
    headers.update(HDRS)
    r = requests.request(method, f"{BASE}{path}", headers=headers, timeout=60, **kw)
    if r.status_code >= 400:
        raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text[:400]}")
    return r.json() if r.text else None


def safe(label: str, fn, *, quiet: bool = False):
    try:
        res = fn()
        COUNTS[label] += 1
        return res
    except Exception as exc:  # noqa: BLE001
        ERRORS.append((label, str(exc)))
        if not quiet:
            print(f"  ! {label}: {exc}")
        return None


def d(x) -> str:
    return str(Decimal(str(x)).quantize(Decimal("0.01")))


def rand_date(dias_atras_min: int, dias_atras_max: int) -> date:
    dias = random.randint(dias_atras_min, dias_atras_max)
    return date.today() - timedelta(days=dias)


# =================================================================== catálogos base
SUC_CENTRO = 5
SUC_BOUTIQUE = 6
SUCURSALES = [SUC_CENTRO, SUC_BOUTIQUE]

NOMBRES_M = ["Carlos", "Juan", "Luis", "Andrés", "Diego", "Pablo", "Santiago", "Mateo", "Fernando",
             "Ricardo", "Esteban", "Iván", "Javier", "Rodrigo", "Sebastián", "Xavier", "Marco", "Gustavo"]
NOMBRES_F = ["María", "Ana", "Gabriela", "Paola", "Verónica", "Cristina", "Daniela", "Fernanda",
             "Silvia", "Patricia", "Carolina", "Lucía", "Mónica", "Isabel", "Valentina", "Adriana"]
APELLIDOS = ["Rivadeneira", "Salazar", "Cevallos", "Andrade", "Cordero", "Vallejo", "Játiva", "Paredes",
             "Zambrano", "Merino", "Chávez", "Naranjo", "Bermeo", "Guerrero", "Villacís", "Espinoza",
             "Toapanta", "Yépez", "Moncayo", "Barragán", "Suárez", "Castillo", "Ortiz", "Pazmiño"]
EMPRESAS = ["Relojería del Valle", "Grupo Andino Comercial", "Inversiones del Pichincha",
            "Joyería Continental", "Comercial Quito Norte S.A.", "Corporación Sierra Nevada"]

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

PIEZAS_CATALOGO = [
    ("COR-STD-18", "Correa de cuero genérica 18mm", "no_original_equivalente", 25, 55, "unidad", None),
    ("COR-STD-20", "Correa de cuero genérica 20mm", "no_original_equivalente", 28, 60, "unidad", None),
    ("BRZ-ACE-OYS", "Brazalete de acero tipo Oyster", "no_original_equivalente", 120, 260, "unidad", "Rolex"),
    ("CRIS-ZAF-30", "Cristal de zafiro 30mm", "no_original_equivalente", 45, 110, "unidad", None),
    ("CRIS-ZAF-40", "Cristal de zafiro 40mm", "no_original_equivalente", 60, 140, "unidad", None),
    ("CRIS-HES-SPD", "Cristal hesalite Speedmaster", "original", 90, 210, "unidad", "Omega"),
    ("CORONA-STD", "Corona de rosca genérica", "no_original_equivalente", 18, 45, "unidad", None),
    ("CORONA-ROL", "Corona original Rolex Twinlock", "original", 140, 320, "unidad", "Rolex"),
    ("JUNTA-CORONA", "Junta de corona", "no_original_equivalente", 3, 12, "unidad", None),
    ("JUNTA-FONDO", "Junta de fondo (caja)", "no_original_equivalente", 4, 15, "unidad", None),
    ("RESORTE-BARR", "Resorte de barrilete genérico", "no_original_equivalente", 15, 40, "unidad", None),
    ("PILA-371", "Pila de reloj SR920SW", "no_original_equivalente", 2, 8, "unidad", None),
    ("PILA-377", "Pila de reloj SR626SW", "no_original_equivalente", 2, 8, "unidad", None),
    ("HEBILLA-DEP", "Hebilla desplegable de acero", "no_original_equivalente", 35, 90, "unidad", None),
    ("VIDRIO-MIN", "Cristal mineral estándar", "no_original_equivalente", 12, 30, "unidad", None),
    ("EJE-CORONA", "Eje de corona / tija", "no_original_equivalente", 8, 20, "unidad", None),
    ("9010", "Lubricante Moebius 9010 (Synt-A-Lube)", "original", 9, None, "ml", None),
    ("9104", "Lubricante Moebius 9104", "original", 10, None, "ml", None),
    ("HP-1300", "Lubricante Moebius HP-1300", "original", 14, None, "ml", None),
    ("9415", "Grasa Moebius 9415", "original", 11, None, "ml", None),
    ("9501", "Grasa Moebius 9501", "original", 10, None, "ml", None),
    ("9504", "Grasa Moebius 9504", "original", 12, None, "ml", None),
    ("8200", "Lubricante Moebius 8200", "original", 13, None, "ml", None),
    ("8217", "Lubricante Moebius 8217 (brake grease)", "original", 15, None, "ml", None),
    ("8513", "Grasa de juntas Moebius 8513", "original", 9, None, "ml", None),
    ("8516", "Grasa de juntas Moebius 8516 alta temp.", "original", 11, None, "ml", None),
]

CONDICIONES_PAGO_IDS = [1, 2, 3, 4, 5, 6]
MEDIOS_PAGO = ["efectivo", "transferencia", "cheque", "tarjeta"]


def main():
    print("== 0. catálogos previos ==")
    consentimiento = safe("consentimiento_texto", lambda: call("GET", "/clientes/texto-consentimiento"))
    version_consentimiento = 1
    if consentimiento:
        version_consentimiento = consentimiento.get("version") or consentimiento.get("version_texto") or 1

    categoria_gasto = call("GET", "/catalogos/categoria-gasto")
    categoria_merma = call("GET", "/catalogos/categoria-merma")
    cat_merma_por_causa: dict[str, list[int]] = defaultdict(list)
    for c in categoria_merma:
        cat_merma_por_causa[c["tipo"]].append(c["id"])
    cat_gasto_ids = [c["id"] for c in categoria_gasto]
    tecnicos_existentes = call("GET", "/tecnicos?size=50")

    # --------------------------------------------------------- beneficiarios
    print("== 1. beneficiarios ==")
    beneficiarios_seed = [
        ("EMAPA-Q Empresa de Agua Potable", None, "Agua potable"),
        ("CNT EP", None, "Telecomunicaciones"),
        ("Empresa Eléctrica Quito", None, "Energía eléctrica"),
        ("Arriendos Torres del Centro", "1791234567001", "Arriendo local"),
    ]
    beneficiario_ids = []
    for nombre, ident, tipo in beneficiarios_seed:
        res = safe("beneficiario", lambda n=nombre, i=ident, t=tipo: call(
            "POST", "/beneficiarios", json={"nombre": n, "identificacion": i, "tipo_servicio": t}))
        if res:
            beneficiario_ids.append(res["id"])

    # --------------------------------------------------------- clientes
    print("== 2. clientes ==")
    cliente_ids = [2, 3]  # ya existentes (natural + jurídica)
    usados_ident = {"1712345678", "1790012345001"}

    def nueva_cedula():
        while True:
            v = f"{random.randint(1, 24):02d}{random.randint(10000000, 99999999)}"
            if v not in usados_ident:
                usados_ident.add(v)
                return v

    for i in range(35):
        es_juridica = i % 9 == 0
        if es_juridica:
            nombre = random.choice(EMPRESAS) + f" {i}"
            ident = nueva_cedula()[:10] + "001"
            tipo = "juridica"
        else:
            es_f = random.random() < 0.5
            nombre = f"{random.choice(NOMBRES_F if es_f else NOMBRES_M)} {random.choice(APELLIDOS)} {random.choice(APELLIDOS)}"
            ident = nueva_cedula()
            tipo = "natural"
        payload = {
            "tipo": tipo, "identificacion": ident, "nombre": nombre,
            "telefono": f"09{random.randint(10000000, 99999999)}",
            "email": f"cliente{i}.{random.randint(100,999)}@example.com",
            "direccion": f"Av. {random.choice(['Amazonas','República','6 de Diciembre','González Suárez','Naciones Unidas'])} N{random.randint(10,60)}-{random.randint(10,99)}, Quito",
            "consentimiento": {"aceptado": True, "version_texto": version_consentimiento},
        }
        res = safe("cliente", lambda p=payload: call("POST", "/clientes", json=p))
        if res:
            cliente_ids.append(res["id"])
    print(f"  clientes totales disponibles: {len(cliente_ids)}")

    # --------------------------------------------------------- proveedores nuevos
    print("== 3. proveedores ==")
    proveedor_ids = [1, 2, 3]
    nuevos_proveedores = [
        ("Suizo Import Ecuador S.A.", "Suizo Import"),
        ("Time Masters Cía. Ltda.", "Time Masters"),
        ("Global Watch Parts Corp.", "Global Watch Parts"),
        ("Andina Relojes S.A.", "Andina Relojes"),
        ("Prestige Timepieces Trading", "Prestige Timepieces"),
    ]
    for razon, comercial in nuevos_proveedores:
        payload = {
            "razon_social": razon, "nombre_comercial": comercial,
            "contacto_nombre": f"{random.choice(NOMBRES_M+NOMBRES_F)} {random.choice(APELLIDOS)}",
            "telefono": f"02{random.randint(1000000,9999999)}",
            "email": f"contacto@{comercial.lower().replace(' ', '')}.com",
            "ruc_nit": nueva_cedula()[:10] + "001",
            "certificacion_autorizada": random.random() < 0.4,
            "condicion_pago_id": random.choice(CONDICIONES_PAGO_IDS),
            "plazo_entrega_dias": random.randint(5, 45),
        }
        res = safe("proveedor", lambda p=payload: call("POST", "/proveedores", json=p))
        if res:
            proveedor_ids.append(res["id"])

    # --------------------------------------------------------- piezas + stock
    print("== 4. piezas + stock ==")
    pieza_ids = [1, 2, 3, 4]  # existentes
    codigo_a_id = {}
    for codigo, desc, tipo, costo, precio, unidad, marca_comp in PIEZAS_CATALOGO:
        payload = {
            "codigo": codigo, "descripcion": desc, "tipo": tipo,
            "costo_adquisicion": costo, "precio_venta_suelta": precio,
            "stock_minimo": random.randint(2, 10), "unidad_medida": unidad,
            "marca_compatible": marca_comp, "proveedor_id": random.choice(proveedor_ids),
        }
        res = safe("pieza", lambda p=payload: call("POST", "/piezas", json=p))
        if res:
            pieza_ids.append(res["id"])
            codigo_a_id[codigo] = res["id"]
            for suc in SUCURSALES:
                cantidad = random.randint(15, 80) if unidad == "ml" else random.randint(5, 40)
                mov = {"sucursal_id": suc, "tipo": "ingreso", "cantidad": cantidad, "nota": "Stock inicial de demo"}
                safe("mov_pieza", lambda pid=res["id"], m=mov: call("POST", f"/piezas/{pid}/movimientos", json=m))

    # --------------------------------------------------------- relojes: venta + servicio
    print("== 5. relojes (inventario para venta) ==")
    relojes_venta = []
    for i in range(140):
        marca = random.choice(list(MARCAS_INFO.keys()))
        lo, hi = MARCAS_INFO[marca]
        precio = round(random.uniform(lo, hi), -1)
        costo = round(precio * random.uniform(0.55, 0.72), 2)
        serie = f"{marca[:3].upper()}-{random.randint(100000,999999)}"
        payload = {
            "numero_serie": serie, "marca": marca, "referencia": random.choice(REFERENCIAS[marca]),
            "anio_fabricacion": random.randint(2019, 2026),
            "material_caja": random.choice(MATERIALES_CAJA),
            "color_esfera": random.choice(COLORES_ESFERA),
            "tipo_cristal": "zafiro", "estado_producto": "nuevo",
            "costo_adquisicion": costo, "precio_venta": precio,
            "motivo_alta_manual": "Alta de inventario — reposición de stock de vitrina (demo)",
            "sucursal_actual_id": random.choice(SUCURSALES),
        }
        res = safe("reloj_venta", lambda p=payload: call(
            "POST", "/relojes", files={"data": (None, json.dumps(p))}))
        if res:
            relojes_venta.append(res)

    print("== 6. relojes (clientes — para servicio técnico) ==")
    relojes_ot = []
    for i in range(50):
        marca = random.choice(list(MARCAS_INFO.keys()))
        lo, hi = MARCAS_INFO[marca]
        serie = f"CLI-{marca[:3].upper()}-{random.randint(100000,999999)}"
        calibre_id = None
        if marca == "Omega":
            calibre_id = 1
        elif marca == "Rolex":
            calibre_id = 2
        payload = {
            "numero_serie": serie, "marca": marca, "referencia": random.choice(REFERENCIAS[marca]),
            "anio_fabricacion": random.randint(2012, 2025), "calibre_id": calibre_id,
            "material_caja": random.choice(MATERIALES_CAJA), "color_esfera": random.choice(COLORES_ESFERA),
            "estado_producto": "usado",
            # No es stock de venta (Const. — no se vende un reloj ajeno), pero igual
            # necesita un precio de referencia: nunca debe quedar "disponible" sin
            # precio (root cause de bug 2026-09-11: el vendedor terminaba inventando
            # uno en el formulario de venta).
            "precio_venta": round(random.uniform(lo, hi), -1),
            "motivo_alta_manual": "Unidad propiedad del cliente, ingresada para servicio técnico (demo)",
            "sucursal_actual_id": random.choice(SUCURSALES),
        }
        res = safe("reloj_ot", lambda p=payload: call(
            "POST", "/relojes", files={"data": (None, json.dumps(p))}))
        if res:
            relojes_ot.append(res)
    print(f"  relojes venta={len(relojes_venta)} relojes ot={len(relojes_ot)}")

    # --------------------------------------------------------- órdenes de compra + recepciones
    print("== 7. órdenes de compra ==")
    for i in range(10):
        prov = random.choice(proveedor_ids)
        suc = random.choice(SUCURSALES)
        n_lineas = random.randint(1, 3)
        lineas = []
        for _ in range(n_lineas):
            if random.random() < 0.5:
                marca = random.choice(list(MARCAS_INFO.keys()))
                lo, hi = MARCAS_INFO[marca]
                lineas.append({
                    "item_tipo": "reloj", "item_ref": random.choice(REFERENCIAS[marca]), "marca": marca,
                    "anio": random.randint(2024, 2026), "cantidad": random.randint(1, 2),
                    "costo_unitario": round(random.uniform(lo, hi) * 0.6, 2),
                })
            else:
                codigo, desc, *_ = random.choice(PIEZAS_CATALOGO)
                lineas.append({
                    "item_tipo": "pieza", "item_ref": codigo, "descripcion": desc,
                    "pieza_id": codigo_a_id.get(codigo), "cantidad": random.randint(5, 30),
                    "costo_unitario": round(random.uniform(5, 60), 2),
                })
        oc_payload = {
            "proveedor_id": prov, "sucursal_destino_id": suc,
            "fecha_pactada": str(rand_date(-20, 30)), "lineas": lineas,
            "urgente": random.random() < 0.15,
        }
        oc = safe("orden_compra", lambda p=oc_payload: call("POST", "/ordenes-compra", json=p))
        if not oc:
            continue
        oid = oc["id"]
        estado_final = random.choices(["borrador", "emitida", "confirmada", "recibida"], weights=[1, 2, 2, 5])[0]
        if estado_final == "borrador":
            continue
        if not safe("oc_emitir", lambda o=oid: call("POST", f"/ordenes-compra/{o}/emitir")):
            continue
        if estado_final == "emitida":
            continue
        if not safe("oc_confirmar", lambda o=oid: call("POST", f"/ordenes-compra/{o}/confirmar")):
            continue
        if estado_final in ("confirmada",):
            continue
        rec_lineas = []
        for ln in oc.get("lineas", []):
            rec_lineas.append({
                "linea_orden_compra_id": ln["id"], "cantidad_recibida": ln["cantidad"],
                "costo_unitario": ln.get("costo_unitario") or round(random.uniform(50, 5000), 2),
            })
        rec_payload = {"fecha_real": str(date.today()), "numero_factura": f"FAC-{random.randint(1000,9999)}",
                       "lineas": rec_lineas}
        safe("oc_recepcion", lambda o=oid, p=rec_payload: call("POST", f"/ordenes-compra/{o}/recepciones", json=p))
        safe("proveedor_calificacion", lambda p=prov: call(
            "POST", f"/proveedores/{p}/calificaciones",
            json={"nota_calidad": random.randint(3, 5), "comentario": "Entrega conforme (demo)"}), quiet=True)

    # --------------------------------------------------------- técnicos
    print("== 8. técnicos ==")
    tecnico_ids = {}
    if not tecnicos_existentes or tecnicos_existentes.get("total", 0) == 0:
        for usuario_id, nombre, especialidades, sueldo in [
            (14, "Tito Técnico", ["Omega", "Tudor"], 950),
            (15, "Jefe Técnico", ["Rolex", "Patek Philippe"], 1500),
        ]:
            payload = {"nombre": nombre, "usuario_id": usuario_id, "especialidades_nuevas": especialidades,
                       "sucursales": SUCURSALES}
            res = safe("tecnico", lambda p=payload: call("POST", "/tecnicos", json=p))
            if res:
                tecnico_ids[nombre] = res["id"]
                safe("tecnico_costo", lambda t=res["id"], s=sueldo: call(
                    "POST", f"/tecnicos/{t}/costo", json={"sueldo_mensual": s, "vigente_desde": "2026-01-01"}))
    else:
        for t in tecnicos_existentes.get("items", []):
            tecnico_ids[t["nombre"]] = t["id"]

    # --------------------------------------------------------- ficha de lubricación
    print("== 9. fichas de lubricación ==")
    for calibre_id, puntos_codigos in [
        (1, [("Barrilete", "8200"), ("Rueda de escape", "9010"), ("Áncora", "9415"), ("Corona/cuerda", "9501")]),
        (2, [("Barrilete", "8217"), ("Tren de rodaje", "9104"), ("Juntas de estanqueidad", "8513"),
             ("Calendario", "9504")]),
    ]:
        puntos = [{"nombre": n, "producto_moebius_codigo": c} for n, c in puntos_codigos]
        safe("ficha_lubricacion", lambda cid=calibre_id, p=puntos: call(
            "PUT", f"/calibres/{cid}/ficha-lubricacion",
            json={"notas_generales": "Ficha estándar de mantenimiento (demo)", "puntos": p}))

    # --------------------------------------------------------- regla de bono
    print("== 10. regla de bono ==")
    reglas = call("GET", "/reglas-bono")
    if not reglas or (isinstance(reglas, list) and len(reglas) == 0):
        safe("regla_bono", lambda: call("POST", "/reglas-bono", json={
            "nombre": "Regla estándar 2026", "periodicidad": "mensual", "vigente_desde": "2026-01-01",
            "componentes": [
                {"tipo": "monto_por_meta", "indicador": "ot_completadas", "umbral": 5, "valor": 40},
                {"tipo": "porcentaje_margen", "indicador": "margen_generado", "umbral": 0, "valor": 0.03},
                {"tipo": "monto_por_meta", "indicador": "cumplimiento_tiempos", "umbral": 0.8, "valor": 25},
            ],
        }))

    # --------------------------------------------------------- citas
    print("== 11. citas ==")
    canal_ids = [c["id"] for c in call("GET", "/catalogos/canal-cita")]
    cita_ids = []
    for i in range(55):
        cliente = random.choice(cliente_ids)
        suc = random.choice(SUCURSALES)
        motivo = random.choices(["compra", "servicio_tecnico", "consulta"], weights=[4, 4, 2])[0]
        dias = random.randint(-45, 15)
        fecha = datetime.now(timezone.utc) + timedelta(days=dias, hours=random.randint(-5, 5))
        payload = {
            "cliente_id": cliente, "sucursal_id": suc, "canal_cita_id": random.choice(canal_ids),
            "motivo": motivo, "fecha_preferida": fecha.isoformat(),
            "observaciones": "Cita generada por script de demo",
        }
        res = safe("cita", lambda p=payload: call("POST", "/citas", json=p))
        if not res:
            continue
        cid = res["id"]
        cita_ids.append(cid)
        roll = random.random()
        if roll < 0.15:
            safe("cita_cancelar", lambda c=cid: call(
                "POST", f"/citas/{c}/cancelar", json={"motivo": "El cliente reprogramó por otro canal"}), quiet=True)
            continue
        if not safe("cita_confirmar", lambda c=cid, f=fecha: call(
                "POST", f"/citas/{c}/confirmar", json={"fecha_confirmada": f.isoformat()}), quiet=True):
            continue
        if roll < 0.65 and dias <= 0:
            safe("cita_atender", lambda c=cid: call("POST", f"/citas/{c}/atender", json={}), quiet=True)

    # --------------------------------------------------------- ventas
    print("== 12. ventas ==")
    relojes_disponibles = list(relojes_venta)
    random.shuffle(relojes_disponibles)
    venta_ids = []
    cxc_pendientes = []
    for i in range(90):
        if not relojes_disponibles:
            break
        n_items = 1 if random.random() < 0.85 else 2
        items = [relojes_disponibles.pop() for _ in range(min(n_items, len(relojes_disponibles)))]
        if not items:
            break
        cliente = random.choice(cliente_ids)
        suc = items[0].get("sucursal_actual_id") or random.choice(SUCURSALES)
        payload = {
            "cliente_id": cliente, "sucursal_id": suc,
            "lineas": [{"item_tipo": "reloj", "reloj_id": r["id"]} for r in items],
        }
        venta = safe("venta_borrador", lambda p=payload: call("POST", "/ventas", json=p))
        if not venta:
            continue
        vid = venta["id"]
        total = Decimal(str(venta["total"]))
        roll = random.random()
        if roll < 0.6:
            medios = random.sample(MEDIOS_PAGO, k=1 if random.random() < 0.8 else 2)
            restante = total
            for j, medio in enumerate(medios):
                monto = restante if j == len(medios) - 1 else (restante * Decimal(random.choice(["0.4", "0.5", "0.6"]))).quantize(Decimal("0.01"))
                if monto <= 0:
                    continue
                safe("venta_pago", lambda v=vid, m=medio, mo=monto: call(
                    "POST", f"/ventas/{v}/pagos", json={"medio_pago": m, "monto": d(mo)}), quiet=True)
                restante -= monto
        elif roll < 0.85:
            parcial = (total * Decimal("0.4")).quantize(Decimal("0.01"))
            safe("venta_pago", lambda v=vid, mo=parcial: call(
                "POST", f"/ventas/{v}/pagos",
                json={"medio_pago": random.choice(MEDIOS_PAGO), "monto": d(mo)}), quiet=True)
        confirmada = safe("venta_confirmar", lambda v=vid: call(
            "POST", f"/ventas/{v}/confirmar", json={}))
        if confirmada:
            venta_ids.append(vid)
            if confirmada.get("saldo") and Decimal(str(confirmada["saldo"])) > 0:
                cxc_pendientes.append(vid)

    print(f"  ventas confirmadas: {len(venta_ids)}; con saldo pendiente: {len(cxc_pendientes)}")

    # unas pocas anulaciones (sobre ventas recién confirmadas y sin OT)
    for vid in random.sample(venta_ids, k=min(5, len(venta_ids))):
        safe("venta_anular", lambda v=vid: call(
            "POST", f"/ventas/{v}/anular", json={"motivo": "Cliente desistió de la compra (demo)"}), quiet=True)

    # --------------------------------------------------------- cobros sobre CxC abiertas
    print("== 13. cobros de CxC ==")
    cxcs = call("GET", "/cxc?estado=abierta&size=100") or call("GET", "/cxc-pendientes")
    lista_cxc = cxcs.get("items", cxcs) if isinstance(cxcs, dict) else (cxcs or [])
    for cxc in lista_cxc:
        if random.random() < 0.6:
            saldo = Decimal(str(cxc.get("saldo", 0)))
            if saldo <= 0:
                continue
            monto = saldo if random.random() < 0.5 else (saldo * Decimal("0.5")).quantize(Decimal("0.01"))
            safe("cxc_cobro", lambda cid=cxc["id"], mo=monto: call(
                "POST", f"/cxc/{cid}/cobros",
                json={"monto": d(mo), "medio_pago": random.choice(MEDIOS_PAGO)}), quiet=True)

    # --------------------------------------------------------- órdenes de trabajo
    print("== 14. órdenes de trabajo ==")
    tipos_reparacion = ["Mantenimiento general", "Cambio de pila", "Pulido y limpieza",
                        "Revisión de estanqueidad", "Cambio de correa", "Overhaul completo",
                        "Ajuste de precisión", "Cambio de cristal"]
    relojes_ot_pool = list(relojes_ot)
    random.shuffle(relojes_ot_pool)
    ot_ids_entregadas = []
    for i, reloj in enumerate(relojes_ot_pool):
        cliente = random.choice(cliente_ids)
        payload = {
            "numero_serie": reloj["numero_serie"], "cliente_id": cliente,
            "motivo": random.choice(["No mantiene la hora", "Se detuvo", "Ruido anormal en el movimiento",
                                     "Requiere mantenimiento preventivo", "Corona floja", "Entra humedad"]),
            "tipo_reparacion": random.choice(tipos_reparacion),
            "override_adquisicion_motivo": "Reloj propiedad del cliente, no adquirido en tienda (demo)",
        }
        ot = safe("ot_crear", lambda p=payload: call("POST", "/ordenes-trabajo", json=p))
        if not ot:
            continue
        oid = ot["id"]
        estado_objetivo = random.choices(
            ["en_diagnostico", "en_reparacion", "listo", "entregado", "entregado", "cancelada"],
            weights=[1, 2, 2, 4, 4, 1])[0]
        if estado_objetivo == "cancelada" and random.random() < 0.5:
            safe("ot_cancelar", lambda o=oid: call(
                "POST", f"/ordenes-trabajo/{o}/estado", json={"estado": "cancelada"}), quiet=True)
            continue

        safe("ot_diagnostico", lambda o=oid: call(
            "POST", f"/ordenes-trabajo/{o}/diagnostico",
            json={"diagnostico": "Se revisó el movimiento; requiere el trabajo indicado (demo)."}))
        if estado_objetivo == "en_diagnostico":
            continue

        piezas_presu = []
        if random.random() < 0.6:
            for _ in range(random.randint(1, 2)):
                pid = random.choice(pieza_ids)
                piezas_presu.append({"pieza_original_id": pid, "cantidad": 1})
        precio_servicio = round(random.uniform(35, 250), 2)
        presu = safe("ot_presupuesto", lambda o=oid, ps=precio_servicio, ln=piezas_presu: call(
            "POST", f"/ordenes-trabajo/{o}/presupuesto", json={"precio_servicio": ps, "lineas": ln}))
        if not presu:
            continue
        aprobado = safe("ot_aprobar", lambda o=oid: call(
            "POST", f"/ordenes-trabajo/{o}/presupuesto/aprobar",
            json={"confirmado_por": "Cliente (telefónico)", "medio_confirmacion": "telefono",
                  "preferencias": [], "fecha_estimada_entrega": str(rand_date(-10, 10) if False else date.today() + timedelta(days=random.randint(1, 10)))}))
        if not aprobado:
            continue
        if estado_objetivo == "cancelada":
            safe("ot_cancelar", lambda o=oid: call(
                "POST", f"/ordenes-trabajo/{o}/estado", json={"estado": "cancelada"}), quiet=True)
            continue

        # aprobar_presupuesto ya transiciona automáticamente a "en_reparacion".
        safe("ot_horas", lambda o=oid: call(
            "POST", f"/ordenes-trabajo/{o}/horas", json={"horas": round(random.uniform(0.5, 6), 1)}), quiet=True)
        for ln in piezas_presu:
            safe("ot_pieza_usada", lambda o=oid, pid=ln["pieza_original_id"]: call(
                "POST", f"/ordenes-trabajo/{o}/piezas", json={"pieza_id": pid, "tipo_elegido": "original"}), quiet=True)
        if reloj.get("calibre_id") and random.random() < 0.5:
            prod = random.choice(["9010", "9104", "9415", "8200", "8513", "9501"])
            safe("ot_lubricacion", lambda o=oid, pr=prod: call(
                "POST", f"/ordenes-trabajo/{o}/lubricacion", json={"producto_usado_codigo": pr}), quiet=True)
        safe("ot_trabajo", lambda o=oid: call(
            "POST", f"/ordenes-trabajo/{o}/trabajo",
            json={"trabajo_realizado": "Servicio realizado conforme al presupuesto aprobado (demo)."}), quiet=True)
        if estado_objetivo == "en_reparacion":
            continue

        safe("ot_listo", lambda o=oid: call("POST", f"/ordenes-trabajo/{o}/estado", json={"estado": "listo"}))
        if estado_objetivo == "listo":
            continue

        costeo = safe("ot_costeo", lambda o=oid: call("GET", f"/ordenes-trabajo/{o}/costeo"), quiet=True)
        if costeo:
            total_cobrar = Decimal(str(costeo.get("precio_cobrado") or costeo.get("precio_sugerido") or precio_servicio))
        else:
            total_cobrar = Decimal(str(precio_servicio))
        safe("ot_pago", lambda o=oid, mo=total_cobrar: call(
            "POST", f"/ordenes-trabajo/{o}/pagos",
            json={"medio_pago": random.choice(MEDIOS_PAGO), "monto": d(mo)}), quiet=True)
        entregada = safe("ot_entregar", lambda o=oid: call(
            "POST", f"/ordenes-trabajo/{o}/entregar", json={}))
        if entregada:
            ot_ids_entregadas.append(oid)

    print(f"  OT entregadas: {len(ot_ids_entregadas)}")

    # un par de reaperturas por garantía
    for oid in random.sample(ot_ids_entregadas, k=min(3, len(ot_ids_entregadas))):
        safe("ot_reabrir_garantia", lambda o=oid: call(
            "POST", f"/ordenes-trabajo/{o}/reabrir-garantia",
            json={"motivo": "El cliente reporta la misma falla (demo)"}), quiet=True)

    # --------------------------------------------------------- bonos
    print("== 15. cálculo de bonos ==")
    for nombre, tid in tecnico_ids.items():
        safe("bono_calcular", lambda t=tid: call("POST", "/bonos/calcular", json={"periodo_id": 1, "tecnico_id": t}),
             quiet=True)

    # --------------------------------------------------------- traslados
    print("== 16. traslados ==")
    relojes_para_traslado = call("GET", "/relojes?disponibilidad=disponible&size=100")
    pool_relojes = (relojes_para_traslado or {}).get("items", [])
    for i in range(20):
        origen, destino = (SUC_CENTRO, SUC_BOUTIQUE) if i % 2 == 0 else (SUC_BOUTIQUE, SUC_CENTRO)
        candidatos = [r for r in pool_relojes if r.get("sucursal_actual_id") == origen]
        lineas = []
        if candidatos and random.random() < 0.7:
            r = random.choice(candidatos)
            candidatos.remove(r)
            lineas.append({"item_tipo": "reloj", "reloj_id": r["id"], "cantidad_enviada": 1})
        else:
            pid = random.choice(pieza_ids)
            lineas.append({"item_tipo": "pieza", "pieza_id": pid, "cantidad_enviada": random.randint(1, 3)})
        payload = {
            "sucursal_origen_id": origen, "sucursal_destino_id": destino,
            "motivo": random.choice(["Reabastecimiento de vitrina", "Solicitud de cliente", "Balanceo de stock"]),
            "lineas": lineas, "enviar_ahora": True,
        }
        tr = safe("traslado", lambda p=payload: call("POST", "/transferencias", json=p))
        if not tr:
            continue
        tid_ = tr["id"]
        roll = random.random()
        if roll < 0.1:
            safe("traslado_cancelar", lambda t=tid_: call(
                "POST", f"/transferencias/{t}/cancelar", json={"motivo": "Ya no se requiere el traslado (demo)"}),
                quiet=True)
            continue
        det = safe("traslado_detalle", lambda t=tid_: call("GET", f"/transferencias/{t}"), quiet=True)
        if not det:
            continue
        rec_lineas = []
        for ln in det.get("lineas", []):
            cantidad = ln["cantidad_enviada"]
            if roll < 0.2:
                cantidad = max(0, cantidad - 1)
            rec_lineas.append({"linea_transferencia_id": ln["id"], "cantidad_recibida": cantidad})
        safe("traslado_recibir", lambda t=tid_, ln=rec_lineas: call(
            "POST", f"/transferencias/{t}/recibir", json={"lineas": ln}), quiet=True)

    # --------------------------------------------------------- mermas
    print("== 17. mermas ==")
    relojes_para_merma = call("GET", "/relojes?disponibilidad=disponible&size=100")
    pool_merma = (relojes_para_merma or {}).get("items", [])
    causas = ["dano_tienda", "dano_transito", "robo_perdida", "defecto_fabrica", "dano_servicio", "insumo_caducado"]
    for i in range(18):
        bien_tipo = "reloj" if random.random() < 0.6 and pool_merma else "pieza"
        causa = random.choice(causas)
        cat_id = random.choice(cat_merma_por_causa.get(causa, [None]))
        payload = {
            "bien_tipo": bien_tipo, "causa": causa, "categoria_merma_id": cat_id,
            "descripcion": "Incidente registrado por el equipo de sucursal (demo)",
            "fecha_evento": str(rand_date(0, 60)), "sucursal_id": random.choice(SUCURSALES),
        }
        if bien_tipo == "reloj" and pool_merma:
            r = random.choice(pool_merma)
            pool_merma.remove(r)
            payload["numero_serie"] = r["numero_serie"]
        else:
            payload["pieza_id"] = random.choice(pieza_ids)
            payload["cantidad"] = random.randint(1, 3)
        merma = safe("merma", lambda p=payload: call("POST", "/mermas", json=p))
        if not merma:
            continue
        mid = merma["id"]
        destino = random.choices(
            ["dado_de_baja", "reparado_reingresado", "en_reclamo_proveedor", "en_reclamo_seguro", None],
            weights=[3, 2, 1, 1, 2])[0]
        if destino is None:
            continue
        if destino == "dado_de_baja":
            costo = Decimal(str(merma.get("costo_perdida", 0) or 0))
            if costo > 200:
                safe("merma_autorizar", lambda m=mid: call(
                    "POST", f"/mermas/{m}/autorizar-baja", json={"observacion": "Autorizado por Gerencia (demo)"}),
                    quiet=True)
        safe("merma_estado", lambda m=mid, e=destino: call(
            "POST", f"/mermas/{m}/estado", json={"estado": e}), quiet=True)
        if destino in ("en_reclamo_proveedor", "en_reclamo_seguro"):
            safe("merma_reclamo", lambda m=mid: call(
                "POST", f"/mermas/{m}/reclamo",
                json={"numero_reclamo": f"RCL-{random.randint(1000,9999)}", "estado": "presentado"}), quiet=True)

    # --------------------------------------------------------- caja + gastos
    print("== 18. sesiones de caja y movimientos ==")
    for suc in SUCURSALES:
        for ciclo in range(6):
            saldo_inicial = round(random.uniform(50, 200), 2)
            sesion = safe("caja_abrir", lambda s=suc, si=saldo_inicial: call(
                "POST", f"/caja/{s}/sesiones?saldo_inicial={si}"))
            if not sesion:
                continue
            for _ in range(random.randint(1, 3)):
                tipo = random.choice(["entrada", "salida"])
                monto = round(random.uniform(10, 300), 2)
                safe("caja_movimiento", lambda s=suc, t=tipo, m=monto: call(
                    "POST", f"/caja/{s}/movimientos",
                    json={"tipo": t, "monto": m, "medio_pago": "efectivo", "nota": "Movimiento manual (demo)"}),
                    quiet=True)
            contado = round(saldo_inicial + random.uniform(-20, 250), 2)
            safe("caja_cerrar", lambda s=suc, c=max(contado, 0): call(
                "POST", f"/caja/{s}/sesiones/actual/cerrar", json={"efectivo_contado": c}))

    print("== 19. gastos ==")
    for i in range(70):
        cat_id = random.choice(cat_gasto_ids)
        cat = next((c for c in categoria_gasto if c["id"] == cat_id), None)
        tipo = (cat or {}).get("tipo", "otros")
        monto = {
            "local_operativos": random.uniform(50, 900), "personal": random.uniform(300, 2500),
            "otros": random.uniform(20, 500), "mermas_perdidas": random.uniform(50, 400),
        }.get(tipo, random.uniform(30, 400))
        estado_pago = random.choices(["pagado", "por_pagar"], weights=[6, 4])[0]
        datos = {
            "sucursal_id": random.choice(SUCURSALES), "categoria_gasto_id": cat_id,
            "monto": round(monto, 2), "fecha": str(rand_date(0, 75)),
            "descripcion": f"Gasto de {tipo.replace('_',' ')} — demo #{i}", "estado_pago": estado_pago,
        }
        if estado_pago == "pagado":
            datos["medio_pago"] = random.choice(MEDIOS_PAGO)
        else:
            if random.random() < 0.5 and proveedor_ids:
                datos["proveedor_id"] = random.choice(proveedor_ids)
            elif beneficiario_ids:
                datos["beneficiario_id"] = random.choice(beneficiario_ids)
            else:
                datos["estado_pago"] = "pagado"
                datos["medio_pago"] = "efectivo"
        gasto = safe("gasto", lambda p=datos: call(
            "POST", "/gastos", files={"data": (None, json.dumps(p))}))

    # --------------------------------------------------------- cxp: pagos parciales
    print("== 20. pagos de CxP ==")
    cxps = call("GET", "/cxp?estado=abierta&size=100") or call("GET", "/cxp/aging")
    lista_cxp = cxps.get("items", cxps) if isinstance(cxps, dict) else (cxps or [])
    for cxp in lista_cxp:
        if random.random() < 0.55:
            saldo = Decimal(str(cxp.get("saldo", 0)))
            if saldo <= 0:
                continue
            monto = saldo if random.random() < 0.5 else (saldo * Decimal("0.5")).quantize(Decimal("0.01"))
            safe("cxp_pago", lambda cid=cxp["id"], mo=monto: call(
                "POST", f"/cxp/{cid}/pagos",
                json={"monto": d(mo), "medio_pago": random.choice(MEDIOS_PAGO)}), quiet=True)

    # --------------------------------------------------------- gastos recurrentes (catálogo, sin correr scheduler)
    print("== 21. gastos recurrentes (catálogo) ==")
    for cat_id, frecuencia, monto in [
        (cat_gasto_ids[0], "mensual", 350), (cat_gasto_ids[min(9, len(cat_gasto_ids)-1)], "mensual", 900),
        (cat_gasto_ids[-1], "trimestral", 180),
    ]:
        safe("gasto_recurrente", lambda c=cat_id, f=frecuencia, m=monto: call(
            "POST", "/gastos-recurrentes", json={
                "sucursal_id": random.choice(SUCURSALES), "categoria_gasto_id": c, "monto": m,
                "frecuencia": f, "descripcion": "Gasto recurrente de demo", "dia_generacion": 1,
            }), quiet=True)

    # --------------------------------------------------------- resumen
    print("\n================ RESUMEN ================")
    for k in sorted(COUNTS):
        print(f"  {k}: {COUNTS[k]}")
    print(f"\n  errores: {len(ERRORS)}")
    por_label: dict[str, int] = defaultdict(int)
    for label, _ in ERRORS:
        por_label[label] += 1
    for label, n in sorted(por_label.items(), key=lambda x: -x[1]):
        print(f"    {label}: {n}")


if __name__ == "__main__":
    main()
